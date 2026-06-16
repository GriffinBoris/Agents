---
id: framework-django-example-serializer-tests
title: Django Serializer Tests Example
description: Example input and output serializer tests with exact field assertions.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - testing
applies_to:
  - django
status: active
order: 16
---

# Django Serializer Tests Example

## Scenario

- Use this shape when adding or changing a Django serializer.
- Use this shape when an input serializer validates organization, workspace, catalog_entry, item, contact, survey, order, or route-owned relationships.
- Use this shape when an input serializer overrides `create()` or `update()`.
- Use this shape when an output serializer exposes related names, nested objects, computed values, context-dependent fields, or frontend-facing payload contracts.
- Use this shape when serializer-only tests should cover validation combinations that would make HTTP view tests too large or repetitive.

## Why This Shape Exists

- Serializer tests are the fastest proof that write validation, protected scope, persistence, and output shape behave as intended.
- View tests prove routing, authentication, permissions, route scope, and standardized HTTP error formatting. Serializer tests prove the serializer boundary in isolation with exact `serializer.errors` and exact `serializer.data`.
- One pytest class per serializer keeps setup focused. Input serializers and output serializers have different responsibilities, so their tests should not be mixed into one broad class.
- Exact output assertions protect the API contract from accidental field drift. If a field is added, removed, renamed, or serialized with the wrong value, the serializer test should fail before frontend code discovers the mismatch.
- Route-owned organization, workspace, contact, catalog_entry, enrollment, and parent IDs must be tested as protected scope. Payloads may include valid object IDs that are still invalid for the current route or context.
- Deterministic helper patching keeps serializer tests focused on serializer behavior instead of time, token, random, generated-key, or external-service behavior.

## Recommended Shape

### Input Serializer Setup

```python
import pytest
from tests.fixtures import FixtureFactory
from contact.models import ApprovedItemPlan
from contact.views.approved_plan.serializers import ApprovedItemPlanInputSerializer


@pytest.mark.django_db
class TestApprovedItemPlanInputSerializer:
    def setup_method(self):
        self.organization = FixtureFactory.create_organization(name='Organization One', slug='organization-one')
        self.other_organization = FixtureFactory.create_organization(name='Organization Two', slug='organization-two')
        self.workspace = FixtureFactory.create_workspace(self.organization, name='Workspace One', slug='workspace-one')
        self.other_workspace = FixtureFactory.create_workspace(self.other_organization, name='Other Workspace', slug='other-workspace')

        self.catalog_entry = FixtureFactory.create_catalog_entry(self.workspace, name='Operations Project', slug='weight-management')
        self.other_catalog_entry = FixtureFactory.create_catalog_entry(self.other_workspace, name='Other CatalogEntry', slug='other-catalog_entry')

        self.item = FixtureFactory.create_item(self.catalog_entry, name='Core Item', slug='core-item')
        self.other_item = FixtureFactory.create_item(self.other_catalog_entry, name='Other Item', slug='other-item')
        self.variant = FixtureFactory.create_item_option(self.item, name='Standard', slug='standard')
        self.other_variant = FixtureFactory.create_item_option(self.other_item, name='Large', slug='large')
        self.plan = FixtureFactory.create_catalog_entry_subscription_plan(
            self.catalog_entry,
            item=self.item,
            item_option=self.variant,
            name='Monthly Plan',
            slug='monthly-plan',
            price_amount='129.00',
        )
        self.other_plan = FixtureFactory.create_catalog_entry_subscription_plan(
            self.other_catalog_entry,
            item=self.other_item,
            item_option=self.other_variant,
            name='Other Plan',
            slug='other-plan',
            price_amount='159.00',
        )

        self.contact = FixtureFactory.create_contact(self.organization, email='contact@example.com')
        self.enrollment = FixtureFactory.create_project_enrollment(self.contact, self.catalog_entry)
        self.valid_payload = {
            'enrollment': self.enrollment.id,
            'item': self.item.id,
            'item_option': self.variant.id,
            'catalog_entry_subscription_plan': self.plan.id,
            'status': ApprovedItemPlan.StatusChoices.APPROVED,
            'notes': 'Approved for treatment.',
        }
```

