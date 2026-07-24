---
id: global-guidance
title: Global Guidance
description: Cross-stack development guidance that applies across the repository.
kind: guidance
scope: global
name: global
tags:
  - global
applies_to: []
status: active
order: 0
---

# Global Guidance

## Purpose

- Capture the development guidance that applies generally across the repository, regardless of language, framework, or feature area.
- Keep project-specific layout, tooling, migration notes, and product architecture decisions in `agents/guidance/project/guidance.md`.
- Read this file before work, then read the relevant language, framework, and project guidance packages.

## Living Document Philosophy

- Guidance evolves with the codebase. When you discover a durable pattern, architectural decision, or recurring mistake, record it here.
- Prefer small, incremental edits over large rewrites, and explain why a rule exists, not just what it is.
- If a rule becomes obsolete, remove or revise it instead of layering exceptions. If two rules conflict, resolve the conflict explicitly.
- Avoid speculative rules. Document decisions made, not hypotheticals.

## Expectations & Best Practices

### Agent Compliance

- If a request conflicts with this file, call out the conflict and follow the most restrictive rule.
- Load the relevant language, framework, and project guidance before stack-specific work.

### Match Existing Patterns

- Follow the project's established coding style, naming conventions, and architectural patterns.
- Reference similar existing code before implementing new features.

### Tool Use

- If the repository exposes web-search, docs, or context tools, use them only when needed and within repository rules.
- If the repository provides custom CLI tooling, prefer it over ad hoc scripts.

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

### Review Reporting

- Full reviews must report every finding in scope, not only the biggest or most representative ones.
- If the same issue appears multiple times, enumerate every audited occurrence or provide the full occurrence list.
- Summaries are fine only when they are paired with a complete findings section.
- List any skipped files, blind spots, or lightly checked areas explicitly.

## General Principles

### Core Philosophy

- **YAGNI first.** Do not add helpers, constants, abstractions, extension points, or configuration layers until the current requirements actually need them.
- **Readability over performance.** If a simpler approach is slightly slower but far easier to understand, choose simplicity. Optimize only when there is a measured, real problem.
- **No defensive programming.** Trust data and contracts. Do not add try or catch blocks, fallback values, or silent error handling just in case.
- **Prefer direct usage over one-off helpers.** If a helper is only used once and adds no clarity, inline it.

### Follow Existing Architecture

- Reference other views, models, serializers, admin files, apps, and folders to mirror the established architecture.
- When adding utilities or one-off data tasks, implement them as management commands, dedicated CLI tools, or equivalent first-class entrypoints instead of placing scripts in the repo root.
- Prefer the clearest end state over the smallest diff. If new work reveals the current structure is the wrong fit, do a focused refactor and remove obsolete code.
- Do not keep layering new logic on top of a messy local design just to avoid rewriting it. If the touched area will be clearer, simpler, and more aligned with guidance after a focused rewrite, rewrite it instead of patching around the existing shape.
- Prefer a clean rewrite of the local unit in scope, such as a file, workflow, view, serializer, or component, over incremental clutter that preserves confusing structure. Keep the rewrite focused, but choose the version future readers will understand fastest.

### Reuse Existing Components

- Reuse existing classes, methods, and structures to preserve consistency and avoid duplication.

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
- Never ship unauthenticated API endpoints.
- Scope data to the current user or tenant.
- Tests must verify ownership boundaries.
- Avoid wildcard `ALLOWED_HOSTS` in production.

### Logging Discipline

- Log at boundaries, not every intermediate step.
- Use one structured line per event.
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

These guidelines are constraints in service of clarity, not bureaucracy. If following a rule would make the code worse, pause and update the rule.
