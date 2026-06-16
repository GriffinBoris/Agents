---
id: framework-django-example-app-layout
title: Django App Layout Example
description: North-star Django app layout standards for flat apps, feature packages, model packages, services, commands, and API boundaries.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - structure
applies_to:
  - django
status: active
order: 5
---

# Django App Layout Example

## Scenario

- Use this standard when creating a Django app, adding a new feature package, or deciding whether an existing app has outgrown a flat layout.
- Use this when an app is mixing domain models, admin registration, serializers, views, services, commands, and tests in files that are becoming hard to scan.
- Use this when deciding whether API transport should live inside the domain app, a feature-local `views/<feature>/` package, or a dedicated API hub such as `core/api/urls.py`.
- Use this during refactors that split god modules, catch-all files, or oversized `models.py`, `views.py`, `serializers.py`, and `urls.py` files into clearer ownership boundaries.

## Why This Shape Exists

- Django apps should start simple. A conventional app root with `models.py`, `views.py`, `serializers.py`, `urls.py`, `admin.py`, and `tests/` is easier to read than a deep package tree when the app has one resource and a small API surface.
- Feature packages become worthwhile when transport code grows by route family. Keeping `views.py`, `serializers.py`, `urls.py`, and feature-specific tests together makes one endpoint family auditable without opening every file in the app.
- Model packages become worthwhile when the domain has many model classes. One model per file keeps field declarations, choices, constraints, lifecycle helpers, and model tests easier to pair.
- Domain apps should own domain models and admin registration. API hubs should own cross-domain routing boundaries. Transport code may live in the domain app when it is feature-local, but project-level routing should stay thin and should not become the place where feature behavior accumulates.
- Service modules are for explicit workflow or integration boundaries. They prevent views, tasks, commands, and models from copying fragile orchestration, third-party calls, cleanup flows, or multi-step persistence.
- Management commands are first-class entrypoints for local data work, seeding, imports, exports, maintenance, and operational workflows. They belong under an app's `management/commands/` package instead of loose repo-root scripts.
- Minimal `__init__.py` files keep packages importable without hiding runtime behavior. Model-package `__init__.py` files may re-export model classes for Django discovery and normal `from app.models import Model` imports; other package `__init__.py` files should usually stay empty.

## Recommended Shape

### Small Or Medium Flat App

Use this when the app has one main domain resource, a short serializer/view surface, and a small number of tests. Keep the structure conventional until a real scanability problem appears.

```text
coupon/
├── __init__.py
├── admin.py
├── apps.py
├── migrations/
│   ├── __init__.py
│   └── 0001_initial.py
├── models.py
├── serializers.py
├── urls.py
├── views.py
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_serializers.py
    └── test_views.py
```

This is not a lesser structure. It is the right structure when one file per concern is still easy to understand. Do not introduce packages just because another app has them.

### Flat Domain App With A Single Feature Package

Use this when the app is still small overall but one route family has enough transport code to deserve local ownership. Keep app-root domain files and move only the feature API surface into `views/<feature>/`. Some existing apps keep feature tests in the app-root `tests/` package; that is acceptable until feature-local tests make ownership clearer.

```text
message/
├── __init__.py
├── admin.py
├── apps.py
├── migrations/
│   ├── __init__.py
│   └── 0001_initial.py
├── models.py
├── urls.py
├── views/
│   ├── __init__.py
│   └── message_template/
│       ├── __init__.py
│       ├── serializers.py
│       ├── urls.py
│       ├── views.py
│       └── tests/
│           ├── __init__.py
│           ├── test_serializers.py
│           └── test_views.py
└── tests/
    └── test_models.py
```

The app-root `tests/` folder owns app-wide model behavior. Feature-local tests own endpoint and serializer contracts for that feature package. If the local app already keeps all view tests in the app-root `tests/` package, follow that pattern until the feature surface becomes large enough to move tests beside the feature.

### Larger Domain App With Feature Packages And Services

Use this when the app owns several route families and has workflow logic shared by views, tasks, commands, or other domain services.

