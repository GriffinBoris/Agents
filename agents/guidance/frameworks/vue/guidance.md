---
id: framework-vue-guidance
title: Vue Guidance
description: Durable Vue, TypeScript, Pinia, and frontend API guidance.
kind: guidance
scope: framework
name: vue
tags:
  - framework
  - vue
applies_to:
  - vue
status: active
order: 2
---

# Vue Guidance

## Purpose

- Capture Vue, TypeScript, Pinia, and frontend API conventions.
- Keep item- and repository-specific shell, workspace, branding, and organization architecture in `agents/guidance/project/guidance.md`.

## Frontend Project Structure

- `src/assets` stores static assets such as images and fonts.
- `src/components` stores reusable UI components and app-shell primitives.
- Use `src/components/ui/` for low-level shared controls and surfaces.
- Use `src/components/forms/` for labeled field wrappers that compose `FormField` plus shared input primitives.
- Use `src/components/layout/` for shell containers, scroll frames, and app-level structural wrappers.
- Use `src/components/navigation/` for sidebar, tabs, menus, and other shared navigation pieces.
- Use `src/components/page/` for reusable page-composition blocks such as `PageHeader`, `PageSection`, split layouts, metric cards, and list rows.
- `src/views` stores route-based folders and route entry views.
- Each route folder under `src/views/` can own the route component, local subcomponents, a descriptively named local store file, route-specific composables, types, and constants.
- Keep shared shell-level state under a dedicated shell folder such as `src/views/application/` instead of a top-level catch-all `src/stores/` directory.
- Prefer one primary route-based feature home such as `src/views/` instead of introducing parallel feature-root trees without a migration plan.
- If legacy or transitional code still exists under `src/features/`, migrate it toward `src/views/` as you touch that route area instead of expanding the old structure.
- Keep the canonical API client in one well-known utility or API module instead of adding parallel service directories for the same transport role.
- `src/composables` stores shared Vue composables used across multiple routes.
- `src/router` stores Vue Router configuration.
- `src/types` stores shared global types.
- `src/core` stores core models and utilities.
- `src/styles` stores global styles and CSS utilities.
- Prefer configured import aliases such as `@/views/...`, `@/types/...`, and `@/utils/...` instead of long relative traversal imports when the project supports aliases.

## Shell And Routing

- Keep one shared shell near `App.vue` that mounts the router outlet plus global feedback UI.
- Switch between authenticated and guest layouts in one shared shell or container instead of duplicating layout logic inside route views.
- Keep shell-only pieces grouped under `src/components/application/`, `src/layouts/`, or an equivalent dedicated folder.
- Let the shell own navigation chrome, top-level bootstrap loading states, and router outlet placement.
- Keep page views focused on page composition and domain workflow concerns rather than re-implementing shell structure.
- Prefer route meta flags such as `requiresAuth` with a single global router guard backed by shared auth state.
- For session-backed apps, use the auth-aware shell example as the baseline for bootstrap state, login, logout, guest-only routes, public routes, and permission redirects.
- Keep session bootstrap in the shared shell store, usually under `src/views/application/`, and let the router guard initialize that store once before protected routes render.
- Route views, dialogs, and route-local stores must not call the auth bootstrap endpoint directly. They should read the shared shell store instead.
- Express route access with route metadata such as `requiresAuth`, `guestOnly`, `skipShellBootstrap`, and `requiredPermissions` instead of route-local redirect logic.
- Reset and re-bootstrap the shell store after any frontend flow that creates a new authenticated session, and reset shell state immediately after logout.
- Mount notification or snackbar containers once near the app root and drive them from a shared store or composable.
- Use shared global notifications for cross-feature success and error feedback instead of rendering one-off banners inside every page.

## Theme And Tokens

- Prefer one theme source of truth instead of mixing multiple theming systems.
- When Tailwind is the primary styling layer, prefer semantic utility names such as `bg-surface`, `text-body`, and `border-line` over raw palette classes in application components.
- CSS variables are a good theme source of truth when runtime theme switching is needed.
- Apply the active theme at the app root instead of toggling per-page theme classes.
- Reserve accent colors for actions, focus states, and active UI states; keep primary reading text on neutral text tokens.
- Keep radius, border, and shadow choices consistent across shared shells, cards, nav items, and controls.

## Frontend API

### Single API Client Rule