Shared setup should create every relationship needed to prove the serializer contract: the in-scope graph, at least one out-of-scope graph, and a reusable valid payload. Keep this in `setup_method` so each test starts with the same readable domain state.

### Create, Update, And Persisted State

```python
def test_valid_payload_creates_instance_with_resolved_price_amount(self):
    serializer = ApprovedItemPlanInputSerializer(data=self.valid_payload)

    assert serializer.is_valid(), serializer.errors
    instance = serializer.save()

    assert instance.enrollment == self.enrollment
    assert instance.item == self.item
    assert instance.item_option == self.variant
    assert instance.catalog_entry_subscription_plan == self.plan
    assert str(instance.resolved_price_amount) == '129.00'


def test_update_refreshes_resolved_price_amount(self):
    instance = FixtureFactory.create_approved_item_plan(
        self.enrollment,
        self.item,
        item_option=self.variant,
        catalog_entry_subscription_plan=self.plan,
        resolved_price_amount='129.00',
    )
    new_plan = FixtureFactory.create_catalog_entry_subscription_plan(
        self.catalog_entry,
        item=self.item,
        item_option=self.variant,
        name='Quarterly Plan',
        slug='quarterly-plan',
        price_amount='149.00',
    )
    serializer = ApprovedItemPlanInputSerializer(
        instance,
        data={'catalog_entry_subscription_plan': new_plan.id},
        partial=True,
    )

    assert serializer.is_valid(), serializer.errors
    updated_instance = serializer.save()

    assert updated_instance.catalog_entry_subscription_plan == new_plan
    assert str(updated_instance.resolved_price_amount) == '149.00'
```

When `create()` or `update()` does more than default `ModelSerializer` persistence, test the saved instance. Assert the route-owned object, related links, normalized values, snapshots, and replaced many-to-many rows that the serializer owns.

### Missing Fields And Domain Validation

```python
def test_requires_enrollment_and_item(self):
    serializer = ApprovedItemPlanInputSerializer(data={})

    assert not serializer.is_valid()
    assert serializer.errors == {
        'enrollment': ['This field is required.'],
        'item': ['This field is required.'],
    }


def test_rejects_variant_for_different_item(self):
    serializer = ApprovedItemPlanInputSerializer(
        data=self.valid_payload | {'item_option': self.other_variant.id},
    )

    assert not serializer.is_valid()
    assert serializer.errors == {'item_option': ['This variant does not belong to the selected item.']}


def test_rejects_item_for_different_catalog_entry(self):
    serializer = ApprovedItemPlanInputSerializer(
        data=self.valid_payload | {'item': self.other_item.id, 'item_option': None},
    )

    assert not serializer.is_valid()
    assert serializer.errors == {'item': ["This item does not belong to the enrollment's catalog_entry."]}


def test_rejects_pricing_plan_for_different_catalog_entry(self):
    serializer = ApprovedItemPlanInputSerializer(
        data=self.valid_payload | {'catalog_entry_subscription_plan': self.other_plan.id},
    )

    assert not serializer.is_valid()
    assert serializer.errors == {
        'catalog_entry_subscription_plan': ["This pricing plan does not belong to the enrollment's catalog_entry."],
    }
```

Assert the exact serializer error dictionary. That proves the field key, message, and validation boundary without depending on DRF's standardized HTTP error wrapper.

### Route-Owned Context And Protected Fields

