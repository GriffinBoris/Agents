---
id: framework-django-example-query-params
title: Django Query Param Parsing Example
description: Example direct query param parsing with optional filters and shared validator helpers.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - query-params
applies_to:
  - django
status: active
order: 8
---

# Django Query Param Parsing Example

## Scenario

- Use this pattern when a DRF list or action view accepts query params such as `search`, `status`, `workspace_id`, `catalog_entry_id`, `start_date`, `end_date`, or comma-separated ID filters.
- Use this pattern when the route already owns organization, workspace, catalog_entry, contact, order, or other parent scope and query params should only narrow the scoped queryset.
- Use this pattern when invalid query input needs the repository's standardized DRF validation-error shape with the exact query-param key as the `attr`.
- Use this pattern when the filter set is small enough to stay readable in the view without introducing a generic filter framework.

## Why This Shape Exists

- Query params are part of the HTTP boundary. They should be parsed once, near the view handler, before queryset filtering or domain work.
- Organization and workspace identity are access boundaries, not convenience filters. The route or access context must establish the base scope before query params are allowed to narrow it.
- Simple internal API params do not need defensive parsing wrappers. Direct reads such as `request.query_params.get('search', '').strip()` are clearer than local `try` or fallback blocks.
- Invalid typed input should still return a consistent `400`. DRF field converters and `parse_integer_query_param(...)` preserve standardized errors while keeping views concise.
- Error keys matter. Re-raising validation under `{'workspace_id': ...}` or `{'status': ...}` lets `drf-standardized-errors` expose the correct frontend-facing `attr`.
- Deterministic ordering belongs at the end of list queryset construction so filtered and unfiltered responses remain stable for tests and frontend reconciliation.

## Recommended Shape

### Shared Integer Query Param Helper

```python
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView


class BaseAPIView(APIView):
	@staticmethod
	def parse_integer_query_param(request, param_name, error_message):
		value = request.query_params.get(param_name)
		if not value:
			return None

		field = serializers.IntegerField(error_messages={'invalid': error_message})

		try:
			return field.to_internal_value(value)
		except serializers.ValidationError as error:
			raise ValidationError({param_name: error.detail[0]}) from error
```

Use the shared helper for optional integer filters that need a standardized `400`, such as `workspace_id`, `catalog_entry_id`, `contact_id`, or `days`. The helper returns `None` when the query param is absent and raises a DRF `ValidationError` under the concrete snake_case param name when the value is invalid.

### Optional Workspace Filter

```python
from rest_framework.exceptions import ValidationError


class AccessContextMixin:
	def resolve_optional_workspace_filter(self, request, organization, error_message='Select a valid workspace filter.'):
		workspace_id = self.parse_integer_query_param(request, 'workspace_id', error_message)
		if workspace_id is None:
			return None

		workspace = self.get_accessible_workspace_queryset(request, organization).filter(pk=workspace_id).first()
		if workspace is None:
			raise ValidationError({'workspace_id': error_message})

		return workspace
```

`workspace_id` is allowed as an optional filter only after the organization has been resolved and only through the accessible-workspace queryset. It must not replace route scope. On a route such as `/api/organizations/<organization_id>/workspaces/<workspace_id>/orders/list/`, the URL-owned `workspace_id` wins and no query param should be able to point the view at a different workspace.

### Scoped List View With Direct And Validated Params

