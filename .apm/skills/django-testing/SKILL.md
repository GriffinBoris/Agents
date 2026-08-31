---
name: django-testing
description: Design small, behavior-focused unit and integration tests for Django, Django REST Framework, Celery, and pytest, including fixtures, serializers, views, models, permissions, ownership isolation, persistence, and API outcomes. Use when creating, editing, reviewing, debugging, or running Django backend tests; do not trigger for production-code-only work.
---

# Django Testing

## Scope

- Apply these conventions to Django, DRF, Celery, serializer, view, model, permission, and backend integration tests.
- Prefer small unit tests at the narrowest boundary that owns the behavior; use framework or database integration only when it is part of the contract being proved.
- Always load `python-conventions` alongside this skill.
- Load `django-patterns` only when production code changes or a test needs the detailed implementation contract for the behavior under test.

## Workflow

1. Inspect the repository's test configuration, exact commands, shared fixture helpers, and closest comparable tests.
2. State the behavior as inputs or preconditions, one action, and observable expected outcomes; identify its owning boundary and read [testing.md](references/testing.md).
3. Open only the matching test example below and any production example needed to establish the contract.
4. Keep ownership, permissions, inputs, state transitions, and expected outcomes visible in the test.
5. Run the smallest relevant pytest target, then the repository's required Ruff or broader verification when warranted.

## Example Selection

- Read [shared test fixtures](references/examples/django-shared-test-fixtures.md) when object construction repeats across test modules or ownership relationships must stay explicit.
- Read [serializer tests](references/examples/django-serializer-tests.md) for input validation, protected scope, custom persistence, exact output shape, nested output, or serializer context.
- Read [view tests](references/examples/django-view-tests.md) for routing, authentication, permissions, ownership isolation, route-owned scope, HTTP errors, or response serialization.
- Read [model tests](references/examples/django-model-tests.md) for persistence behavior, lifecycle methods, state transitions, constraints, history, or model-backed tasks.

Open an example only when its test boundary matches the task. Read its scenario and heading list first, then load only the relevant sections. Treat paths and domain names as illustrative; use `project-architecture` and the closest repository tests for actual locations and commands.

## Completion Checklist

- Each test proves a meaningful behavior and would fail if that behavior were absent, reversed, or returned the wrong outcome.
- Tests stay at the smallest useful boundary and do not merely execute code, chase coverage, or assert private implementation details.
- Shared builders keep required ownership relationships explicit and do not hide permissions or assertions.
- Serializer tests cover validation, protected scope, persistence, and exact output shape where applicable.
- View tests cover positive, unauthenticated, permission-negative, ownership-negative, and spoofed-scope behavior where applicable.
- Model tests refresh state and assert persisted behavior at the model boundary.
- Session-authentication tests cover the repository's bootstrap, CSRF, login, refresh, and logout contracts when those behaviors change.
- The smallest relevant pytest target and required lint checks were run or their blockers were reported.
