# Vue API And Type Contracts

## Contents

- Canonical API client and request patterns
- Standardized API errors and boundary casing
- Type discipline

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
- Keep SSO login URL builders near the canonical API client so they share the same API base URL, but use normal browser navigation for SSO redirects instead of `apiClient.get(...)`.
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

### Casing Discipline

- Frontend code uses camelCase everywhere.
- Backend API responses stay snake_case and are converted by the API client.
- Frontend request bodies and query params should be authored in camelCase and converted only at the API boundary.
- Never pass snake_case keys from components or stores to the API client.
- Never manually convert casing in components.
