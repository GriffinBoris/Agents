---
description: Always-on cross-stack engineering rules and routing to task-specific guidance skills.
---

# Agent Guidance

## Purpose

- Capture the development guidance that applies generally across the repository, regardless of language, framework, or feature area.
- Keep project-specific layout, tooling, migration notes, and product architecture decisions in `project-architecture` guidance skill.

## Living Document Philosophy

- Guidance evolves with the codebase. Update it when you discover repeated patterns, architectural decisions, common mistakes, or better ways to explain existing guidance.
- When a task reveals a verified, durable pattern that would help future work, update the relevant guidance when that documentation change is within scope. Otherwise, recommend the update rather than changing policy incidentally.
- Before finishing a task that changes guidance or exposes a repeatable guidance gap, decide whether a rule refinement, exception, or clarification should be recorded.
- When reflecting at the end of a task, explicitly check for:
  - verification coverage and any failures or timeouts
  - UI and UX consistency with existing patterns
  - reuse of existing components or utilities before creating new ones
  - data handling consistency, including query params, formatting, and error handling

### How to Update

- Edit authored `.apm/` sources, not generated `AGENTS.md` files or harness output.
- Put reusable rules and examples with the shared skill that owns the concern; keep repository-specific guidance in the consuming repository's `project-architecture` skill.
- Prefer small, incremental edits over large rewrites.
- Add context explaining why a rule exists, not just what it is.
- If a rule becomes obsolete, remove or revise it instead of layering exceptions.
- If two rules conflict, resolve the conflict explicitly.
- Avoid speculative rules. Document decisions made, not hypotheticals.

## Expectations & Best Practices

### Agent Compliance

- Treat this file as required always-on guidance.
- Before making changes, identify and follow the sections relevant to the task.
- Resolve conflicts by instruction authority first and specificity second. At the same authority level, repository-specific guidance overrides general shared guidance for that repository. Surface any unresolved conflict instead of silently choosing a rule.
- Read the relevant language, framework, and project guidance before stack-specific or project-specific work.

### Match Existing Patterns

- Before choosing a pattern, inspect the closest comparable code and follow the project's established style, naming, and architecture unless the task deliberately changes that pattern.

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

- **Simplicity, readability, and organization above all else.** Every decision should optimize for code that is easy to understand, intelligently organized, loosely coupled, and minimal in scope.
- **YAGNI first.** Every line and abstraction must earn its place. Do not add helpers, constants, extension points, configuration layers, or other structures until the current requirements need them.
- **Readability over performance.** If a simpler approach is slightly slower but far easier to understand, choose simplicity. Optimize only when there is a measured, real problem.
- **No speculative defensive programming.** Trust verified internal contracts and avoid broad fallback behavior that hides defects. Handle expected failures at external, user-input, cleanup, and integration boundaries; never silently swallow errors.
- **Keep one source of truth.** Reuse existing behavior, data shapes, components, and utilities before introducing a second concept that models the same thing. Remove redundant normalization, casting, null checks, intermediate values, or fallback logic after verifying the real contract.
- **Prefer direct code over premature reuse.** A repeated line or two can be clearer than indirection. Extract a helper or abstraction when actual reuse or a material clarity improvement justifies it; inline one-off helpers that add no clarity.
- **Loose coupling.** Components, modules, and services should have clear boundaries and minimal dependency on each other's internals.
- **Intelligent organization.** Group related things together, separate unrelated things, and make the codebase structure reflect the domain.

### Follow Existing Architecture

- When adding utilities or one-off data tasks, implement them as management commands, dedicated CLI tools, or equivalent first-class entrypoints instead of placing scripts in the repo root.
- Prefer the clearest verified end state over the smallest possible diff. Use a focused refactor when the current structure is demonstrably the wrong fit, the refactor remains within scope, and relevant behavior can be verified.
- An in-scope refactor may replace the local implementation completely when that produces the clearest verified design. Do not preserve obsolete structure by layering a half-migrated hybrid of old and new patterns; retain compatibility or staged-migration code only when a demonstrated requirement needs it.
- Do not layer new logic onto a confusing local design solely to avoid changing it. Rewrite the local unit only when doing so is simpler than a patch and does not create unnecessary migration or regression risk.

### Control Flow

- Keep conditional logic shallow.
- Return early when possible to avoid deep nesting and keep intent clear.

### Keep Logic Simple

- Group related steps together so future readers can follow the intent quickly.
- If the current local design has become harder to understand than the underlying requirement, consider a focused rewrite rather than preserving the complexity with another layer.
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
- Combine conditions when they lead to the same outcome.
- Encapsulate fragile third-party integrations behind a small service layer so views, commands, and tasks use a stable interface.

### Parameters and Variables

- Do not add unused parameters to function signatures.
- Remove unused parameters instead of suppressing warnings.

### ID Generation (If Applicable)

- If you use incremental counters for IDs, make the semantics explicit and use them consistently across the codebase.

### God Module Prevention

- One responsibility per file.
- Treat file length and unrelated responsibilities as review signals, not automatic split thresholds. Split a file when the resulting boundaries make ownership and navigation clearer.
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
- Give every API endpoint an explicit access model. Default to authenticated access; make public endpoints deliberate and test their intended boundary.
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
- Use the repository's dependency strategy consistently: lock reproducible application environments, and use intentional compatible ranges when publishing reusable libraries.
- Remove unused dependencies.
- Keep dependency versions consistent across projects that share packages.

### Tooling & CLI Contracts

- Honor all declared CLI arguments.
- Do not hardcode user paths.
- Use context managers or equivalent scoped resource cleanup for files, database connections, and disposable resources.

## Code Review Practices

- Verify usage before claiming redundancy.
- Distinguish intentional design from accidental complexity.
- Document architectural decisions when you discover why something is designed a certain way.
- Create refactoring plans before implementing non-trivial structural changes.

### Readability And Structure Review

- Full reviews should assess file structure, folder structure, module boundaries, and code shape together, not as separate afterthoughts.
- If you cannot summarize the purpose of a file, module, or workflow in one sentence, treat that as a signal that the structure may be too complex.
- Prefer the smallest change that restores clarity, explicit control flow, and sensible boundaries.
- Review public API surface, helper count, and abstraction layers for proportionality to the real problem being solved.

### Centralize Constants

- Put deploy-time configuration in the appropriate settings system. Keep domain constants with the code that owns their meaning, and avoid duplicating either source of truth.
- Keep large SQL or query text in code, not in settings.

## Guidance Skill Routing

- Keep this baseline limited to rules that apply regardless of language, framework, or repository.
- Load `python-conventions` when creating, editing, reviewing, or testing Python code.
- Load `django-patterns` for Django, DRF, Celery, backend API, authorization, serializer, model, migration, or backend-test work.
- Load `vue-patterns` for Vue, TypeScript, Pinia, frontend API, routing, form, component, or frontend-test work.
- Load `ai-generation-patterns` for backend AI or LLM generation workflows.
- Load `integration-boundaries` when code owns external-resource lifecycles or sends requests to user-configurable destinations.
- Load the consuming repository's `project-architecture` skill for repository-specific structure, commands, architecture, and product conventions.
- Load `migration-baseline` only when porting repository-owned or locally modified guidance from a legacy `agents/` or `AGENTS.md` layout into the consumer's local APM guidance.
