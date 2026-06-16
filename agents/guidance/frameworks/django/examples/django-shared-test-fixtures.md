---
id: framework-django-example-shared-test-fixtures
title: Django Shared Test Fixtures Example
description: Example shared object builders that keep API tests explicit without repeating setup in each module.
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
order: 17
---

# Django Shared Test Fixtures Example

## Scenario

- Use this pattern when many Django tests need the same users, organizations, workspaces, contacts, catalog_entries, items, enrollments, memberships, or other domain records.
- Use this pattern when a feature test needs realistic ownership setup but should not repeat raw `Model.objects.create(...)` calls in every module.
- Use this pattern when duplicated setup starts obscuring the behavior under test, but the test still needs to keep its permission matrix, out-of-scope records, and assertions visible.

## Why This Shape Exists

- Shared builders keep object construction consistent across the backend without turning tests into a factory DSL that hides the scenario.
- Required relationships such as `organization`, `workspace`, `catalog_entry`, `contact`, and `enrollment` are ownership boundaries. Passing them explicitly makes it clear which records belong together.
- Sensible defaults keep tests short for fields that are not part of the behavior under test, while named parameters keep important differences visible.
- Permission and membership setup is part of the test scenario. Builders may create membership rows, but they should not decide which user is allowed to perform an action or hide permission assertions.
- Local setup remains valuable when the setup is unique to one test class, is asserting a feature-specific graph, or would make a shared builder too broad.

## Recommended Shape

### Shared Builders In `tests/fixtures.py`

```python
from typing import Optional

from workspace.models import Workspace, WorkspaceMembership
from core.utility import random_string
from contact.models import Contact, ProjectEnrollment
from django.contrib.auth.models import User
from catalog_entry.models import CatalogEntry
from item.models import Item
from tenancy.models import Organization, OrganizationMembership


class FixtureFactory:
    @staticmethod
    def create_user(
        email: Optional[str] = None,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        is_superuser: bool = False,
        password: Optional[str] = None,
    ):
        email = email or f'{random_string()}@notreal.fake'
        user = User.objects.create(
            username=username or email,
            first_name=first_name or random_string(),
            last_name=last_name or random_string(),
            email=email,
            is_staff=is_superuser,
            is_superuser=is_superuser,
        )
        if password is None:
            user.set_unusable_password()
        else:
            user.set_password(password)

        user.save(update_fields=['password'])
        return user

    @staticmethod
    def create_organization(
        name: Optional[str] = None,
        slug: Optional[str] = None,
        status: str = Organization.StatusChoices.ACTIVE,
        brand_name: str = '',
        support_email: str = '',
    ):
        name = name or f'Organization {random_string()}'
        return Organization.objects.create(
            name=name,
            slug=slug,
            status=status,
            brand_name=brand_name,
            support_email=support_email,
        )

    @staticmethod
    def create_organization_membership(
        user: User,
        organization: Organization,
        role: str = OrganizationMembership.RoleChoices.ADMIN,
        is_active: bool = True,
    ):
        return OrganizationMembership.objects.create(
            user=user,
            organization=organization,
            role=role,
            is_active=is_active,
        )

    @staticmethod
    def create_workspace(
        organization: Organization,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        status: str = Workspace.StatusChoices.ACTIVE,
        contact_name: str = '',
        contact_email: str = '',
        support_phone: str = '',
    ):
        name = name or f'Workspace {random_string()}'
        return Workspace.objects.create(
            organization=organization,
            name=name,
            slug=slug,
            status=status,
            contact_name=contact_name,
            contact_email=contact_email,
            support_phone=support_phone,
        )

    @staticmethod
    def create_workspace_membership(
        user: User,
        workspace: Workspace,
        role: str = WorkspaceMembership.RoleChoices.ADMIN,
        is_active: bool = True,
    ):
        return WorkspaceMembership.objects.create(
            user=user,
            workspace=workspace,
            role=role,
            is_active=is_active,
        )

    @staticmethod
    def create_catalog_entry(
        workspace: Workspace,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        status: str = CatalogEntry.StatusChoices.ACTIVE,
        summary: str = 'CatalogEntry summary',
        description: str = 'CatalogEntry description',
        available_states: Optional[list[str]] = None,
        sort_order: int = 0,
    ):
        name = name or f'CatalogEntry {random_string()}'
        return CatalogEntry.objects.create(
            workspace=workspace,
            name=name,
            slug=slug,
            status=status,
            summary=summary,
            description=description,
            available_states=available_states or [],
            sort_order=sort_order,
        )

    @staticmethod
    def create_item(
        catalog_entry: CatalogEntry,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        status: str = Item.StatusChoices.ACTIVE,
        summary: str = 'Item summary',
        description: str = 'Item description',
        sort_order: int = 0,
    ):
        name = name or f'Item {random_string()}'
        return Item.objects.create(
            catalog_entry=catalog_entry,
            name=name,
            slug=slug,
            status=status,
            summary=summary,
            description=description,
            sort_order=sort_order,
        )

    @staticmethod
    def create_contact(
        organization: Organization,
        email: Optional[str] = None,
        user: Optional[User] = None,
        first_name: str = '',
        last_name: str = '',
        phone: str = '',
        status: str = Contact.StatusChoices.ACTIVE,
    ):
        email = (email or f'{random_string().lower()}@contact.fake').lower()
        return Contact.objects.create(
            organization=organization,
            user=user,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            status=status,
        )

    @staticmethod
    def create_project_enrollment(
        contact: Contact,
        catalog_entry: CatalogEntry,
        status: str = ProjectEnrollment.StatusChoices.SURVEY_SUBMITTED,
    ):
        return ProjectEnrollment.objects.create(
            contact=contact,
            catalog_entry=catalog_entry,
            status=status,
        )
```

