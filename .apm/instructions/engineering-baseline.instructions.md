---
description: Complete legacy aggregate guidance retained as the always-on APM baseline during migration.
---

# Agent Guidance

## Purpose

- Capture the development guidance that applies generally across the repository, regardless of language, framework, or feature area.
- Keep project-specific layout, tooling, migration notes, and product architecture decisions in `project-architecture` guidance skill.
- Read this file before work, then read the relevant language, framework, and project guidance packages.
- Load `ai-generation-patterns` for backend AI or LLM generation work.

## Living Document Philosophy

- Guidance evolves with the codebase. Update it when you discover repeated patterns, architectural decisions, common mistakes, or better ways to explain existing guidance.
- When you encounter durable patterns or learnings that would help future work, update the relevant guidance immediately.
- Before finishing a task, re-check the relevant guidance and decide whether a new lesson, rule refinement, exception, or clarification should be recorded.
- When reflecting at the end of a task, explicitly check for:
  - verification coverage and any failures or timeouts
  - UI and UX consistency with existing patterns
  - reuse of existing components or utilities before creating new ones
  - data handling consistency, including query params, formatting, and error handling
- If no update is needed, state that you reviewed the guidance and decided no changes were warranted.

### How to Update

- Prefer small, incremental edits over large rewrites.
- Add context explaining why a rule exists, not just what it is.
- If a rule becomes obsolete, remove or revise it instead of layering exceptions.
- If two rules conflict, resolve the conflict explicitly.
- Avoid speculative rules. Document decisions made, not hypotheticals.

## Expectations & Best Practices

### Agent Compliance

- Read this file at the start of every task and treat it as required instructions.
- Read the entire document top to bottom and confirm you reviewed all relevant requirements before taking action.
- Before making changes, scan all sections for relevant requirements and follow them explicitly.
- If a request conflicts with this file, call out the conflict and follow the most restrictive rule.
- Read the relevant language, framework, and project guidance before stack-specific or project-specific work.
- Explicitly confirm in the final response that you reviewed and complied with the relevant guidance.

### Match Existing Patterns

- Follow the project's established coding style, naming conventions, and architectural patterns.
- Reference similar existing code before implementing new features.

### Verification Required

- Verify changes for each task when there is any reasonable local option.
- Use minimal tools first:
  - Python: `ruff check`, `pytest`, or targeted test files
  - TypeScript and Vue: linter and typecheck
  - C# and .NET: `dotnet build`, `dotnet test`
  - Rust: `cargo check`, `cargo test`, `cargo fmt --check`, `cargo clippy`
  - Focused `grep` or `rg` searches to verify usage patterns
- Treat verification as the default, not optional, and report what you ran.
- Always run the relevant linter on modified files before completing a task. Pre-commit hooks and CI enforce lint rules and will reject unclean code.
- If you cannot run verification, explicitly say why and list the exact commands the user should run.

### External Resource Test Seams

- When a workflow owns a hardware device, operating-system service, network stream, child process, or another resource that is impractical to exercise in ordinary tests, keep the acquire-and-release boundary small and replaceable.
- Test the workflow's lifecycle with a fake resource: successful start, invalid concurrent start, pause or resume when applicable, cleanup on stop, failed startup, and a subsequent retry.
- Keep production adapters responsible for the real integration and resource cleanup. Do not introduce a broad abstraction for pure code or a single straightforward call that needs no isolated lifecycle testing.

### Review Reporting

- Full reviews must report every finding in scope, not only the biggest or most representative ones.
- If the same issue appears multiple times, enumerate every audited occurrence or provide the full occurrence list.
- Summaries are fine only when they are paired with a complete findings section.
- List any skipped files, blind spots, or lightly checked areas explicitly.

## General Principles

### Core Philosophy

- **Simplicity, readability, and organization above all else.** Every decision should optimize for code that is easy to understand, intelligently organized, loosely coupled, and minimal in scope.
- **YAGNI first.** Do not add helpers, constants, abstractions, extension points, or configuration layers until the current requirements actually need them.
- **Readability over performance.** If a simpler approach is slightly slower but far easier to understand, choose simplicity. Optimize only when there is a measured, real problem.
- **No defensive programming.** Trust data and contracts. Do not add try or catch blocks, fallback values, or silent error handling just in case.
- **No bloat.** Every line, abstraction, and helper must earn its place. Remove anything that does not improve clarity or correctness.
- **Avoid redundancy.** Remove unnecessary normalization, casting, or fallback logic once you verify the real behavior.
- **KISS and DRY apply by default.** Keep behavior, data shapes, and control flow as simple as the real requirement allows. Reuse an existing source of truth before introducing a second concept, field, helper, or abstraction that models the same thing.
- **Prefer direct usage over one-off helpers.** If a helper is only used once and adds no clarity, inline it.
- **Loose coupling.** Components, modules, and services should have clear boundaries and minimal dependency on each other's internals.
- **Intelligent organization.** Group related things together, separate unrelated things, and make the codebase structure reflect the domain.

### Follow Existing Architecture

- Reference other views, models, serializers, admin files, apps, and folders to mirror the established architecture.
- When adding utilities or one-off data tasks, implement them as management commands, dedicated CLI tools, or equivalent first-class entrypoints instead of placing scripts in the repo root.
- Prefer the clearest end state over the smallest diff. If new work reveals the current structure is the wrong fit, do a focused refactor and remove obsolete code.
- Do not keep layering new logic on top of a messy local design just to avoid rewriting it. If the touched area will be clearer, simpler, and more aligned with guidance after a focused rewrite, rewrite it instead of patching around the existing shape.
- Prefer a clean rewrite of the local unit in scope, such as a file, workflow, view, serializer, or component, over incremental clutter that preserves confusing structure. Keep the rewrite focused, but choose the version future readers will understand fastest.

### Reuse Existing Components

- Reuse existing classes, methods, and structures to preserve consistency and avoid duplication.

### Control Flow

- Keep conditional logic shallow.
- Return early when possible to avoid deep nesting and keep intent clear.

