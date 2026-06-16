---
id: framework-django-example-crud-view
title: Django CRUD View Example
description: Example DRF list, create, and detail/update views with scoped querysets and serializer-driven responses.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - view
applies_to:
  - django
status: active
order: 2
---

# Django CRUD View Example

## Scenario

- Use this shape when adding list, create, detail, update, or action endpoints under nested organization, workspace, catalog_entry, contact, order, or other owned-resource routes.
- Use this shape when the URL determines scope, such as `organization_id`, `workspace_id`, `catalog_entry_id`, or `item_id`.
- Use this shape when the view must combine shared access helpers, explicit permissions, input serializers, output serializers, deterministic querysets, and HTTP-boundary tests.
- Use the serializer and view-test examples for deeper serializer validation and test-matrix details; this example is the north-star for view structure.

## Why This Shape Exists

- Views are the HTTP boundary where authentication, route-owned context, permissions, query scoping, serializer validation, persistence, and response serialization meet.
- Organization and workspace scope must be resolved before object lookup or mutation so inaccessible records return hidden-resource behavior instead of leaking existence.
- URL-owned identity must win over request payload identity. If `/organizations/1/workspaces/2/catalog-entries/3/items/create/` receives `{"catalog_entry": 99}`, the view must either overwrite that field with catalog_entry `3` or reject it explicitly.
- Input serializers and output serializers have different responsibilities. The view should validate with the input serializer, save the instance, then serialize the saved resource through the output serializer.
- Querysets should be shaped in one clear path: start from the scoped parent, apply optional filters, add select/prefetch/annotations when needed, then finish with deterministic ordering.
- Permissions should be auditable at the top of each mutating action. Reviewers should not have to search through serializer code or model side effects to find who may change data.

## Recommended Shape

### Feature Route Placement

```python
# backend/item/urls.py

from django.urls import include, path

app_name = 'item'

urlpatterns = [
	path('', include('item.views.item.urls')),
	path('<int:item_id>/variants/', include('item.views.item_option.urls')),
]
```

```python
# backend/item/views/item/urls.py

from django.urls import path
from item.views.item import views

urlpatterns = [
	path('list/', views.ItemListView.as_view(), name='item-list'),
	path('create/', views.ItemCreateView.as_view(), name='item-create'),
	path('<int:item_id>/', views.ItemDetailView.as_view(), name='item-detail'),
]
```

Keep the app-level URL module as an include hub and keep feature-local route definitions beside the feature views and serializers. Use kebab-case route names with `-list`, `-create`, and `-detail` suffixes.

### Scoped List View

```python
from common.access.base_views import AuthenticatedAccessAPIView
from item.views.item.serializers import ItemOutputSerializer
from rest_framework import status
from rest_framework.response import Response


class ItemListView(AuthenticatedAccessAPIView):
	def get(self, request, organization_id: int, workspace_id: int, catalog_entry_id: int):
		_, _, catalog_entry = self.resolve_catalog_entry_scope(request, organization_id, workspace_id, catalog_entry_id)

		queryset = catalog_entry.items.order_by('sort_order', 'id')
		serializer = ItemOutputSerializer(queryset, many=True, context={'request': request})
		return Response(serializer.data, status=status.HTTP_200_OK)
```

The route resolver is the ownership boundary. Once the catalog_entry is resolved through `resolve_catalog_entry_scope(...)`, the list queryset starts from `catalog_entry.items` instead of accepting an arbitrary `catalog_entry` query parameter.

### Filtered List View

```python
from common.access.base_views import AuthenticatedAccessAPIView
from django.db.models import Count, Q
from catalog_entry.models import CatalogEntry
from catalog_entry.views.catalog_entry.serializers import CatalogEntryOutputSerializer
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response


class CatalogEntryListView(AuthenticatedAccessAPIView):
	def get(self, request, organization_id: int, workspace_id: int):
		_, workspace = self.resolve_workspace_scope(request, organization_id, workspace_id)

		search = request.query_params.get('search', '').strip()
		status_filter = request.query_params.get('status')

		queryset = workspace.catalog_entries.select_related('workspace').annotate(items_count=Count('items', distinct=True))

		if search:
			queryset = queryset.filter(Q(name__icontains=search))

		if status_filter:
			valid_statuses = {choice for choice, _ in CatalogEntry.StatusChoices.choices}
			if status_filter not in valid_statuses:
				raise ValidationError({'status': 'Select a valid status filter.'})

			queryset = queryset.filter(status=status_filter)

		queryset = queryset.order_by('sort_order', 'id')
		context = self.get_workspace_serializer_context(request, [workspace])
		serializer = CatalogEntryOutputSerializer(queryset, many=True, context=context)
		return Response(serializer.data, status=status.HTTP_200_OK)
```

