---
id: framework-django-example-action-view
title: Django Action View Example
description: Example non-CRUD DRF action endpoints with scoped lookup, explicit validation, delegated domain work, serializer-backed responses, and focused tests.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - drf
  - actions
  - permissions
  - organization-scope
applies_to:
  - django
status: active
order: 10
---

# Django Action View Example

## Scenario

- Use this pattern when the API operation is a command, workflow step, lifecycle transition, preview, retry, clone, resend, revoke, activate, deactivate, link, or unlink action instead of ordinary create, update, or delete.
- Use this pattern when a field must not be editable through a generic update serializer because it has business rules, audit behavior, side effects, or different permissions.
- Use this pattern when the route owns organization, workspace, catalog_entry, contact, order, enrollment, survey form, or rate card scope and the action must not trust those identities from request payload.
- Use this pattern when the action needs required body fields or query params before it can safely perform one focused operation.

## Why This Shape Exists

- Action endpoints are easy places to hide too much behavior. A thin action view keeps the HTTP boundary auditable: scope, permission, input validation, domain operation, response.
- Dedicated action routes make lifecycle changes explicit. Reviewers can see that `status`, `is_active`, resend, revoke, retry, and similar commands do not slip through a generic `PUT`.
- Route-scoped lookups prevent data leaks. The current user must first resolve access to the parent organization, workspace, or other route object, then the child object is fetched inside that boundary.
- Action input serializers give body validation a named contract. Required values, allowed choices, and cross-object checks stay in one place and return standardized DRF validation errors.
- Query params still need a validation boundary. Use `parse_integer_query_param(...)`, a DRF field converter, or a small action serializer so bad query input returns a clear `400` under the concrete param key.
- The view should not become the workflow engine. Model methods or service modules own multi-step business behavior, external I/O, bulk persistence, retries, or lifecycle invariants.
- Successful mutating actions should return the affected resource or a deliberate custom contract. Empty success payloads make frontend state reconciliation and tests weaker.

## Recommended Shape

### Dedicated Action URL

```python
from django.urls import path
from survey.views.survey_form import views

urlpatterns = [
	path('list/', views.SurveyFormListView.as_view(), name='survey-form-list'),
	path('create/', views.SurveyFormCreateView.as_view(), name='survey-form-create'),
	path('<int:survey_form_id>/', views.SurveyFormDetailView.as_view(), name='survey-form-detail'),
	path('<int:survey_form_id>/transition/', views.SurveyFormTransitionView.as_view(), name='survey-form-transition'),
]
```

Give non-CRUD work a route named for the action. Prefer routes such as `transition/`, `activate/`, `deactivate/`, `resend/`, `revoke/`, `retry/`, `clone/`, `preview/`, `link-catalog_entry/`, and `unlink-catalog_entry/` over overloading a generic detail update.

### Generic Update Blocks Lifecycle Fields

```python
from rest_framework import serializers

PUBLISHED_STATUS_CONFLICT_MESSAGE = 'This catalog_entry already has a published survey form.'
STATUS_TRANSITION_MESSAGE = 'Use the survey form transition endpoint for lifecycle changes.'


class SurveyFormInputSerializer(serializers.ModelSerializer):
	class Meta:
		model = SurveyForm
		fields = (
			'id',
			'catalog_entry',
			'name',
			'slug',
			'status',
			'page_mode',
			'intro_title',
			'intro_body',
			'theme_override',
			'theme_overrides',
			'sort_order',
		)
		read_only_fields = ('id', 'slug')

	def validate(self, attrs):
		attrs = super().validate(attrs)

		if self.instance and 'status' in self.initial_data:
			raise serializers.ValidationError({'status': STATUS_TRANSITION_MESSAGE})

		if self.instance:
			catalog_entry = self.instance.catalog_entry
			status = self.instance.status
		else:
			catalog_entry = attrs['catalog_entry']
			status = attrs.get('status', SurveyForm.StatusChoices.DRAFT)

		if 'catalog_entry' in attrs:
			catalog_entry = attrs['catalog_entry']
		if 'status' in attrs:
			status = attrs['status']

		if status == SurveyForm.StatusChoices.PUBLISHED:
			validate_published_status_conflict(catalog_entry, self.instance)

		return attrs
```

