---
id: framework-django-example-request-context-middleware
title: Django Request Context Middleware Example
description: Example middleware that attaches a domain-scoped request context for reuse across views and serializers.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - middleware
applies_to:
  - django
status: active
order: 13
---

# Django Request Context Middleware Example

## Scenario

- Use this pattern when many authenticated API views need the same request-owned domain context, such as organization access, workspace access, current employee, current member, or contact portal identity.
- Use this pattern when context resolution depends on `request.user` and should be available to views, scope helpers, bootstrap endpoints, and serializers without each view repeating the same membership queries.
- Use this pattern when route handlers must stay explicit about the organization, workspace, catalog_entry, contact, order, or other owned-resource boundary while still sharing one access contract.
- Use the CRUD view and shared scope validation examples for endpoint-specific view and serializer details; this example is the north-star for attaching and consuming request-scoped context.

## Why This Shape Exists

- Access context is a request boundary. It belongs on the request once, near authentication, so every downstream view talks about the same user, membership, organization, and workspace state.
- Repeated ad hoc lookups make ownership rules easy to drift. If five views each fetch a membership differently, reviewers have to prove five security boundaries instead of one shared contract.
- Middleware should attach the context, not choose feature scope. The view still resolves route-owned IDs explicitly at the top of the handler so organization and workspace boundaries stay visible.
- Lazy request context keeps anonymous-safe and public endpoints cheap. Routes that never inspect access context should not pay membership query cost just because middleware ran.
- Missing or inaccessible context should fail through framework paths. Required authenticated views use DRF authentication; inaccessible organization or workspace routes resolve through scoped querysets and return hidden-resource `404`; insufficient permissions raise `PermissionDenied`; serializers read required context directly instead of inventing fallback scope.
- Serializer context should be prepared once from the request context when output fields need membership-specific data. Serializers should not re-query organization or workspace memberships row by row.

## Recommended Shape

### Middleware Stack Placement

```python
# backend/core/settings/base.py

MIDDLEWARE = [
	'django.middleware.security.SecurityMiddleware',
	'django.contrib.sessions.middleware.SessionMiddleware',
	'corsheaders.middleware.CorsMiddleware',
	'django.middleware.common.CommonMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'core.access.middleware.AccessContextMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

Place request-context middleware after Django authentication middleware so `request.user` is already available. Keep it before view dispatch and before any middleware that might rely on the same context.

### Middleware Attaches The Context Only

```python
# backend/core/access/middleware.py

from core.access.context import AccessContext
from django.utils.functional import SimpleLazyObject


class AccessContextMiddleware:
	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		request.access_context = SimpleLazyObject(lambda: AccessContext(request))
		return self.get_response(request)
```

The middleware has one responsibility: add the request-scoped context object. It does not fetch an organization, pick a workspace, catch missing memberships, or write feature-specific attributes such as `request.current_catalog_entry`.

`SimpleLazyObject` delays construction until a view, serializer context helper, or bootstrap endpoint actually needs access data. This keeps the request contract available everywhere without forcing every request to run membership queries.

### Access Context Owns Shared Membership Queries

```python
# backend/core/access/context.py

from workspace.models import Workspace, WorkspaceMembership
from core.access.policy import get_workspace_permissions, get_organization_permissions
from rest_framework.exceptions import PermissionDenied
from tenancy.models import Organization, OrganizationMembership