```python
import pytest
from tests.fixtures import FixtureFactory
from survey.models.MappingTarget import MappingTarget
from survey.views.survey_mapping.serializers import MappingTargetInputSerializer


@pytest.mark.django_db
class TestMappingTargetInputSerializer:
    def setup_method(self):
        self.organization = FixtureFactory.create_organization(name='Organization One', slug='organization-one')
        self.other_organization = FixtureFactory.create_organization(name='Organization Two', slug='organization-two')
        self.workspace = FixtureFactory.create_workspace(self.organization, name='Workspace One', slug='workspace-one')
        self.service_network = FixtureFactory.create_service_network(self.organization, name='Service Network')
        self.other_service_network = FixtureFactory.create_service_network(
            self.other_organization,
            name='Other Service Network',
        )
        self.context = {'workspace': self.workspace}
        self.valid_payload = {
            'service_network': self.service_network.id,
            'key': ' contact_email ',
            'name': ' Contact email ',
            'target_type': MappingTarget.TargetTypeChoices.CONTACT_ATTRIBUTE,
            'data_type': MappingTarget.DataTypeChoices.STRING,
        }

    def test_valid_payload_creates_instance_under_context_workspace(self):
        serializer = MappingTargetInputSerializer(data=self.valid_payload, context=self.context)

        assert serializer.is_valid(), serializer.errors
        instance = serializer.save()

        assert instance.workspace == self.workspace
        assert instance.service_network == self.service_network
        assert instance.key == 'contact_email'
        assert instance.name == 'Contact email'

    def test_payload_cannot_change_context_owned_workspace(self):
        other_workspace = FixtureFactory.create_workspace(self.other_organization, name='Other Workspace', slug='other-workspace')
        serializer = MappingTargetInputSerializer(
            data=self.valid_payload | {'workspace': other_workspace.id},
            context=self.context,
        )

        assert serializer.is_valid(), serializer.errors
        instance = serializer.save()

        assert instance.workspace == self.workspace

    def test_rejects_service_network_from_other_organization(self):
        serializer = MappingTargetInputSerializer(
            data=self.valid_payload | {'service_network': self.other_service_network.id},
            context=self.context,
        )

        assert not serializer.is_valid()
        assert serializer.errors == {
            'service_network': ['The service network must belong to the same organization as the workspace.'],
        }
```

Use this shape when the view resolves the route scope and passes it through serializer context. If the serializer intentionally ignores a protected payload field, prove the saved instance still uses `self.context[...]`. If the protected field should be rejected instead, assert the exact serializer error.

### Context-Dependent Serializer With Request State

```python
from rest_framework.test import APIRequestFactory
from tenancy.models import OrganizationMembership
from tenancy.views.membership.serializers import OrganizationMembershipInputSerializer


@pytest.mark.django_db
class TestOrganizationMembershipInputSerializer:
    def setup_method(self):
        self.factory = APIRequestFactory()
        self.request_user = FixtureFactory.create_user(email='organization-admin@example.com')
        self.existing_user = FixtureFactory.create_user(email='member@example.com')
        self.organization = FixtureFactory.create_organization(name='Organization One', slug='organization-one')
        self.request = self.factory.post('/fake/')
        self.request.user = self.request_user
        self.context = {'request': self.request, 'organization': self.organization}

    def test_valid_payload_creates_membership_for_context_organization(self):
        serializer = OrganizationMembershipInputSerializer(
            data={'email': self.existing_user.email, 'role': OrganizationMembership.RoleChoices.MEMBER, 'is_active': True},
            context=self.context,
        )

        assert serializer.is_valid(), serializer.errors
        membership = serializer.save()

        assert membership.organization == self.organization
        assert membership.user == self.existing_user
        assert membership.role == OrganizationMembership.RoleChoices.MEMBER

    def test_rejects_membership_state_change_on_update(self):
        membership = FixtureFactory.create_organization_membership(
            self.request_user,
            self.organization,
            role=OrganizationMembership.RoleChoices.ADMIN,
        )
        serializer = OrganizationMembershipInputSerializer(
            membership,
            data={'is_active': False},
            partial=True,
            context=self.context,
        )

        assert not serializer.is_valid()
        assert serializer.errors == {
            'is_active': ['Use the membership activate or deactivate action to change membership state.'],
        }
```

When a serializer uses `request`, `organization`, `workspace`, `version`, `contact`, or another required context value, build that context in `setup_method` and pass it explicitly in every serializer construction.

### Exact Output Shape

