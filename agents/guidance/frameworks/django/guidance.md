---
id: framework-django-guidance
title: Django Guidance
description: Durable Django, DRF, and Celery guidance.
kind: guidance
scope: framework
name: django
tags:
  - framework
  - django
applies_to:
  - django
status: active
order: 1
---

# Django Guidance

## Purpose

- Capture Django, DRF, and Celery conventions.
- Keep Python-wide conventions in `agents/guidance/languages/python/guidance.md`.
- Keep product- and repository-specific tenant, clinic, shell, and workflow architecture in `agents/guidance/project/guidance.md`.

## App Structure

- For small or medium Django apps, a conventional app-root layout with `models.py`, `views.py`, `serializers.py`, `urls.py`, `admin.py`, and `tests/` is fine when the surface area is still easy to scan.
- In larger Django apps, prefer a feature-foldered layout with app-root files plus `views/`, `services/`, `tests/`, `management/`, and `models/` packages when the surface area warrants it.
- When a repository separates transport from domain code, keep domain models and admin in domain apps and group DRF routes under a dedicated `api/` app or namespace instead of mixing every endpoint into the model app.
- Keep feature API code in `views/<feature>/` packages or `api/<domain>/<feature>/` packages with `views.py`, `serializers.py`, `urls.py`, and `tests/` colocated when that organization improves ownership and discoverability.
- Use the app-layout example as the baseline when deciding between `models.py` and a `models/` package, or between flat files and feature packages.
- Keep the project-root `urls.py` thin and use it to include the main app or API hubs.
- Keep the app-root `urls.py` thin and use it as an include hub for feature URL modules.
- Keep app-wide model tests in `<app>/tests/` and feature-specific API tests next to the feature package when that split keeps responsibilities clearer.
- When an app has many models, prefer a `models/` package with one model per file and re-export from `models/__init__.py` instead of growing one giant `models.py`.
- Keep service modules in `<app>/services/` and management commands under `<app>/management/commands/`.

## Data Ownership And Tenant Scoping

- Every authenticated endpoint must scope data to the current user or tenant. This is a security requirement, not a convenience.
- List endpoints must filter by ownership, such as `request.user`, `request.employee.company`, or the equivalent boundary.
- Detail, update, and delete endpoints must verify that the requested object belongs to the current user or tenant before operating on it.
- Tests must verify ownership boundaries. If an endpoint is scoped to user A, add a test proving user B cannot see user A's data.
- When multi-tenant middleware exists, keep queries flowing through that boundary instead of re-implementing tenant selection ad hoc.
- When repeated scoping depends on a request-owned domain object such as `request.employee` or `request.member`, attach it once in middleware and let views and serializers reuse that shared boundary.

## Views And APIs

### View Basics

- Keep views thin: permission checks first, object lookup or queryset shaping next, serializer validation after that, then response serialization.
- Keep view attribute ordering consistent and follow the canonical view examples for shared helpers, object lookup, and response flow.
- All views should inherit from the repository's shared base API view when one exists.
- Reuse existing lookup patterns with `get_object_or_404`.
- Reuse shared permission and request-validation helpers when the repository already provides them.
- For custom permissions, use the repository's shared permission helpers instead of indexing `_meta.permissions` or hand-building strings.

### Query Parameters And Filtering

- Trust internal API data and avoid excessive defensive parsing.
- Use direct conversion for common params, such as `int(request.query_params.get('page', 1))`.
- Skip local try-except wrappers for routine query-param parsing unless you need a standardized DRF validation error.
- When you need a standardized `400`, use a DRF field converter and let `ValidationError` bubble up.
- For comma-separated lists, parse them with straightforward splitting and trimming.
- Prefer passing defaults into `request.query_params.get(...)` directly.
- Backend query params must be snake_case. Do not add new camelCase query params.
- Avoid reserved renderer names such as `format` for feature-specific query params.
- Reuse shared helpers for common query param shapes, such as date ranges or CSV lists, instead of re-implementing them.
- Favor queryset scoping over branching. Build a base queryset, then apply optional filters.
- Finish list querysets with deterministic ordering, typically `.order_by('id')`, and add `.distinct()` when joins can duplicate rows.
- Keep metadata builders straightforward with early returns, single-purpose helpers, and shallow loops.