Builders stay explicit. Required foreign keys are positional or named parameters without defaults because the caller must decide ownership. Optional domain fields get stable defaults only when those values are not the point of most tests.

### Test Class Setup Keeps The Scenario Visible

```python
import pytest
from workspace.models import WorkspaceMembership
from tests.fixtures import FixtureFactory
from contact.views.contact.serializers import ContactOutputSerializer
from django.urls import reverse
from rest_framework import status
from tenancy.models import OrganizationMembership


@pytest.mark.django_db
class TestContactViews:
    def setup_method(self):
        self.organization_admin = FixtureFactory.create_user(email='organization-admin@example.com')
        self.workspace_operator = FixtureFactory.create_user(email='workspace-operator@example.com')
        self.outsider = FixtureFactory.create_user(email='outsider@example.com')

        self.organization = FixtureFactory.create_organization(name='Contact Organization', slug='contact-organization')
        self.other_organization = FixtureFactory.create_organization(name='Other Organization', slug='other-organization')
        self.workspace = FixtureFactory.create_workspace(self.organization, name='Primary Workspace', slug='primary-workspace')
        self.other_workspace = FixtureFactory.create_workspace(self.organization, name='Other Workspace', slug='other-workspace')
        self.other_organization_workspace = FixtureFactory.create_workspace(self.other_organization, name='Other Organization Workspace', slug='other-organization-workspace')

        FixtureFactory.create_organization_membership(self.organization_admin, self.organization, role=OrganizationMembership.RoleChoices.ADMIN)
        FixtureFactory.create_organization_membership(self.workspace_operator, self.organization, role=OrganizationMembership.RoleChoices.MEMBER)
        FixtureFactory.create_organization_membership(self.outsider, self.other_organization, role=OrganizationMembership.RoleChoices.ADMIN)
        self.workspace_operator_membership = FixtureFactory.create_workspace_membership(
            self.workspace_operator,
            self.workspace,
            role=WorkspaceMembership.RoleChoices.OPERATOR,
        )

        self.catalog_entry = FixtureFactory.create_catalog_entry(self.workspace, name='Operations Project', slug='weight-management')
        self.other_catalog_entry = FixtureFactory.create_catalog_entry(self.other_workspace, name='Support Project', slug='primary-care')
        self.other_organization_catalog_entry = FixtureFactory.create_catalog_entry(self.other_organization_workspace, name='Other Organization CatalogEntry', slug='other-organization-catalog_entry')

        self.contact = FixtureFactory.create_contact(self.organization, email='contact@example.com', first_name='Casey')
        self.other_contact = FixtureFactory.create_contact(self.organization, email='other@example.com', first_name='Jamie')
        self.other_organization_contact = FixtureFactory.create_contact(self.other_organization, email='other-organization@example.com')
        FixtureFactory.create_project_enrollment(self.contact, self.catalog_entry)
        FixtureFactory.create_project_enrollment(self.other_contact, self.other_catalog_entry)
        FixtureFactory.create_project_enrollment(self.other_organization_contact, self.other_organization_catalog_entry)

        self.list_url = reverse('contact:contact-list', kwargs={'organization_id': self.organization.id})
        self.workspace_list_url = reverse('contact:contact-list', kwargs={'organization_id': self.organization.id, 'workspace_id': self.workspace.id})

    def test_organization_admin_can_list_organization_contacts(self, client):
        client.force_login(self.organization_admin)

        response = client.get(self.list_url, content_type='application/json')

        expected = ContactOutputSerializer([self.contact, self.other_contact], many=True).data
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected

    def test_workspace_operator_only_lists_contacts_for_assigned_workspace(self, client):
        client.force_login(self.workspace_operator)

        response = client.get(self.list_url, content_type='application/json')

        expected = ContactOutputSerializer([self.contact], many=True).data
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected

    def test_outsider_cannot_view_other_organization_contacts(self, client):
        client.force_login(self.outsider)

        response = client.get(self.list_url, content_type='application/json')

        assert response.status_code == status.HTTP_404_NOT_FOUND
```

