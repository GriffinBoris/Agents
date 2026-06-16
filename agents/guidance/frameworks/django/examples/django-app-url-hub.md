---
id: framework-django-example-app-url-hub
title: Django App URL Hub Example
description: Example app-root URL module that stays thin and delegates to feature URL packages.
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
order: 6
---

# Django App URL Hub Example

## Scenario

- Use this pattern when a Django app has enough API surface that features should own their own `urls.py` modules while the app root stays as a routing hub.
- Use it when an app is included under organization, workspace, catalog_entry, contact, order, or other parent prefixes and the app needs one stable namespace for `reverse(...)`.
- Use it when feature-local URL modules live beside feature views and serializers, such as `item.views.item.urls` and `item.views.item_option.urls`.
- Use it when an app needs nested include prefixes, such as item variants under `<int:item_id>/variants/` or approved plans under `<int:enrollment_id>/approved-plans/`.

## Why This Shape Exists

- The app-root `urls.py` is the boundary between the project or API router and feature-local route modules. It should explain the app's public route map without owning every endpoint.
- `app_name` gives tests, views, templates, and clients a stable namespace. A route such as `reverse('contact:contact-detail', kwargs={...})` should keep working even when the route is included below `/api/organizations/<organization_id>/`.
- `include(...)` lets feature packages own their detailed route lists next to the views they serve. That keeps app roots from becoming large flat files that import every feature view class.
- Nested prefixes keep parent identifiers explicit in the URL. The app hub owns the parent path segment, and the feature module owns the leaf list/create/detail/action routes below that segment.
- The tradeoff is one more small URL file per feature, but the payoff is clearer ownership and easier route review as the app grows.

## Recommended Shape

### App Root As Thin Include Hub

```python
from django.urls import include, path

app_name = 'item'

urlpatterns = [
	path('<int:item_id>/variants/', include('item.views.item_option.urls')),
	path('', include('item.views.item.urls')),
]
```

The app root imports only `include` and `path`, defines `app_name`, and delegates to feature URL modules. It does not import `ItemListView`, `ItemOptionDetailView`, serializers, permissions, or models.

### Feature Module Owns Leaf Routes

```python
from django.urls import path
from item.views.item import views

urlpatterns = [
	path('list/', views.ItemListView.as_view(), name='item-list'),
	path('create/', views.ItemCreateView.as_view(), name='item-create'),
	path('<int:item_id>/', views.ItemDetailView.as_view(), name='item-detail'),
]
```

```python
from django.urls import path
from item.views.item_option import views

urlpatterns = [
	path('list/', views.ItemOptionListView.as_view(), name='item-option-list'),
	path('create/', views.ItemOptionCreateView.as_view(), name='item-option-create'),
	path('<int:variant_id>/', views.ItemOptionDetailView.as_view(), name='item-option-detail'),
]
```

The feature module owns the endpoint names and view imports. At the app layer, those route names contribute to the app namespace:

```python
reverse(
	'item:item-option-detail',
	kwargs={'item_id': item.id, 'variant_id': variant.id},
)
```

When the app hub is nested below other hubs, the namespace composes into the full include chain, such as `workspace:catalog_entry:item:item-option-detail`.

### Group Related Features Under Parent Prefixes

```python
from django.urls import include, path

app_name = 'contact'

urlpatterns = [
	path('contacts/', include('contact.views.contact.urls')),
	path('workspaces/<int:workspace_id>/contacts/', include('contact.views.contact.urls')),
	path('contacts/<int:contact_id>/addresses/', include('contact.views.contact_address.urls')),
	path('workspaces/<int:workspace_id>/contacts/<int:contact_id>/addresses/', include('contact.views.contact_address.urls')),
	path('enrollments/', include('contact.views.enrollment.urls')),
	path('workspaces/<int:workspace_id>/enrollments/', include('contact.views.enrollment.urls')),
	path('enrollments/<int:enrollment_id>/approved-plans/', include('contact.views.approved_plan.urls')),
	path('workspaces/<int:workspace_id>/enrollments/<int:enrollment_id>/approved-plans/', include('contact.views.approved_plan.urls')),
]
```

Use repeated includes when the same feature supports both app-wide and nested scoped entry points. Keep the route-owned identifiers in the prefix so the view signature receives the full scope, such as `organization_id`, `workspace_id`, `contact_id`, or `enrollment_id`.

### Nested App Hubs Compose Namespaces

```python
from django.urls import include, path

app_name = 'workspace'

urlpatterns = [
	path('', include('workspace.views.workspace.urls')),
	path('<int:workspace_id>/rate-cards/', include('pricing.urls')),
	path('<int:workspace_id>/catalog-entries/', include('catalog_entry.urls')),
	path('<int:workspace_id>/memberships/', include('workspace.views.membership.urls')),
	path('<int:workspace_id>/invitations/', include('workspace.views.invitation.urls')),
]
```

```python
from django.urls import include, path

app_name = 'catalog_entry'

urlpatterns = [
	path('<int:catalog_entry_id>/service-networks/', include('partner.views.catalog_entry_service_network.urls')),
	path('<int:catalog_entry_id>/vendors/', include('partner.views.catalog_entry_vendor.urls')),
	path('', include('catalog_entry.views.catalog_entry.urls')),
	path('<int:catalog_entry_id>/subscription-plans/', include('pricing.views.catalog_entry_subscription_plan.urls')),
	path('<int:catalog_entry_id>/items/', include('item.urls')),
	path('<int:catalog_entry_id>/survey-forms/', include('survey.urls')),
]
```

Nested hubs make namespaces compose naturally:

```python
reverse(
	'workspace:catalog_entry:survey:survey-form-version-detail',
	kwargs={
		'organization_id': organization.id,
		'workspace_id': workspace.id,
		'catalog_entry_id': catalog_entry.id,
		'survey_form_id': survey_form.id,
		'version_id': version.id,
	},
)
```

The namespace chain mirrors the include chain. Reviewers can move from `workspace.urls` to `catalog_entry.urls` to `survey.urls` to the feature-local module without searching through unrelated endpoints.

### App-Level Route Contract Tests

```python
from django.urls import reverse
from item import urls as item_urls


def test_item_app_routes_follow_expected_contract(organization, workspace, catalog_entry, item, variant):
	assert item_urls.app_name == 'item'
	assert [pattern.pattern._route for pattern in item_urls.urlpatterns] == [
		'<int:item_id>/variants/',
		'',
	]

	detail_url = reverse(
		'workspace:catalog_entry:item:item-option-detail',
		kwargs={
			'organization_id': organization.id,
			'workspace_id': workspace.id,
			'catalog_entry_id': catalog_entry.id,
			'item_id': item.id,
			'variant_id': variant.id,
		},
	)

	assert detail_url == (
		f'/api/organizations/{organization.id}/workspaces/{workspace.id}/catalog-entries/{catalog_entry.id}/items/{item.id}/'
		f'variants/{variant.id}/'
	)
```

Most view tests should build URLs with `reverse(...)` and then assert behavior. Add an app-level route contract assertion when route shape, include order, or namespace composition is easy to regress.

## Things To Notice

- The app-root URL file stays thin and mostly delegates prefixes to feature URL modules.
- Feature packages keep ownership of their detailed route lists.
- `app_name` lives at the app hub so `reverse('item:item-list')`, `reverse('contact:contact-detail')`, and nested names such as `reverse('workspace:catalog_entry:survey:...')` have stable namespaces.
- Nested parent identifiers live in the include prefix, not duplicated in every feature route.
- Feature-local modules import their own `views` module and define route names such as `item-list`, `item-create`, and `item-detail`.
- App hubs use `include('package.path.urls')` strings so the app root does not import every feature view class.
- Route names stay kebab-case and action-oriented. The namespace identifies the app or nested app, while the route name identifies the feature endpoint.
- Feature modules can stay un-namespaced when they are always included through the app hub. Give a feature module its own `app_name` only when it is deliberately used as an independent namespace.

## Rules To Follow

- Every Django app URL hub needs `app_name` unless the file is a private include-only helper that is never reversed as an app.
- Keep app-root `urls.py` files thin: import `include` and `path`, set `app_name`, and list include prefixes.
- Do not import every feature view into the app-root `urls.py`. View imports belong in feature-local URL modules.
- Group feature routes by domain package, such as `views/item/urls.py`, `views/item_option/urls.py`, or `views/contact_address/urls.py`.
- Put parent identifiers in the include prefix when the parent scope applies to every route in that feature module.
- Use nested include prefixes for nested resources instead of repeating parent path fragments inside every leaf route.
- Keep route names kebab-case and predictable, normally ending in `-list`, `-create`, `-detail`, or a concrete action such as `-transition`, `-publish`, or `-validate`.
- Build tests and internal callers with `reverse(...)` and the app namespace instead of hard-coded paths.
- Add narrow route contract assertions when changing include order, adding nested app namespaces, or exposing the same feature under multiple prefixes.
- Keep project/API root URL files responsible for top-level includes only. App hubs should own app-level feature grouping, and feature modules should own concrete endpoint names.
- Avoid generic catch-all URL files such as `common/urls.py` or `api_urls.py` when a domain-specific app or feature module can own the routes.

## Refactor Signals

- An app-root `urls.py` imports many view classes and has a long flat `urlpatterns` list.
- The same parent prefix, such as `<int:workspace_id>/` or `<int:catalog_entry_id>/`, is repeated across many feature-local routes instead of being owned by the app hub include prefix.
- Feature routes for one domain are scattered across the project root, app root, and unrelated feature modules.
- Tests hard-code endpoint paths repeatedly instead of using `reverse('app:route-name', kwargs={...})`.
- Route names are duplicated, camelCase, or unclear about whether they are list, create, detail, or action endpoints.
- A feature module has its own `app_name` but the intended reverse name should be app-scoped, causing unnecessary namespace depth.
- An app hub lacks `app_name`, so callers cannot use a stable app namespace.
- A new nested resource is added by inserting more leaf routes into the app root instead of creating or reusing a feature-local URL module.
- Reviewers cannot summarize the app's route groups by scanning the app-root `urlpatterns`.

## Verification

- For guidance-only edits, verify frontmatter, headings, and code fences in the changed markdown file.
- For URL code changes, run the smallest affected view test target, such as:

```bash
pytest backend/item/tests/test_item_views.py::TestItemViews
```

- Add or update focused route contract tests when the change affects path prefixes, `app_name`, include ordering, nested namespace composition, or duplicate route exposure.
- Use `reverse(...)` in tests to verify the route contract and add one exact-path assertion only when the literal URL shape is part of the public API.
- Run `ruff check` on modified Python URL or test files when code changes accompany the guidance.
- For guidance build verification, run:

```bash
python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean
```

## Why It Helps

- Routing stays organized by app and feature instead of becoming one long ungrouped file.
- App-level namespaces keep tests, redirects, and internal callers stable while project-level prefixes evolve.
- Feature packages can grow independently without expanding the app root into a god module.
- Nested resource routes remain auditable because parent scope is visible in the include chain.
- Route contract tests catch accidental namespace, prefix, and include-order regressions before clients or frontend code break.
