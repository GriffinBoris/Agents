---
name: vue-patterns
description: Apply production-code implementation conventions for Vue 3, TypeScript, Pinia, Vue Router, API clients, session authentication, components, forms, styling, and state management. Use when creating, editing, reviewing, or refactoring Vue production code; do not trigger for test-only work.
---

# Vue Guidance

## Scope

- Apply these conventions to Vue, TypeScript, Pinia, Vue Router, frontend API, component, form, and other production frontend work.
- Load `vue-testing` when test files change or test design is part of the task.

## Workflow

1. Inspect a comparable route, component, composable, store, type, and API module before choosing a pattern.
2. Identify the affected concerns and read only the matching references below.
3. Open only the examples needed to confirm a concrete implementation pattern.
4. Reuse the repository's existing UI, API, state, and validation infrastructure.
5. Run the repository's linter, typecheck, tests, and build checks appropriate to the change; use `vue-testing` for test implementation or review.

## Reference Selection

| Work being performed | Read |
| --- | --- |
| Project structure, route folders, application shell, router guards, session auth, SSO, or legacy migration | [structure-routing-and-auth.md](references/structure-routing-and-auth.md) |
| API client, Axios ownership, requests, errors, casing conversion, or TypeScript API contracts | [api-and-types.md](references/api-and-types.md) |
| Pinia stores, domain models, request types, route views, async orchestration, or polling | [state-and-views.md](references/state-and-views.md) |
| Components, shared UI, theme tokens, layout, forms, validation, dialogs, or visual consistency | [ui-and-forms.md](references/ui-and-forms.md) |

Read every reference whose row matches the task. For cross-cutting changes, load multiple references; do not load unrelated references preemptively.

## Example Selection

- App shell and routing: [app layout](references/examples/vue-app-layout.md), [auth shell](references/examples/vue-auth-shell.md), [route auth guard](references/examples/vue-route-auth-guard.md), [route folder](references/examples/vue-route-folder.md), and [workspace shell page](references/examples/vue-workspace-shell-page.md).
- API boundaries and errors: [API client](references/examples/vue-api-client.md), [standardized error helpers](references/examples/vue-standardized-error-helpers.md), and [type interface pattern](references/examples/vue-type-interface-pattern.md).
- State and route orchestration: [feature store route](references/examples/vue-feature-store-route.md), [route query state](references/examples/vue-route-query-state.md), [composable reactivity](references/examples/vue-composable-reactivity.md), [polling](references/examples/vue-polling.md), and [task polling](references/examples/vue-task-polling.md).
- Forms and dialogs: [form validation](references/examples/vue-form-validation.md), [dialog form](references/examples/vue-dialog-form.md), and [multi-step form](references/examples/vue-multi-step-form.md).
- Shared UI and feedback: [app-owned wrapper](references/examples/vue-app-owned-wrapper-component.md), [table wrapper](references/examples/vue-table-wrapper.md), [loading/error states](references/examples/vue-loading-error-states.md), [notification system](references/examples/vue-notification-system.md), and [clipboard](references/examples/vue-clipboard.md).
- Route views and authentication: [view pattern](references/examples/vue-view-pattern.md) and [session SSO login](references/examples/vue-session-sso-login.md).

Open an example only when its pattern matches the task. For a long example, read its scenario and heading list first, then load only the relevant section instead of the entire file. Treat examples as structural references, not mandatory boilerplate. Treat their paths, folder names, and domain names as illustrative; use `project-architecture` and the closest repository code for actual route roots, shell locations, API-client paths, and migration targets.

## Completion Checklist

- Component names and file casing are correct.
- Existing UI primitives are reused before new ones are created.
- Spacing and styling align with comparable features.
- API calls flow through the single canonical client.
- API boundary types avoid `any` and `unknown`.
- Components do not mix Options API and Composition API.
- Form state uses dedicated input types instead of entity models with placeholder IDs.
- Session-backed auth uses the shared API client, shared shell store, route metadata, and one global router guard instead of route-local bootstrap or redirect logic.
