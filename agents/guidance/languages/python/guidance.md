---
id: language-python-guidance
title: Python Guidance
description: Durable Python conventions used by backend and agent code in this repository.
kind: guidance
scope: language
name: python
tags:
  - language
  - python
applies_to:
  - python
status: active
order: 1
---

# Python Guidance

## Purpose

- Capture Python-specific conventions that apply across backend and agent code.
- Keep Django, DRF, and Celery rules in `agents/guidance/frameworks/django/guidance.md`.
- Keep repository- or product-specific architecture decisions in `agents/guidance/project/guidance.md`.

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