```python
import pytest
from tests.fixtures import FixtureFactory
from contact.models import ApprovedItemPlan
from contact.views.approved_plan.serializers import ApprovedItemPlanOutputSerializer


@pytest.mark.django_db
class TestApprovedItemPlanOutputSerializer:
    def setup_method(self):
        self.organization = FixtureFactory.create_organization(name='Organization One', slug='organization-one')
        self.workspace = FixtureFactory.create_workspace(self.organization, name='Workspace One', slug='workspace-one')
        self.catalog_entry = FixtureFactory.create_catalog_entry(self.workspace, name='Operations Project', slug='weight-management')
        self.item = FixtureFactory.create_item(self.catalog_entry, name='Core Item', slug='core-item')
        self.variant = FixtureFactory.create_item_option(self.item, name='Standard', slug='standard')
        self.plan = FixtureFactory.create_catalog_entry_subscription_plan(
            self.catalog_entry,
            item=self.item,
            item_option=self.variant,
            name='Monthly Plan',
            slug='monthly-plan',
            price_amount='129.00',
        )
        self.contact = FixtureFactory.create_contact(self.organization, email='contact@example.com')
        self.enrollment = FixtureFactory.create_project_enrollment(self.contact, self.catalog_entry)
        self.instance = FixtureFactory.create_approved_item_plan(
            self.enrollment,
            self.item,
            item_option=self.variant,
            catalog_entry_subscription_plan=self.plan,
            status=ApprovedItemPlan.StatusChoices.APPROVED,
            notes='Approved for treatment.',
            resolved_price_amount='129.00',
        )

    def test_output_payload(self):
        data = dict(ApprovedItemPlanOutputSerializer(self.instance).data)

        assert data.pop('id') == self.instance.id
        assert data.pop('enrollment') == self.enrollment.id
        assert data.pop('catalog_entry_name') == self.catalog_entry.name
        assert data.pop('item') == self.item.id
        assert data.pop('item_name') == self.item.name
        assert data.pop('item_slug') == self.item.slug
        assert data.pop('item_option') == self.variant.id
        assert data.pop('item_option_name') == self.variant.name
        assert data.pop('catalog_entry_subscription_plan') == self.plan.id
        assert data.pop('catalog_entry_subscription_plan_name') == self.plan.name
        assert data.pop('status') == self.instance.status
        assert data.pop('notes') == self.instance.notes
        assert data.pop('resolved_price_amount') == '129.00'
        assert data.pop('order_id') is None
        assert data.pop('approved_ts') is None
        assert data.pop('created_ts')
        assert data.pop('updated_ts')
        assert not data
```

Copy `serializer.data` into a mutable dict, pop every expected key, and finish with `assert not data`. This catches both missing expected keys and unexpected extra keys.

### Nested Output Shape

```python
def test_output_payload(self):
    data = dict(InputBindingMappingOutputSerializer(self.instance).data)
    mapping_target_detail = dict(data.pop('mapping_target_detail'))

    assert data.pop('id') == self.instance.id
    assert data.pop('survey_form_version') == self.version.id
    assert data.pop('input_binding') == self.input_binding.id
    assert data.pop('mapping_target') == self.mapping_target.id
    assert data.pop('transform_type') == self.instance.transform_type
    assert data.pop('required') is True
    assert data.pop('send_condition') == self.instance.send_condition
    assert data.pop('transform_config') == self.instance.transform_config
    assert data.pop('created_ts')
    assert data.pop('updated_ts')
    assert not data

    assert mapping_target_detail.pop('id') == self.mapping_target.id
    assert mapping_target_detail.pop('workspace') == self.workspace.id
    assert mapping_target_detail.pop('service_network') is None
    assert mapping_target_detail.pop('vendor') is None
    assert mapping_target_detail.pop('key') == self.mapping_target.key
    assert mapping_target_detail.pop('name') == self.mapping_target.name
    assert mapping_target_detail.pop('target_type') == self.mapping_target.target_type
    assert mapping_target_detail.pop('data_type') == self.mapping_target.data_type
    assert mapping_target_detail.pop('created_ts')
    assert mapping_target_detail.pop('updated_ts')
    assert not mapping_target_detail
```