### Keep Logic Simple

- Favor straightforward, explicit code even if it means repeating a line or two.
- Group related steps together so future readers can follow the intent quickly.
- Do not over-engineer solutions. Avoid unnecessary abstractions, helper functions, or complex patterns when a simple approach works.
- If the current local design has become harder to understand than the underlying requirement, prefer a focused rewrite of that local unit over preserving the complexity with one more layer.
- Do not keep speculative structures around for imagined future reuse. When future requirements become real, refactor then.
- Be deterministic.
  - If something must be uniquely identified, require the full identity at the API boundary.
  - Do not guess by matching on non-unique fields.
  - Avoid best-effort fallback logic that masks underlying issues.
  - When required data is expected, access it directly and fail fast.
  - When a non-fatal exception must be caught, such as a cache miss or optional external call, log it at `warning` with `exc_info=True` so the failure stays visible.
- Fix root problems, not symptoms.
  - Identify and fix the underlying cause instead of adding a band-aid.
  - Do not add defensive code to handle edge cases that should not exist.
  - If data is malformed, fix the source rather than adding cleanup code everywhere.
  - Fallback logic should only exist for legitimate alternative paths.
- Keep code readable.
  - Use logical spacing to separate chunks of code.
  - Avoid comments or docstrings unless they explain non-obvious logic, the reason something is done, or a business rule that is not self-evident.
  - Prefer full descriptive variable names and avoid abbreviations unless they are universally clear.
  - Eliminate redundant null checks and unnecessary intermediate variables.
- Combine conditions when they lead to the same outcome.
- Encapsulate fragile third-party integrations behind a small service layer so views, commands, and tasks use a stable interface.

### Parameters and Variables

- Do not add unused parameters to function signatures.
- Remove unused parameters instead of suppressing warnings.

### God Module Prevention

- One responsibility per file.
- Watch for growth signals. When a file exceeds roughly 300 lines or handles three or more unrelated concerns, split it.
- Name files by their responsibility, not by their location. Avoid names such as `common.py`, `utils.py`, and `helpers.py` when more specific names would clarify intent.
- Apply this across all stacks.

### Dead Code Discipline

- Delete commented-out code.
- Remove dead dependencies.
- Remove dead features unless there is a documented reason they must remain.

### Security Rules

- Never commit secrets or credentials.
- Treat serialized integration configuration as sensitive even when the endpoint is authenticated. A read or list response can leak authorization headers, signing secrets, tokens, or private metadata just as easily as a write path can.
- Require the same privileged permission used to manage secret-bearing configuration, or use an explicitly redacted output contract for lower-privilege readers. Add negative tests that assert both access denial and the absence of secret fields where redaction is supported.
- Never ship unauthenticated API endpoints.
- Scope data to the current user or tenant.
- Tests must verify ownership boundaries.
- Avoid wildcard `ALLOWED_HOSTS` in production.
- Treat requests to user-configurable destinations as an SSRF boundary. Restrict schemes and ports, reject credentials and non-public network ranges, and disable redirects unless every hop is independently validated.
- Do not validate a hostname and then let the HTTP client resolve it again. Resolve once, validate every returned address, connect to a validated address, and preserve the original hostname for the HTTP `Host` header and TLS SNI/certificate verification. Test literal blocked addresses, DNS-rebinding behavior, redirects, and invalid ports.

### Logging Discipline

- Log at boundaries, not every intermediate step.
- Use one structured line per event.
- Aim for roughly five log lines per method maximum.
- Remove development-only logging before merge.
- Use proper logging frameworks instead of `print()` or `Console.WriteLine` in production code.
- Do not use joke or placeholder log messages.

### Dependency Hygiene

- Declare all dependencies.
- Pin versions.
- Remove unused dependencies.
- Keep dependency versions consistent across projects that share packages.

### Tooling & CLI Contracts

- Honor all declared CLI arguments.
- Do not hardcode user paths.
- Use context managers or equivalent scoped resource cleanup for files, database connections, and disposable resources.

## Code Review Practices

- Verify usage before claiming redundancy.
- Gather comprehensive context first.
- Distinguish intentional design from accidental complexity.
- Document architectural decisions when you discover why something is designed a certain way.
- Create refactoring plans before implementing non-trivial structural changes.

### Readability And Structure Review

- Full reviews should assess file structure, folder structure, module boundaries, and code shape together, not as separate afterthoughts.
- If you cannot summarize the purpose of a file, module, or workflow in one sentence, treat that as a signal that the structure may be too complex.
- Prefer the smallest change that restores clarity, explicit control flow, and sensible boundaries.
- Review public API surface, helper count, and abstraction layers for proportionality to the real problem being solved.

### Centralize Constants

- Move feature-level constants and configuration into the appropriate settings system instead of duplicating module-level config.
- Keep large SQL or query text in code, not in settings.

## Languages

# Python Guidance

## Purpose

- Capture Python-specific conventions that apply across backend and agent code.
- Keep Django, DRF, and Celery rules in `django-patterns` guidance skill.
- Keep repository- or product-specific architecture decisions in `project-architecture` guidance skill.

## Key Patterns

### Organization And Imports

- Order imports as standard library, third-party, framework, then project-local.
- Place imports at the top of the file.
- Avoid inline imports inside functions unless you are breaking a circular dependency and there is no cleaner option.
- Avoid wildcard imports.
- Prefer direct, explicit project import paths over re-exported or indirect paths when the direct module is clearer.
- Keep `__init__.py` files minimal. Use them only for module declarations or explicit exports when that materially improves imports.
- Do not put runtime logic, workflow code, view classes, or business logic in `__init__.py` files unless there is a strong, unavoidable reason.

### Implementation

- Stick to single quotes unless triple quotes are required.
- Use logical spacing between imports, constants, classes, and function groups.
- Use one blank line between methods and two blank lines between classes.
- Keep functions small; extract helpers only when they are reused or materially improve clarity.
- Prefer explicit, descriptive names over abbreviations.
- Catch specific exceptions and let unexpected errors surface.
- Avoid dynamic `getattr` and `setattr` unless they are truly necessary.

