---
id: framework-django-example-feature-url-module
title: Django Feature URL Module Example
description: Example feature-local URL module with predictable REST-style and action routes.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - urls
applies_to:
  - django
status: active
order: 7
---

# Django Feature URL Module Example

## Scenario

- Use this pattern when a Django feature package owns its own `views.py`, `serializers.py`, and route list.
- Use this pattern when an app-root `urls.py` delegates to feature packages such as `contact.views.contact.urls`, `workspace.views.invitation.urls`, or `survey.views.survey_form.urls`.
- Use this pattern when routes are nested under organization, workspace, catalog_entry, contact, enrollment, survey form, item, or other parent resources.
- Use this pattern when a feature exposes ordinary list, create, and detail endpoints plus command-style actions such as transition, resend, revoke, activate, deactivate, link, unlink, preview, or retry.

## Why This Shape Exists

- Feature-local URL modules keep routing beside the views and serializers that implement the feature. A reviewer can open one package and see the route contract, request handlers, and payload shape together.
- App-root URL modules stay thin routing hubs. They should decide feature prefixes and namespace boundaries, not own every endpoint in a growing app.
- Nested URL identifiers make ownership explicit at the API boundary. The URL says which organization, workspace, catalog_entry, contact, enrollment, or parent record scopes the child resource before the view reads request data.
- Predictable route names make `reverse(...)` calls stable in tests and views. They also make route audits faster because list, create, detail, and action endpoints can be found by name.
- Kebab-case path segments and route names match the repository's public API style while Python package names remain snake_case.
- Contract tests catch accidental route drift before frontend API clients, nested includes, or permission-scoped view tests fail in less obvious ways.

## Recommended Shape

### Feature Package Layout

```text
backend/contact/
	urls.py
	views/
		contact/
			serializers.py
			urls.py
			views.py
		contact_address/
			serializers.py
			urls.py
			views.py
		enrollment/
			serializers.py
			urls.py
			views.py
```

Keep feature API files together when the app has grown beyond a single small `views.py`. The feature folder owns the concrete endpoint list; the app root only includes it under the right prefix.

### App URL Hub

```python
from django.urls import include, path

app_name = 'contact'

urlpatterns = [
	path('', include('contact.views.contact.urls')),
	path('<int:contact_id>/addresses/', include('contact.views.contact_address.urls')),
	path('enrollments/', include('contact.views.enrollment.urls')),
]
```

Use the app-root `urls.py` as a hub. The hub owns `app_name`, top-level prefixes, and parent identifiers that apply to an included feature module. It should not import feature view classes or mix unrelated feature route lists inline.

### Simple Feature URL Module

```python
from contact.views.contact import views
from django.urls import path

urlpatterns = [
	path('list/', views.ContactListView.as_view(), name='contact-list'),
	path('create/', views.ContactCreateView.as_view(), name='contact-create'),
	path('<int:contact_id>/', views.ContactDetailView.as_view(), name='contact-detail'),
]
```

Import `path` from `django.urls` and import the local feature's `views` module directly. Keep the route names REST-style and kebab-case:

- `contact-list`
- `contact-create`
- `contact-detail`

Use the model or feature name as the route-name prefix. Use explicit lookup names such as `contact_id`, `workspace_id`, `enrollment_id`, `survey_form_id`, or `variant_id` instead of a generic `pk` when the identifier is part of a public route contract.

### Action Routes Beside CRUD Routes

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

Actions should live beside the CRUD routes they extend. Name command endpoints by the action they perform, such as `transition`, `resend`, `revoke`, `activate`, `deactivate`, `link`, `unlink`, `preview`, or `retry`.

### Nested Feature URL Module

```python
from django.urls import path
from survey.views.survey_mapping import views

urlpatterns = [
	path('list/', views.InputBindingMappingListView.as_view(), name='input-binding-mapping-list'),
	path('create/', views.InputBindingMappingCreateView.as_view(), name='input-binding-mapping-create'),
	path('preview/', views.InputBindingMappingPreviewView.as_view(), name='input-binding-mapping-preview'),
	path('<int:mapping_id>/', views.InputBindingMappingDetailView.as_view(), name='input-binding-mapping-detail'),
	path('targets/list/', views.MappingTargetListView.as_view(), name='mapping-target-list'),
	path('targets/create/', views.MappingTargetCreateView.as_view(), name='mapping-target-create'),
	path('targets/<int:target_id>/', views.MappingTargetDetailView.as_view(), name='mapping-target-detail'),
]
```

Nested child resources should keep parent identity in the path. If the app hub already supplies `organization_id`, `workspace_id`, `catalog_entry_id`, or `survey_form_id`, the feature module should add only the next resource identifiers it owns, such as `mapping_id` or `target_id`.

### Route Contract Tests