Nested serializers need exact checks for the nested object too. Do not stop after checking that the nested object exists.

### Context-Dependent Output Shape

```python
def test_output_payload_includes_context_membership_role(self):
    membership = FixtureFactory.create_workspace_membership(self.user, self.workspace, role='OPERATOR')

    data = dict(
        SurveyFormListOutputSerializer(
            self.survey_form,
            context={'membership_by_workspace_id': {self.workspace.id: membership}},
        ).data
    )

    assert data.pop('id') == self.survey_form.id
    assert data.pop('catalog_entry') == self.catalog_entry.id
    assert data.pop('catalog_entry_name') == self.catalog_entry.name
    assert data.pop('name') == self.survey_form.name
    assert data.pop('status') == self.survey_form.status
    assert data.pop('membership_role') == membership.role
    assert data.pop('created_ts')
    assert data.pop('updated_ts')
    assert not data
```

If output depends on serializer context, test both the field value and the context shape that produces it. This complements view tests that pass `context={'request': response.wsgi_request, ...}` from the HTTP response path.

### Deterministic Helpers And Monkeypatching

```python
def test_output_payload_uses_deterministic_effective_status(self, monkeypatch):
    invitation = FixtureFactory.create_operator_invitation(
        self.organization,
        workspace=self.workspace,
        email='invite@example.com',
        invited_by=self.invited_by,
    )
    monkeypatch.setattr(invitation, 'get_effective_status', lambda: 'EXPIRED')
    monkeypatch.setattr(
        'tenancy.views.invitation.serializers.has_user_with_case_insensitive_email',
        lambda email: True,
    )

    data = dict(InvitationDetailOutputSerializer(invitation).data)

    assert data.pop('id') == invitation.id
    assert data.pop('email') == invitation.email
    assert data.pop('organization') == self.organization.id
    assert data.pop('organization_name') == self.organization.name
    assert data.pop('workspace') == self.workspace.id
    assert data.pop('workspace_name') == self.workspace.name
    assert data.pop('organization_role') == invitation.organization_role
    assert data.pop('workspace_role') == invitation.workspace_role
    assert data.pop('status') == invitation.status
    assert data.pop('effective_status') == 'EXPIRED'
    assert data.pop('is_workspace_invitation') is True
    assert data.pop('has_existing_user') is True
    assert data.pop('expires_ts')
    assert not data
```

Monkeypatch helper calls when the serializer delegates to logic with time, generated tokens, random keys, API calls, or complex model state that is not the subject of the test. Patch the smallest helper that makes the serializer output deterministic, then still assert the exact field set.

### Serializer Tests Complement View Tests

```python
def test_view_returns_serializer_payload(self, client):
    client.force_login(self.organization_admin)

    response = client.post(
        self.create_url,
        {
            'enrollment': self.enrollment.id,
            'item': self.item.id,
            'item_option': self.variant.id,
            'catalog_entry_subscription_plan': self.plan.id,
        },
        content_type='application/json',
    )

    instance = ApprovedItemPlan.objects.get(enrollment=self.enrollment)
    assert response.status_code == 201
    assert response.json() == ApprovedItemPlanOutputSerializer(instance).data
```

Keep detailed validation combinations in serializer tests. Keep HTTP tests focused on auth, permissions, route-owned scope, standardized errors, response status, and proving the view returns the output serializer payload.

## Things To Notice

- Each serializer has its own pytest class.
- `setup_method` builds shared users, organization or workspace scope, in-scope related objects, out-of-scope related objects, serializer context, and reusable valid payloads.
- Input serializer tests call `serializer.is_valid()` before `serializer.save()` and include `serializer.errors` in the assert message on the happy path.
- Create and update tests assert persisted model state, not only `serializer.is_valid()`.
- Missing-field and domain-validation tests assert exact `serializer.errors` dictionaries.
- Protected scope comes from serializer context or view-injected serializer data, not from client-owned payload fields.
- Cross-scope validation tests create real out-of-scope records so the test proves relationship ownership, not just missing data.
- Output serializer tests pop every expected field from a mutable dict and end with `assert not data`.
- Nested output serializers get their own nested exact-field assertions.
- Context-dependent serializers include the same context shape the view is expected to pass.
- Monkeypatching is reserved for deterministic serializer boundaries, not for hiding validation or persistence behavior.
- Serializer tests and view tests are paired: serializer tests cover validation and shape in detail; view tests cover HTTP behavior, permissions, route scope, and standardized error formatting.

