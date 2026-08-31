---
name: django-patterns
description: Apply production-code implementation conventions for Django, Django REST Framework, Celery, backend APIs, authorization, serializers, models, migrations, session authentication, and integrations. Use when creating, editing, reviewing, or refactoring Django production code; do not trigger for test-only work.
---

# Django Guidance

## Scope

- Apply these conventions to Django, DRF, Celery, backend API, and other production backend work.
- Always load `python-conventions` alongside this skill.
- Load `django-testing` when test files change or test design is part of the task.

## Workflow

1. Inspect nearby Django code and repository-local guidance before choosing a pattern.
2. Identify the affected concerns and read only the matching references below.
3. Open only the examples needed to confirm a concrete structure or implementation pattern.
4. Implement consistently with the local repository and the loaded rules.
5. Run the repository's targeted verification; use `django-testing` for test implementation or review.

## Reference Selection

| Work being performed | Read |
| --- | --- |
| Apps, feature packages, module boundaries, URLs, admin, commands, or settings | [application-structure.md](references/application-structure.md) |
| Views, APIs, query parameters, scoping, permissions, serializers, or DRF errors | [api-and-data.md](references/api-and-data.md) |
| Models, migrations, lifecycle methods, or Celery tasks | [models-and-tasks.md](references/models-and-tasks.md) |
| Browser sessions, CSRF, SSO, sensitive uploads, or Django security configuration | [browser-auth-and-security.md](references/browser-auth-and-security.md) |
| External services, webhooks, provider events, retry behavior, or concurrency-safe idempotency | [integrations-and-idempotency.md](references/integrations-and-idempotency.md) |

Read every reference whose row matches the task. For cross-cutting changes, load multiple references; do not load unrelated references preemptively.

## Example Selection

- App and route organization: [app layout](references/examples/django-app-layout.md), [project URL hub](references/examples/django-project-url-hub.md), [app URL hub](references/examples/django-app-url-hub.md), and [feature URL module](references/examples/django-feature-url-module.md).
- Views and actions: [view](references/examples/django-view.md), [action view](references/examples/django-action-view.md), [transition endpoint](references/examples/django-transition-endpoint.md), and [query parameters](references/examples/django-query-params.md).
- Serializers and models: [serializer](references/examples/django-serializer.md), [model](references/examples/django-model.md), [concrete model metadata](references/examples/django-concrete-model-meta.md), [direct attribute access](references/examples/django-direct-attribute-access.md), and [domain profile ownership](references/examples/django-domain-profile-vs-auth-user.md).
- Request context and authorization: [request-context middleware](references/examples/django-request-context-middleware.md) and [shared scope validation](references/examples/django-shared-scope-validation.md).
- Sessions and SSO: [session/CSRF SPA](references/examples/django-session-csrf-spa.md) and [browser-session SSO](references/examples/django-session-sso.md).
- Tasks and operations: [Celery enqueue](references/examples/django-celery-enqueue.md), [task dispatch](references/examples/django-task-dispatch.md), [management command](references/examples/django-management-command.md), and [admin](references/examples/django-admin.md).
- Integrations: [durable sync event processing](references/examples/django-durable-sync-events.md).

Open an example only when its pattern matches the task. For a long example, read its scenario and heading list first, then load only the relevant section instead of the entire file. Treat examples as structural references, not mandatory boilerplate.

## Completion Checklist

- Views inherit from the expected base classes.
- Serializer field tuples are complete and non-duplicated.
- URL names follow kebab-case `{model}-{action}` patterns.
- List endpoints are scoped to the current user or organization.
- Mutating endpoints return the created or updated resource.
- Model lifecycle methods do not hide third-party I/O.
- Session-authenticated browser APIs keep CSRF enabled and provide a bootstrap flow for session state and a CSRF token.