```python
from common.access.base_views import AuthenticatedAccessAPIView
from django.db.models import Count, Q
from catalog_entry.models import CatalogEntry
from catalog_entry.views.catalog_entry.serializers import CatalogEntryOutputSerializer
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response


class CatalogEntryListBaseView(AuthenticatedAccessAPIView):
	def get_catalog_entry_queryset(self, request, organization, workspace=None):
		if workspace is not None:
			return workspace.catalog_entries.select_related('workspace').annotate(items_count=Count('items', distinct=True))

		accessible_workspaces = self.get_accessible_workspace_queryset(request, organization)
		return CatalogEntry.objects.filter(workspace__in=accessible_workspaces).select_related('workspace').annotate(
			items_count=Count('items', distinct=True),
		)

	def filter_catalog_entry_queryset(self, queryset, search, status_filter):
		if search:
			queryset = queryset.filter(Q(name__icontains=search))

		if status_filter:
			valid_statuses = {choice for choice, _ in CatalogEntry.StatusChoices.choices}
			if status_filter not in valid_statuses:
				raise ValidationError({'status': 'Select a valid status filter.'})

			queryset = queryset.filter(status=status_filter)

		return queryset.order_by('sort_order', 'id')


class OrganizationCatalogEntryListView(CatalogEntryListBaseView):
	def get(self, request, organization_id: int):
		organization = self.resolve_organization_scope(request, organization_id)

		search = request.query_params.get('search', '').strip()
		status_filter = request.query_params.get('status')
		workspace = self.resolve_optional_workspace_filter(request, organization)

		queryset = self.filter_catalog_entry_queryset(
			self.get_catalog_entry_queryset(request, organization, workspace=workspace),
			search,
			status_filter,
		)
		workspaces = [workspace] if workspace is not None else list(self.get_accessible_workspace_queryset(request, organization))
		context = self.get_workspace_serializer_context(request, workspaces)
		serializer = CatalogEntryOutputSerializer(queryset, many=True, context=context)
		return Response(serializer.data, status=status.HTTP_200_OK)
```

This is the default shape: resolve route-owned scope first, read simple params directly, validate typed or choice params explicitly, apply filters to a scoped queryset, then finish with deterministic ordering.

### Route-Scoped List View Where Query Params Must Not Replace Scope

```python
from typing import Optional


class OrderListView(OrderAccessMixin):
	def get(self, request, organization_id: int, workspace_id: Optional[int] = None):
		organization, workspace = self.resolve_workspace_route_scope(request, organization_id, workspace_id)
		queryset = self.get_order_queryset(request, organization, workspace)

		if workspace is None:
			workspace = self.resolve_optional_workspace_filter(request, organization)

		if workspace is not None:
			queryset = queryset.filter(workspace=workspace).order_by('id')

		return Response(OrderListOutputSerializer(queryset, many=True).data, status=status.HTTP_200_OK)
```

This pattern supports both organization-level and workspace-level routes without letting `?workspace_id=` override a workspace route. When `workspace_id` is present in the URL, that route scope is already authoritative. When the route is organization-level, `?workspace_id=` may narrow the organization-scoped queryset through the shared accessible-workspace helper.

### Additional Typed Params

```python
from rest_framework import serializers
from rest_framework.exceptions import ValidationError


class SurveySessionListView(AuthenticatedAccessAPIView):
	def get(self, request, organization_id: int, workspace_id: int):
		_, workspace = self.resolve_workspace_scope(request, organization_id, workspace_id)

		start_date = self.parse_date_query_param(request, 'start_date')
		end_date = self.parse_date_query_param(request, 'end_date')
		statuses = self.parse_csv_query_param(request, 'statuses')
		item_ids = self.parse_integer_csv_query_param(request, 'item_ids')

		queryset = SurveySession.objects.filter(workspace=workspace)

		if start_date is not None:
			queryset = queryset.filter(started_at__date__gte=start_date)
		if end_date is not None:
			queryset = queryset.filter(started_at__date__lte=end_date)
		if statuses:
			valid_statuses = {choice for choice, _ in SurveySession.StatusChoices.choices}
			invalid_statuses = [status for status in statuses if status not in valid_statuses]
			if invalid_statuses:
				raise ValidationError({'statuses': 'Select valid status filters.'})

			queryset = queryset.filter(status__in=statuses)
		if item_ids:
			queryset = queryset.filter(selected_item_id__in=item_ids)

		queryset = queryset.order_by('-started_at', '-id')
		return Response(SurveySessionOutputSerializer(queryset, many=True).data, status=status.HTTP_200_OK)

	def parse_date_query_param(self, request, param_name):
		value = request.query_params.get(param_name)
		if not value:
			return None

		field = serializers.DateField()

		try:
			return field.to_internal_value(value)
		except serializers.ValidationError as error:
			raise ValidationError({param_name: error.detail[0]}) from error

	def parse_csv_query_param(self, request, param_name):
		value = request.query_params.get(param_name, '')
		return [item.strip() for item in value.split(',') if item.strip()]

	def parse_integer_csv_query_param(self, request, param_name):
		values = self.parse_csv_query_param(request, param_name)
		ids = []

		for value in values:
			field = serializers.IntegerField(error_messages={'invalid': 'Select valid ID filters.'})
			try:
				ids.append(field.to_internal_value(value))
			except serializers.ValidationError as error:
				raise ValidationError({param_name: error.detail[0]}) from error

		return ids
```