The shared builders remove repetitive field noise, but the setup still names each role, membership, in-scope record, and out-of-scope record. A reviewer can see exactly why the list endpoint should return one contact for an operator and two for an organization admin.

### Keep Feature-Specific Setup Local

```python
@pytest.mark.django_db
class TestTaskModel:
    def setup_method(self):
        self.user = FixtureFactory.create_user(email='task-model@example.com')
        self.task_name = Task.TaskNameChoices
        self.status = Task.StatusChoices

    def _create_task(self, name=None, data=None, status=None, percent_complete=0):
        return Task.objects.create(
            name=name or self.task_name.PURGE_OLD_TASKS,
            data=data or {},
            status=status or self.status.PENDING,
            percent_complete=percent_complete,
        )

    def test_create_singleton_task_reuses_existing_pending_task(self):
        existing_task = self._create_task(data={'source': 'existing'}, status=self.status.PENDING)

        task, created = Task.create_singleton_task(self.task_name.PURGE_OLD_TASKS, data={'source': 'new'})

        assert created is False
        assert task.id == existing_task.id
        assert task.data == {'source': 'existing'}
```

Local helpers are fine when the object is private to one test class or when sharing the helper would force a broad, weak abstraction. This `_create_task(...)` helper belongs near `Task` model tests because it is not a general domain builder.

### Avoid Catch-All Builders

```python
# Avoid this shape.
class FixtureFactory:
    @staticmethod
    def create_contact(**kwargs):
        organization = kwargs.pop('organization', FixtureFactory.create_organization())
        defaults = {
            'email': f'{random_string()}@contact.fake',
            'first_name': '',
            'last_name': '',
            'status': 'ACTIVE',
        }
        defaults.update(kwargs)
        return Contact.objects.create(organization=organization, **defaults)
```

This hides the ownership boundary by silently creating an organization. It also accepts any field name, so misspelled parameters become runtime surprises and reviewers cannot tell which fields are intentional.

Prefer the explicit version:

```python
class FixtureFactory:
    @staticmethod
    def create_contact(
        organization: Organization,
        email: Optional[str] = None,
        user: Optional[User] = None,
        first_name: str = '',
        last_name: str = '',
        phone: str = '',
        status: str = Contact.StatusChoices.ACTIVE,
    ):
        email = (email or f'{random_string().lower()}@contact.fake').lower()
        return Contact.objects.create(
            organization=organization,
            user=user,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            status=status,
        )
```

### Do Not Hide Assertions Or Permissions In Builders

```python
# Avoid this shape.
class FixtureFactory:
    @staticmethod
    def create_authorized_workspace_admin(organization=None, workspace=None):
        organization = organization or FixtureFactory.create_organization()
        workspace = workspace or FixtureFactory.create_workspace(organization)
        user = FixtureFactory.create_user()
        FixtureFactory.create_organization_membership(user, organization, role=OrganizationMembership.RoleChoices.MEMBER)
        FixtureFactory.create_workspace_membership(user, workspace, role=WorkspaceMembership.RoleChoices.ADMIN)
        return user
```

That helper hides the scenario name, silently chooses organization and workspace scope, and makes it harder to add a lower-permission user or other-organization user beside it. Prefer visible setup in the test class:

```python
self.workspace_admin = FixtureFactory.create_user(email='workspace-admin@example.com')
self.workspace_operator = FixtureFactory.create_user(email='workspace-operator@example.com')

FixtureFactory.create_organization_membership(self.workspace_admin, self.organization, role=OrganizationMembership.RoleChoices.MEMBER)
FixtureFactory.create_organization_membership(self.workspace_operator, self.organization, role=OrganizationMembership.RoleChoices.MEMBER)
FixtureFactory.create_workspace_membership(self.workspace_admin, self.workspace, role=WorkspaceMembership.RoleChoices.ADMIN)
FixtureFactory.create_workspace_membership(self.workspace_operator, self.workspace, role=WorkspaceMembership.RoleChoices.OPERATOR)
```