```python
from django.urls import reverse


def test_contact_routes_follow_contract(self):
	assert reverse('contact:contact-list', kwargs={'organization_id': self.organization.id}) == (
		f'/api/organizations/{self.organization.id}/contacts/list/'
	)
	assert reverse('contact:contact-create', kwargs={'organization_id': self.organization.id}) == (
		f'/api/organizations/{self.organization.id}/contacts/create/'
	)
	assert reverse(
		'contact:contact-detail',
		kwargs={'organization_id': self.organization.id, 'contact_id': self.contact.id},
	) == f'/api/organizations/{self.organization.id}/contacts/{self.contact.id}/'


def test_survey_form_action_route_follows_contract(self):
	assert reverse(
		'workspace:catalog_entry:survey:survey-form-transition',
		kwargs={
			'organization_id': self.organization.id,
			'workspace_id': self.workspace.id,
			'catalog_entry_id': self.catalog_entry.id,
			'survey_form_id': self.survey_form.id,
		},
	) == (
		f'/api/organizations/{self.organization.id}/workspaces/{self.workspace.id}/catalog-entries/'
		f'{self.catalog_entry.id}/survey-forms/{self.survey_form.id}/transition/'
	)
```

Use `reverse(...)` for normal test setup and client calls. Add exact string assertions when the route shape itself is a contract with the frontend, when a nested include is easy to wire incorrectly, or when a feature is being refactored into a package.

## Things To Notice

- The app-root hub owns `app_name`; included feature URL modules usually rely on that namespace instead of declaring their own.
- The feature module imports its local `views` module directly, such as `from contact.views.contact import views`.
- Python package names stay snake_case, while URL path segments and route names use kebab-case.
- Standard resource routes are immediately recognizable: `list/`, `create/`, and `<int:resource_id>/`.
- Route names end in `-list`, `-create`, and `-detail` for ordinary resource endpoints.
- Action route names end with the concrete action, such as `-transition`, `-resend`, `-revoke`, `-activate`, `-deactivate`, `-link`, `-unlink`, `-preview`, or `-retry`.
- Nested parent identifiers stay in the URL path, not headers, query params, or request body fields.
- Route tests use `reverse(...)` with named kwargs so test setup fails when a route contract changes.
- Feature-local URL modules match feature-local view packages; avoid placing one feature's routes in another feature's `urls.py`.

## Rules To Follow

- Put a feature-local `urls.py` beside that feature's `views.py` and `serializers.py` once the app uses feature packages.
- Keep app-root `urls.py` files thin: define `app_name`, include feature URL modules, and own only the prefixes that connect features together.
- Import `path` from `django.urls`.
- Import the feature's local `views` module directly. Do not import view classes from an unrelated app root or through broad re-export modules.
- Use REST-style route names for normal resources: `{resource}-list`, `{resource}-create`, and `{resource}-detail`.
- Use action route names for command endpoints: `{resource}-{action}` or `{resource-assignment}-{action}`.
- Use kebab-case for route names and URL path segments. Keep snake_case for Python packages and variable names.
- Include every parent identifier needed to scope the child resource in the URL path.
- Use explicit identifier names in route converters, such as `<int:contact_id>`, `<int:workspace_id>`, `<int:enrollment_id>`, `<int:survey_form_id>`, and `<int:variant_id>`.
- Build test URLs with `reverse(...)` and named kwargs.
- Add route contract tests when URL shape is externally consumed, deeply nested, newly refactored, or easy to miswire.
- Keep route order easy to scan: list, create, collection actions, detail, item actions, then child-resource groups when a feature owns them.

## Refactor Signals

- An app-root `urls.py` imports many feature view classes and contains a long flat endpoint list.
- A feature package has `views.py` and `serializers.py` but its routes live somewhere else.
- Route names mix underscores, camelCase, or vague names such as `get-items`, `do-action`, or `update-status`.
- Detail routes use `<int:pk>` even though tests, views, or frontend code treat the identifier as a named domain object.
- A child resource is scoped by query params or request body IDs when the parent identity belongs in the URL path.
- CRUD routes and action routes are split across unrelated files, making the feature's API contract hard to audit.
- Tests hard-code endpoint paths for normal client calls instead of using `reverse(...)`.
- No route contract test covers a nested include that combines organization, workspace, catalog_entry, survey form, or other parent identifiers.
- A feature URL module imports serializers, models, permissions, or services even though routing only needs view classes.
- A new feature adds a custom namespace inside the feature module without a clear standalone public API boundary.

## Verification

- Run a focused route test after changing URL modules, such as `pytest backend/contact/tests/test_views.py::TestContactViews::test_contact_routes_follow_contract`.
- Run the feature's view tests when route names, nested identifiers, or action endpoints change.
- Use `python manage.py check` when changing include boundaries or namespaces and a focused pytest target is not available.
- For documentation changes to this example, check that Markdown fences are balanced and rebuild generated guidance when practical:

```bash
python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean
```

## Why It Helps

- Feature routing stays close to the views and serializers it serves.
- App URL hubs remain readable as the API grows.
- Nested route scopes are visible and testable at the HTTP boundary.
- Predictable names make `reverse(...)` usage clear and keep frontend API contracts stable.
- Route contract tests catch accidental path, namespace, and kwarg changes early.
- Reviewers can audit a feature's full API surface without searching through unrelated route files.