Use this shape when a view has a few local typed filters and no shared helper exists yet. CSV parsing is straightforward splitting and trimming. Date and integer conversion use DRF fields so invalid input returns standardized validation errors. If several views need the same date range or CSV integer parsing, move that exact shape into a shared helper instead of cloning it.

### Simple Params That Stay Direct

```python
page = int(request.query_params.get('page', 1))
page_size = int(request.query_params.get('page_size', 25))
search = request.query_params.get('search', '').strip()

if search:
	queryset = queryset.filter(Q(name__icontains=search) | Q(email__icontains=search))

queryset = queryset.order_by('id')
```

Direct parsing is appropriate when the param has an obvious default, bad input can fail fast, and the endpoint does not need a custom standardized error message. Do not wrap this in a local `try` or fallback just to keep a malformed request alive.

### Query Param Tests

```python
from core.tests.assertions import assert_standardized_validation_error
from rest_framework import status


def test_workspace_operator_can_filter_contacts_for_accessible_workspace(self, client):
	client.force_login(self.workspace_operator)

	response = client.get(f'{self.list_url}?workspace_id={self.workspace.id}', content_type='application/json')

	expected = ContactOutputSerializer([self.contact], many=True).data
	assert response.status_code == status.HTTP_200_OK
	assert response.json() == expected


def test_contact_list_rejects_non_numeric_workspace_filter(self, client):
	client.force_login(self.organization_admin)

	response = client.get(f'{self.list_url}?workspace_id=abc', content_type='application/json')

	assert response.status_code == status.HTTP_400_BAD_REQUEST
	assert_standardized_validation_error(response, attr='workspace_id', detail='Select a valid workspace filter.')


def test_contact_list_rejects_inaccessible_workspace_filter(self, client):
	client.force_login(self.workspace_operator)

	response = client.get(f'{self.list_url}?workspace_id={self.other_workspace.id}', content_type='application/json')

	assert response.status_code == status.HTTP_400_BAD_REQUEST
	assert_standardized_validation_error(response, attr='workspace_id', detail='Select a valid workspace filter.')


def test_catalog_entry_list_rejects_invalid_status_filter(self, client):
	client.force_login(self.organization_admin)

	response = client.get(f'{self.list_url}?status=INVALID', content_type='application/json')

	assert response.status_code == status.HTTP_400_BAD_REQUEST
	assert_standardized_validation_error(response, attr='status', detail='Select a valid status filter.')
```

Invalid query-param tests should assert both the status code and the standardized error attribute. Positive filter tests should create enough in-scope and out-of-scope data to prove the filter narrows the already-scoped queryset.

## Things To Notice

- Scope is resolved before query params are parsed. The view starts from `resolve_organization_scope(...)`, `resolve_workspace_scope(...)`, or a route-scope helper, not from query-param identity.
- Optional filters narrow a scoped queryset. They do not determine organization, workspace, or parent ownership.
- `search` stays direct because an empty string simply means no search filter.
- `status` is validated against model choices before it is applied to the queryset.
- `workspace_id` and `catalog_entry_id` use `parse_integer_query_param(...)` so invalid values return a standardized `400`.
- Accessible-workspace filtering checks both type validity and permission. A numeric but inaccessible `workspace_id` is still invalid for the request.
- Error dictionaries use exact snake_case query-param names such as `{'workspace_id': ...}`, `{'catalog_entry_id': ...}`, and `{'status': ...}`.
- CSV params are parsed with simple splitting and trimming. Typed CSV values then pass through DRF field converters.
- Date params use DRF `DateField` conversion when invalid date input should produce a standardized error.
- List querysets finish with deterministic `order_by(...)`, and `.distinct()` is added when joins can duplicate rows.
- Query params are snake_case on the backend. Frontend camelCase conversion belongs in the frontend API client, not in Django views.
- `format` is reserved by DRF renderers. Do not use `format` as a business query param; choose a concrete name such as `export_type`, `date_format`, or `response_mode`.