Optional filters should narrow a scoped queryset, not choose the scope. Query parameters stay snake_case, validation errors use DRF exceptions, and the final ordering is deterministic.

### Create View With Edited Data

```python
from common.access.base_views import AuthenticatedAccessAPIView
from common.permissions import AppPermission, AppPermissionChoices
from item.views.item.serializers import ItemInputSerializer, ItemOutputSerializer
from rest_framework import status
from rest_framework.response import Response


class ItemCreateView(AuthenticatedAccessAPIView):
	def post(self, request, organization_id: int, workspace_id: int, catalog_entry_id: int):
		_, workspace, catalog_entry = self.resolve_catalog_entry_scope(request, organization_id, workspace_id, catalog_entry_id)
		self.require_permission(request, AppPermission.permission(AppPermissionChoices.WORKSPACE_MANAGE), workspace=workspace)

		edited_data = self.build_serializer_data(request, catalog_entry=catalog_entry.id)
		serializer = ItemInputSerializer(data=edited_data)
		serializer.is_valid(raise_exception=True)

		instance = serializer.save()
		return Response(ItemOutputSerializer(instance, context={'request': request}).data, status=status.HTTP_201_CREATED)
```

`edited_data` is the route-owned field boundary. The client may submit `catalog_entry`, `workspace`, or `organization`, but the view replaces protected identity with the resolved route object before validation. `self.build_serializer_data(request, catalog_entry=catalog_entry.id)` is the preferred helper for that merge.

### Detail And Update View

```python
class ItemDetailView(AuthenticatedAccessAPIView):
	def get(self, request, organization_id: int, workspace_id: int, catalog_entry_id: int, item_id: int):
		_, _, _, item = self.resolve_item_scope(request, organization_id, workspace_id, catalog_entry_id, item_id)
		return Response(ItemOutputSerializer(item, context={'request': request}).data, status=status.HTTP_200_OK)

	def put(self, request, organization_id: int, workspace_id: int, catalog_entry_id: int, item_id: int):
		_, workspace, catalog_entry, item = self.resolve_item_scope(request, organization_id, workspace_id, catalog_entry_id, item_id)
		self.require_permission(request, AppPermission.permission(AppPermissionChoices.WORKSPACE_MANAGE), workspace=workspace)

		edited_data = self.build_serializer_data(request, catalog_entry=catalog_entry.id)
		serializer = ItemInputSerializer(item, data=edited_data, partial=True)
		serializer.is_valid(raise_exception=True)

		instance = serializer.save()
		return Response(ItemOutputSerializer(instance, context={'request': request}).data, status=status.HTTP_200_OK)
```

Detail and update views resolve the full nested object path instead of looking up `Item.objects.get(pk=item_id)` directly. That keeps cross-organization, cross-workspace, and cross-catalog_entry access hidden behind the shared access-scope behavior.

### Action View

```python
from item.models import Item


class ItemArchiveView(AuthenticatedAccessAPIView):
	def post(self, request, organization_id: int, workspace_id: int, catalog_entry_id: int, item_id: int):
		_, workspace, _, item = self.resolve_item_scope(request, organization_id, workspace_id, catalog_entry_id, item_id)
		self.require_permission(request, AppPermission.permission(AppPermissionChoices.WORKSPACE_MANAGE), workspace=workspace)

		item.status = Item.StatusChoices.INACTIVE
		item.save(update_fields=['status', 'updated_ts'])
		return Response(ItemOutputSerializer(item, context={'request': request}).data, status=status.HTTP_200_OK)
```

Use dedicated action views for lifecycle transitions that have business rules, permission requirements, audit behavior, or side effects. Do not quietly expose those changes through broad generic update serializers.

### View Test Expectations

