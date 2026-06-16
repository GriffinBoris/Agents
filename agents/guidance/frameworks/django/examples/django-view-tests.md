---
id: framework-django-example-view-tests
title: Django View Tests Example
description: Example permission-aware API tests for nested organization and workspace routes with serializer-backed expectations and ownership-boundary coverage.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - testing
  - views
  - permissions
  - organization-scope
applies_to:
  - django
status: active
order: 15
---

# Django View Tests Example

## Scenario

- Use this shape when testing Django API views that are scoped to an organization, workspace, user, contact, order, catalog_entry, or other owned resource.
- Use this shape when routes enforce permissions through shared access helpers.
- Use this shape when views return serializer-shaped payloads and must protect route-owned scope from spoofed request data.

## Why This Shape Exists

- View tests are the main proof that permission checks and ownership boundaries actually work at the HTTP boundary.
- Serializer tests prove validation and payload shape in isolation; view tests prove routing, authentication, permissions, scoping, persistence, and serialization work together.
- Nested URLs such as `/api/organizations/<organization_id>/workspaces/<workspace_id>/...` must prove that the URL scope wins over client-submitted protected fields.
- Cross-organization and cross-workspace tests are security tests, not edge-case niceties.

## Recommended Shape

### Shared Setup

```python
import pytest
from workspace.models import WorkspaceMembership
from workspace.views.workspace.serializers import WorkspaceOutputSerializer
from tests.fixtures import FixtureFactory
from django.urls import reverse
from rest_framework import status
from tenancy.models import OrganizationMembership


@pytest.mark.django_db
class TestWorkspaceViews:
    def setup_method(self):
        self.platform_admin = FixtureFactory.create_user(email='platform-admin@example.com', is_superuser=True)
        self.organization_admin = FixtureFactory.create_user(email='organization-admin@example.com')
        self.organization_member = FixtureFactory.create_user(email='organization-member@example.com')
        self.workspace_admin = FixtureFactory.create_user(email='workspace-admin@example.com')
        self.workspace_operator = FixtureFactory.create_user(email='workspace-operator@example.com')
        self.outsider = FixtureFactory.create_user(email='outsider@example.com')
        self.other_organization_admin = FixtureFactory.create_user(email='other-organization-admin@example.com')

        self.organization = FixtureFactory.create_organization(name='Workspace Organization', slug='workspace-organization')
        self.other_organization = FixtureFactory.create_organization(name='Other Organization', slug='other-organization')
        self.workspace = FixtureFactory.create_workspace(self.organization, name='Primary Workspace', slug='primary-workspace')
        self.other_workspace = FixtureFactory.create_workspace(self.organization, name='Secondary Workspace', slug='secondary-workspace')
        self.other_organization_workspace = FixtureFactory.create_workspace(self.other_organization, name='Other Organization Workspace', slug='other-organization-workspace')

        FixtureFactory.create_organization_membership(self.organization_admin, self.organization, role=OrganizationMembership.RoleChoices.ADMIN)
        FixtureFactory.create_organization_membership(self.organization_member, self.organization, role=OrganizationMembership.RoleChoices.MEMBER)
        FixtureFactory.create_organization_membership(self.workspace_admin, self.organization, role=OrganizationMembership.RoleChoices.MEMBER)
        FixtureFactory.create_organization_membership(self.workspace_operator, self.organization, role=OrganizationMembership.RoleChoices.MEMBER)
        FixtureFactory.create_organization_membership(self.other_organization_admin, self.other_organization, role=OrganizationMembership.RoleChoices.ADMIN)

        self.workspace_admin_membership = FixtureFactory.create_workspace_membership(self.workspace_admin, self.workspace, role=WorkspaceMembership.RoleChoices.ADMIN)
        self.workspace_operator_membership = FixtureFactory.create_workspace_membership(self.workspace_operator, self.workspace, role=WorkspaceMembership.RoleChoices.OPERATOR)

        self.list_url = reverse('workspace:workspace-list', kwargs={'organization_id': self.organization.id})
        self.create_url = reverse('workspace:workspace-create', kwargs={'organization_id': self.organization.id})
        self.detail_url = reverse('workspace:workspace-detail', kwargs={'organization_id': self.organization.id, 'workspace_id': self.workspace.id})
```

