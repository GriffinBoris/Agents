---
name: frontend-homogeneity-audit
description: Audit Vue and TypeScript frontend code against established route, component, composable, store, shell, API, form, and UI patterns. Use when explicitly reviewing or comparing frontend consistency; do not trigger for ordinary implementation that only needs Vue guidance.
---

# Frontend Homogeneity Audit

## Scope

- Compare Vue and TypeScript frontend code with the closest established repository patterns.

### Boundaries

- Use this as the frontend pattern-matching audit for Vue and TypeScript code.
- Pair it with `architecture-audit` when file, folder, or code structure also needs review.
- Follow the shared review contract in [review-workflows](../review-workflows/SKILL.md); the criteria and output below are additions specific to frontend consistency.

## Workflow

1. Apply the shared review workflow.
2. Load the Vue guidance and only the examples matching the frontend concerns in scope.
3. Inspect the closest comparable route, component, store, composable, and API module, then apply every relevant criterion below.

## Reference Selection

- [Vue patterns](../vue-patterns/SKILL.md)
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

In addition to the shared review output, include:

- preferred reference files and why they fit
- reused shared pieces or route patterns

## Completion Checklist

- The closest comparable route, component, store, composable, and API patterns were reviewed where applicable.
- Every applicable route, API, shell, UI, and form concern above was evaluated.