class AccessContext:
	def __init__(self, request):
		self.request = request
		self._organization_membership_by_organization_id = {}
		self._workspace_membership_by_workspace_id = {}

	@staticmethod
	def get_membership_context(memberships):
		return {
			'membership_by_organization_id': {membership.organization_id: membership for membership in memberships},
		}

	@staticmethod
	def get_workspace_membership_context(memberships):
		return {
			'membership_by_workspace_id': {membership.workspace_id: membership for membership in memberships},
		}

	def is_authenticated(self):
		return self.request.user.is_authenticated

	def has_platform_access(self):
		return self.is_authenticated() and self.request.user.is_superuser

	def get_accessible_organization_queryset(self):
		queryset = Organization.objects.filter(status=Organization.StatusChoices.ACTIVE).order_by('id')
		if self.has_platform_access():
			return queryset

		if not self.is_authenticated():
			return queryset.none()

		return queryset.filter(memberships__user=self.request.user, memberships__is_active=True).distinct()

	def get_memberships_for_organizations(self, organizations):
		if self.has_platform_access() or not self.is_authenticated():
			return []

		organization_ids = [organization.id for organization in organizations]
		if not organization_ids:
			return []

		memberships = list(
			OrganizationMembership.objects.filter(
				user=self.request.user,
				is_active=True,
				organization_id__in=organization_ids,
			).select_related('organization').order_by('organization_id'),
		)
		for membership in memberships:
			self._organization_membership_by_organization_id[membership.organization_id] = membership

		return memberships

	def get_organization_membership(self, organization):
		if self.has_platform_access():
			return None

		membership = self._organization_membership_by_organization_id.get(organization.id)
		if membership is None:
			membership = OrganizationMembership.objects.filter(user=self.request.user, organization=organization, is_active=True).first()
			self._organization_membership_by_organization_id[organization.id] = membership

		if not membership:
			raise PermissionDenied('You do not have access to this organization.')

		return membership

	def get_accessible_workspace_queryset(self, organization):
		queryset = Workspace.objects.filter(organization=organization).order_by('id')
		if self.has_platform_access():
			return queryset

		membership = self.get_organization_membership(organization)
		if membership.role == membership.RoleChoices.ADMIN:
			return queryset

		return queryset.filter(memberships__user=self.request.user, memberships__is_active=True).distinct()

	def get_workspace_memberships_for_workspaces(self, workspaces):
		if self.has_platform_access() or not self.is_authenticated():
			return []

		workspace_ids = [workspace.id for workspace in workspaces]
		if not workspace_ids:
			return []

		memberships = list(
			WorkspaceMembership.objects.filter(
				user=self.request.user,
				is_active=True,
				workspace_id__in=workspace_ids,
			).select_related('workspace').order_by('workspace_id'),
		)
		for membership in memberships:
			self._workspace_membership_by_workspace_id[membership.workspace_id] = membership

		return memberships

	def can(self, permission, organization=None, workspace=None):
		if not self.is_authenticated():
			return False

		if self.has_platform_access():
			return True

		if workspace is not None:
			organization_membership = self.get_organization_membership(workspace.organization)
			if permission in get_organization_permissions(organization_membership):
				return True

			workspace_membership = self._workspace_membership_by_workspace_id.get(workspace.id)
			if workspace_membership is None:
				workspace_membership = WorkspaceMembership.objects.filter(user=self.request.user, workspace=workspace, is_active=True).first()
				self._workspace_membership_by_workspace_id[workspace.id] = workspace_membership

			return bool(workspace_membership and permission in get_workspace_permissions(workspace_membership))

		if organization is not None:
			return permission in get_organization_permissions(self.get_organization_membership(organization))

		return False

	def require(self, permission, organization=None, workspace=None):
		if self.can(permission, organization=organization, workspace=workspace):
			return

		raise PermissionDenied('You do not have permission to access this resource.')
```

Keep the context focused on access state that is repeatedly needed across routes: accessible organization querysets, accessible workspace querysets, membership maps, permission checks, and bootstrap payload data. Caches are request-local and keyed by stable IDs, so one request can reuse membership work without leaking state between users.

Do not turn the context into a feature query service. Item lists, survey form builders, order filters, and workflow-specific queryset shaping belong in the owning view, model, or service after the route scope has been resolved.

### Access Views Expose A Narrow Contract

```python
# backend/common/access/base_views.py

from common.access.context import AccessContext
from common.access.scopes import get_workspace_scope, get_organization_scope
from common.base_views import AuthenticatedAPIView, BaseAPIView
from rest_framework.authentication import SessionAuthentication


class AccessContextMixin:
	def get_access_context(self, request):
		return request.access_context

	def get_accessible_organization_queryset(self, request):
		return self.get_access_context(request).get_accessible_organization_queryset()

	def get_accessible_workspace_queryset(self, request, organization):
		return self.get_access_context(request).get_accessible_workspace_queryset(organization)

	def get_memberships_for_organizations(self, request, organizations):
		return self.get_access_context(request).get_memberships_for_organizations(organizations)

	def get_workspace_memberships_for_workspaces(self, request, workspaces):
		return self.get_access_context(request).get_workspace_memberships_for_workspaces(workspaces)

	def get_membership_context(self, memberships):
		return AccessContext.get_membership_context(memberships)

	def get_workspace_membership_context(self, memberships):
		return AccessContext.get_workspace_membership_context(memberships)

	def require_permission(self, request, permission, organization=None, workspace=None):
		self.get_access_context(request).require(permission, organization=organization, workspace=workspace)

	def build_access_payload(self, request, organizations):
		return self.get_access_context(request).build_access_payload(organizations)

	def resolve_organization_scope(self, request, organization_id: int):
		return get_organization_scope(self.get_access_context(request), organization_id)

	def resolve_workspace_scope(self, request, organization_id: int, workspace_id: int):
		return get_workspace_scope(self.get_access_context(request), organization_id, workspace_id)

	def get_organization_serializer_context(self, request, organizations):
		memberships = self.get_memberships_for_organizations(request, organizations)
		return self.get_membership_context(memberships) | {'request': request}

	def get_workspace_serializer_context(self, request, workspaces):
		memberships = self.get_workspace_memberships_for_workspaces(request, workspaces)
		return self.get_workspace_membership_context(memberships) | {'request': request}