Generic update serializers should reject fields that belong to action endpoints. This makes the action route the only place where lifecycle-specific permission, validation, audit, and persistence behavior can happen.

### Action Input Serializer

```python
class SurveyFormTransitionInputSerializer(serializers.Serializer):
	status = serializers.ChoiceField(choices=SurveyForm.StatusChoices.choices)

	def validate(self, attrs):
		attrs = super().validate(attrs)
		instance = self.context['instance']

		if attrs['status'] == SurveyForm.StatusChoices.PUBLISHED:
			validate_published_status_conflict(instance.catalog_entry, instance)

		return attrs
```

Use a plain `serializers.Serializer` when an action accepts a small command payload instead of a full model write contract. Access required context directly with `self.context[...]` when the view is responsible for providing it.

### Thin Action View

```python
from common.access.base_views import AuthenticatedAccessAPIView
from common.permissions import AppPermission, AppPermissionChoices
from survey.models.SurveyForm import SurveyForm
from survey.views.survey_form.serializers import SurveyFormListOutputSerializer, SurveyFormTransitionInputSerializer
from rest_framework import status
from rest_framework.response import Response


class SurveyFormTransitionView(AuthenticatedAccessAPIView):
	def post(self, request, organization_id: int, workspace_id: int, catalog_entry_id: int, survey_form_id: int):
		_, workspace, _, instance = self.resolve_survey_form_scope(
			request,
			organization_id,
			workspace_id,
			catalog_entry_id,
			survey_form_id,
		)
		self.require_permission(
			request,
			AppPermission.permission(AppPermissionChoices.WORKSPACE_MANAGE),
			workspace=workspace,
		)

		serializer = SurveyFormTransitionInputSerializer(
			data=self.build_serializer_data(request),
			context={'instance': instance},
		)
		serializer.is_valid(raise_exception=True)

		instance.status = serializer.validated_data['status']
		instance.save(update_fields=['status', 'updated_ts'])

		instance = SurveyForm.objects.select_related(
			'catalog_entry__workspace',
			'catalog_entry__workspace__default_survey_theme',
			'theme_override',
		).get(pk=instance.pk)
		context = self.get_workspace_serializer_context(request, [workspace])
		return Response(SurveyFormListOutputSerializer(instance, context=context).data, status=status.HTTP_200_OK)
```

Keep the handler in this order:

- Resolve route-owned scope.
- Require the action-specific permission.
- Validate the action payload or query params.
- Perform one focused state change or delegate to one domain/service call.
- Re-load any related data the output serializer expects.
- Return the output serializer for the updated resource.

### Delegated Workflow Action

```python
from common.access.base_views import AuthenticatedAccessAPIView
from common.permissions import AppPermission, AppPermissionChoices
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from tenancy.invitation_service import OperatorInvitationWorkflowService
from tenancy.models import OperatorInvitation
from tenancy.views.invitation.serializers import OperatorInvitationOutputSerializer


class WorkspaceInvitationRevokeView(AuthenticatedAccessAPIView):
	def post(self, request, organization_id: int, workspace_id: int, invitation_id: int):
		organization, workspace = self.resolve_workspace_scope(request, organization_id, workspace_id)
		self.require_permission(
			request,
			AppPermission.permission(AppPermissionChoices.WORKSPACE_MANAGE),
			workspace=workspace,
		)
		invitation = get_object_or_404(OperatorInvitation, pk=invitation_id, organization=organization, workspace=workspace)
		invitation = OperatorInvitationWorkflowService(invitation).revoke()
		return Response(OperatorInvitationOutputSerializer(invitation).data, status=status.HTTP_200_OK)
```

When the action is a workflow step, put the workflow in a focused service or model method. The view should choose the accessible object and call the operation; it should not own email delivery, retry behavior, external API calls, task scheduling, timeline logging, or multi-record orchestration inline.

### Body Validation For Related Objects

