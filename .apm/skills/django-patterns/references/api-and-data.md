# Django APIs And Data Boundaries

## Contents

- Data ownership and organization scoping
- Views, query parameters, API structure, and permissions
- Serializers
- Backend coding style and error handling

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

## Backend Coding Style And Error Handling

- Use explicit local names such as `instance` and `queryset`, reuse existing permission checks, and follow the common attribute ordering.
- When class-based views expose shared attributes, prefer the common ordering `constants`, `queryset`, `serializer_class`, `permission_classes`, then methods.
- Prefer using `settings.<VAR>` directly instead of copying settings values into local module constants.
- If the repository uses standardized DRF error responses, raise DRF exceptions from views and keep serializer-level validation inside serializers so the shared error shape stays consistent.
- Only return custom `{'detail': ...}` payloads when there is a strong reason and it matches surrounding code.