class AccessAPIView(AccessContextMixin, BaseAPIView):
	authentication_classes = (SessionAuthentication,)


class AuthenticatedAccessAPIView(AccessContextMixin, AuthenticatedAPIView):
	pass
```

Feature views should depend on the mixin methods, not on the context internals. This keeps most code reading like `resolve_workspace_scope(...)`, `get_accessible_workspace_queryset(...)`, `require_permission(...)`, and `get_workspace_serializer_context(...)` instead of manually building membership queries.

If the middleware is missing, `request.access_context` should fail loudly. Do not add fallback construction in every view; fix `MIDDLEWARE` so the request contract is consistent.

### Scope Helpers Own Hidden-Resource Behavior

```python
# backend/core/access/scopes.py

from django.shortcuts import get_object_or_404


def get_organization_scope(access_context, organization_id: int):
	queryset = access_context.get_accessible_organization_queryset()
	return get_object_or_404(queryset, pk=organization_id)


def get_workspace_scope(access_context, organization_id: int, workspace_id: int):
	organization = get_organization_scope(access_context, organization_id)
	queryset = access_context.get_accessible_workspace_queryset(organization)
	workspace = get_object_or_404(queryset, pk=workspace_id)
	return organization, workspace
```

Route-owned organization and workspace IDs are resolved against access-filtered querysets. Inaccessible records return `404` through `get_object_or_404(...)`, which avoids leaking whether another organization's or another workspace's resource exists.

Add one focused scope helper when several views share the same nested resource path. Keep the helper about ownership and object resolution only; feature-specific filters still belong in the feature view.

### Views Resolve Scope Up Front

```python
# backend/workspace/views/workspace/views.py

from workspace.views.workspace.serializers import WorkspaceInputSerializer, WorkspaceOutputSerializer
from common.access.base_views import AuthenticatedAccessAPIView
from common.permissions import AppPermission, AppPermissionChoices
from rest_framework import status
from rest_framework.response import Response


class WorkspaceListView(AuthenticatedAccessAPIView):
	def get(self, request, organization_id: int):
		organization = self.resolve_organization_scope(request, organization_id)
		queryset = list(self.get_accessible_workspace_queryset(request, organization))
		context = self.get_workspace_serializer_context(request, queryset)
		serializer = WorkspaceOutputSerializer(queryset, many=True, context=context)
		return Response(serializer.data, status=status.HTTP_200_OK)


class WorkspaceCreateView(AuthenticatedAccessAPIView):
	def post(self, request, organization_id: int):
		organization = self.resolve_organization_scope(request, organization_id)
		self.require_permission(request, AppPermission.permission(AppPermissionChoices.ORGANIZATION_WORKSPACES_CREATE), organization=organization)

		serializer = WorkspaceInputSerializer(data=self.build_serializer_data(request, organization=organization.id))
		serializer.is_valid(raise_exception=True)

		instance = serializer.save()
		context = self.get_workspace_serializer_context(request, [instance])
		return Response(WorkspaceOutputSerializer(instance, context=context).data, status=status.HTTP_201_CREATED)
```

The first meaningful line resolves the route-owned organization. The view then uses the shared context to fetch accessible workspaces, check permissions, and build serializer context. The view still owns HTTP flow, protected payload fields, output serialization, and response status.

Do not replace this with direct re-lookups such as `OrganizationMembership.objects.get(user=request.user, organization_id=organization_id)` inside every view. That repeats security-sensitive logic and bypasses request-local caching.

### Serializers Consume Prepared Context

```python
# backend/workspace/views/workspace/serializers.py

from workspace.models import Workspace
from rest_framework import serializers


class WorkspaceOutputSerializer(serializers.ModelSerializer):
	membership_role = serializers.SerializerMethodField()

	class Meta:
		model = Workspace
		fields = (
			'id',
			'organization',
			'name',
			'slug',
			'status',
			'contact_name',
			'contact_email',
			'support_phone',
			'membership_role',
			'created_ts',
			'updated_ts',
		)
		read_only_fields = fields

	def get_membership_role(self, obj):
		membership_by_workspace_id = self.context.get('membership_by_workspace_id', {})
		membership = membership_by_workspace_id.get(obj.id)
		if membership:
			return membership.role

		return None