### API Structure

- Add views, serializers, and URLs inside the app you are updating.
- Mirror existing `urls.py` and `views.py` layouts for routing and logic decisions.
- Create view and serializer tests in the app's `tests` package when behavior changes.
- Design API responses so the frontend can match rows deterministically.
- Prefer composite identifiers when a display name is not globally unique.
- Avoid backend logic that matches rows by a non-unique attribute.
- Backend API responses must use snake_case so the frontend API client can convert them consistently.
- Mutating endpoints must return the created or updated resource. Do not return empty `{}` payloads on success.
- Serialize POST and PUT response bodies through output serializers instead of ad hoc dict construction.
- When responding with selectable options from Django `choices`, use a shared helper when the repository already provides one.
- For integration-heavy endpoints, keep views thin, call small service modules, and let operator retry screens read sync-event records instead of inferring integration history from order or enrollment state.

### Permission And Request Patterns

- Verify context first at the top of every action.
- Pair membership checks with staff checks for staff-only actions.
- When a view behaves differently for owners and staff, copy the existing permission pattern rather than inventing a new one.
- Use property-scoped checks for property-owned resources.
- Use explicit permission checks for cross-entity reads.
- Raise `PermissionDenied` when owned-resource business rules fail.
- For serializers that need enforced context, wrap request data in an `edited_data` dict so callers cannot spoof protected fields.
- Validate special-action query params and return `400 BAD REQUEST` when required values are missing.

## Serializers

### Input And Output Split

- Prefer two serializers per model: `ModelInputSerializer` for writes and `ModelOutputSerializer` for reads.
- Use a single serializer only when input and output requirements are truly identical.
- When one serializer handles both directions, name it `ModelSerializer`.
- Input serializers validate incoming data for POST and PUT requests.
- Output serializers shape response payloads for GET and mutation responses.

### Structure And Fields

- Every serializer needs a `Meta` class with `model` and `fields`.
- Output serializers should normally set `read_only_fields = fields`.
- Always include `id` first in the fields tuple.
- Verify field tuples for completeness. Duplicate entries can silently hide missing fields.
- For long field lists, keep tuple formatting multi-line and easy to scan.
- Default fields to read-only unless they truly need to be writable.

### Relationships And Computed Data

- Use `source` when exposing related-object fields.
- Use nested output serializers for related collections when that matches surrounding patterns.
- Use `SerializerMethodField` for computed fields.

### Validation And Persistence

- Implement `validate_<field>()` or `validate()` for custom validation.
- When an action depends on identifiers to associate records correctly, validate those identifiers explicitly.
- Implement `create()` or `update()` only when you need explicit control over persistence.
- Always return the saved instance from custom `create()` and `update()` methods.
- Use `.get()` with defaults for optional fields during custom persistence.

## Migrations

- Prefer model-driven schema changes over custom SQL or data migrations whenever Django can represent the change directly.
- When a migration both creates custom permissions and grants them to groups, create or fetch the permission rows inside the migration before assigning groups.
- For model-backed task frameworks where a field such as `name` is intentionally tied to the live task registry, it is acceptable to import the task model and use its `TextChoices` directly in the migration instead of creating a new migration every time a new task name is added. Use this pattern only when the migration is deliberately acting as a registry contract, not for ordinary domain enums that should remain historical schema snapshots.

## Models

- Extend the repository's shared base model when one exists.
- Prefer `models.TextField` for new string fields unless a real length constraint is required.
- Keep model declarations in this order:
  - class definition
  - `Meta`
  - supporting inner classes such as `TextChoices`
  - field declarations
  - optional dunder methods
  - optional `save()` and `delete()`
  - remaining helpers
