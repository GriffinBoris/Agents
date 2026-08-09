# Vue UI, Theme, And Forms

## Contents

- Theme and tokens
- Shared UI and visual consistency
- Component paradigms
- Forms, cascading selects, and dialog ownership

## Theme And Tokens

- Prefer one theme source of truth instead of mixing multiple theming systems.
- When Tailwind is the primary styling layer, prefer semantic utility names such as `bg-surface`, `text-body`, and `border-line` over raw palette classes in application components.
- CSS variables are a good theme source of truth when runtime theme switching is needed.
- Apply the active theme at the app root instead of toggling per-page theme classes.
- Reserve accent colors for actions, focus states, and active UI states; keep primary reading text on neutral text tokens.
- Keep radius, border, and shadow choices consistent across shared shells, cards, nav items, and controls.

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

## Component Paradigms

- Do not mix Options API and Composition API in the same component.
- New code should use `<script setup lang="ts">`.
- If a legacy file uses Options API, keep that file internally consistent unless you are doing a full migration.

## Forms And Error Handling

### Forms

- Keep isolated one-off form state straightforward inside the local view, component, or dialog.
- When multiple route-local sections or dialogs edit the same record or share the same validation and save workflow, move that form DTO, field errors, and save action into the route-local feature store.
- Treat this shared edit workflow as enough to justify the store even when fewer than three components share unrelated route state.
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
