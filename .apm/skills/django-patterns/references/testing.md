# Django Testing

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
