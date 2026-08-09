---
name: python-conventions
description: Apply the repository's Python implementation, typing, testing, and verification conventions when editing Python modules, tooling, or tests.
---

# Python Guidance

## Scope

- Capture Python-specific conventions that apply across backend and agent code.
- Keep Django, DRF, and Celery rules in the `django-patterns` guidance skill.
- Keep repository- or product-specific architecture decisions in the `project-architecture` guidance skill.

## Workflow

1. Inspect nearby Python modules, tests, and repository-local guidance before choosing a pattern.
2. Identify the affected concerns and read every matching reference below.
3. Open only the examples needed to confirm a concrete implementation pattern.
4. Implement consistently with the local repository and the loaded rules.
5. Run targeted Ruff and pytest verification appropriate to the change.

## Reference Selection

| Work being performed | Read |
| --- | --- |
| Imports, modules, implementation shape, classes, stateful services, typing, or readability | [implementation.md](references/implementation.md) |
| Ruff, pytest, HTTP helpers, adapters, logging, debugging, or test structure | [verification-and-testing.md](references/verification-and-testing.md) |

Read every reference whose row matches the task. For ordinary Python code changes, load both references when implementation and verification are both in scope.

## Example Selection

- Read [stateful service class](references/examples/python-stateful-service-class.md) when several operations share client, identity, or configuration state.
- Read [segmented API client](references/examples/python-segmented-api-client.md) when organizing a client with several endpoint groups.
- Read [pytest class setup](references/examples/python-pytest-class-setup.md) when tests share explicit per-test setup.

Open an example only when its pattern matches the task. For a long example, read its scenario and heading list first, then load only the relevant section instead of the entire file. Treat examples as structural references, not mandatory boilerplate.

## Completion Checklist

- Imports are explicit, ordered, and top-level.
- `__init__.py` files stay minimal.
- Typing follows repository conventions.
- `ruff check` expectations are clear and were followed for modified files.
- Django-specific behavior is documented in the Django guide instead of being duplicated here.
