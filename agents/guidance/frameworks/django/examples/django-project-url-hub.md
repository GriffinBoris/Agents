---
id: framework-django-example-project-url-hub
title: Django Project URL Hub Example
description: Example project-root URL module that keeps only top-level site, admin, docs, and include hubs.
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
order: 4
---

# Django Project URL Hub Example

## Scenario

- Use this pattern when a Django project's root URL module needs to expose the site shell, Django admin, developer-only admin tools, API entrypoints, and generated API documentation without becoming a feature router.
- Use this pattern when production serves a same-origin SPA index through Django while API traffic stays under `/api/`.
- Use this pattern when a project is large enough to need a project-root URL module, an API hub, app-level URL hubs, and feature-local URL modules.
- Use this pattern when a tiny group of authentication routes exists but has not yet grown into its own app-level module.
- Use the app URL hub and feature URL module examples for deeper routing below the API hub; this example is only about the top-level boundary.

## Why This Shape Exists

- The project root is the first routing boundary every request crosses. If feature routes live there, reviewers have to scan unrelated admin, docs, auth, organization, workspace, contact, order, and public-survey paths in one file.
- A thin project-root router keeps ownership visible. The root decides which broad area owns a prefix; apps and feature packages decide the detailed route list.
- Same-origin production SPA serving needs one predictable index route while preserving `/api/`, `/admin/`, docs, schema, static, and media behavior.
- Generated schema and documentation are cross-cutting API surfaces, but they are still API concerns. In larger projects, they belong in the API hub instead of being scattered through the project root.
- Route order is security and correctness work, not style. Specific admin/dev routes and API routes must appear before broad includes or SPA catch-alls so Django never hands an API or admin request to the frontend shell.
- Tiny auth route groups are acceptable only while they are genuinely tiny and cohesive. Once user auth, session state, onboarding, invitations, password reset, and access bootstrap routes grow, they need their own URL module or hub.

## Recommended Shape

### Project Root Owns Only Top-Level Boundaries

```python
# backend/core/urls.py

from core.views.index import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
	path('', views.index),
	path('admin/dev/', include('dev.urls')),
	path('admin/', admin.site.urls),
	path('api/', include('core.api.urls')),
]

if settings.DEBUG:
	urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

The project root is an include map. It owns:

- the same-origin SPA index route
- the Django admin boundary
- developer-only admin tooling when enabled by project settings and local routing
- the single `/api/` include boundary
- development media serving when `DEBUG` is true

It does not own organization, workspace, contact, order, item, survey, billing, or other feature routes.

### API Hub Owns API Families, Schema, And Docs

```python
# backend/core/api/urls.py