- For field declarations, prefer this argument order:
  - target model for relations
  - field-specific arguments
  - `default`
  - `null`
  - `blank`
  - `verbose_name`
  - `on_delete` for relations
- Only set `default` when the field has a real domain-level default value.
- Do not use empty-string or other placeholder defaults as a shortcut for optional data, form convenience, or avoiding validation.
- For relation fields, pass the target model as `'app.Model'` and set `on_delete` explicitly.
- Keep field declarations on one line.
- Wrap human-readable `TextChoices` labels in `gettext(...)`.
- Prefer `@staticmethod` over `@classmethod` for model helper methods.
- Keep intrinsic lifecycle and invariant rules on the model.
- Prefer direct attribute access over `getattr` when a field is guaranteed by the model or serializer contract.
- Choose an explicit `on_delete` strategy for every relation and follow the repository's established convention unless you are deliberately migrating away from it.
- Be aware of the trade-offs between `DO_NOTHING`, `CASCADE`, `SET_NULL`, and `PROTECT`, and match the actual domain relationship.

### Model Lifecycle Side Effects

- Do not hide third-party I/O in model `save()` or `delete()` methods.
- Keep lifecycle methods limited to database concerns such as defaults, validation, and audit logging.
- Put network I/O in explicit service functions or Celery tasks that views or commands call directly.
- If existing code already has I/O in `save()` or `delete()`, do not add more. When you touch that code, consider extracting the I/O into a service layer.

## Module Boundaries

- Do not add new unrelated concerns to an existing catch-all module.
- If you are touching one concern inside a god module, consider extracting that concern into a dedicated module instead of growing the shared file further.
- In new projects, start with split modules instead of growing a single `common.py`-style catch-all file.

## URL Patterns

- Each app needs its own `urls.py` with `app_name` defined.
- Project-root URL modules should usually own only index, admin, docs, and top-level include boundaries.
- Larger APIs can use layered routing such as project root -> `api/urls.py` -> domain `urls.py` -> feature `urls.py`.
- Import `path` from `django.urls` and import the app's views directly.
- Follow REST-style route naming:
  - list routes end with `-list`
  - create routes end with `-create`
  - detail routes end with `-detail`
- Nested resources should include the parent identifier in the path.
- Feature-local URL modules can live beside feature views inside `views/<feature>/` or `api/<domain>/<feature>/` packages.
- Use kebab-case route names.

## Admin Configuration

- Register models with `@admin.register(Model)` and subclass `admin.ModelAdmin`.
- Always include `id`, `created_ts`, and `updated_ts` in `list_display` and `readonly_fields`.
- Use `search_fields`, `list_filter`, and `raw_id_fields` where relevant.
- Keep custom actions in the `actions` tuple and give them meaningful `short_description` values.
- Use multi-line tuples when admin field lists grow long.

## Management Commands

- Structure commands around argument parsing, focused helper methods, and early guard clauses so `handle()` stays readable.
- Use `call_command` for programmatic management command execution.

## Background Tasks (Celery)

- Use Celery for background work that does not need to complete synchronously.
- Never run cleanup, purge, or third-party I/O operations in model lifecycle methods or directly in views.
- Follow the repository's task registration pattern consistently so task discovery, scheduling, and retries stay predictable.
- If the task framework supports progress reporting, update task status through the shared progress hooks instead of inventing parallel state tracking.
- When scheduling recurring tasks, use explicit cron syntax such as `crontab(minute='*/30')`.

## Settings Hierarchy

- Follow the repository's established settings inheritance chain instead of inventing ad hoc environment modules.
- Keep shared configuration in the base settings layer and local or environment-specific overrides in dedicated child settings modules.
- Production settings must not hardcode secrets.
- Wildcard imports from base settings are acceptable only inside settings modules.

## Security Checklist