- Maintain exactly one canonical API client.
- Do not keep parallel implementations such as `apiService.ts` and `useApiClient.ts` when they serve the same role.
- The canonical client should centralize Axios configuration, CSRF handling, snake_case to camelCase conversion, and typed response handling.
- Outside of tests, `axios` imports should live only in the canonical API client layer.
- Put the canonical client in one obvious location, commonly `src/utils/api.ts` or `src/api/client.ts`, and make that location the only runtime Axios owner.
- For Django session-backed browser apps, keep `withCredentials`, XSRF cookie/header configuration, and any Django-rendered CSRF token handoff inside the canonical API client setup path.
- Do not introduce a separate auth API client or local-storage token helper for login, logout, registration, password reset, or invitation acceptance flows.

### API Client Patterns

- Route every request through the canonical shared frontend API client.
- Use `apiClient.get(...)`, `apiClient.post(...)`, `apiClient.put(...)`, and `apiClient.delete(...)` for JSON API requests.
- Use `apiClient.postForm(...)` and `apiClient.putForm(...)` for `FormData` uploads.
- Use `apiClient.setCsrfToken(...)` only at shell/bootstrap boundaries when a CSRF token is read from the rendered page.
- Backend responses should stay snake_case; the client layer converts them to camelCase.
- Components, composables, stores, and route views should work only with camelCase field names.
- The API client converts POST and PUT JSON request bodies from camelCase to snake_case before sending them to the backend.
- Query params should be passed to `buildParamsConfig(...)` as camelCase objects so the shared helper can convert them to snake_case.
- Import query-param helpers with `import { buildParamsConfig } from '@/utils/apiParams'` in domain API modules that accept filters.
- Response and standardized error payloads are converted to camelCase by the API client's response interceptor before callers read them.
- Form uploads should use the API client's FormData methods so payload keys and browser-managed multipart headers are not rewritten like JSON bodies.
- CSRF, credentials, timeout, base URL, and response interception belong inside the canonical API client instead of being configured in route code.
- Group API methods by domain and use consistent names such as `list`, `create`, `detail`, `update`, and `delete`.
- Specialized verbs such as `duplicate` are acceptable when they clearly describe a non-CRUD action.
- Type all responses and payloads.
- Use RESTful URL structures with IDs in the path and nested paths for related resources.
- Use `FormData` for uploads only when needed.
- Customize headers for uploads only when the request truly requires it.
- Use the shared query-param helper when one exists and let the API client handle casing conversion.
- Define domain API modules as top-level `const` blocks and export them through one unified API object.
- Order method parameters from most important to least important.
- Do not set Axios defaults in `main.ts`, stores, or route views; keep transport configuration inside the canonical client.

### API Error Handling

- Use the shared error helpers for standardized DRF error responses instead of parsing Axios errors directly in views or stores.
- Use `extractFirstFieldErrors(...)` for form field error maps and `extractFieldErrors(...)` when multiple messages per field are needed.
- Use `getFirstApiErrorMessage(...)` for workflow-level fallback messages, `getFirstApiErrorCode(...)` for code-specific behavior, and `getApiErrorStatus(...)` for status-specific behavior.
- Use `parseApiError(...)` only inside shared helpers or specialized flows that truly need the full standardized error object.
- Field-error keys should be treated as camelCase on the frontend, even when the backend returned snake_case `attr` values.
- Keep fallback user-facing error messages in the view or store that owns the workflow, but keep response-shape parsing in the shared error helpers.

### Casing Helpers

- `camelToSnake(...)`, `snakeToCamel(...)`, and `snakeFieldAttrToCamel(...)` are API-boundary utilities, not component-level formatting helpers.
- Do not call casing helpers from components, route views, or stores unless you are maintaining the shared API client, query-param helper, or error helpers.
- If a feature needs manual casing conversion, first check whether the data should instead flow through `apiClient`, `buildParamsConfig(...)`, or the shared error helpers.

## Type Discipline