The membership builders create rows. The test decides which user logs in, which request is made, and whether the expected result is `200`, `403`, or hidden-resource `404`.

## Things To Notice

- Shared builders live in one reusable module, usually `tests/fixtures.py` or an equivalent shared helper.
- Builder names use the direct model concept: `create_organization`, `create_workspace`, `create_catalog_entry`, `create_item`, `create_contact`, `create_organization_membership`.
- Required relationships are explicit parameters. A `Workspace` builder requires a `organization`; an `CatalogEntry` builder requires a `workspace`; a `Item` builder requires an `catalog_entry`.
- Defaults are realistic domain defaults, such as active statuses, stable summaries, empty optional contact fields, and generated emails.
- Tests create both in-scope and out-of-scope records when the behavior depends on ownership.
- Membership builders create the membership row only. They do not log users in, grant hidden privileges, make requests, or assert response behavior.
- Feature-specific local helpers are acceptable when they are private to one test class and clearer than expanding `tests/fixtures.py`.
- Assertions, permission expectations, serializer comparisons, and HTTP status decisions stay in tests.

## Rules To Follow

- Add reusable Django object builders to `backend/tests/fixtures.py` or the repository's equivalent shared fixture module.
- Name builders `create_<model_or_domain_object>` and keep the name aligned with the object being returned.
- Require ownership relationships as parameters instead of creating parent records inside the builder.
- Keep builder signatures explicit with named parameters. Do not use catch-all `**kwargs` for ordinary model fields.
- Use `Optional[...]` rather than `|` union syntax in builder type hints.
- Give optional fields sensible defaults only when those defaults represent normal test data and are not hiding important behavior.
- Use model choice constants for default statuses and roles when they are available.
- Do not put assertions, HTTP calls, `client.force_login(...)`, permission expectations, or serializer comparisons inside shared builders.
- Do not create "authorized user" mega-builders that bundle user, organization, workspace, membership, and permissions into one opaque return value.
- Keep permission and membership setup visible in `setup_method` when the test is proving access control.
- Prefer local helper methods for one-off setup that is unique to a model, serializer, or feature test class.
- Move repeated local setup into a shared builder only after several tests need the same object construction and the builder can keep an explicit, narrow signature.

## Refactor Signals

- Several test modules repeat the same raw `Model.objects.create(...)` calls for a common domain object.
- A test-local builder for an organization, workspace, catalog_entry, item, contact, enrollment, order, coupon, or survey object appears in more than one module.
- A shared builder accepts `**kwargs` and passes them directly to `Model.objects.create(...)`.
- A builder silently creates parent records such as organization, workspace, catalog_entry, contact, or enrollment when those relationships are ownership boundaries.
- A builder returns a full scenario bundle or tuple where the caller cannot quickly tell which user, organization, workspace, and records were created.
- A helper named like `create_admin_user(...)` or `create_authorized_operator(...)` hides membership setup that should be visible in the test.
- Tests rely on builder side effects for permissions but do not show which role or membership grants access.
- A shared builder contains assertions, HTTP client calls, route reversing, serializer expectations, monkeypatching, or feature-specific validation rules.
- Multiple tests duplicate a long, identical object graph, but a focused builder for the reusable leaf object would remove the repetition.
- A local helper grows beyond one test class or starts accepting many optional flags to serve unrelated scenarios.

## Verification

- For a guidance-only edit, inspect Markdown frontmatter, headings, and code fences instead of running backend test suites.
- Check that Python snippets follow repository conventions: explicit imports, single quotes, `Optional[...]`, no catch-all `**kwargs`, and no hidden parent creation for owned records.
- Check that the example does not conflict with `agents/guidance/frameworks/django/guidance.md`, the view-test example, or the serializer-test example.
- When changing actual fixture code, run `ruff check backend/tests/fixtures.py` and the smallest affected pytest target.
- When practical for guidance authoring, run the guidance build:

```bash
python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean
```

## Why It Helps

- Shared setup becomes consistent without turning every feature test into its own factory island.
- Explicit relationships make ownership and organization scope easy to audit.
- Visible membership setup keeps permission tests readable and reduces accidental access-control gaps.
- Focused builders make duplicated setup cheap to remove without creating broad abstractions that future tests have to work around.
- Future contributors can add new tests by composing obvious domain builders and keeping the behavior-specific setup beside the assertions.