Keep setup explicit. Create users for each relevant access role, create records in both the in-scope organization and out-of-scope organization, and build URLs with `reverse(...)`. Avoid hard-coded URLs except when a test is intentionally asserting the route contract.

### Route Contract Test

```python
def test_workspace_routes_follow_nested_resource_contract(self):
    assert self.list_url == f'/api/organizations/{self.organization.id}/workspaces/list/'
    assert self.create_url == f'/api/organizations/{self.organization.id}/workspaces/create/'
    assert self.detail_url == f'/api/organizations/{self.organization.id}/workspaces/{self.workspace.id}/'
```

Route contract tests are useful when URL shape is part of the frontend API contract or when nested resources are easy to wire incorrectly.

### Positive List Cases

```python
def test_organization_admin_can_list_all_workspaces(self, client):
    client.force_login(self.organization_admin)

    response = client.get(self.list_url, content_type='application/json')

    expected = WorkspaceOutputSerializer([self.workspace, self.other_workspace], many=True, context={'request': response.wsgi_request}).data
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == expected


def test_workspace_operator_only_lists_assigned_workspaces(self, client):
    client.force_login(self.workspace_operator)

    response = client.get(self.list_url, content_type='application/json')

    expected = WorkspaceOutputSerializer(
        [self.workspace],
        many=True,
        context={
            'request': response.wsgi_request,
            'membership_by_workspace_id': {self.workspace.id: self.workspace_operator_membership},
        },
    ).data
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == expected
```

Positive list tests should prove both broad and narrowed access. If organization admins can see all organization rows and workspace operators can only see assigned rows, test both. Compare the payload to the output serializer so the test tracks the live response contract.

### Create And Route-Owned Scope

```python
def test_organization_admin_can_create_workspace(self, client):
    client.force_login(self.organization_admin)

    response = client.post(
        self.create_url,
        {
            'name': 'Created Workspace',
            'status': 'ACTIVE',
            'contact_name': 'Created Contact',
        },
        content_type='application/json',
    )

    workspace = self.organization.workspaces.get(slug='created-workspace')
    expected = WorkspaceOutputSerializer(workspace, context={'request': response.wsgi_request}).data
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == expected


def test_workspace_create_keeps_route_organization_scope_when_payload_includes_other_organization(self, client):
    client.force_login(self.organization_admin)

    response = client.post(
        self.create_url,
        {'name': 'Scoped Workspace', 'status': 'ACTIVE', 'organization': self.other_organization.id},
        content_type='application/json',
    )

    workspace = self.organization.workspaces.get(slug='scoped-workspace')
    expected = WorkspaceOutputSerializer(workspace, context={'request': response.wsgi_request}).data
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == expected
    assert workspace.organization_id == self.organization.id
```

Every create endpoint with URL-owned scope should have a spoofed-payload test. If the client submits another organization, workspace, contact, or parent ID, the URL scope should still win or the request should fail explicitly.

### Update, Permission, And Isolation Cases

```python
def test_workspace_admin_can_update_workspace(self, client):
    client.force_login(self.workspace_admin)

    response = client.put(
        self.detail_url,
        {'contact_name': 'Updated Workspace Contact'},
        content_type='application/json',
    )

    self.workspace.refresh_from_db()
    expected = WorkspaceOutputSerializer(
        self.workspace,
        context={
            'request': response.wsgi_request,
            'membership_by_workspace_id': {self.workspace.id: self.workspace_admin_membership},
        },
    ).data
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == expected


def test_workspace_operator_cannot_update_workspace(self, client):
    client.force_login(self.workspace_operator)

    response = client.put(
        self.detail_url,
        {'contact_name': 'Blocked Operator Update'},
        content_type='application/json',
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_outsider_cannot_access_workspace(self, client):
    client.force_login(self.outsider)

    response = client.get(self.detail_url, content_type='application/json')

    assert response.status_code == status.HTTP_404_NOT_FOUND
```