- Do not use `any` or `unknown` at API transport boundaries.
- If the backend shape is uncertain, define an interface with optional fields instead of using `any`.
- If a method declares `Promise<ThingInterface>` or `Promise<ThingResponseInterface>`, it must return the unwrapped payload instead of an `AxiosResponse` object.
- Do not mix unwrapped model returns and `AxiosResponse` returns across API modules.
- Separate form DTOs from persisted entity models.
- Do not use placeholder IDs like `0` or `-1` in form state just to satisfy entity interfaces.
- Prefer `[Thing]RequestInterface` for data sent to the backend.
- Prefer descriptive names for data returned by the backend: use `[Thing]Interface` for persisted resources, names such as `[Thing]AvailableOptionsInterface` for option bundles, and `[Action]ResponseInterface` for endpoint-specific responses that do not have a clearer domain noun.
- Treat returned-data interfaces as API output contracts. Include backend-owned fields such as `id`, timestamps, status, nested output objects, and read-only derived values when the API returns them.
- Treat request interfaces as create/update/action payload and form contracts. Include only fields the frontend can submit, and omit backend-owned fields such as `id`, `createdTs`, `updatedTs`, and read-only derived values.
- Existing `[Thing]InputInterface` files do not need churn-only renames, but prefer `[Thing]RequestInterface` when adding a new API request contract.
- Do not create a dedicated filter interface by default. Type simple query params inline at the API method boundary and pass them through `buildParamsConfig(...)`; extract a named request interface only when the query shape is reused or complex.
- Prefer Zod-inferred request types when a form validates the same shape it submits, and colocate `createDefault...Request()` with that schema.

## Models And Stores

### Models

- Organize models by domain under `src/types/<domain>/`.
- Keep related models together inside the same domain folder.
- Use explicit filenames such as `[Thing]Interface.ts`, `[Thing]RequestInterface.ts`, `[Thing]AvailableOptionsInterface.ts`, `[Action]ResponseInterface.ts`, and `[Thing]Enums.ts` when those shapes exist.
- Store-related view models should live in shared model files rather than being declared inside stores or views.
- Request files may colocate a Zod schema plus a `createDefault...()` helper when that keeps form state and validation close to the request contract.
- Keep request interfaces and returned-data interfaces in separate files when an endpoint or resource has both read and write contracts.
- Keep enum definitions with the returned resource interface when they describe persisted or backend-returned values, and import those enums into request interfaces when forms need to submit them.

### Stores

- Use Pinia intentionally: keep cross-route shell state in shared shell stores, and keep route or feature state in route-local stores.
- Put route-only state in the route folder when that state is not reused elsewhere.
- Keep shared shell-level stores under the shell/application folder instead of a top-level catch-all `src/stores/` directory.
- Do not name local store files `store.ts`; use a descriptive name such as `contactsStore.ts`, `organizationSettingsStore.ts`, or `workspaceDetailStore.ts`.
- Shared shell stores should bootstrap cross-route context once, then expose selected organization, current user, or similar shell-level state for route views to consume.
- Prefer a route-local feature store when three or more route-local components share the same record, loading state, filters, form DTO, or mutation workflow.
- Let route-local feature stores own business state, data fetching, mutations, shared form state, permission-derived actions, and derived domain state used across sibling components.
- Let route-local components under `src/views/<route>/components/` import their colocated feature store directly when that removes prop chains and keeps ownership obvious.
- Keep shared components under `src/components/` store-agnostic and prop-driven even when route-local components are store-aware.
- Avoid passing route-local records, IDs, loading flags, error strings, and mutation callbacks through multiple component layers when the same route-local store can be consumed directly.
- Prefer one focused feature store per route or domain workflow instead of one giant app store.
- Reload data through store actions instead of manually clearing state.
- Use stable, deterministic keys for UI rows and lookup maps.
- If uniqueness depends on multiple fields, use a composite key instead of a display name.
- Do not implement fallback matching based on non-unique attributes.
- Access store state, getters, and actions directly on the store object instead of destructuring them.
- Replace optimistic or streamed array items with new objects instead of mutating captured raw references.

## UI And Component Conventions

### Shared UI