```text
survey/
├── __init__.py
├── admin.py
├── apps.py
├── migrations/
│   ├── __init__.py
│   └── 0001_initial.py
├── models/
│   ├── __init__.py
│   ├── SurveyForm.py
│   ├── SurveyFormVersion.py
│   └── SurveyPage.py
├── services/
│   ├── __init__.py
│   ├── clone_version.py
│   ├── component_validation.py
│   ├── survey_forms.py
│   └── publish_snapshot.py
├── urls.py
├── views/
│   ├── __init__.py
│   ├── common.py
│   ├── survey_form/
│   │   ├── __init__.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_serializers.py
│   │       └── test_views.py
│   ├── survey_page/
│   │   ├── __init__.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_serializers.py
│   │       └── test_views.py
│   └── public_runtime/
│       ├── __init__.py
│       ├── urls.py
│       └── views.py
└── tests/
    ├── __init__.py
    └── test_models.py
```

Keep `views/common.py` small and specific when a few feature packages share one rule. If it starts collecting unrelated queryset builders, serializer helpers, permission logic, and workflow utilities, split those concerns into feature packages or named service modules.

### Large Model Surface With A Models Package

Use this when `models.py` has become a catalog of unrelated model classes. model package filenames should match the model class name, such as `SurveyForm.py`, not snake_case names such as `survey_form.py`.

```text
survey/
├── models/
│   ├── __init__.py
│   ├── ComponentNode.py
│   ├── SurveyAnswer.py
│   ├── SurveyForm.py
│   ├── SurveyFormVersion.py
│   ├── SurveyPage.py
│   └── SurveySubmission.py
└── tests/
    ├── __init__.py
    ├── test_component_models.py
    └── test_models.py
```

```python
# backend/survey/models/__init__.py

from survey.models.ComponentNode import ComponentNode  # noqa: F401
from survey.models.SurveyAnswer import SurveyAnswer  # noqa: F401
from survey.models.SurveyForm import SurveyForm  # noqa: F401
from survey.models.SurveyFormVersion import SurveyFormVersion  # noqa: F401
from survey.models.SurveyPage import SurveyPage  # noqa: F401
from survey.models.SurveySubmission import SurveySubmission  # noqa: F401
```

This is an explicit export contract for model discovery and normal imports. Do not put query builders, runtime setup, signal registration, task wiring, or business workflows in `models/__init__.py`.

### Domain App URLs As Include Hubs

Keep app-root `urls.py` files thin. They should define `app_name` and delegate route families to feature-local URL modules.

```python
# backend/item/urls.py

from django.urls import include, path

app_name = 'item'

urlpatterns = [
	path('<int:item_id>/variants/', include('item.views.item_option.urls')),
	path('', include('item.views.item.urls')),
]
```

```python
# backend/survey/urls.py

from django.urls import include, path

app_name = 'survey'

urlpatterns = [
	path('<int:survey_form_id>/submissions/', include('survey.views.survey_submission.urls')),
	path('<int:survey_form_id>/versions/', include('survey.views.survey_version.urls')),
	path('', include('survey.views.survey_form.urls')),
]
```

Do not grow app-root URL files into long mixed lists of every list, create, detail, action, and nested route. The app root should show feature boundaries, not endpoint implementation details.

### Feature-Local API Package

Each feature package should contain the transport pieces needed to review that route family end to end.

```text
item/views/item_option/
├── __init__.py
├── serializers.py
├── urls.py
├── views.py
└── tests/
    ├── __init__.py
    ├── test_serializers.py
    └── test_views.py
```

```python
# backend/item/views/item_option/urls.py

from django.urls import path
from item.views.item_option import views

urlpatterns = [
	path('list/', views.ItemOptionListView.as_view(), name='item-option-list'),
	path('create/', views.ItemOptionCreateView.as_view(), name='item-option-create'),
	path('<int:variant_id>/', views.ItemOptionDetailView.as_view(), name='item-option-detail'),
]
```