### Classes And Stateful OOP

- Prefer a class when multiple methods share the same subject, dependency, or workflow state.
- Store stable dependencies and shared context in `__init__` instead of threading them through every method call.
- Keep instance state small and intentional: one domain object, one client, one config object, or a few workflow flags is usually enough.
- Prefer one clear public entrypoint with focused private helpers when a workflow has multiple steps.
- Use private helper methods to break up a larger workflow only when they genuinely share the same instance state.
- Use `@staticmethod` only for logic that does not depend on instance state.
- Use abstract base classes only when multiple implementations truly share the same contract.
- If a class owns resources such as temp files, sessions, or connections, make setup and cleanup explicit, ideally with a context manager.
- Do not create a class when a single pure function would be clearer.

### Types And Readability

- Do not use `from __future__ import annotations` for type hints.
- Use `typing.Optional` and `typing.Union` instead of the `|` union syntax.
- Use builtin collection types such as `list`, `dict`, and `tuple` instead of `typing.List`, `typing.Dict`, and `typing.Tuple`.
- Avoid regex when an exact match works.
- Avoid type-only casts and broad `# type: ignore[...]` pragmas when a clearer boundary exists.
- At third-party integration boundaries, prefer real stubs or isolated service-layer workarounds over broad `# type: ignore[import-untyped]` usage.

### Verification

- Run `ruff check` on modified Python files before completing a task.
- Prefer targeted `pytest` runs first when shared infrastructure is unchanged.
- When changing formatter or lint settings in new Python projects, prefer a 120-character-friendly line length unless repository constraints require something else.
- Keep local formatting and import ordering aligned with the repository's active lint and formatter configuration.

### HTTP, Adapters, And Debugging

- Use concrete HTTP verb helpers such as `requests.get` and `requests.post` when the method is already known.
- Do not hide straightforward request flow or one-off logic behind tiny wrapper helpers that only shuffle arguments around.
- Prefer built-in logging or framework error paths over ad hoc print debugging in committed code.

### Testing

- Keep Python tests explicit and readable.
- Prefer explicit fixture builders and helper methods over catch-all `**kwargs` patterns.

## Consistency Checklist

### Python

- Imports are explicit, ordered, and top-level.
- `__init__.py` files stay minimal.
- Typing follows repository conventions.
- `ruff check` expectations are clear and were followed for modified files.
- Django-specific behavior is documented in the Django guide instead of being duplicated here.

## Frameworks

# Django Guidance

## Purpose

- Capture Django, DRF, and Celery conventions.
- Keep Python-wide conventions in `python-conventions` guidance skill.
- Keep product- and repository-specific domain architecture in `project-architecture` guidance skill.

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

## Data Ownership And Organization Scoping

- Every authenticated endpoint must scope data to the current user or organization. This is a security requirement, not a convenience.
- List endpoints must filter by ownership, such as `request.user`, `request.employee.company`, or the equivalent boundary.
- Detail, update, and delete endpoints must verify that the requested object belongs to the current user or organization before operating on it.
- Tests must verify ownership boundaries. If an endpoint is scoped to user A, add a test proving user B cannot see user A's data.
- When multi-organization middleware exists, keep queries flowing through that boundary instead of re-implementing organization selection ad hoc.
- When repeated scoping depends on a request-owned domain object such as `request.employee` or `request.member`, attach it once in middleware and let views and serializers reuse that shared boundary.
- When one auth user can hold roles in multiple organizations, model authorization with membership records. Do not treat a tenant-specific auth-user table or a request header alone as the authorization boundary.

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
- When re-raising converter validation for a named query parameter, attach it to that concrete parameter key so standardized error responses identify the field correctly.
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
- Serializer `Meta` inheritance is acceptable when a derived serializer is intentionally extending a base serializer's `fields` tuple or other serializer metadata. Do not apply the concrete-model-`Meta` example to serializers.
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
- Prefer `@staticmethod` for model helpers that do not need class state. Use `@classmethod` only when the helper genuinely depends on `cls`, such as shared permission-name helpers.
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

## Sessions, CSRF, And Frontend Serving

