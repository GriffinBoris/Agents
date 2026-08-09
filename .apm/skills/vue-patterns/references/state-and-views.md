# Vue State And View Patterns

## Contents

- Domain models and request types
- Pinia store ownership
- Route-view orchestration and polling

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