Feature-local packages should not import through package-level `__init__.py` re-export tricks. Import the concrete module path so reviewers can jump directly to the owner.
Feature-local URL modules usually rely on the app-root `app_name` namespace; add a feature-level `app_name` only when that module is deliberately included as an independent namespace.

### Project API Hub And Domain Apps

Use a project API hub for top-level API namespaces, schema routes, public entrypoints, and cross-domain include boundaries.

```python
# backend/core/urls.py

from core.views.index import views
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
	path('', views.index),
	path('admin/', admin.site.urls),
	path('api/', include('core.api.urls')),
]
```

```python
# backend/core/api/urls.py

from django.urls import include, path

urlpatterns = [
	path('public/survey-forms/', include('survey.views.public_survey.urls', namespace='public-survey')),
	path('organizations/', include('core.organizations.urls')),
	path('user/', include('core.user.urls')),
]
```

The API hub should not own domain behavior. It chooses which app namespace handles a URL prefix. The domain app or feature package owns serializers, permissions, object lookup, persistence, and tests.

### Services And Commands

Put explicit multi-step workflows in named service modules when more than one entrypoint needs them or when the workflow is too large for a thin view.

```text
survey/services/
├── __init__.py
├── clone_version.py
├── component_validation.py
├── survey_forms.py
└── publish_snapshot.py
```

```python
# backend/survey/services/survey_forms.py

from django.db import transaction
from survey.models.ComponentNode import ComponentNode
from survey.models.SurveyForm import SurveyForm
from survey.models.SurveyFormVersion import SurveyFormVersion


def delete_or_archive_survey_form(instance: SurveyForm):
	if instance.submissions.exists():
		instance.status = SurveyForm.StatusChoices.ARCHIVED
		instance.save(update_fields=['status', 'updated_ts'])
		return False

	with transaction.atomic():
		ComponentNode.objects.filter(survey_form_version__survey_form=instance).delete()
		SurveyFormVersion.objects.filter(survey_form=instance).delete()
		instance.delete()

	return True
```

Put operational entrypoints in management commands, not in repo-root scripts.

```text
core/management/
├── __init__.py
└── commands/
    ├── __init__.py
    ├── seed_e2e_workspace.py
    └── wait_for_database.py
```

```python
# backend/core/management/commands/seed_e2e_workspace.py

from django.core.management.base import BaseCommand


class Command(BaseCommand):
	help = 'Seed deterministic workspace data for end-to-end browser tests.'

	def handle(self, *args, **options):
		self._delete_existing_seed_data()
		self._create_seed_data()
		self.stdout.write(self.style.SUCCESS('Seeded end-to-end workspace data.'))
```

Commands can orchestrate helpers, write user-facing command output, and own CLI arguments. They should not become hidden libraries that normal views import for business behavior.

## Things To Notice

- Start with `models.py` when the app only has one or a few closely related models.
- Move to a `models/` package when model count or model size makes one file harder to scan, and name model files after their classes.
- App-root files are still useful. `admin.py`, `apps.py`, `urls.py`, app-wide `tests/`, and a small `models.py` should stay at the root until they have a real reason to split.
- Feature-local API packages group `views.py`, `serializers.py`, `urls.py`, and endpoint tests so one route family has a clear owner.
- App-root model tests stay in `<app>/tests/` because model behavior is app-wide, not tied to one API route.
- Service modules sit under `<app>/services/` and are named after the workflow or integration they own, not `utils.py`.
- Management commands sit under `<app>/management/commands/` and are the right home for repeatable data or operations tasks.
- Domain apps own models and admin. API hubs and project URL modules own include boundaries only.
- Most `__init__.py` files should be empty. A model package may re-export models, but runtime behavior should live in named modules.
- A flat app is acceptable when it is readable. A package tree is acceptable when it reflects real feature, model, service, or command boundaries.

## Rules To Follow