## Rules To Follow

- Write one pytest class per serializer, usually named `TestModelInputSerializer` or `TestModelOutputSerializer`.
- Use `setup_method` for shared fixture state when a serializer needs more than one object or context value.
- Use shared fixture builders from `tests.fixtures.FixtureFactory`; add reusable builders there instead of creating one-off builders in serializer test modules.
- Test the input serializer happy path, missing required fields, domain-specific validation, and every cross-scope related-object failure.
- When `create()` or `update()` is overridden, test the saved instance and any computed, normalized, replaced, linked, or snapshot fields.
- When the route owns scope, test that payload scope cannot override context scope or that the serializer rejects spoofed scope explicitly.
- Assert exact `serializer.errors` for serializer-level validation tests.
- For output serializers, assert every field value and finish with `assert not data`.
- For nested output serializers, assert every nested field and finish with `assert not nested_data`.
- For context-dependent output, build the context explicitly and assert the fields that depend on it.
- Monkeypatch time, token, generated-key, external-service, or helper-derived values only when needed to make output deterministic.
- Keep serializer tests below the HTTP boundary. Use view tests for authentication, permissions, URL routing, `reverse(...)`, status codes, standardized DRF error responses, and response payloads.
- Run the focused serializer test class after implementation changes, plus `ruff check` on modified Python files.

## Refactor Signals

- A serializer test module has one broad class covering several unrelated serializers.
- A serializer with custom `create()` or `update()` has no test that calls `serializer.save()`.
- Tests assert only `serializer.is_valid()` and never inspect saved state.
- Output tests check one or two fields and never fail on unexpected keys.
- A nested output serializer is tested only by asserting the nested key exists.
- Serializer validation tests assert only that a field appears in `serializer.errors`, not the exact field-to-message mapping.
- A route-scoped serializer accepts `organization`, `workspace`, `contact`, `catalog_entry`, `enrollment`, or parent IDs from payload without a spoofing test.
- Cross-scope tests use missing or invalid IDs instead of valid IDs from another organization, workspace, catalog_entry, item, contact, or survey version.
- Tests duplicate setup inline in every method instead of using a small `setup_method`.
- Serializer tests build ad hoc users, organizations, workspaces, or items instead of using shared fixture builders.
- Time, token, generated-key, or external helper output makes the test flaky because no deterministic monkeypatch is used.
- View tests contain a long matrix of serializer-only validation combinations that should be moved down to serializer tests.

## Verification

- For implementation changes, run the smallest relevant serializer target first, for example:

```bash
pytest backend/contact/tests/test_additional_serializers.py::TestApprovedItemPlanInputSerializer
pytest backend/survey/views/survey_mapping/tests/test_serializers.py::TestMappingTargetInputSerializer
```

- Run the matching view test when route scope, permissions, standardized HTTP errors, or response serialization changes, for example:

```bash
pytest backend/contact/tests/test_approved_plan_views.py::TestApprovedPlanViews
```

- Run `ruff check` on modified Python files when serializer code or tests change.
- For guidance-only edits, inspect the Markdown frontmatter, headings, and fenced code blocks. Run the guidance builder when practical:

```bash
python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean
```

## Why It Helps

- Serializer tests catch API-contract drift before frontend code or view tests become noisy.
- Exact validation assertions keep field-level errors stable for forms and standardized HTTP error wrappers.
- Route-owned scope tests prevent cross-organization, cross-workspace, and cross-parent data leaks at the serializer boundary.
- Create and update tests make persistence behavior reviewable when serializers normalize values, attach context, replace related rows, or snapshot derived data.
- Focused serializer tests keep view tests smaller and make failures easier to diagnose.