```python
import pytest
from workspace.models import WorkspaceMembership
from tests.fixtures import FixtureFactory
from django.urls import reverse
from item.models import Item
from item.views.item.serializers import ItemOutputSerializer
from rest_framework import status
from tenancy.models import OrganizationMembership


@pytest.mark.django_db
class TestItemViews:
	def setup_method(self):
		self.organization_admin = FixtureFactory.create_user(email='organization-admin@example.com')
		self.workspace_admin = FixtureFactory.create_user(email='workspace-admin@example.com')
		self.workspace_operator = FixtureFactory.create_user(email='workspace-operator@example.com')
		self.other_organization_admin = FixtureFactory.create_user(email='other-organization-admin@example.com')

		self.organization = FixtureFactory.create_organization(name='Workspace Organization', slug='workspace-organization')
		self.other_organization = FixtureFactory.create_organization(name='Other Organization', slug='other-organization')
		self.workspace = FixtureFactory.create_workspace(self.organization, name='Primary Workspace', slug='primary-workspace')
		self.other_workspace = FixtureFactory.create_workspace(self.other_organization, name='Other Workspace', slug='other-workspace')

		FixtureFactory.create_organization_membership(self.organization_admin, self.organization, role=OrganizationMembership.RoleChoices.ADMIN)
		FixtureFactory.create_organization_membership(self.workspace_admin, self.organization, role=OrganizationMembership.RoleChoices.MEMBER)
		FixtureFactory.create_organization_membership(self.workspace_operator, self.organization, role=OrganizationMembership.RoleChoices.MEMBER)
		FixtureFactory.create_organization_membership(self.other_organization_admin, self.other_organization, role=OrganizationMembership.RoleChoices.ADMIN)
		FixtureFactory.create_workspace_membership(self.workspace_admin, self.workspace, role=WorkspaceMembership.RoleChoices.ADMIN)
		FixtureFactory.create_workspace_membership(self.workspace_operator, self.workspace, role=WorkspaceMembership.RoleChoices.OPERATOR)

		self.catalog_entry = FixtureFactory.create_catalog_entry(self.workspace, name='Operations Project', slug='weight-management')
		self.other_catalog_entry = FixtureFactory.create_catalog_entry(self.workspace, name='Support Project', slug='primary-care')
		self.item = FixtureFactory.create_item(self.catalog_entry, name='Starter Package', slug='glp1-treatment')

		self.list_url = reverse(
			'workspace:catalog_entry:item:item-list',
			kwargs={'organization_id': self.organization.id, 'workspace_id': self.workspace.id, 'catalog_entry_id': self.catalog_entry.id},
		)
		self.create_url = reverse(
			'workspace:catalog_entry:item:item-create',
			kwargs={'organization_id': self.organization.id, 'workspace_id': self.workspace.id, 'catalog_entry_id': self.catalog_entry.id},
		)
		self.detail_url = reverse(
			'workspace:catalog_entry:item:item-detail',
			kwargs={'organization_id': self.organization.id, 'workspace_id': self.workspace.id, 'catalog_entry_id': self.catalog_entry.id, 'item_id': self.item.id},
		)

	def test_organization_admin_can_list_items(self, client):
		client.force_login(self.organization_admin)

		response = client.get(self.list_url, content_type='application/json')

		assert response.status_code == status.HTTP_200_OK
		assert response.json() == ItemOutputSerializer([self.item], many=True, context={'request': response.wsgi_request}).data

	def test_create_keeps_route_catalog_entry_scope_when_payload_includes_other_catalog_entry(self, client):
		client.force_login(self.workspace_admin)

		response = client.post(
			self.create_url,
			{
				'name': 'Scoped Item',
				'status': Item.StatusChoices.ACTIVE,
				'summary': 'Scoped summary',
				'description': 'Scoped description',
				'catalog_entry': self.other_catalog_entry.id,
			},
			content_type='application/json',
		)

		instance = Item.objects.get(catalog_entry=self.catalog_entry, slug='scoped-item')
		assert response.status_code == status.HTTP_201_CREATED
		assert response.json() == ItemOutputSerializer(instance, context={'request': response.wsgi_request}).data
		assert instance.catalog_entry_id == self.catalog_entry.id

	def test_workspace_operator_cannot_create_item(self, client):
		client.force_login(self.workspace_operator)

		response = client.post(self.create_url, {'name': 'Blocked Item'}, content_type='application/json')

		assert response.status_code == status.HTTP_403_FORBIDDEN

	def test_other_organization_admin_cannot_access_item(self, client):
		client.force_login(self.other_organization_admin)

		response = client.get(self.detail_url, content_type='application/json')

		assert response.status_code == status.HTTP_404_NOT_FOUND
```

View tests prove the route, permission, scoping, mutation, and response contracts together. They should use shared fixture builders, build URLs with `reverse(...)`, compare successful responses against output serializers, include lower-permission cases, and include other-organization or other-scope isolation cases.