- Do not split an app just to look sophisticated. Split when the current file or package no longer has one obvious responsibility.
- Keep one responsibility per file. If a file mixes unrelated models, unrelated route families, service workflows, CLI behavior, and tests, move each concern to its owning module.
- Keep project-root `urls.py` and API hub URL files thin. They should include app or feature URL modules and avoid endpoint implementation details.
- Keep app-root `urls.py` as an include hub once an app has multiple feature packages.
- Put feature serializers beside feature views when the serializer exists to serve that feature's API contract.
- Put model tests in `<app>/tests/` and feature API tests in the feature package or app-root test package according to the local app's established pattern.
- Use `models.py` for small domains and `models/` for large domains. Do not keep adding unrelated model classes to a giant `models.py`.
- When using `models/`, put one model class per file and re-export model classes from `models/__init__.py` only for import/discovery compatibility.
- Keep `__init__.py` files free of business logic, view classes, serializer classes, signal side effects, and runtime setup.
- Put shared workflows in named service modules only when they are reused, integration-heavy, or too large for a thin view. Do not create generic `common.py`, `utils.py`, or `helpers.py` buckets for unrelated leftovers.
- Put repeatable operational tasks in management commands and honor declared CLI arguments.
- Keep admin registration in the domain app's `admin.py`; do not centralize unrelated model admin classes in a cross-app admin module.
- Before adding a new app, package, service, or helper, inspect similar existing apps and mirror the repository's naming, route, serializer, and test placement patterns.

## Refactor Signals

- `models.py` is over roughly 300 lines, contains many unrelated classes, or requires repeated search to find one model's fields, choices, constraints, and lifecycle helpers.
- `views.py` contains several unrelated route families, such as items, variants, pricing, invitations, and history endpoints in one file.
- `serializers.py` contains serializers for unrelated features and reviewers cannot tell which view owns which serializer.
- App-root `urls.py` has a long flat endpoint list instead of a short include list that names feature boundaries.
- Project-root `urls.py` or `core/api/urls.py` contains domain endpoint details instead of namespace includes.
- `common.py`, `utils.py`, or `helpers.py` is collecting unrelated queryset builders, serializer shaping, permission checks, integration calls, and workflow behavior.
- `__init__.py` imports views, performs runtime setup, registers behavior, or hides the actual module where code lives.
- A feature's tests are scattered across several app-root test files with no clear relationship to the views and serializers they cover.
- A loose script in the repo root performs Django setup, creates data, imports models, or operates on the database when it should be a management command.
- A view duplicates multi-step workflow logic that already exists in another view, command, task, or service module.
- A service module has become a dumping ground for one-off logic that belongs on a model, serializer, view, command, or a more specifically named service.

## Verification

- For guidance-only changes, check the Markdown structure and code fences for the changed example.
- When refactoring app layout, run `ruff check` on modified Python files and targeted tests for the affected app or feature package.
- When moving models into a `models/` package, run `python manage.py makemigrations --check` or the project's equivalent migration check to confirm Django still discovers the same models.
- When moving URLs, run targeted view tests that use `reverse(...)` and verify old route names still resolve or are deliberately migrated.
- When moving serializers or views, run the feature's serializer and view tests, including permission and ownership-boundary cases.
- When adding or changing a management command, run the command's targeted tests or execute the command with safe local options.
- When splitting service modules, run all tests for callers that use the moved workflow, such as views, tasks, commands, and model tests.

## Why It Helps

- Teams can scale a Django app from a readable flat layout to feature packages, service modules, commands, and a model package without losing the original app boundary.
- Reviewers can find the ownership boundary for a feature quickly: app URL hub, feature URL module, feature view, feature serializer, feature tests, service workflow, and model tests each have a predictable home.
- Security-sensitive API code stays easier to audit because route scoping, permissions, serializers, and tests live together instead of being spread through unrelated files.
- Refactors become safer because app-root domain code, project API routing, feature transport code, operational commands, and service workflows have separate responsibilities.
- New contributors can copy a structure that matches the app's actual size instead of defaulting to either a giant flat module or an unnecessary package maze.