- Reuse existing components, tokens, and layout patterns before creating new ones.
- Prefer PrimeVue for foundational controls and surfaces when it fits the need.
- Do not rebuild standard buttons, inputs, dialogs, menus, tables, or common feedback patterns from scratch unless the shared component layer is a poor fit.
- Keep shared wrappers app-owned even when the implementation is backed by PrimeVue.
- Keep shared components under `src/components/` free of route-specific business logic, route params, API calls, and domain-store imports.
- When a PrimeVue-backed wrapper and a plain HTML wrapper solve the same item problem, keep their app-facing props as similar as practical and let only the internals differ.
- Keep component filenames PascalCase and composables prefixed with `use`.
- Favor shared SCSS or utility classes instead of inline styles unless values are dynamic.
- Prefer Tailwind flex utilities for layout before reaching for grid.
- Prefer Tailwind utility classes directly in components for shell, layout, and surface styling.
- Keep raw CSS limited to base reset concerns unless utilities are not sufficient.
- Keep modal structure consistent with header, body, footer, and accessibility attributes such as `role="dialog"` and `aria-label`.
- Reuse confirm dialogs for destructive actions.
- Respect existing responsive breakpoints when building or reusing dialogs.
- Use shared loading UI before introducing new spinners or progress banners.
- Use shared loading, error, and other feedback components before inventing local alternatives.
- Use the repository's shared clipboard helper instead of direct `navigator.clipboard` calls when one exists.
- Prefer extracting sizable UI blocks into subcomponents so pages stay readable.
- When a route view or shell view starts mixing several distinct sections, split those sections into local subcomponents so the parent reads like a page outline.
- Prefer route-local subcomponents under `src/views/<route>/components/` for route-specific panels, summaries, drawers, and list sections before promoting them into shared `src/components/`.
- When one component contains both desktop and mobile versions of the same UI, prefer small focused subcomponents when that split makes the responsive behavior easier to scan.
- Prefer shared UI inputs and keep spacing consistent with existing utility classes.
- Prefer page-composition wrappers for repeated screen structure so route views can read as page outlines instead of piles of low-level surface markup.
- For repeated resource lists, prefer a shared table or list wrapper that owns headings, loading state, empty state, and pagination slots while feature components supply filters and row markup.
- Prefer shared PrimeVue-based wrappers for shell and navigation primitives such as menus, drawers, and surfaces instead of repeating custom sidebar markup.
- Keep PrimeVue dialog, tooltip, dropdown, and autocomplete usage aligned with established shared patterns instead of introducing one-off variants.
- Avoid ambiguous bulk-table interactions: use explicit selection scope, unique row keys, and pre-sorted data when default ordering depends on multiple fields.
- Do not ship dashboards or cards backed only by placeholder values.

### Styling And Visual Consistency

- Follow established form layout, validation messaging, and table column ordering conventions.
- Keep semantic colors scoped to success, warning, and error states.
- Avoid ad hoc hex colors for surfaces, borders, hover states, and selected states.
- Promote repeated UI into reusable shared components only when reuse is real; otherwise keep composition view-local.
- Keep radii restrained and consistent across shells, cards, and controls.
- Use the same radius family across the workspace by default unless a component has a clear reason to deviate.
- Avoid introducing new global styles when shared utility patterns already exist.
- Align error and retry UI with shared patterns: shared error messages, warn-toned retry buttons, and minimal centered loading states.
- Prefer small shared PrimeVue wrappers for repeated control styling.
- Add tests for complex components using the same local patterns, such as unit, shallow-mount, or snapshot tests, when those patterns already exist in the feature area.

### Casing Discipline

- Frontend code uses camelCase everywhere.
- Backend API responses stay snake_case and are converted by the API client.
- Frontend request bodies and query params should be authored in camelCase and converted only at the API boundary.
- Never pass snake_case keys from components or stores to the API client.
- Never manually convert casing in components.

## Component Paradigms

- Do not mix Options API and Composition API in the same component.
- New code should use `<script setup lang="ts">`.
- If a legacy file uses Options API, keep that file internally consistent unless you are doing a full migration.

## Forms And Error Handling

### Forms

- Keep isolated one-off form state straightforward inside the local view, component, or dialog.
- When multiple route-local sections or dialogs edit the same record or share the same validation and save workflow, move that form DTO, field errors, and save action into the route-local feature store.
- Centralize DRF standardized-error parsing in shared frontend error helpers.
- Delete stale shared validation abstractions when they are no longer used.
- Follow the established validation and dialog examples for dual client and server error handling.
- For multi-step flows, keep the parent responsible for the shared DTO and active step, and let each step component own its local validation and submit or advance logic.

### Cascading Selects

- Use `resetField('fieldName')` to clear dependent fields without marking them touched or dirty.
- Do not directly assign `null` when the form library provides a reset helper.

### Dialog Ownership

