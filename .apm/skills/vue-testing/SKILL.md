---
name: vue-testing
description: Design small, behavior-focused unit, component, and end-to-end tests for Vue 3 and TypeScript across components, composables, Pinia stores, Vue Router, forms, API boundaries, and browser outcomes. Use when creating, editing, reviewing, debugging, or running Vue frontend tests; do not trigger for production-code-only work.
---

# Vue Testing

## Scope

- Apply these conventions to Vue and TypeScript unit, component, composable, store, router, browser, and end-to-end tests.
- Prefer small unit tests at the narrowest boundary that owns the behavior; use component, router, or end-to-end tests only when the contract crosses those boundaries.
- Load `vue-patterns` only when production code changes or a test needs the detailed implementation contract for the behavior under test.

## Workflow

1. Inspect the repository's test runner, commands, setup files, helpers, and closest comparable tests before choosing tools or structure.
2. State the behavior as inputs or preconditions, one action, and observable expected outcomes; read [testing.md](references/testing.md), then identify the owning boundary and failure modes.
3. Use the selection table below to inspect only the relevant test or verification sections of the matching Vue examples.
4. Keep tests focused on public behavior, emitted events, state changes, routing outcomes, and user-visible states instead of implementation details.
5. Run the smallest relevant frontend test target, then the repository's required lint, typecheck, or broader verification when warranted.

## Contract-Specific Selection

| Test concern | Inspect |
| --- | --- |
| API client ownership, request helpers, or standardized errors | [API client](../vue-patterns/references/examples/vue-api-client.md) and [error helpers](../vue-patterns/references/examples/vue-standardized-error-helpers.md) |
| Store, composable, polling, timer, stale-response, or browser API behavior | [feature store](../vue-patterns/references/examples/vue-feature-store-route.md), [polling](../vue-patterns/references/examples/vue-polling.md), [task polling](../vue-patterns/references/examples/vue-task-polling.md), and [clipboard](../vue-patterns/references/examples/vue-clipboard.md) |
| Loading, error, empty, retry, notification, or stale-data states | [loading and errors](../vue-patterns/references/examples/vue-loading-error-states.md) and [notifications](../vue-patterns/references/examples/vue-notification-system.md) |
| Router, auth guard, session bootstrap, SSO, redirect, or query state | [route guard](../vue-patterns/references/examples/vue-route-auth-guard.md), [auth shell](../vue-patterns/references/examples/vue-auth-shell.md), [session SSO](../vue-patterns/references/examples/vue-session-sso-login.md), and [route query state](../vue-patterns/references/examples/vue-route-query-state.md) |
| Form, dialog, or multi-step validation behavior | [form validation](../vue-patterns/references/examples/vue-form-validation.md), [dialog form](../vue-patterns/references/examples/vue-dialog-form.md), and [multi-step form](../vue-patterns/references/examples/vue-multi-step-form.md) |
| Route view, shared component, wrapper, or table behavior | [view pattern](../vue-patterns/references/examples/vue-view-pattern.md), [app-owned wrapper](../vue-patterns/references/examples/vue-app-owned-wrapper-component.md), and [table wrapper](../vue-patterns/references/examples/vue-table-wrapper.md) |

Inspect each example's scenario and heading list first. Load only the test, verification, refactor-signal, or contract sections needed for the task; do not load entire implementation examples by default.

## Completion Checklist

- Each test proves a meaningful behavior and would fail if that behavior were absent, reversed, or returned the wrong outcome.
- Tests stay at the smallest useful boundary and do not merely execute code, chase coverage, or assert private implementation details.
- Tests follow the repository's established runner, mounting, mocking, and file-placement patterns.
- Assertions cover observable success, failure, boundary, and cleanup behavior relevant to the changed contract.
- Router, authentication, asynchronous, and scoped state tests cover stale or unauthorized outcomes where applicable.
- End-to-end coverage is reserved for behavior that crosses browser, navigation, session, or multiple-component boundaries.
- The smallest relevant test target and required lint or type checks were run or their blockers were reported.
