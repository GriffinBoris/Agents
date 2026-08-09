# Python Implementation Conventions

## Contents

- Organization and imports
- Implementation choices
- Classes and stateful object-oriented design
- Types and readability

## Organization And Imports

- Order imports as standard library, third-party, framework, then project-local.
- Place imports at the top of the file.
- Avoid inline imports inside functions unless you are breaking a circular dependency and there is no cleaner option.
- Avoid wildcard imports.
- Prefer direct, explicit project import paths over re-exported or indirect paths when the direct module is clearer.
- Keep `__init__.py` files minimal. Use them only for module declarations or explicit exports when that materially improves imports.
- Do not put runtime logic, workflow code, view classes, or business logic in `__init__.py` files unless there is a strong, unavoidable reason.

## Implementation

- Stick to single quotes unless triple quotes are required.
- Use logical spacing between imports, constants, classes, and function groups.
- Use one blank line between methods and two blank lines between classes.
- Keep functions small; extract helpers only when they are reused or materially improve clarity.
- Prefer explicit, descriptive names over abbreviations.
- Catch specific exceptions and let unexpected errors surface.
- Avoid dynamic `getattr` and `setattr` unless they are truly necessary.

## Classes And Stateful OOP

- Prefer a class when multiple methods share the same subject, dependency, or workflow state.
- Store stable dependencies and shared context in `__init__` instead of threading them through every method call.
- Keep instance state small and intentional: one domain object, one client, one config object, or a few workflow flags is usually enough.
- Prefer one clear public entrypoint with focused private helpers when a workflow has multiple steps.
- Use private helper methods to break up a larger workflow only when they genuinely share the same instance state.
- Use `@staticmethod` only for logic that does not depend on instance state.
- Use abstract base classes only when multiple implementations truly share the same contract.
- If a class owns resources such as temp files, sessions, or connections, make setup and cleanup explicit, ideally with a context manager.
- Do not create a class when a single pure function would be clearer.

## Types And Readability

- Do not use `from __future__ import annotations` for type hints.
- Use `typing.Optional` and `typing.Union` instead of the `|` union syntax.
- Use builtin collection types such as `list`, `dict`, and `tuple` instead of `typing.List`, `typing.Dict`, and `typing.Tuple`.
- Avoid regex when an exact match works.
- Avoid type-only casts and broad `# type: ignore[...]` pragmas when a clearer boundary exists.
- At third-party integration boundaries, prefer real stubs or isolated service-layer workarounds over broad `# type: ignore[import-untyped]` usage.
