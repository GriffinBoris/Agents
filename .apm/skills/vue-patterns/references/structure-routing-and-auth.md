# Vue Structure, Routing, And Authentication

## Contents

- Frontend project structure
- Shell, routing, and session-backed authentication
- Legacy migration tolerance
- Frontend code-reference workflow

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
- For session-backed SSO, route provider sign-in buttons to backend SSO login URLs and let the backend complete the provider callback, create the Django session, and redirect back to the SPA.
- Preserve the intended destination as a relative redirect path in the SSO login URL, and let the backend reject unsafe redirect values.
- Let the shared shell bootstrap own post-callback session detection. Do not add frontend token parsing, local-storage auth, or route-local provider callback handlers unless the backend contract explicitly requires them.
- Render available password and SSO methods from the bootstrap payload instead of hardcoding provider buttons in the login page.
- Mount notification or snackbar containers once near the app root and drive them from a shared store or composable.
- Use shared global notifications for cross-feature success and error feedback instead of rendering one-off banners inside every page.

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