- For isolated create or edit flows, dialogs can own their API calls, error handling, and success toasts.
- When a dialog participates in a larger route workflow shared with sibling sections, prefer a route-local feature store for fetch, mutation, shared form state, and success handling, and let the dialog stay focused on UI state and field rendering.
- Emit only the smallest event surface needed. If the dialog and parent already share a route-local store, prefer `close` or `cancel` events over replaying domain data through emits.
- Keep the parent route view focused on page composition, route lifecycle wiring, and navigation rather than forwarding business callbacks through several local layers.
- For admin and settings pages, prefer creation flows in focused dialogs while the page keeps the list or detail context.
- Prefer shared PrimeVue input helpers over ad hoc implementations, and await shared clipboard helpers before showing success UI.

## View Patterns

- Keep derived collections such as filtered rows and grouped data in `computed` getters.
- Use `usePolling` for auto-refresh behavior instead of manual intervals or timeouts.
- Guard optional identifiers before using them and return early when dependencies are missing.
- Use small helper functions for repeated lookups instead of inline template ternaries.
- Build view models with explicit loop-based transformers instead of long `map`/`filter`/`reduce` chains when clarity is better.
- Let route views compose shared `page/` wrappers, shared `ui/` controls, and route-local sections.
- Prefer one page-level shell store or parent view to own organization selection, bootstrap context, and shared loading/error state instead of re-fetching that context in each child page.
- For simple pages, route views can still own their fetch helpers and local computed data directly.
- For larger route folders, prefer a route-local feature store to own orchestration, data loading, mutation actions, stale-request guards, and shared workflow state, while the route view stays focused on page composition and route lifecycle wiring.
- Let route-local components consume the route-local feature store directly when doing so removes prop drilling and keeps the component API smaller.
- Keep data-fetch helpers focused on a single resource.
- Call data-fetch helpers sequentially when later requests depend on earlier metadata.
- Guard against stale async responses overwriting newer state when organization or route selection changes during a request.
- Follow the established polling and route-query examples for component polling, task polling, and URL-driven view state instead of ad hoc timers or path/query mixes.
- Fetch backend-provided defaults from the API instead of hardcoding the same values again in the client.

## Legacy Anti-Patterns And Tolerance

### Anti-Patterns To Avoid

- Do not perform heavy lookups, formatting, or ternaries inline in templates.
- Do not scatter ad hoc boolean flags across templates when they can be derived from a single source of truth.
- Do not use `.value` on nested refs or nested computeds in templates when a top-level computed would preserve clearer reactivity.
- Do not keep route-local business workflows split across a prop-heavy parent, several thin child wrappers, and multiple duplicated dialog submit handlers when one route-local feature store would make ownership clearer.

### Legacy Tolerance

- If the repository has a legacy frontend, keep the local file internally consistent while you work there instead of partially mixing old and new patterns.
- Do not reintroduce legacy frontend patterns into modern feature areas.
- For the application's modern frontend migration, treat `src/views/` as the target structure and avoid creating new route surfaces under `src/features/`.
- For the application's structure cleanup, avoid recreating top-level `src/stores/` or `src/services/` folders for modern code.

## Frontend Code Reference Workflow

- Identify an existing route or view folder similar to the one you are building.
- Inspect its route view, local subcomponents, local store usage, and API usage.
- List reusable pieces before coding.
- Reuse those pieces first, then add new code only when necessary.
- When reorganizing route code, prefer moving it into `src/views/` rather than creating or extending a parallel feature-root folder.
- When adding shared shell-level state, prefer `src/views/application/` before introducing a new global store directory.
- When adding transport helpers, prefer `src/utils/api.ts` and nearby utilities before introducing a new services root.
- Run the linter and formatter so the new code matches project style.

## Consistency Checklist

### Vue

- Component names and file casing are correct.
- Existing UI primitives are reused before new ones are created.
- Spacing and styling align with comparable features.
- API calls flow through the single canonical client.
- API boundary types avoid `any` and `unknown`.
- Components do not mix Options API and Composition API.
- Form state uses dedicated input types instead of entity models with placeholder IDs.
- Vue-specific examples live in the Vue `examples/` folder instead of inline guidance blocks.
- Session-backed auth uses the shared API client, shared shell store, route metadata, and one global router guard instead of route-local bootstrap or redirect logic.