## Things To Notice

- The first line inside each handler resolves the route-owned context through `resolve_organization_scope(...)`, `resolve_workspace_scope(...)`, `resolve_catalog_entry_scope(...)`, or a more specific helper.
- Permission checks happen immediately after context resolution and before serializer validation or persistence.
- Lists start from scoped relationships such as `catalog_entry.items` or access-filtered querysets such as `self.get_accessible_workspace_queryset(...)`.
- Optional filters narrow an already-scoped queryset. They do not replace route scope or accept protected identity from query params.
- `edited_data` is built from `request.data` plus server-owned route fields before passing data to the input serializer.
- Mutating endpoints return the created or updated resource through an output serializer and a concrete `201` or `200` status.
- Detail and update endpoints resolve the full nested resource path, not only the leaf primary key.
- Feature views, serializers, URLs, and feature-specific tests live together when that improves discoverability.
- Shared access helpers stay responsible for access context and scope resolution; feature views keep domain queryset shaping local.

## Rules To Follow

- Inherit authenticated organization or workspace views from `AuthenticatedAccessAPIView` when the application's access context is required.
- Resolve route-owned scope at the top of every handler before querying, validating, saving, or returning data.
- Use `require_permission(...)` with `AppPermission.permission(...)` for mutating or staff-only actions.
- Do not accept organization, workspace, catalog_entry, contact, order, or parent identity from request data when the URL already determines it.
- Use `self.build_serializer_data(request, protected_field=resolved.id)` or an explicit `edited_data` dict to enforce route-owned fields.
- Validate writes through `ModelInputSerializer`; serialize read and mutation responses through `ModelOutputSerializer`.
- Return the saved resource from successful `POST`, `PUT`, and action endpoints unless the endpoint has a documented custom contract.
- Build list querysets from scoped parents or access-filtered querysets, apply filters afterward, and finish with deterministic ordering.
- Keep query params snake_case and raise `ValidationError({param_name: message})` for invalid filter values.
- Use `get_object_or_404(...)` only after the queryset has already been scoped to the current user, organization, workspace, or parent resource.
- Put feature routes in feature-local `urls.py` modules and include them through thin app-level URL hubs.
- Add view tests for the positive case, lower-permission case, ownership-boundary case, and route-owned payload-spoofing case.
- Compare successful response bodies against output serializer data instead of hand-built response dictionaries.

## Refactor Signals

- A view looks up an object by leaf `pk` without filtering through the organization, workspace, catalog_entry, contact, order, or access context first.
- A mutating view validates `request.data` directly even though the URL owns fields such as `organization`, `workspace`, `catalog_entry`, `contact`, or `enrollment`.
- Permission checks appear after serializer validation, after saving, or inside unrelated helper code.
- A list endpoint starts from `Model.objects.all()` and then tries to hide inaccessible rows later.
- Optional query params choose organization or workspace scope instead of narrowing a route-scoped queryset.
- A mutation returns `{}` or an ad hoc dict instead of the output serializer for the saved resource.
- One serializer is doing both broad write validation and read-only response shaping when the input and output contracts differ.
- Multiple views repeat the same nested object lookup instead of using an existing `resolve_*_scope(...)` helper.
- Feature route definitions are scattered in the project root or a catch-all URL module instead of the owning app or feature package.
- View tests cover only the happy path, create no out-of-scope records, or skip payload-spoofing cases for route-owned fields.

## Verification

- For a view change, run the smallest relevant test target, such as `pytest backend/item/tests/test_item_views.py::TestItemViews`.
- Run serializer tests when the view change depends on serializer validation or output fields.
- Run `ruff check` on modified Python files when code changes accompany the guidance.
- For guidance-only edits, inspect the Markdown headings and code fences, and run the guidance build when practical:

```bash
python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean
```

- Before review, confirm the updated example still has valid frontmatter, balanced code fences, current class names, and no conflicts with the Django serializer or view-test examples.

## Why It Helps

- View code becomes easy to audit because every handler follows the same order: resolve context, check permission, shape queryset or serializer input, validate, save, serialize response.
- Organization and workspace boundaries are enforced at the HTTP boundary before data can leak or cross-scope records can be persisted.
- Frontend contracts stay stable because successful responses always use output serializers.
- Tests catch security regressions in route-owned scope, ownership filtering, and lower-permission access.
- Future contributors can add new endpoints by copying a complete shape instead of inventing permission, scoping, and response behavior each time.