- Use the session-CSRF-SPA example as the baseline when Django APIs are consumed by a browser SPA.
- Prefer Django's cookie-backed session authentication for browser API requests instead of adding JWT, bearer-token, or local-storage auth alongside Django sessions.
- Keep `SessionMiddleware`, `CsrfViewMiddleware`, and `AuthenticationMiddleware` in the request stack, and keep authenticated DRF browser views on `SessionAuthentication`.
- Do not disable CSRF or make browser mutation endpoints CSRF-exempt to work around split-origin local development. Fix `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, credentialed requests, and the bootstrap CSRF flow instead.
- When local development uses separate frontend and backend servers, keep the frontend origin in both CORS and CSRF trusted-origin settings, allow credentials, and make the frontend API client send credentials and the CSRF header.
- Provide one anonymous-safe bootstrap endpoint that sets a CSRF cookie and returns current session state, current user data, organization or access context, and any shell bootstrap data needed before route pages load.
- In production, prefer same-origin API calls from the built frontend served by Django. Keep production hosts and trusted origins environment-driven, require secure cookies, and avoid wildcard `ALLOWED_HOSTS`.
- Keep frontend session state in the shared shell bootstrap flow instead of asking every route to check authentication or fetch current-user data independently.

## Browser Session SSO

- Use the session SSO example as the baseline when a browser SPA signs in through an OAuth or OIDC identity provider and Django owns the session cookie.
- Keep provider client secrets, token exchange, ID-token validation, profile loading, and profile mapping on the backend. The frontend should only navigate the browser to a backend SSO login URL.
- Store the SSO `state`, provider identifier, and normalized relative frontend redirect path in the server-side session before redirecting to the provider.
- On callback, validate and remove the stored state before exchanging the authorization code. Never create or log in a user after an invalid, missing, or mismatched state.
- Normalize post-login redirects to relative frontend paths. Reject absolute URLs, protocol-relative URLs, and values containing carriage returns or newlines.
- Put provider URLs, scopes, client IDs, client secrets, JWKS URLs, issuer expectations, and request timeouts in settings, with secrets coming from environment variables.
- Expose available auth methods from the anonymous-safe bootstrap endpoint so the frontend can show password and SSO options from backend-owned feature flags or configuration.
- Treat signed ID-token validation as the identity boundary. Verify signature through provider JWKS, expected audience, expiry, issued-at presence, issuer expectations, and provider-specific email ownership claims before linking or creating a user.
- Map provider claims through a small backend service boundary, keep provider-specific trust semantics in mappers or equivalent functions, require a valid email address, and fail on ambiguous account matches.
- Create SSO-only users with an unusable password unless the product explicitly supports password setup after SSO.
- Apply product-specific access checks before calling `login(...)` when an SSO identity can belong to more than one app surface, such as operator and patient portals.
- Log callback failures at `warning` with provider context and `exc_info=True`, then redirect the browser to a stable frontend error code instead of returning provider details.

## Security Checklist

- Do not hardcode secrets in settings files.
- Do not disable CSRF without explicit justification.
- Gate admin tools behind `DEBUG=True` or explicit admin-only access.
- Ensure `.env.secret` files are gitignored.
- Use encrypted fields for sensitive credentials when the project already supports them.
- Classify uploaded files before serving them. Expose only genuinely public files from a public media path; serve sensitive or tenant-owned uploads through authorized views or private storage with signed, expiring URLs. Never treat an unguessable path as access control.

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

## External Event Idempotency

- Treat webhook event IDs and provider object IDs as database invariants, not application-level hints. Back each claimed identifier with a unique constraint at the provider's documented scope, using an account-qualified composite constraint when the identifier is not globally unique.
- Do not use an `exists()`-then-create check as the only duplicate guard. Concurrent deliveries can both pass the check; claim the event inside `transaction.atomic()` and treat the unique-constraint conflict as the duplicate path. Catch `IntegrityError` outside the atomic block that attempted the insert, or use an inner savepoint when a larger transaction must continue.
- For database-only handlers, keep the event claim and its domain writes in the same transaction so a failed handler does not permanently consume the event. When processing includes external I/O, avoid holding a database transaction open; persist an explicit processing state and define retry or stale-claim recovery semantics instead.
- Protect the domain effect as well as the delivery ledger. When a provider payment, refund, shipment, or similar object has its own stable external ID, enforce uniqueness at the documented provider scope on that domain record so different deliveries cannot apply the same effect twice.
- Lock mutable aggregate or lifecycle rows with `select_for_update()` before calculating and writing balances, totals, or status transitions that concurrent events can change.
- Test repeated delivery, duplicate provider-object IDs, handler failure followed by retry, and stale-instance updates. Use the production database engine for true concurrency tests when backend locking behavior is part of the contract.

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

- Add reusable object builders to the repository's shared test-fixture helpers, usually `tests/fixtures.py` or an equivalent shared module, instead of creating ad hoc builders inside test modules.
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
- List endpoints are scoped to the current user or organization.
- Mutating endpoints return the created or updated resource.
- Model lifecycle methods do not hide third-party I/O.
- Tests cover permission-positive, permission-negative, and cross-user isolation paths.
- Django-specific examples live in the Django `examples/` folder instead of inline guidance blocks.
- Session-authenticated browser APIs keep CSRF enabled and have a tested bootstrap flow that provides session state and a CSRF token.

# Vue Guidance

## Purpose

- Capture Vue, TypeScript, Pinia, and frontend API conventions.
- Keep item- and repository-specific shell, workspace, branding, and organization architecture in `project-architecture` guidance skill.

## Frontend Project Structure

- `src/assets` stores static assets such as images and fonts.
- `src/components` stores reusable UI components and app-shell primitives.
- Use `src/components/ui/` for low-level shared controls and surfaces.
- Use `src/components/forms/` for labeled field wrappers that compose `FormField` plus shared input primitives.
- Use `src/components/layout/` for shell containers, scroll frames, and app-level structural wrappers.
- Use `src/components/navigation/` for sidebar, tabs, menus, and other shared navigation pieces.
- Use `src/components/page/` for reusable page-composition blocks such as `PageHeader`, `PageSection`, split layouts, metric cards, and list rows.
- `src/views` stores route-based folders and route entry views.
- Each route folder under `src/views/` can own the route component, local subcomponents, a descriptively named local store file, route-specific composables, types, and constants.
- Keep shared shell-level state under a dedicated shell folder such as `src/views/application/` instead of a top-level catch-all `src/stores/` directory.
- Prefer one primary route-based feature home such as `src/views/` instead of introducing parallel feature-root trees without a migration plan.
- If legacy or transitional code still exists under `src/features/`, migrate it toward `src/views/` as you touch that route area instead of expanding the old structure.
- Keep the canonical API client in one well-known utility or API module instead of adding parallel service directories for the same transport role.
- `src/composables` stores shared Vue composables used across multiple routes.
- `src/router` stores Vue Router configuration.
- `src/types` stores shared global types.
- `src/core` stores core models and utilities.
- `src/styles` stores global styles and CSS utilities.
- Prefer configured import aliases such as `@/views/...`, `@/types/...`, and `@/utils/...` instead of long relative traversal imports when the project supports aliases.

## Shell And Routing

- Keep one shared shell near `App.vue` that mounts the router outlet plus global feedback UI.
- Switch between authenticated and guest layouts in one shared shell or container instead of duplicating layout logic inside route views.
- Keep shell-only pieces grouped under `src/components/application/`, `src/layouts/`, or an equivalent dedicated folder.
- Let the shell own navigation chrome, top-level bootstrap loading states, and router outlet placement.
- Keep page views focused on page composition and domain workflow concerns rather than re-implementing shell structure.
- Prefer route meta flags such as `requiresAuth` with a single global router guard backed by shared auth state.
- For session-backed apps, use the auth-aware shell example as the baseline for bootstrap state, login, logout, guest-only routes, public routes, and permission redirects.
- Keep session bootstrap in the shared shell store, usually under `src/views/application/`, and let the router guard initialize that store once before protected routes render.
- Route views, dialogs, and route-local stores must not call the auth bootstrap endpoint directly. They should read the shared shell store instead.
- Express route access with route metadata such as `requiresAuth`, `guestOnly`, `skipShellBootstrap`, and `requiredPermissions` instead of route-local redirect logic.
- Reset and re-bootstrap the shell store after any frontend flow that creates a new authenticated session, and reset shell state immediately after logout.
- For session-backed SSO, route provider sign-in buttons to backend SSO login URLs and let the backend complete the provider callback, create the Django session, and redirect back to the SPA.
- Preserve the intended destination as a relative redirect path in the SSO login URL, and let the backend reject unsafe redirect values.
- Let the shared shell bootstrap own post-callback session detection. Do not add frontend token parsing, local-storage auth, or route-local provider callback handlers unless the backend contract explicitly requires them.
- Render available password and SSO methods from the bootstrap payload instead of hardcoding provider buttons in the login page.
- Mount notification or snackbar containers once near the app root and drive them from a shared store or composable.
- Use shared global notifications for cross-feature success and error feedback instead of rendering one-off banners inside every page.

## Theme And Tokens

- Prefer one theme source of truth instead of mixing multiple theming systems.
- When Tailwind is the primary styling layer, prefer semantic utility names such as `bg-surface`, `text-body`, and `border-line` over raw palette classes in application components.
- CSS variables are a good theme source of truth when runtime theme switching is needed.
- Apply the active theme at the app root instead of toggling per-page theme classes.
- Reserve accent colors for actions, focus states, and active UI states; keep primary reading text on neutral text tokens.
- Keep radius, border, and shadow choices consistent across shared shells, cards, nav items, and controls.

## Frontend API

### Single API Client Rule

- Maintain exactly one canonical API client.
- Do not keep parallel implementations such as `apiService.ts` and `useApiClient.ts` when they serve the same role.
- The canonical client should centralize Axios configuration, CSRF handling, snake_case to camelCase conversion, and typed response handling.
- Outside of tests, `axios` imports should live only in the canonical API client layer.
- Put the canonical client in one obvious location, commonly `src/utils/api.ts` or `src/api/client.ts`, and make that location the only runtime Axios owner.
- For Django session-backed browser apps, keep `withCredentials`, XSRF cookie/header configuration, and any Django-rendered CSRF token handoff inside the canonical API client setup path.
- Do not introduce a separate auth API client or local-storage token helper for login, logout, registration, password reset, or invitation acceptance flows.

### API Client Patterns

- Route every request through the canonical shared frontend API client.
- Use `apiClient.get(...)`, `apiClient.post(...)`, `apiClient.put(...)`, and `apiClient.delete(...)` for JSON API requests.
- Use `apiClient.postForm(...)` and `apiClient.putForm(...)` for `FormData` uploads.
- Use `apiClient.setCsrfToken(...)` only at shell/bootstrap boundaries when a CSRF token is read from the rendered page.
- Keep SSO login URL builders near the canonical API client so they share the same API base URL, but use normal browser navigation for SSO redirects instead of `apiClient.get(...)`.
- Backend responses should stay snake_case; the client layer converts them to camelCase.
- Components, composables, stores, and route views should work only with camelCase field names.
- The API client converts POST and PUT JSON request bodies from camelCase to snake_case before sending them to the backend.
- Query params should be passed to `buildParamsConfig(...)` as camelCase objects so the shared helper can convert them to snake_case.
- Import query-param helpers with `import { buildParamsConfig } from '@/utils/apiParams'` in domain API modules that accept filters.
- Response and standardized error payloads are converted to camelCase by the API client's response interceptor before callers read them.
- Form uploads should use the API client's FormData methods so payload keys and browser-managed multipart headers are not rewritten like JSON bodies.
- CSRF, credentials, timeout, base URL, and response interception belong inside the canonical API client instead of being configured in route code.
- Group API methods by domain and use consistent names such as `list`, `create`, `detail`, `update`, and `delete`.
- Specialized verbs such as `duplicate` are acceptable when they clearly describe a non-CRUD action.
- Type all responses and payloads.
- Use RESTful URL structures with IDs in the path and nested paths for related resources.
- Use `FormData` for uploads only when needed.
- Customize headers for uploads only when the request truly requires it.
- Use the shared query-param helper when one exists and let the API client handle casing conversion.
- Define domain API modules as top-level `const` blocks and export them through one unified API object.
- Order method parameters from most important to least important.
- Do not set Axios defaults in `main.ts`, stores, or route views; keep transport configuration inside the canonical client.

### API Error Handling

- Use the shared error helpers for standardized DRF error responses instead of parsing Axios errors directly in views or stores.
- Use `extractFirstFieldErrors(...)` for form field error maps and `extractFieldErrors(...)` when multiple messages per field are needed.
- Use `getFirstApiErrorMessage(...)` for workflow-level fallback messages, `getFirstApiErrorCode(...)` for code-specific behavior, and `getApiErrorStatus(...)` for status-specific behavior.
- Use `parseApiError(...)` only inside shared helpers or specialized flows that truly need the full standardized error object.
- Field-error keys should be treated as camelCase on the frontend, even when the backend returned snake_case `attr` values.
- Keep fallback user-facing error messages in the view or store that owns the workflow, but keep response-shape parsing in the shared error helpers.

### Casing Helpers

- `camelToSnake(...)`, `snakeToCamel(...)`, and `snakeFieldAttrToCamel(...)` are API-boundary utilities, not component-level formatting helpers.
- Do not call casing helpers from components, route views, or stores unless you are maintaining the shared API client, query-param helper, or error helpers.
- If a feature needs manual casing conversion, first check whether the data should instead flow through `apiClient`, `buildParamsConfig(...)`, or the shared error helpers.

## Type Discipline

- Do not use `any` or `unknown` at API transport boundaries.
- If the backend shape is uncertain, define an interface with optional fields instead of using `any`.
- If a method declares `Promise<ThingInterface>` or `Promise<ThingResponseInterface>`, it must return the unwrapped payload instead of an `AxiosResponse` object.
- Do not mix unwrapped model returns and `AxiosResponse` returns across API modules.
- Separate form DTOs from persisted entity models.
- Do not use placeholder IDs like `0` or `-1` in form state just to satisfy entity interfaces.
- Prefer `[Thing]RequestInterface` for data sent to the backend.
- Prefer descriptive names for data returned by the backend: use `[Thing]Interface` for persisted resources, names such as `[Thing]AvailableOptionsInterface` for option bundles, and `[Action]ResponseInterface` for endpoint-specific responses that do not have a clearer domain noun.
- Treat returned-data interfaces as API output contracts. Include backend-owned fields such as `id`, timestamps, status, nested output objects, and read-only derived values when the API returns them.
- Treat request interfaces as create/update/action payload and form contracts. Include only fields the frontend can submit, and omit backend-owned fields such as `id`, `createdTs`, `updatedTs`, and read-only derived values.
- Existing `[Thing]InputInterface` files do not need churn-only renames, but prefer `[Thing]RequestInterface` when adding a new API request contract.
- Do not create a dedicated filter interface by default. Type simple query params inline at the API method boundary and pass them through `buildParamsConfig(...)`; extract a named request interface only when the query shape is reused or complex.
- Prefer Zod-inferred request types when a form validates the same shape it submits, and colocate `createDefault...Request()` with that schema.

## Models And Stores

### Models

- Organize models by domain under `src/types/<domain>/`.
- Keep related models together inside the same domain folder.
- Use explicit filenames such as `[Thing]Interface.ts`, `[Thing]RequestInterface.ts`, `[Thing]AvailableOptionsInterface.ts`, `[Action]ResponseInterface.ts`, and `[Thing]Enums.ts` when those shapes exist.
- Store-related view models should live in shared model files rather than being declared inside stores or views.
- Request files may colocate a Zod schema plus a `createDefault...()` helper when that keeps form state and validation close to the request contract.
- Keep request interfaces and returned-data interfaces in separate files when an endpoint or resource has both read and write contracts.
- Keep enum definitions with the returned resource interface when they describe persisted or backend-returned values, and import those enums into request interfaces when forms need to submit them.

### Stores

- Use Pinia intentionally: keep cross-route shell state in shared shell stores, and keep route or feature state in route-local stores.
- Put route-only state in the route folder when that state is not reused elsewhere.
- Keep shared shell-level stores under the shell/application folder instead of a top-level catch-all `src/stores/` directory.
- Do not name local store files `store.ts`; use a descriptive name such as `contactsStore.ts`, `organizationSettingsStore.ts`, or `workspaceDetailStore.ts`.
- Shared shell stores should bootstrap cross-route context once, then expose selected organization, current user, or similar shell-level state for route views to consume.
- Prefer a route-local feature store when three or more route-local components share the same record, loading state, filters, form DTO, or mutation workflow.
- Let route-local feature stores own business state, data fetching, mutations, shared form state, permission-derived actions, and derived domain state used across sibling components.
- Let route-local components under `src/views/<route>/components/` import their colocated feature store directly when that removes prop chains and keeps ownership obvious.
- Keep shared components under `src/components/` store-agnostic and prop-driven even when route-local components are store-aware.
- Avoid passing route-local records, IDs, loading flags, error strings, and mutation callbacks through multiple component layers when the same route-local store can be consumed directly.
- Prefer one focused feature store per route or domain workflow instead of one giant app store.
- Reload data through store actions instead of manually clearing state.
- Use stable, deterministic keys for UI rows and lookup maps.
- If uniqueness depends on multiple fields, use a composite key instead of a display name.
- Do not implement fallback matching based on non-unique attributes.
- Access store state, getters, and actions directly on the store object instead of destructuring them.
- Replace optimistic or streamed array items with new objects instead of mutating captured raw references.

## UI And Component Conventions

### Shared UI

- Reuse existing components, tokens, and layout patterns before creating new ones.
- Prefer PrimeVue for foundational controls and surfaces when it fits the need.
- Do not rebuild standard buttons, inputs, dialogs, menus, tables, or common feedback patterns from scratch unless the shared component layer is a poor fit.
- Keep shared wrappers app-owned even when the implementation is backed by PrimeVue.
- Keep shared components under `src/components/` free of route-specific business logic, route params, API calls, and domain-store imports.
- When a PrimeVue-backed wrapper and a plain HTML wrapper solve the same item problem, keep their app-facing props as similar as practical and let only the internals differ.
- Keep component filenames PascalCase and composables prefixed with `use`.
- Favor shared SCSS or utility classes instead of inline styles unless values are dynamic.
- Prefer Tailwind flex utilities for layout before reaching for grid.
- Prefer Tailwind utility classes directly in components for shell, layout, and surface styling.
- Keep raw CSS limited to base reset concerns unless utilities are not sufficient.
- Keep modal structure consistent with header, body, footer, and accessibility attributes such as `role="dialog"` and `aria-label`.
- Reuse confirm dialogs for destructive actions.
- Respect existing responsive breakpoints when building or reusing dialogs.
- Use shared loading UI before introducing new spinners or progress banners.
- Use shared loading, error, and other feedback components before inventing local alternatives.
- Use the repository's shared clipboard helper instead of direct `navigator.clipboard` calls when one exists.
- Prefer extracting sizable UI blocks into subcomponents so pages stay readable.
- When a route view or shell view starts mixing several distinct sections, split those sections into local subcomponents so the parent reads like a page outline.
- Prefer route-local subcomponents under `src/views/<route>/components/` for route-specific panels, summaries, drawers, and list sections before promoting them into shared `src/components/`.
- When one component contains both desktop and mobile versions of the same UI, prefer small focused subcomponents when that split makes the responsive behavior easier to scan.
- Prefer shared UI inputs and keep spacing consistent with existing utility classes.
- Prefer page-composition wrappers for repeated screen structure so route views can read as page outlines instead of piles of low-level surface markup.
- For repeated resource lists, prefer a shared table or list wrapper that owns headings, loading state, empty state, and pagination slots while feature components supply filters and row markup.
- Prefer shared PrimeVue-based wrappers for shell and navigation primitives such as menus, drawers, and surfaces instead of repeating custom sidebar markup.
- Keep PrimeVue dialog, tooltip, dropdown, and autocomplete usage aligned with established shared patterns instead of introducing one-off variants.
- Avoid ambiguous bulk-table interactions: use explicit selection scope, unique row keys, and pre-sorted data when default ordering depends on multiple fields.
- Do not ship dashboards or cards backed only by placeholder values.

### Styling And Visual Consistency

- Follow established form layout, validation messaging, and table column ordering conventions.
- Keep semantic colors scoped to success, warning, and error states.
- Avoid ad hoc hex colors for surfaces, borders, hover states, and selected states.
- Promote repeated UI into reusable shared components only when reuse is real; otherwise keep composition view-local.
- Keep radii restrained and consistent across shells, cards, and controls.
- Use the same radius family across the workspace by default unless a component has a clear reason to deviate.
- Avoid introducing new global styles when shared utility patterns already exist.
- Align error and retry UI with shared patterns: shared error messages, warn-toned retry buttons, and minimal centered loading states.
- Prefer small shared PrimeVue wrappers for repeated control styling.
- Add tests for complex components using the same local patterns, such as unit, shallow-mount, or snapshot tests, when those patterns already exist in the feature area.

### Casing Discipline

- Frontend code uses camelCase everywhere.
- Backend API responses stay snake_case and are converted by the API client.
- Frontend request bodies and query params should be authored in camelCase and converted only at the API boundary.
- Never pass snake_case keys from components or stores to the API client.
- Never manually convert casing in components.

## Component Paradigms

- Do not mix Options API and Composition API in the same component.
- New code should use `<script setup lang="ts">`.
- If a legacy file uses Options API, keep that file internally consistent unless you are doing a full migration.

## Forms And Error Handling

### Forms

- Keep isolated one-off form state straightforward inside the local view, component, or dialog.
- When multiple route-local sections or dialogs edit the same record or share the same validation and save workflow, move that form DTO, field errors, and save action into the route-local feature store.
- Centralize DRF standardized-error parsing in shared frontend error helpers.
- Delete stale shared validation abstractions when they are no longer used.
- Follow the established validation and dialog examples for dual client and server error handling.
- For multi-step flows, keep the parent responsible for the shared DTO and active step, and let each step component own its local validation and submit or advance logic.

### Cascading Selects

- Use `resetField('fieldName')` to clear dependent fields without marking them touched or dirty.
- Do not directly assign `null` when the form library provides a reset helper.

### Dialog Ownership

- For isolated create or edit flows, dialogs can own their API calls, error handling, and success toasts.
- When a dialog participates in a larger route workflow shared with sibling sections, prefer a route-local feature store for fetch, mutation, shared form state, and success handling, and let the dialog stay focused on UI state and field rendering.
- Emit only the smallest event surface needed. If the dialog and parent already share a route-local store, prefer `close` or `cancel` events over replaying domain data through emits.
- Keep the parent route view focused on page composition, route lifecycle wiring, and navigation rather than forwarding business callbacks through several local layers.
- For admin and settings pages, prefer creation flows in focused dialogs while the page keeps the list or detail context.
- Prefer shared PrimeVue input helpers over ad hoc implementations, and await shared clipboard helpers before showing success UI.

## View Patterns

- Keep derived collections such as filtered rows and grouped data in `computed` getters.
- Use `usePolling` for auto-refresh behavior instead of manual intervals or timeouts.
- Guard optional identifiers before using them and return early when dependencies are missing.
- Use small helper functions for repeated lookups instead of inline template ternaries.
- Build view models with explicit loop-based transformers instead of long `map`/`filter`/`reduce` chains when clarity is better.
- Let route views compose shared `page/` wrappers, shared `ui/` controls, and route-local sections.
- Prefer one page-level shell store or parent view to own organization selection, bootstrap context, and shared loading/error state instead of re-fetching that context in each child page.
- For simple pages, route views can still own their fetch helpers and local computed data directly.
- For larger route folders, prefer a route-local feature store to own orchestration, data loading, mutation actions, stale-request guards, and shared workflow state, while the route view stays focused on page composition and route lifecycle wiring.
- Let route-local components consume the route-local feature store directly when doing so removes prop drilling and keeps the component API smaller.
- Keep data-fetch helpers focused on a single resource.
- Call data-fetch helpers sequentially when later requests depend on earlier metadata.
- Guard against stale async responses overwriting newer state when organization or route selection changes during a request.
- Follow the established polling and route-query examples for component polling, task polling, and URL-driven view state instead of ad hoc timers or path/query mixes.
- Fetch backend-provided defaults from the API instead of hardcoding the same values again in the client.

## Legacy Anti-Patterns And Tolerance

### Anti-Patterns To Avoid

- Do not perform heavy lookups, formatting, or ternaries inline in templates.
- Do not scatter ad hoc boolean flags across templates when they can be derived from a single source of truth.
- Do not use `.value` on nested refs or nested computeds in templates when a top-level computed would preserve clearer reactivity.
- Do not keep route-local business workflows split across a prop-heavy parent, several thin child wrappers, and multiple duplicated dialog submit handlers when one route-local feature store would make ownership clearer.

### Legacy Tolerance

- If the repository has a legacy frontend, keep the local file internally consistent while you work there instead of partially mixing old and new patterns.
- Do not reintroduce legacy frontend patterns into modern feature areas.
- For the application's modern frontend migration, treat `src/views/` as the target structure and avoid creating new route surfaces under `src/features/`.
- For the application's structure cleanup, avoid recreating top-level `src/stores/` or `src/services/` folders for modern code.

## Frontend Code Reference Workflow

- Identify an existing route or view folder similar to the one you are building.
- Inspect its route view, local subcomponents, local store usage, and API usage.
- List reusable pieces before coding.
- Reuse those pieces first, then add new code only when necessary.
- When reorganizing route code, prefer moving it into `src/views/` rather than creating or extending a parallel feature-root folder.
- When adding shared shell-level state, prefer `src/views/application/` before introducing a new global store directory.
- When adding transport helpers, prefer `src/utils/api.ts` and nearby utilities before introducing a new services root.
- Run the linter and formatter so the new code matches project style.

## Consistency Checklist

### Vue

- Component names and file casing are correct.
- Existing UI primitives are reused before new ones are created.
- Spacing and styling align with comparable features.
- API calls flow through the single canonical client.
- API boundary types avoid `any` and `unknown`.
- Components do not mix Options API and Composition API.
- Form state uses dedicated input types instead of entity models with placeholder IDs.
- Vue-specific examples live in the Vue `examples/` folder instead of inline guidance blocks.
- Session-backed auth uses the shared API client, shared shell store, route metadata, and one global router guard instead of route-local bootstrap or redirect logic.

## Project

# Project Guidance

## Purpose

- Capture repository-specific conventions, local tooling, and product architecture decisions.
- Keep general development rules in the root baseline instruction.
- Use this file for decisions tied to this repo's structure, migration state, or product direction.

## Guidance Authoring And Migration

### Authored Guidance

- Update authored guidance under `.apm/` instead of editing generated `AGENTS.md` output directly.

### Guidance Map

| File | Scope |
|---|---|
| the root baseline instruction | Shared development guidance |
| `python-conventions` guidance skill | Python guidance |
| `django-patterns` guidance skill | Django, DRF, and Celery guidance |
| `vue-patterns` guidance skill | Vue, TypeScript, Pinia, and frontend API guidance |
| `project-architecture` guidance skill | Project-specific guidance |
| `review-workflows` skill reference `antipatterns.md` | Cross-stack anti-pattern catalog |
| `review-workflows` skill `references/` directory | Review rubric and reporting templates |

### Skills And Commands

- OpenCode command content currently spans `.apm/prompts/` in the new tree and `.apm/prompts/` in the legacy tree.

## Repository Layout

- **Backend**: Django REST Framework app in `backend/` when present.
  - Apps usually follow Django conventions with `models.py`, `views.py`, `serializers.py`, `urls.py`, `admin.py`, and `tests/`.
  - Base classes typically live in `core/`, such as `ProjectBaseModel` and `ProjectBaseAPIView`.
- **Frontend**: Vue 3 and TypeScript in `frontend/` when present.
  - Common directories include `src/components/`, `src/views/`, `src/composables/`, `src/types/`, `src/core/`, `src/styles/`, and `src/utils/`.
  - Route folders under `src/views/` can own their route component, subcomponents, local store modules, and route-specific helpers.
  - Shared shell-level frontend state should live under `src/views/application/`, and the canonical API client should live under `src/utils/api.ts`.

## Current Architecture Decisions

### Django Repository Conventions

- Base backend classes live in `core/`, with `ProjectBaseModel` and `ProjectBaseAPIView` currently provided through `core/common.py`.
- Backend views should inherit from `ProjectBaseAPIView`, use `check_has_permission` for permission checks, and call `require_fields` when explicit payload-field validation is needed before serializer validation.
- For custom permissions, use `ProjectBaseModel.get_custom_permission(...)` instead of indexing `_meta.permissions` or hand-building permission strings.
- Models should continue extending `ProjectBaseModel`.
- When model audit tracking is needed, use `history_log_fields` or `history_log_private_fields` and pass `log_user_id` into `save()`.
- Existing backend relationships in this repo follow `on_delete=models.DO_NOTHING`; keep that convention unless you are making a deliberate migration with a clear data-integrity plan.
- `core/common.py` is already overloaded. Do not add new unrelated concerns there, and prefer extracting focused modules such as `core/base_models.py`, `core/base_views.py`, `core/auth_backends.py`, `core/encryption.py`, `core/email.py`, `core/admin_widgets.py`, or `core/test_fixtures.py` when touching one concern deeply.
- When the base view exposes helpers such as `create_options_from_choices`, use them instead of rebuilding choice-option payloads ad hoc.
- This repo uses `drf-standardized-errors`; in views, raise `rest_framework.exceptions.ValidationError`, and in serializers, keep field validation in `serializers.ValidationError` so responses stay in the standardized shape.
- Shared backend fixture builders belong in `core/test_fixtures.py`, and tests should mirror those helpers instead of creating one-off builders in each module.
- When view tests need model permissions, resolve them through the model helper methods the repo already uses and grant them explicitly.
- The Django settings chain in this repo is `base.py -> dev_local.py -> dev_pytest.py -> dev_docker.py -> dev_github.py -> production.py`.
- Background task wiring follows the task-app pattern already used in the repo: add behavior on the task model or task class, register it in the task map, expose a Celery entrypoint, schedule it when needed, and add tests in the task app.
- When the task framework supports progress reporting, use `self.set_message_and_percent(...)` instead of inventing parallel progress tracking.

### Frontend Repository Conventions

- The canonical frontend API client in this repo is `ApiClient`; keep Axios imports there and route domain modules through it.
- In this repository, `ApiClient` lives in `src/utils/api.ts` rather than a top-level `src/services/` folder.
- Use `buildParamsConfig` with camelCase params and let the API client handle casing conversion.
- Reuse the repo's shared loading, error, markdown, recent-run, and assistant-state components before adding view-local replacements.
- Do not render a second empty optimistic assistant bubble while a waiting-state card is already visible.
- Use `useClipboard` for copy interactions instead of direct `navigator.clipboard` calls.

## Consistency Checklist

### Project

- Project-specific rules are captured here instead of being mixed into global guidance.
- Repository layout, local tooling, and migration notes are explicit.
- Cross-cutting product and architecture decisions that are not general development rules live here.
