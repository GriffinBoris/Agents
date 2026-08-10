---
name: frontend-homogeneity-audit
description: Audit Vue and TypeScript frontend code against established route, component, composable, store, shell, API, form, and UI patterns. Use when explicitly reviewing or comparing frontend consistency; do not trigger for ordinary implementation that only needs Vue guidance.
---

# Frontend Homogeneity Audit

## Scope

- Compare Vue and TypeScript frontend code with the closest established repository patterns.
- Report reusable pieces, verified deviations, and the simplest fixes within the declared review scope.

### Boundaries

- Use this as the frontend pattern-matching audit for Vue and TypeScript code.
- Pair it with `architecture-audit` when file, folder, or code structure also needs review.
- Use `full-review` for the final comprehensive scoped review workflow.

## Workflow

1. State the exact frontend scope and any blind spots.
2. Load the applicable baseline, Vue, project, and example guidance.
3. Inspect the closest comparable route, component, store, composable, and API module before judging the change.
4. Compare every relevant concern below and record each verifiable deviation.
5. Report reused patterns, simplest fixes, or explicitly state that no deviations were found.

## Reference Selection

- [Engineering baseline](../../instructions/engineering-baseline.instructions.md)
- [Vue patterns](../vue-patterns/SKILL.md)
- the consumer-owned `project-architecture` skill
- relevant docs in `.apm/skills/vue-patterns/references/examples/`

## Review Criteria

### Inspection Targets

- the repository's configured route root, commonly `frontend/src/views/` or `frontend/src/features/`
- `frontend/src/components/`
- `frontend/src/composables/`
- the canonical API-client or transport module
- shared shell stores and route-local stores in their established locations
- nearby route folders similar to the work in scope

### Route structure
- route folder layout under the repository's chosen route root
- route-local descriptively named stores, composables, types, constants, and subcomponents
- whether state belongs in the route folder or a shared store

### API usage
- one canonical API client
- camelCase params through the shared query-param helper
- typed request and response models

### Shell and navigation
- auth-aware shell patterns
- route meta and global guard usage
- root-level notification containers

### Shared UI
- loading, error, dialog, clipboard, polling, notification, and table-wrapper patterns
- view-local composition versus genuinely shared primitives

### Forms
- dialog ownership
- shared validation and error parsing
- parent-owned multi-step DTOs when flows span multiple screens

## Output
- preferred reference files and why they fit
- reused shared pieces or route patterns
- deviations found and the simplest fixes
- every verifiable in-scope guidance deviation, or an explicit statement that none were found
- blind spots and unverified areas

## Completion Checklist

- The exact frontend scope and any unverified areas are stated.
- The closest comparable route, component, store, composable, and API patterns were reviewed where applicable.
- Every verified deviation or an explicit no-findings result is reported.

## Maintenance

- If you find a durable frontend pattern missing from the guidance skills, update `.apm/skills/vue-patterns/`, the consumer's `project-architecture` skill, or add a named example under `vue-patterns/references/examples/`.