```python
class RateCardCatalogEntryActionInputSerializer(serializers.Serializer):
	catalog_entry = serializers.PrimaryKeyRelatedField(queryset=CatalogEntry.objects.all())

	def validate(self, attrs):
		attrs = super().validate(attrs)
		workspace = self.context['workspace']
		catalog_entry = attrs['catalog_entry']

		if catalog_entry.workspace_id != workspace.id:
			raise serializers.ValidationError({'catalog_entry': 'This catalog_entry does not belong to the rate card workspace.'})

		return attrs
```

If a body field points at another model, validate that object against the already resolved route scope. Do not match by name, slug, or any other non-unique display value when a primary key or composite route identity is required.

### Query Param Validation

```python
class OrderListView(AuthenticatedAccessAPIView):
	def get(self, request, organization_id: int):
		organization = self.resolve_organization_scope(request, organization_id)
		workspace = self.resolve_optional_workspace_filter(
			request,
			organization,
			error_message='Select a workspace you can access.',
		)

		queryset = Order.objects.filter(organization=organization)
		if workspace:
			queryset = queryset.filter(workspace=workspace)

		queryset = queryset.order_by('id')
		return Response(OrderOutputSerializer(queryset, many=True).data, status=status.HTTP_200_OK)
```

Use shared query-param helpers when they exist. If an action has required query params, validate them before object lookup or domain work. For integer params, use `parse_integer_query_param(...)` or a DRF field converter and re-raise errors under the exact snake_case query-param name.

### Focused Action Tests