```

Output serializers can read prepared context maps for display-only data such as membership role. They should not perform one membership lookup per object. The view or base access helper prepares `membership_by_workspace_id` from the request context, then the serializer reads by object ID.

For write serializers that require a route-owned object, pass the resolved object in `context` or inject the route-owned ID with `build_serializer_data(...)`. Access validation stays explicit at the view or serializer boundary; it does not happen by guessing from request headers, payload fields, or global state.

### Bootstrap Reuses The Same Context

```python
# backend/core/views/user_state/views.py

from common.access.base_views import AccessAPIView
from core.views.user_state.serializers import AppBootstrapOutputSerializer
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.response import Response


@method_decorator(ensure_csrf_cookie, name='dispatch')
class AppBootstrapView(AccessAPIView):
	def get(self, request):
		user = request.user if request.user.is_authenticated else None
		organizations = []
		memberships = []
		workspaces = []

		if request.user.is_authenticated:
			organizations = list(self.get_accessible_organization_queryset(request))
			memberships = self.get_memberships_for_organizations(request, organizations)
			selected_organization = organizations[0] if len(organizations) == 1 else None
			if selected_organization is not None:
				workspaces = list(self.get_accessible_workspace_queryset(request, selected_organization))

		workspace_memberships = self.get_workspace_memberships_for_workspaces(request, workspaces)
		context = self.get_membership_context(memberships) | self.get_workspace_membership_context(workspace_memberships) | {'request': request}
		serializer = AppBootstrapOutputSerializer(
			{
				'access': self.build_access_payload(request, organizations),
				'workspaces': workspaces,
				'is_authenticated': request.user.is_authenticated,
				'user': user,
				'organizations': organizations,
			},
			context=context,
		)
		return Response(serializer.data, status=status.HTTP_200_OK)
```

Bootstrap endpoints are allowed to use `AccessAPIView` because they must be anonymous-safe while still returning access context for authenticated users. Anonymous requests get empty access data from the same context contract; authenticated requests get organizations, workspaces, membership roles, and permission payloads without route-local duplication.

### Tests Cover The Contract

```python
# backend/core/tests/test_access_middleware.py

import pytest
from core.access.context import AccessContext
from tests.fixtures import FixtureFactory
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestAccessContextMiddleware:
	def test_middleware_attaches_access_context_to_request_contract(self, client):
		user = FixtureFactory.create_user(email='access-context@example.com')
		client.force_login(user)

		response = client.get(reverse('user-bootstrap'))

		assert response.status_code == status.HTTP_200_OK
		assert response.wsgi_request.access_context.__class__ is AccessContext
```

```python
# backend/core/tests/test_access_scopes.py

import pytest
from core.access.context import AccessContext
from core.access.scopes import get_workspace_scope, get_organization_scope
from django.http import Http404
from rest_framework.test import APIRequestFactory


@pytest.mark.django_db
class TestAccessScopes:
	def build_access_context(self, user):
		request = self.factory.get('/api/test/')
		request.user = user
		return AccessContext(request)

	def test_get_organization_scope_raises_404_for_inaccessible_organization(self):
		access_context = self.build_access_context(self.outsider)

		with pytest.raises(Http404):
			get_organization_scope(access_context, self.organization.id)

	def test_get_workspace_scope_raises_404_for_unassigned_workspace_in_same_organization(self):
		access_context = self.build_access_context(self.workspace_operator)

		with pytest.raises(Http404):
			get_workspace_scope(access_context, self.organization.id, self.other_workspace.id)
```

```python
# backend/core/tests/test_user_state_views.py

def test_unauthenticated_user_gets_empty_bootstrap(self, client):
	response = client.get(reverse('user-bootstrap'))

	assert response.status_code == status.HTTP_200_OK
	assert 'csrftoken' in response.cookies
	assert response.json() == {
		'access': {
			'workspace_permissions': {},
			'permissions': [],
			'organization_permissions': {},
		},
		'workspaces': [],
		'is_authenticated': False,
		'current_workspace_id': None,
		'current_organization_id': None,
		'stripe_public_key': '',
		'organizations': [],
		'user': None,
	}