## Rules To Follow

- Resolve organization, workspace, catalog_entry, contact, order, or parent route scope before reading query params that filter data.
- Do not accept `organization_id`, `workspace_id`, or parent identity as a query-param substitute when the URL already owns that scope.
- Allow optional `workspace_id` only as a narrowing filter on organization-level routes, and validate it through accessible-workspace scope.
- Keep backend query params snake_case.
- Do not add feature-specific query params named `format`.
- Use direct parsing for simple internal params with obvious defaults, such as `int(request.query_params.get('page', 1))` and `request.query_params.get('search', '').strip()`.
- Use `parse_integer_query_param(...)` or a DRF field converter when invalid input needs a standardized validation response.
- Re-raise DRF converter failures under the exact query-param key so standardized errors expose the correct `attr`.
- Validate choice filters against the model's `TextChoices` or field choices before applying them.
- Parse comma-separated lists with straightforward splitting and trimming, then validate typed values before using `__in` filters.
- Reuse a shared helper for repeated date range, CSV list, or integer parsing. Keep one-off parsing local when it is clearer and not duplicated.
- Build one base scoped queryset, apply optional filters with shallow `if` blocks, then finish with deterministic ordering.
- Add `.distinct()` when a query-param filter joins through relationships that can duplicate rows.
- Add invalid-param tests for typed, choice, date, CSV, and access-scoped filters.
- Assert standardized validation errors with the concrete query-param `attr`, not only the `400` status code.

## Refactor Signals

- A list endpoint starts from `Model.objects.all()` and relies on `?organization_id=` or `?workspace_id=` to find the user's data boundary.
- A workspace-level route accepts `?workspace_id=` and lets it override the URL workspace.
- A view catches broad exceptions around `int(...)`, date parsing, or choice validation and silently falls back to unfiltered results.
- Invalid query-param tests only assert `400` and never assert the standardized error `attr`.
- A view returns different row order depending on which optional filters are present.
- A status filter accepts arbitrary strings instead of validating against model choices.
- A CSV filter applies raw strings to integer foreign keys without DRF field conversion.
- Multiple views duplicate the same date range or CSV integer parsing logic instead of sharing a focused helper.
- Query params use camelCase in backend code or reuse reserved names such as `format`.
- A query-param filter broadens access by switching organizations, workspaces, catalog_entries, contacts, orders, or enrollments instead of narrowing the already-resolved scope.

## Verification

- For guidance-only edits, inspect the Markdown headings and code fences instead of running backend test suites.
- For view behavior changes that add or alter query params, run the smallest relevant pytest target, such as `pytest backend/contact/tests/test_views.py::TestContactViews`.
- Add positive tests proving filters narrow the scoped queryset and do not include inaccessible organization or workspace rows.
- Add invalid-value tests for each typed or choice filter, such as `?workspace_id=abc`, `?catalog_entry_id=abc`, `?status=INVALID`, `?start_date=not-a-date`, or `?item_ids=1,abc`.
- Use `assert_standardized_validation_error(response, attr='param_name', detail='...')` for standardized query-param failures.
- Add access-negative tests for numeric but inaccessible IDs, such as `?workspace_id=<other_workspace.id>`.
- For route-scoped endpoints, add a test proving query params cannot replace URL scope, or avoid accepting the overlapping query param at that route entirely.

## Why It Helps

- Query params stay readable without hiding normal view flow behind unnecessary abstractions.
- Typed and choice filters fail consistently, with frontend-usable error attributes.
- Organization and workspace boundaries remain auditable because query params only narrow scoped data.
- Tests cover the failure modes that most often create leaks: malformed IDs, inaccessible IDs, invalid choices, and route-scope spoofing.
- Deterministic ordering and serializer-backed expectations make filtered list endpoints stable for future frontend and test changes.