from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
	path('invitations/', include('tenancy.views.public_invitation.urls', namespace='invitations')),
	path('public/survey-forms/', include('survey.views.public_survey.urls', namespace='public-survey')),
	path('public/survey-sessions/', include('survey.views.public_runtime.urls', namespace='public-survey-runtime')),
	path('organizations/', include('core.organizations.urls')),
	path('user/', include('core.user.urls')),
	path('schema/', SpectacularAPIView.as_view(), name='schema'),
	path('schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
	path('schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
```

The API hub is the first place where API concerns are named. It can include public API families, organization-scoped API families, session/user routes, and generated schema or docs. Keeping these under `/api/` gives clients a stable prefix and keeps the project root focused.

For very small projects, `api/schema/` and `api/schema/swagger-ui/` may live directly in the project-root URL file. Move them into an API hub once the root also includes multiple app or domain route families.

### Organization Or Domain Hub Delegates To Apps

```python
# backend/core/organizations/urls.py

from django.urls import include, path

urlpatterns = [
	path('', include('tenancy.urls')),
	path('<int:organization_id>/', include('contact.urls')),
	path('<int:organization_id>/', include('coupon.urls')),
	path('<int:organization_id>/', include('notification_template.urls')),
	path('<int:organization_id>/', include('order.urls')),
	path('<int:organization_id>/', include('partner.urls')),
	path('<int:organization_id>/catalog-entries/', include('catalog_entry.views.organization_catalog_entry.urls')),
	path('<int:organization_id>/workspaces/', include('workspace.urls')),
]
```

The project root should not know every organization-scoped feature. An organization or domain hub owns the route-scoped identity and delegates to app-level hubs. This lets organization, workspace, catalog_entry, contact, order, and survey routes grow without expanding the project root.

### App And Feature Routes Stay Below The Hub

```python
# backend/order/urls.py

from django.urls import include, path

app_name = 'order'

urlpatterns = [
	path('orders/', include('order.views.order.urls')),
	path('workspaces/<int:workspace_id>/orders/', include('order.views.order.urls')),
	path('enrollments/<int:enrollment_id>/approved-plans/<int:approved_plan_id>/', include('order.views.approved_plan_order.urls')),
	path('workspaces/<int:workspace_id>/enrollments/<int:enrollment_id>/approved-plans/<int:approved_plan_id>/', include('order.views.approved_plan_order.urls')),
]
```

```python
# backend/order/views/order/urls.py

from django.urls import path
from order.views.order import views

urlpatterns = [
	path('list/', views.OrderListView.as_view(), name='order-list'),
	path('<int:order_id>/', views.OrderDetailView.as_view(), name='order-detail'),
]
```

This is the layering the project root is protecting:

- project root chooses `/api/`
- API hub chooses `organizations/`
- organization hub chooses `<int:organization_id>/`
- app hub chooses `orders/` or `workspaces/<int:workspace_id>/orders/`
- feature module chooses `list/` and `<int:order_id>/`

### Tiny Auth Route Groups Are Acceptable Until They Grow

```python
# acceptable in a small project-root module while the group is tiny

from core.views.user_auth import views
from django.urls import include, path

user_urlpatterns = [
	path('login/', views.LoginView.as_view(), name='user-login'),
	path('logout/', views.LogoutView.as_view(), name='user-logout'),
]

urlpatterns = [
	path('api/user/', include(user_urlpatterns)),
]
```

Inline route lists should remain an exception for very small, cohesive route groups. Once the user surface includes registration, password reset, bootstrap, onboarding, invitation acceptance, settings, or profile routes, split it into modules.

```python
# backend/core/user/urls.py

from django.urls import include, path

urlpatterns = [
	path('', include('core.views.user_auth.urls')),
	path('', include('core.views.user_state.urls')),
	path('onboarding/', include('core.views.user_onboarding.urls')),
]
```

The split keeps auth, session state, and onboarding from turning the project root into an account-management router.

### Same-Origin SPA Index Stays Thin

```python
# backend/core/views/index/views.py

from django.conf import settings
from django.shortcuts import render


def index(request):
	context = {
		'is_authenticated': request.user.is_authenticated,
		'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
	}

	return render(request, settings.DEFAULT_INDEX_TEMPLATE_PATH, context=context)
```

The index route renders the frontend shell and small server-owned boot values. Route data, organization access, workspace access, permissions, and user bootstrap state belong in `/api/user/bootstrap/`, not in the template context.

If the production SPA uses browser history routes that Django must serve directly, put a catch-all after every admin, docs, schema, static, media, and API route:

```python
from core.views.index import views
from django.contrib import admin
from django.urls import include, path, re_path

urlpatterns = [
	path('admin/', admin.site.urls),
	path('api/', include('core.api.urls')),
	path('', views.index),
	re_path(r'^(?!api/|admin/|static/|media/).*$', views.index),
]
```

Do not place a broad SPA catch-all before `/api/` or `/admin/`. A catch-all is only safe when it is last and explicitly excludes backend-owned prefixes.

### Avoid Feature Routes In The Project Root

```python
# avoid this shape

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView
from core.views.index import views as index_views
from order.views.order import views as order_views
from item.views.item import views as item_views

urlpatterns = [
	path('', index_views.index),
	path('admin/', admin.site.urls),
	path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
	path('api/organizations/<int:organization_id>/orders/list/', order_views.OrderListView.as_view(), name='order-list'),
	path('api/organizations/<int:organization_id>/orders/<int:order_id>/', order_views.OrderDetailView.as_view(), name='order-detail'),
	path('api/organizations/<int:organization_id>/workspaces/<int:workspace_id>/items/list/', item_views.ItemListView.as_view(), name='item-list'),
	path('api/organizations/<int:organization_id>/workspaces/<int:workspace_id>/items/create/', item_views.ItemCreateView.as_view(), name='item-create'),
	path('api/user/', include('core.user.urls')),
]
```

This file now owns index rendering, admin, schema, auth, organization identity, workspace identity, order routes, and item routes. Move the feature routes down to API, organization, app, and feature URL modules.

### Route Contract Tests

```python
from django.urls import reverse
from order.views.approved_plan_order import urls as approved_plan_order_urls
from order.views.order import urls as order_urls


class TestOrderRoutes:
	def setup_method(self):
		self.organization_id = 10
		self.workspace_id = 20
		self.enrollment_id = 30
		self.approved_plan_id = 40
		self.order_id = 50

	def test_routes_follow_contract(self):
		assert reverse('order:order-list', kwargs={'organization_id': self.organization_id}) == f'/api/organizations/{self.organization_id}/orders/list/'
		assert reverse('order:order-detail', kwargs={'organization_id': self.organization_id, 'order_id': self.order_id}) == f'/api/organizations/{self.organization_id}/orders/{self.order_id}/'
		assert reverse(
			'order:order-create-from-approved-plan',
			kwargs={
				'organization_id': self.organization_id,
				'workspace_id': self.workspace_id,
				'enrollment_id': self.enrollment_id,
				'approved_plan_id': self.approved_plan_id,
			},
		) == (
			f'/api/organizations/{self.organization_id}/workspaces/{self.workspace_id}/'
			f'enrollments/{self.enrollment_id}/approved-plans/{self.approved_plan_id}/orders/create/'
		)
		assert [pattern.name for pattern in order_urls.urlpatterns] == ['order-list', 'order-detail']
		assert [pattern.name for pattern in approved_plan_order_urls.urlpatterns] == ['order-create-from-approved-plan']
```

Route tests are valuable when nested includes are deep, when route order matters, or when a refactor moves routes between hubs. Use `reverse(...)` instead of hard-coded URLs in ordinary view tests, but route contract tests may assert the final path string when the URL itself is part of the frontend contract.

## Things To Notice

- The project root delegates `/api/` to `core.api.urls`; it does not include individual organization, workspace, order, item, survey, or contact feature modules.
- The API hub owns API documentation routes such as `schema/`, `schema/swagger-ui/`, and `schema/redoc/` so generated docs remain under the API prefix.
- The same-origin SPA index route is thin and only renders the shell. Session, CSRF, user, organization, workspace, and permission state are fetched through API routes.
- Developer-only admin tools use a specific route such as `admin/dev/` before the broader `admin/` boundary.
- `static(settings.MEDIA_URL, ...)` is appended only under `DEBUG`; production media serving does not belong in the project root URL module.
- Nested route ownership is visible by reading one file at a time: project root, API hub, organization hub, app hub, feature route module.
- Inline `user_urlpatterns` are only for tiny cohesive groups. A growing user surface gets a dedicated hub such as `core.user.urls`.
- Broad SPA catch-alls are last and exclude backend-owned prefixes.
- Route tests assert both final `reverse(...)` paths and local feature route order when URL shape is a contract.

## Rules To Follow

- Keep the project-root URL module limited to index, admin, developer-admin boundaries, docs or schema boundaries for small projects, top-level API includes, and debug-only static or media serving.
- Prefer `path('api/', include('core.api.urls'))` over adding many `api/...` feature paths to the project root.
- Put generated API schema and docs in the API hub once the project has one.
- Put organization, workspace, contact, order, item, survey, billing, notification, and other feature routes below API, domain, app, and feature URL modules.
- Give each app-level URL module an `app_name` when it is reversed by namespace.
- Keep feature-local route names kebab-case and use the established `-list`, `-create`, `-detail`, and action suffixes.
- Put more specific routes before broader includes and put SPA catch-alls last.
- Do not put route-owned organization or workspace identity in query params when the route hierarchy already owns that identity.
- Do not let a catch-all index route handle `/api/`, `/admin/`, `/api/schema/`, docs, static, or media paths.
- Keep same-origin SPA rendering separate from API bootstrap. Template context may include tiny server-owned boot values; user, organization, workspace, and permission data should come from an API endpoint.
- Move inline auth route groups into dedicated modules when they grow beyond a tiny login/logout style pair or start mixing auth, session state, onboarding, password reset, and invitation concerns.
- Add route contract tests when changing nested includes, namespaces, route order, schema/docs placement, or SPA catch-all behavior.

## Refactor Signals

- The project-root `urlpatterns` contains model or feature view imports such as `OrderListView`, `ItemCreateView`, `ContactDetailView`, or `SurveyFormTransitionView`.
- The project-root URL module has many `api/organizations/<int:organization_id>/...` paths instead of one `/api/` include.
- A new app route is added to `core/urls.py` instead of the API hub, organization hub, app hub, or feature route module.
- Schema or Swagger routes are duplicated across both project root and API hub.
- A route named for one feature sits beside unrelated route families because there is no app-level `urls.py`.
- A broad `re_path` or catch-all index route appears before `/api/` or `/admin/`.
- The index view starts loading route data, organization records, permission matrices, or current-user details that should come from bootstrap APIs.
- Inline auth URL lists contain registration, password reset, bootstrap, onboarding, or invitation flows.
- Tests hard-code long route strings in ordinary view tests because nested route names are unclear or missing namespaces.
- A feature URL module cannot be summarized in one sentence because it mixes unrelated app, domain, and project-root concerns.

## Verification

- For URL behavior changes, add or update route contract tests that call `reverse(...)` for representative list, create, detail, and action routes.
- When route ordering matters, import the local URL module and assert the relevant `pattern.name` or `pattern.pattern._route` sequence.
- When adding a same-origin SPA catch-all, test that `/api/...`, `/admin/...`, schema, and docs URLs still resolve to backend views before the index fallback.
- When moving schema or docs routes, test `reverse('schema')`, `reverse('swagger-ui')`, and any docs route names that the project exposes.
- When changing a guidance-only Markdown example, inspect frontmatter, heading order, and fenced code blocks instead of running backend test suites.
- Run the guidance builder when practical:

```bash
python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean
```

- Before review, confirm the generated guidance metadata still lists this example under Django URL examples and that the document does not conflict with the app URL hub, feature URL module, session-CSRF-SPA, or view-test examples.

## Why It Helps

- The project root stays small enough to audit during security, deployment, and routing reviews.
- Feature teams can change app and feature routes without editing the highest-level router.
- Deep organization and workspace routes keep their ownership boundary visible without making the project root understand every domain.
- Generated schema and docs stay discoverable under the API prefix.
- Same-origin SPA serving works without stealing API or admin requests.
- Route names stay stable for frontend clients, tests, and `reverse(...)` callers.
- Refactors become safer because route contract tests catch accidental path, namespace, and ordering changes.