```

Test the middleware contract directly, test scope helpers without going through every route, test anonymous and authenticated bootstrap behavior, and test feature views for permission and ownership boundaries. This layered coverage proves the request context exists, behaves correctly, and is used by HTTP endpoints.

## Things To Notice

- Middleware resolves the repeated context once and makes it part of the request contract.
- `SimpleLazyObject` means the context is available on every request but only evaluated when accessed.
- The context stores request-local membership caches. It does not store global state and does not survive across requests.
- Access views expose narrow methods so feature views do not reach into `request.access_context` internals.
- Scope helpers return `404` for inaccessible organization or workspace records by resolving against access-filtered querysets.
- Views still resolve route scope explicitly at the top of each handler. Middleware does not hide which organization, workspace, catalog_entry, or order the route is using.
- Serializers consume prepared context maps for output-only membership data instead of issuing per-row access queries.
- Anonymous-safe views use the same context contract but return empty access data; authenticated views should rely on DRF authentication before they require domain context.
- Missing middleware should be treated as a configuration error, not patched around with per-view fallback construction.

## Rules To Follow

- Attach repeated request-owned domain or access context once in middleware after `AuthenticationMiddleware`.
- Keep middleware limited to assigning the request attribute. Do not query feature resources, select a current organization, perform permission checks, or catch access failures there.
- Make the request attribute name explicit and stable, such as `request.access_context`, `request.employee`, or `request.member`.
- Use lazy construction when context may be unused by anonymous-safe, public, static, or health-check routes.
- Put shared membership, access, and permission methods on the context object or a focused access helper, not in every view.
- Keep route-owned scope resolution visible at the top of each view handler with `resolve_organization_scope(...)`, `resolve_workspace_scope(...)`, or a more specific shared scope helper.
- Use `get_object_or_404(...)` on already-access-filtered querysets for owned resources that should be hidden when inaccessible.
- Raise `PermissionDenied` for authenticated users who can see the scope but lack the requested action permission.
- Pass prepared membership or request context into serializers. Do not let serializers independently re-fetch the same user membership for every object.
- Inject route-owned IDs with `build_serializer_data(...)` or pass resolved objects through serializer context. Do not let payload fields choose organization, workspace, or parent scope.
- Add direct tests for middleware attachment, access-scope helpers, bootstrap context, and representative feature views.

## Refactor Signals

- Multiple views repeat `OrganizationMembership.objects...`, `WorkspaceMembership.objects...`, `Employee.objects...`, or `Member.objects...` lookups based on `request.user`.
- A view starts from `Organization.objects.get(...)`, `Workspace.objects.get(...)`, or a leaf model primary key before proving the object is accessible to the request.
- Middleware catches missing membership and returns `None` for context that authenticated views later require.
- Views check `if request.employee is None` or `if not request.member` in many places instead of using DRF authentication, scoped querysets, or a single access helper.
- Serializers perform access or membership queries inside `SerializerMethodField` for every row.
- Feature-specific queryset builders, workflow state, or mutation rules are being added to a global access context.
- Bootstrap, list, and detail endpoints each compute accessible organizations or workspaces through different query shapes.
- Tests only prove the happy path and do not cover inaccessible organization, inaccessible workspace, anonymous bootstrap, or missing-permission behavior.
- A view constructs a new `AccessContext(request)` manually because the middleware contract is missing or unreliable.

## Verification

- For middleware changes, run the focused middleware test:

```bash
pytest backend/core/tests/test_access_middleware.py::TestAccessContextMiddleware
```

- For access-scope changes, run the focused scope tests:

```bash
pytest backend/core/tests/test_access_scopes.py::TestAccessScopes
```

- For bootstrap changes, run the focused bootstrap tests:

```bash
pytest backend/core/tests/test_user_state_views.py::TestAppBootstrapView
```

- For feature views that consume request context, run the relevant view test class and include positive, permission-negative, and ownership-boundary cases.
- Run `ruff check` on modified Python files when implementation code changes.
- For guidance-only edits, inspect the Markdown frontmatter, headings, and code fences, and run the guidance builder when practical:

```bash
python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean
```

## Why It Helps

- Request-scoped access context gives every view the same source of truth for organization, workspace, membership, and permission state.
- Views become easier to audit because they resolve route scope explicitly and then call shared access helpers instead of rebuilding membership logic.
- Serializers stay focused on shaping data and validating submitted relationships, not discovering who the current user can access.
- Hidden-resource behavior is consistent across endpoints because scope helpers resolve objects from access-filtered querysets.
- Bootstrap and feature routes share the same access contract, so frontend shell state and backend authorization do not drift.
- Tests can cover the middleware, context, scope helpers, and representative views directly instead of re-proving the same membership lookup in every endpoint.