- Do not hardcode secrets in settings files.
- Do not disable CSRF without explicit justification.
- Gate admin tools behind `DEBUG=True` or explicit admin-only access.
- Ensure `.env.secret` files are gitignored.
- Use encrypted fields for sensitive credentials when the project already supports them.

## Services And Shared Helpers

- Wrap external systems behind focused service modules instead of spreading auth, retry, or network details through views and tasks.
- Centralize session-refresh or retry logic inside one service helper instead of repeating reconnect logic at each call site.
- Prefer small service classes when multiple operations share the same client or identity context, but do not cache plain Django settings in `__init__` just to avoid repeated `settings.<VAR>` reads.
- Extract repeated setup or teardown only after multiple call sites clearly share the same boilerplate.
- When a backend workflow naturally breaks into stages, prefer responsibility-based module names such as `adapters/`, `extractors/`, `loaders/`, or `transforms/` instead of generic `utils.py` buckets.
- Avoid near-duplicate views; if two routes need the same behavior, point them at the same view class.
- Prefer normal `.objects` manager access over `_base_manager` unless lower-level behavior is truly required.
- Avoid regex queries when exact equality or `__in` filters express the rule more clearly.
- Read configuration directly from `settings.<VAR>` unless local caching materially improves readability.

## Backend Coding Style And Error Handling

- Review similar apps before adding new patterns.
- Use explicit names such as `instance` and `queryset` to match surrounding code.
- Reuse existing permission checks and common attribute ordering.
- When class-based views expose shared attributes, prefer the common ordering `constants`, `queryset`, `serializer_class`, `permission_classes`, then methods.
- Compare new serializers and views against similar existing ones to maintain structural parity.
- Prefer using `settings.<VAR>` directly instead of copying settings values into local module constants.
- If the repository uses standardized DRF error responses, raise DRF exceptions from views and keep serializer-level validation inside serializers so the shared error shape stays consistent.
- Only return custom `{'detail': ...}` payloads when there is a strong reason and it matches surrounding code.

## Testing Guidelines

- Add reusable object builders to the repository's shared test-fixture helpers, usually `core/test_fixtures.py` or an equivalent shared module, instead of creating ad hoc builders inside test modules.
- Keep fixture helpers explicit with named parameters and sensible defaults.
- Place tests alongside their feature modules when that is the local pattern.
- Tests should assign permissions explicitly instead of relying on implicit defaults.

### Serializer Tests

- Create a pytest class per serializer and use `setup_method` for shared setup.
- Cover the happy path, missing required fields, and domain-specific validation.
- When serializers override `create()` or `update()`, add tests that exercise those code paths and confirm persisted state.
- For output serializers, assert the exact field set, verify expected values, inspect nested objects, and confirm there are no unexpected keys.
- When output serializers depend on lookups or helpers, monkeypatch them to deterministic stub values.

### View Tests

- Mirror existing authentication and shared fixture setup from the repository's fixture helpers.
- Resolve permissions with the model's shared permission helpers and grant them explicitly.
- Build endpoint URLs with `django.urls.reverse` instead of hard-coded paths.
- Compare response payloads against serializer output so tests stay aligned with the actual serialization layer.
- Cover positive, permission-negative, and ownership-boundary cases.
- Assert database state after each action.

### Model Tests

- Group related assertions in a single test class per model.
- Prefer shared helper methods for repeated object construction.
- Cover steady-state behavior and state transitions.
- Refresh instances before asserting post-conditions.
- Call `timezone.now()` once per helper to avoid drift-related failures.

## Consistency Checklist

### Django

- Views inherit from the expected base classes.
- Serializer field tuples are complete and non-duplicated.
- URL names follow kebab-case `{model}-{action}` patterns.
- List endpoints are scoped to the current user or tenant.
- Mutating endpoints return the created or updated resource.
- Model lifecycle methods do not hide third-party I/O.
- Tests cover permission-positive, permission-negative, and cross-user isolation paths.
- Django-specific examples live in the Django `examples/` folder instead of inline guidance blocks.