```python
import pytest
from workspace.models import WorkspaceMembership
from tests.fixtures import FixtureFactory
from core.tests.assertions import assert_standardized_validation_error
from django.urls import reverse
from survey.models.SurveyForm import SurveyForm
from survey.views.survey_form.serializers import SurveyFormListOutputSerializer
from rest_framework import status
from tenancy.models import OrganizationMembership


@pytest.mark.django_db
class TestSurveyFormTransitionView:
	def setup_method(self):
		self.organization = FixtureFactory.create_organization(name='Workspace Organization', slug='workspace-organization')
		self.workspace = FixtureFactory.create_workspace(self.organization, name='Primary Workspace', slug='primary-workspace')
		self.other_workspace = FixtureFactory.create_workspace(self.organization, name='Other Workspace', slug='other-workspace')
		self.catalog_entry = FixtureFactory.create_catalog_entry(self.workspace, name='Weight Care', slug='weight-care')
		self.other_catalog_entry = FixtureFactory.create_catalog_entry(self.other_workspace, name='Other Care', slug='other-care')
		self.survey_form = FixtureFactory.create_survey_form(
			self.catalog_entry,
			name='Main Survey',
			slug='main-survey',
			status=SurveyForm.StatusChoices.DRAFT,
		)
		self.workspace_admin = FixtureFactory.create_user(email='workspace-admin@example.com')
		self.workspace_operator = FixtureFactory.create_user(email='workspace-operator@example.com')
		self.other_workspace_admin = FixtureFactory.create_user(email='other-workspace-admin@example.com')
		FixtureFactory.create_organization_membership(self.workspace_admin, self.organization, role=OrganizationMembership.RoleChoices.MEMBER)
		FixtureFactory.create_organization_membership(self.workspace_operator, self.organization, role=OrganizationMembership.RoleChoices.MEMBER)
		FixtureFactory.create_organization_membership(self.other_workspace_admin, self.organization, role=OrganizationMembership.RoleChoices.MEMBER)
		self.workspace_admin_membership = FixtureFactory.create_workspace_membership(
			self.workspace_admin,
			self.workspace,
			role=WorkspaceMembership.RoleChoices.ADMIN,
		)
		FixtureFactory.create_workspace_membership(
			self.workspace_operator,
			self.workspace,
			role=WorkspaceMembership.RoleChoices.OPERATOR,
		)
		FixtureFactory.create_workspace_membership(
			self.other_workspace_admin,
			self.other_workspace,
			role=WorkspaceMembership.RoleChoices.ADMIN,
		)

		self.transition_url = reverse(
			'workspace:catalog_entry:survey:survey-form-transition',
			kwargs={
				'organization_id': self.organization.id,
				'workspace_id': self.workspace.id,
				'catalog_entry_id': self.catalog_entry.id,
				'survey_form_id': self.survey_form.id,
			},
		)

	def test_route_contract(self):
		assert self.transition_url == (
			f'/api/organizations/{self.organization.id}/workspaces/{self.workspace.id}/catalog-entries/'
			f'{self.catalog_entry.id}/survey-forms/{self.survey_form.id}/transition/'
		)

	def test_workspace_admin_can_transition_survey_form_status(self, client):
		client.force_login(self.workspace_admin)

		response = client.post(
			self.transition_url,
			{'status': SurveyForm.StatusChoices.ARCHIVED},
			content_type='application/json',
		)

		self.survey_form.refresh_from_db()
		expected = SurveyFormListOutputSerializer(
			self.survey_form,
			context={
				'request': response.wsgi_request,
				'membership_by_workspace_id': {self.workspace.id: self.workspace_admin_membership},
			},
		).data
		assert response.status_code == status.HTTP_200_OK
		assert response.json() == expected
		assert self.survey_form.status == SurveyForm.StatusChoices.ARCHIVED

	def test_workspace_operator_cannot_transition_survey_form(self, client):
		client.force_login(self.workspace_operator)

		response = client.post(
			self.transition_url,
			{'status': SurveyForm.StatusChoices.ARCHIVED},
			content_type='application/json',
		)

		assert response.status_code == status.HTTP_403_FORBIDDEN

	def test_other_workspace_admin_cannot_transition_out_of_scope_survey_form(self, client):
		client.force_login(self.other_workspace_admin)

		response = client.post(
			self.transition_url,
			{'status': SurveyForm.StatusChoices.ARCHIVED},
			content_type='application/json',
		)

		assert response.status_code == status.HTTP_404_NOT_FOUND

	def test_transition_rejects_conflicting_published_status(self, client):
		FixtureFactory.create_survey_form(
			self.catalog_entry,
			name='Published Survey',
			slug='published-survey',
			status=SurveyForm.StatusChoices.PUBLISHED,
		)
		client.force_login(self.workspace_admin)

		response = client.post(
			self.transition_url,
			{'status': SurveyForm.StatusChoices.PUBLISHED},
			content_type='application/json',
		)

		assert response.status_code == status.HTTP_400_BAD_REQUEST
		assert_standardized_validation_error(
			response,
			attr='status',
			detail='This catalog_entry already has a published survey form.',
		)

	def test_detail_update_rejects_status_transition(self, client):
		client.force_login(self.workspace_admin)
		detail_url = reverse(
			'workspace:catalog_entry:survey:survey-form-detail',
			kwargs={
				'organization_id': self.organization.id,
				'workspace_id': self.workspace.id,
				'catalog_entry_id': self.catalog_entry.id,
				'survey_form_id': self.survey_form.id,
			},
		)

		response = client.put(
			detail_url,
			{'status': SurveyForm.StatusChoices.ARCHIVED},
			content_type='application/json',
		)

		assert response.status_code == status.HTTP_400_BAD_REQUEST
		assert_standardized_validation_error(
			response,
			attr='status',
			detail='Use the survey form transition endpoint for lifecycle changes.',
		)
```

Tests for an action endpoint should prove routing, permission, ownership hiding, validation, response shape, and persisted state. Keep serializer-only validation combinations in serializer tests, but prove at least the action-specific HTTP boundary here.

## Things To Notice

- The action has its own URL and route name instead of sharing the generic detail route.
- Route scope is resolved at the top of the handler before permission checks, payload validation, or domain work.
- The scoped lookup uses route-owned parent objects. The child action target is never fetched by bare primary key alone.
- Permission checks use the repository access helpers and action-specific permission, such as `WORKSPACE_MANAGE`.
- Generic update serializers reject lifecycle fields that belong to the action route.
- Action input serializers validate required body fields and cross-object relationships against context supplied by the view.
- Query-param validation uses shared helpers or DRF field converters and reports errors under snake_case param names.
- Simple intrinsic state changes can stay direct in the view when the flow is still one clear operation.
- Multi-step workflows, external I/O, retries, task scheduling, timeline entries, or invitation-style state machines belong in a model method or service module.
- Mutating actions return output serializers for the affected resource unless the endpoint intentionally has a different response contract.
- Tests compare successful responses to the output serializer and refresh the model before checking persisted state.

