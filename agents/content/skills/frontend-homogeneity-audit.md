---
kind: skill
name: frontend-homogeneity-audit
description: >
  Find and compare frontend patterns such as route views, local route state,
  shared components, composables, stores, and API usage so new work matches
  established Vue and project conventions.
---

# Frontend Homogeneity Audit

## When to use
- Adding or reviewing a Vue route, route-local component set, store, composable, or API call
- Checking whether a frontend change matches the established shell, route, and UI patterns
- Looking for reusable UI and route-folder patterns before creating something new

## Boundary
- Use this as the frontend pattern-matching audit for Vue and TypeScript code.
- Pair it with `architecture-audit` when file, folder, or code structure also needs review.
- Use `full-review` for the final comprehensive scoped review workflow.

## Read first
- `agents/guidance/guidance.md`
- `agents/guidance/frameworks/vue/guidance.md`
- `agents/guidance/project/guidance.md`
- relevant docs in `agents/guidance/frameworks/vue/examples/`

## Where to look
- `frontend/src/views/`
- `frontend/src/components/`
- `frontend/src/composables/`
- `frontend/src/services/`
- `frontend/src/stores/`
- nearby route folders similar to the work in scope

## What to compare

### Route structure
- route folder layout under `src/views/`
- route-local `store.ts`, composables, types, constants, and subcomponents
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

## Living document note
- If you find a durable frontend pattern missing from the modular guidance tree, update `agents/guidance/frameworks/vue/`, `agents/guidance/project/`, or add a named example.
