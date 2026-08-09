# Django Application Structure

## Contents

- App and feature layout
- Module boundaries
- URL organization
- Admin configuration
- Management commands
- Settings hierarchy

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
- When using a `models/` package, name each model file after the model class itself, such as `InvoiceBatch.py`, instead of snake_case filenames such as `invoice_batch.py`. This keeps model-package imports and file discovery aligned with the class names they define.
- Keep service modules in `<app>/services/` and management commands under `<app>/management/commands/`.

## Module Boundaries

- Do not add new unrelated concerns to an existing catch-all module.
- If you are touching one concern inside a god module, consider extracting that concern into a dedicated module instead of growing the shared file further.
- In new projects, start with split modules instead of growing a single `common.py`-style catch-all file.
- Keep shared access or base-view modules focused on request context, permission checks, and scoped object resolution. Do not place feature-specific queryset builders or domain query shaping there; keep that logic in the owning app's views, models, or app-local query helpers.

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

- Keep each model's admin registration in that model app's `admin.py` instead of centralizing unrelated registrations in a shared module.
- Register models with `@admin.register(Model)` and subclass `admin.ModelAdmin`.
- Always include `id`, `created_ts`, and `updated_ts` in `list_display` and `readonly_fields`.
- Use `search_fields`, `list_filter`, and `raw_id_fields` where relevant.
- Keep custom actions in the `actions` tuple and label them with `@admin.action(description='...')`.
- Use multi-line tuples when admin field lists grow long.

## Management Commands

- Structure commands around argument parsing, focused helper methods, and early guard clauses so `handle()` stays readable.
- Use `call_command` for programmatic management command execution.

## Settings Hierarchy

- Follow the repository's established settings inheritance chain instead of inventing ad hoc environment modules.
- Keep shared configuration in the base settings layer and local or environment-specific overrides in dedicated child settings modules.
- Production settings must not hardcode secrets.
- Wildcard imports from base settings are acceptable only inside settings modules.