## Rules To Follow

- Use a dedicated action endpoint when an operation is not plain CRUD or has lifecycle-specific rules.
- Do not allow a generic update serializer to mutate protected action fields such as `status`, `is_active`, workflow state, retry state, or external sync state.
- Resolve organization, workspace, catalog_entry, contact, order, enrollment, and child-resource scope before validating payload fields that depend on that scope.
- Require permissions before performing the action.
- Use `get_object_or_404(...)` or existing `resolve_*_scope(...)` helpers with parent-scope filters for action targets.
- Validate required body input with an action serializer when the payload has more than trivial shape.
- Validate required query params before domain work, and keep backend query-param names snake_case.
- Validate submitted related objects against the route-owned scope.
- Raise DRF or serializer `ValidationError` from the right layer so standardized error responses preserve the field or query-param attr.
- Keep the view to one operation. Move loops, external calls, retries, bulk persistence, and workflow branching into a focused service or model method.
- Return the updated or created resource through an output serializer for mutating actions unless a different response contract is deliberate and tested.
- Name action routes and URL names in kebab-case with the resource and action, such as `survey-form-transition` or `workspace-invitation-revoke`.
- Add HTTP tests for successful action behavior, lower-permission denial, cross-scope hidden access, validation errors, response payload, and database state.

## Refactor Signals

- A `put()` handler accepts `status`, `is_active`, or another lifecycle field and changes it without a dedicated action route.
- An action view starts by reading `request.data` before resolving the organization, workspace, or parent object.
- A child action target is fetched with only `pk=...` instead of being filtered through the route-owned parent scope.
- A view trusts `organization`, `workspace`, `catalog_entry`, `contact`, or parent IDs from request payload when the URL already determines them.
- Required query params are pulled with `.get(...)` and used directly without `parse_integer_query_param(...)`, a DRF field converter, or equivalent action validation.
- Action code contains several branches, loops, outbound calls, or task scheduling inline in the view.
- The endpoint returns `{}` or only `{'detail': ...}` after mutating a resource the frontend must refresh.
- Validation errors are hand-built inconsistently instead of coming from serializers or shared DRF validation helpers.
- Tests cover the happy path but do not prove permission denial, other-organization or other-workspace isolation, invalid input, and persisted state.
- Tests assert only one response field instead of comparing against the output serializer or an explicit custom contract.

## Verification

- Run the focused pytest target for the action view, for example `pytest backend/survey/views/survey_form/tests/test_views.py::TestSurveyFormViews`.
- Run the serializer tests when the action serializer or generic update serializer changed.
- Include tests for:
  - successful action response and database state
  - unauthorized or unauthenticated access if the app's convention requires it
  - lower-permission `403`
  - cross-organization or cross-workspace `404`
  - missing or invalid required body fields
  - invalid required query params under the exact query-param attr
  - generic update rejection for fields that must go through the action route
- Use `reverse(...)` for URLs and compare successful responses with the output serializer.
- Run `ruff check` on modified Python files. For guidance-only Markdown edits, inspect heading structure and code fences, and run the guidance builder when practical.

## Why It Helps

- Action behavior stays discoverable because routes name the workflow command directly.
- Permission and scoping reviews become mechanical: scope first, permission second, validation third, one operation, serializer response.
- Organization and workspace isolation is enforced before business logic can touch the wrong object.
- Frontend state stays stable because mutating actions return the same output contract as the relevant detail or list views.
- Tests catch the failures that matter most for actions: unauthorized workflow changes, hidden cross-scope resources, invalid command input, and stale persisted state.
- Service and model delegation keeps action views small enough that future workflow changes do not turn DRF handlers into hard-to-review business modules.