Use `403` expectations for authenticated users who can reach the scoped object but do not have the required permission. Use `404` expectations when the object is outside the user's organization or workspace boundary and should not be revealed.

### Standardized Validation Errors

```python
from core.tests.assertions import assert_standardized_validation_error


def test_workspace_admin_cannot_create_membership_for_non_organization_user(self, client):
    new_user = FixtureFactory.create_user(email='outsider-workspace-user@example.com')
    client.force_login(self.workspace_admin)

    response = client.post(
        self.membership_create_url,
        {'email': new_user.email, 'role': WorkspaceMembership.RoleChoices.OPERATOR, 'is_active': True},
        content_type='application/json',
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert_standardized_validation_error(
        response,
        attr='email',
        detail='User must belong to the organization before joining a workspace.',
    )
```

When the project uses standardized DRF errors, assert the standardized shape through shared assertion helpers instead of only checking status code.

## Things To Notice

- `setup_method` creates every role needed to test the permission matrix.
- Tests create out-of-scope records on purpose so ownership boundaries are actually exercised.
- URLs are built with `reverse(...)`; optional route contract tests assert exact URL strings separately.
- Positive responses are compared against output serializers, including serializer context when response fields depend on the current user's membership.
- Mutation tests refresh records from the database before asserting persisted state.
- Scope-spoofing tests prove that URL-owned organization and workspace IDs cannot be overridden by request payload.
- Permission-negative tests and ownership-negative tests assert different status codes when the API is designed to distinguish `403` from hidden `404`.
- Standardized validation errors use shared assertion helpers.

## Rules To Follow

- Every authenticated list endpoint needs at least one test proving the returned rows are scoped to the current user, organization, or workspace.
- Every detail, update, delete, and action endpoint needs a test proving an outsider or other-organization user cannot access the resource.
- Every staff/admin-only endpoint needs a permission-negative test for a lower-privilege user.
- Every mutating endpoint with URL-owned scope needs a spoofed-payload test or an explicit validation-error test.
- Successful mutation tests should assert both response payload and database state.
- Response payload assertions should use the same output serializer as the view unless the endpoint intentionally returns a custom contract.
- URL construction in tests should use `reverse(...)` with route kwargs.
- Use shared fixture builders from `tests/fixtures.py` instead of ad hoc factory islands in each test module.
- Keep view tests at the HTTP boundary. Put detailed serializer-only validation combinations in serializer tests.
- Run the smallest relevant pytest target after changing view behavior.

## Refactor Signals

- A view test only checks the happy path and does not cover unauthenticated, lower-permission, or outsider access.
- A list endpoint test creates only in-scope records, so it cannot prove filtering excludes other organizations, workspaces, or users.
- A detail or update test never tries an object from another organization or workspace.
- A mutating endpoint with URL-owned scope has no test where the payload tries to spoof a different organization, workspace, contact, or parent object.
- Response assertions check only one or two fields instead of comparing against the output serializer or an exact response contract.
- Tests hard-code endpoint paths repeatedly instead of using `reverse(...)` and route kwargs.
- Each test module creates its own one-off object builders instead of using or extending shared fixture helpers.
- Validation-error tests only assert `400` and do not assert the standardized error attribute and message.
- State-changing tests assert only the response and never refresh the model from the database to verify persistence.

## Why It Helps

- Tests catch permission regressions before they become data leaks.
- Serializer-backed expectations keep API tests aligned with the live response contract.
- Scope-spoofing tests prove that route-owned identity is enforced.
- Future contributors can add endpoints by following a repeatable coverage pattern instead of guessing which security cases matter.
