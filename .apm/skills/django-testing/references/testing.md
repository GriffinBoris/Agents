# Django Testing

## Contents

- Behavioral test design
- Test quality
- Shared test fixtures and permissions
- Serializer tests
- View tests
- Model tests

## Behavioral Test Design

- Test the public behavior or contract, not the implementation steps used to produce it. Express each scenario as preconditions and inputs, one action, and concrete observable outcomes.
- Use the narrowest boundary that can prove the behavior. Prefer a small unit test for pure domain logic; use serializer, model, view, task, or database integration tests only when that boundary owns validation, persistence, authorization, dispatch, or another framework-backed contract.
- Keep each test about one behavior. Multiple assertions are appropriate when they jointly describe the same outcome, such as a response and its persisted state.
- Cover the normal positive outcome and meaningful negative, failure, and boundary outcomes. Choose cases from the contract and risk; do not add permutations that prove nothing new.
- Derive expected values from the requirement or domain contract. Do not reproduce the production algorithm in the test and then compare the implementation with itself.
- Assert the returned value, raised domain error, response, persisted state, emitted task, or absence of a prohibited side effect. Assert collaborator calls only when the interaction itself is part of the public contract.
- Name tests for the behavior and expected outcome so a failure explains which contract broke.

## Test Quality

- A useful test fails when the intended behavior is removed, reversed, or produces the wrong result. Verify this mentally while reviewing the test; a test that still passes against a broken implementation is not protecting the contract.
- Do not add tests merely to increase coverage, execute a line, prove that an object can be constructed, assert only that a value is not `None`, or verify a mock called another mock. Those checks are valid only when that exact fact is a meaningful contract.
- Do not test Django, DRF, pytest, or another library's own behavior. Test the application decision or configuration that uses it.
- Mock external I/O, time, randomness, and other nondeterministic boundaries when they are not the subject of the test. Do not mock away the validation, persistence, authorization, or domain behavior being proved.
- Prefer direct outcome assertions over broad call-count assertions. Use exact interaction assertions for contracts such as “enqueue once,” “send nothing,” or “do not call the provider after validation fails.”
- Keep setup minimal and relevant. If a broad fixture hides the input, actor, ownership scope, or expected state that makes the scenario meaningful, make those facts explicit in the test.
- Treat coverage as a way to find unexamined behavior, not as evidence that the behavior is tested correctly.

## Shared Test Fixtures and Permissions

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
- Compare response payloads against independently tested serializer output when the view's contract is to return that serializer shape; also assert any status, persistence, or side effect owned by the view.
- Cover positive, permission-negative, and ownership-boundary cases.
- For mutations, assert the intended database state after success and the absence of prohibited changes after failure.

### Model Tests

- Group related assertions in a single test class per model.
- Prefer shared helper methods for repeated object construction.
- Cover steady-state behavior and state transitions.
- Refresh instances before asserting post-conditions.
- Call `timezone.now()` once per helper to avoid drift-related failures.
