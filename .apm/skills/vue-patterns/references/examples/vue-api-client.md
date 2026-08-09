---
id: framework-vue-example-api-client
title: Vue API Client Example
description: Example API module shape using the repository's single-client pattern.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - api
applies_to:
  - vue
status: active
order: 1
---

# Vue API Client Example

## Scenario

- Use this shape when adding or refactoring a frontend API endpoint family.
- Use this shape when a route view, route-local store, dialog, or component needs backend data.
- Use this shape when wiring Django session-backed auth, CSRF-protected mutations, query params, or typed response contracts.
- Use this shape when removing older direct `axios`, direct `fetch`, separate auth-client, or local-storage token patterns from modern frontend code.

The standard home for the application's frontend API boundary is `frontend/src/utils/api.ts`. Supporting request-param casing belongs in `frontend/src/utils/apiParams.ts`, and generic casing conversion belongs in `frontend/src/utils/caseConversion.ts`.

## Why This Shape Exists

- Django owns sessions, CSRF validation, secure cookies, and snake_case API payloads.
- Vue owns camelCase application state, typed DTOs, route-local stores, and user-facing workflows.
- A single canonical client keeps the browser transport contract auditable: credentials, XSRF headers, timeout behavior, request casing, response casing, and response unwrapping live in one place.
- Local development runs Vite and Django on split origins, so authenticated requests need credentialed cross-origin Axios configuration. Production serves the built frontend through Django, so API calls should be same-origin with an empty `__API_URL__`.
- Domain API segments make stores and components read in domain terms such as `api.catalogEntries.listByOrganization(...)` instead of transport terms such as `axios.get(...)`.
- Keeping auth inside the same API object prevents drift between login, logout, bootstrap, password reset, invitation, and normal domain requests. Those flows all use the same Django session and CSRF boundary.

## Recommended Shape

### Vite Chooses The API Origin

```typescript
// frontend/vite.config.ts

const apiPort = process.env.PLAYWRIGHT_BACKEND_PORT ?? process.env.VITE_API_PORT ?? "8000";
const developmentApiUrl = process.env.VITE_API_URL ?? `http://localhost:${apiPort}`;

export default defineConfig({
  define: {
    __API_URL__: process.env.NODE_ENV === "production" ? JSON.stringify("") : JSON.stringify(developmentApiUrl),
    __IS_DEVELOPMENT__: process.env.NODE_ENV === "development",
  },
});
```

Production uses `""` so requests go to the same origin that served the app. Local development can call a separate Django origin such as `http://localhost:8000`.

### Canonical Client Owns Axios

```typescript
// frontend/src/utils/api.ts

import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
} from "axios";

import { camelToSnake, snakeToCamel } from "@/utils/caseConversion";

declare const __API_URL__: string;

export class ApiClient {
  private axios: AxiosInstance;

  constructor(baseURL: string) {
    this.axios = axios.create({
      baseURL,
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      xsrfHeaderName: "X-CSRFTOKEN",
      xsrfCookieName: "csrftoken",
      withCredentials: true,
      withXSRFToken: true,
      timeout: 60_000,
    });

    this.axios.interceptors.response.use(
      (response: AxiosResponse) => {
        response.data = snakeToCamel(response.data);
        return response;
      },
      (error: AxiosError) => {
        const data = error.response?.data;
        if (error.response && data) {
          error.response.data = snakeToCamel(data);
        }

        return Promise.reject(error);
      }
    );
  }

  setCsrfToken(token: string) {
    this.axios.defaults.headers.common["X-CSRFTOKEN"] = token;
  }

  async get<TResponse>(url: string, config?: AxiosRequestConfig): Promise<TResponse> {
    const { data } = await this.axios.get<TResponse>(url, config);
    return data;
  }

  async post<TResponse, TBody>(url: string, body?: TBody, config?: AxiosRequestConfig): Promise<TResponse> {
    const { data } = await this.axios.post<TResponse>(url, camelToSnake(body), config);
    return data;
  }

  async put<TResponse, TBody>(url: string, body?: TBody, config?: AxiosRequestConfig): Promise<TResponse> {
    const { data } = await this.axios.put<TResponse>(url, camelToSnake(body), config);
    return data;
  }
}

export const apiClient = new ApiClient(__API_URL__);
```

`ApiClient` is the only production application layer that imports the Axios runtime and creates an Axios instance. It unwraps `data`, converts outgoing JSON bodies from camelCase to snake_case, converts successful and standardized error responses back to camelCase, and applies Django session credentials and XSRF configuration.

### Django-Rendered CSRF Seed

```typescript
// frontend/src/main.ts

import { apiClient } from "./utils/api";

const csrfTokenInput = document.querySelector<HTMLInputElement>('input[name="csrfmiddlewaretoken"]');
if (csrfTokenInput?.value) {
  apiClient.setCsrfToken(csrfTokenInput.value);
}
```

When production uses Django-rendered HTML and `CSRF_USE_SESSIONS = True`, the template can include `{% csrf_token %}` before Vue mounts. Read that token once and seed the canonical client. Do not make route views, stores, or auth helpers scrape CSRF tokens themselves.

### Query Params Stay CamelCase At Call Sites

```typescript
// frontend/src/utils/apiParams.ts

import type { AxiosRequestConfig } from "axios";

import { camelToSnake } from "./caseConversion.ts";

export function buildParamsConfig<T>(params?: T): AxiosRequestConfig | undefined {
  if (!params) {
    return undefined;
  }

  return {
    params: camelToSnake(params),
  };
}
```

```typescript
const catalogEntries = {
  listByOrganization: (organizationId: number, filters?: CatalogEntryOrganizationListFiltersInterface) =>
    apiClient.get<CatalogEntryInterface[]>(
      `api/organizations/${organizationId}/catalog-entries/list/`,
      buildParamsConfig(filters)
    ),
};

await api.catalogEntries.listByOrganization(organizationId, {
  workspaceId: activeWorkspaceFilter === "all" ? undefined : activeWorkspaceFilter,
  search: activeSearch,
  status: activeStatus,
});
```

Frontend callers pass `workspaceId`, `search`, and `status`. `buildParamsConfig(...)` converts `workspaceId` to `workspace_id` at the transport boundary. Components and stores should never manually build snake_case query objects.

### Domain Segments Live In `api.ts`

```typescript
import type { ContactRequestInterface } from "@/types/contact/ContactRequestInterface";
import type { ContactInterface } from "@/types/contact/ContactInterface";
import type { CatalogEntryRequestInterface } from "@/types/catalogEntry/CatalogEntryRequestInterface";
import type { CatalogEntryInterface } from "@/types/catalogEntry/CatalogEntryInterface";
import type { CatalogEntryOrganizationListFiltersInterface } from "@/types/catalogEntry/CatalogEntryOrganizationListFiltersInterface";
import { buildParamsConfig } from "@/utils/apiParams";

const auth = {
  bootstrap: () => apiClient.get<AppBootstrapResponseInterface>("api/user/bootstrap/"),
  login: (payload: LoginRequestInterface) =>
    apiClient.post<EmptyResponseInterface, LoginRequestInterface>("api/user/login/", payload),
  logout: () => apiClient.post<EmptyResponseInterface, undefined>("api/user/logout/"),
  passwordResetRequest: (payload: ForgotPasswordRequestInterface) =>
    apiClient.post<EmptyResponseInterface, ForgotPasswordRequestInterface>(
      "api/user/password-reset/request/",
      payload
    ),
};

const catalogEntries = {
  create: (organizationId: number, workspaceId: number, payload: CatalogEntryRequestInterface) =>
    apiClient.post<CatalogEntryInterface, CatalogEntryRequestInterface>(
      `api/organizations/${organizationId}/workspaces/${workspaceId}/catalog-entries/create/`,
      payload
    ),
  detail: (organizationId: number, workspaceId: number, catalogEntryId: number) =>
    apiClient.get<CatalogEntryInterface>(
      `api/organizations/${organizationId}/workspaces/${workspaceId}/catalog-entries/${catalogEntryId}/`
    ),
  listByOrganization: (organizationId: number, filters?: CatalogEntryOrganizationListFiltersInterface) =>
    apiClient.get<CatalogEntryInterface[]>(
      `api/organizations/${organizationId}/catalog-entries/list/`,
      buildParamsConfig(filters)
    ),
  update: (organizationId: number, workspaceId: number, catalogEntryId: number, payload: Partial<CatalogEntryRequestInterface>) =>
    apiClient.put<CatalogEntryInterface, Partial<CatalogEntryRequestInterface>>(
      `api/organizations/${organizationId}/workspaces/${workspaceId}/catalog-entries/${catalogEntryId}/`,
      payload
    ),
};

const contacts = {
  create: (organizationId: number, workspaceId: number, payload: ContactRequestInterface) =>
    apiClient.post<ContactInterface, ContactRequestInterface>(
      `api/organizations/${organizationId}/workspaces/${workspaceId}/contacts/create/`,
      payload
    ),
  detail: (organizationId: number, workspaceId: number, contactId: number) =>
    apiClient.get<ContactInterface>(
      `api/organizations/${organizationId}/workspaces/${workspaceId}/contacts/${contactId}/`
    ),
  listByWorkspace: (organizationId: number, workspaceId: number) =>
    apiClient.get<ContactInterface[]>(
      `api/organizations/${organizationId}/workspaces/${workspaceId}/contacts/list/`
    ),
  update: (organizationId: number, workspaceId: number, contactId: number, payload: Partial<ContactRequestInterface>) =>
    apiClient.put<ContactInterface, Partial<ContactRequestInterface>>(
      `api/organizations/${organizationId}/workspaces/${workspaceId}/contacts/${contactId}/`,
      payload
    ),
};

export const api = {
  auth,
  contacts,
  catalogEntries,
};
```

Each segment is a top-level `const` in `api.ts` and is exported through the unified `api` object. Methods return unwrapped typed payloads such as `Promise<CatalogEntryInterface>` by way of `apiClient.get<CatalogEntryInterface>(...)`, not `AxiosResponse<CatalogEntryInterface>`.

### Route Code Consumes Domain Methods

```typescript
// frontend/src/views/contactDetail/contactDetailStore.ts

async function load() {
  const activeOrganizationId = organizationId.value;
  const activeWorkspaceId = workspaceId.value;
  const activeContactId = contactId.value;

  if (!activeOrganizationId || !activeWorkspaceId || !activeContactId) {
    contact.value = null;
    reset();
    return;
  }

  const nextContact = await api.contacts.detail(activeOrganizationId, activeWorkspaceId, activeContactId);
  applyContact(nextContact);
}
```

Stores and components should depend on `api`, not on Axios, `apiClient`, transport headers, CSRF cookies, local-storage auth tokens, or response casing.

### Uploads Are A Narrow Exception

```typescript
// frontend/src/utils/api.ts

async postForm<TResponse>(url: string, body: FormData, config?: AxiosRequestConfig): Promise<TResponse> {
  const { data } = await this.axios.post<TResponse>(url, body, {
    ...config,
    headers: {
      ...(config?.headers ?? {}),
      "Content-Type": undefined,
    },
  });
  return data;
}
```

Use `FormData` and form-specific helpers only for endpoints that truly upload files or need multipart bodies. Normal JSON create and update endpoints should use `post` and `put` so request casing and response unwrapping stay consistent.

### Avoid Parallel Clients

```typescript
// Do not add this shape.

const authClient = axios.create({ baseURL: "/api" });

export function getToken() {
  return window.localStorage.getItem("access_token");
}

export async function login(payload: LoginRequestInterface) {
  return authClient.post("/user/login/", payload, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
}
```

This application is session-backed. Auth flows belong in `api.auth`, and the browser session belongs to Django cookies. A local-storage token helper or separate auth client is the wrong contract for this architecture.

## Things To Notice

- `frontend/src/utils/api.ts` is the canonical API boundary. It owns Axios runtime imports, `axios.create(...)`, credentials, XSRF names, timeout, request casing, response casing, upload helpers, and the unified `api` object.
- `frontend/src/utils/apiParams.ts` may import Axios types because it returns an `AxiosRequestConfig`, but it should stay a tiny params helper and should not issue requests.
- Production sets `__API_URL__` to `""`; local development can set it to a split Django origin.
- `withCredentials`, `withXSRFToken`, `xsrfCookieName`, and `xsrfHeaderName` are part of the Django session contract and stay centralized in the client constructor.
- The production CSRF token seed happens once in `main.ts` through `apiClient.setCsrfToken(...)`; route code does not repeat this work.
- Backend responses and DRF standardized errors stay snake_case until the response interceptor converts them to camelCase.
- Frontend request bodies and query params stay camelCase until `camelToSnake(...)` or `buildParamsConfig(...)` runs at the API boundary.
- Domain segments are grouped by item concept and exported once through `api`.
- Auth is just another API segment. Do not create a separate `authService`, `authClient`, `useApiClient`, or token-storage module.
- Stores and components receive already-unwrapped typed payloads. They should not branch on `response.data` or import `AxiosResponse`.
- Endpoint parameters should be ordered from broad scope to specific record to payload, such as `organizationId`, `workspaceId`, `catalogEntryId`, then `payload`.
- Upload helpers exist for real multipart endpoints only. Do not use `FormData` as a generic way to avoid DTO typing.

## Rules To Follow

- Keep exactly one canonical frontend API client in `frontend/src/utils/api.ts`.
- Outside tests and narrow helper types, do not import `axios` anywhere except the canonical API client layer.
- Do not call `fetch(...)`, `axios(...)`, `axios.get(...)`, or `apiClient` directly from route views, Pinia stores, dialogs, or shared components. Use `api.<domain>.<method>(...)`.
- Do not configure Axios defaults in `main.ts`, stores, route views, or component setup blocks.
- Do not create a separate auth client, token helper, bearer-token local-storage helper, or duplicate API service for login, logout, registration, password reset, invitation acceptance, or bootstrap.
- Keep Django session settings in the canonical client: `withCredentials`, `withXSRFToken`, `xsrfCookieName`, and `xsrfHeaderName`.
- Keep production API calls same-origin by leaving production `__API_URL__` empty. Use environment-driven split-origin URLs only for local development and test harnesses.
- Type every API method response and payload. Return unwrapped data, not `AxiosResponse`.
- Keep API output interfaces separate from request DTOs when backend-owned fields differ from submit fields.
- Pass query params as camelCase objects and route them through `buildParamsConfig(...)`.
- Never manually send snake_case keys from a component or store.
- Keep domain API segments as top-level `const` blocks in `api.ts` and export them through one `api` object.
- Use conventional method names such as `list`, `create`, `detail`, `update`, and `delete`; use specialized verbs only when the backend action is genuinely not CRUD, such as `publish`, `clone`, `transition`, or `preview`.
- Use `FormData`, `postForm`, and `putForm` only for actual multipart upload endpoints.
- If a request needs endpoint-specific config such as a longer AI-generation timeout, pass that config at the domain API method in `api.ts`, not at the component call site.

## Refactor Signals

- A store, route view, or component imports `axios`, calls `fetch(...)`, or reaches for `apiClient` directly.
- More than one frontend file calls `axios.create(...)`, sets `axios.defaults`, or defines XSRF names.
- Auth code lives in `authService.ts`, `apiService.ts`, `useApiClient.ts`, a local-storage token helper, or any module other than the `auth` segment in `api.ts`.
- Callers read `response.data` from API methods that should already return unwrapped payloads.
- API methods return mixed shapes, such as some methods returning `ThingInterface` and others returning `AxiosResponse<ThingInterface>`.
- Components or stores pass `workspace_id`, `search_term`, or other snake_case params instead of camelCase params.
- A route manually converts response keys from snake_case to camelCase.
- New query filter interfaces are created for one-off simple filters instead of typing params inline or reusing an existing request interface.
- Generic `Record<string, unknown>` payloads appear in domain API methods where a DTO interface or Zod-inferred request type should exist.
- Multipart upload helpers are used for normal JSON create or update endpoints.
- Environment-specific base URLs are hardcoded in stores, components, or domain API methods.
- A new endpoint family is added under a top-level `src/services/` directory instead of the canonical `src/utils/api.ts`.

## Verification

- Run `cd frontend && npm run type-check` after changing API method signatures, DTO interfaces, or consumer call sites.
- Run `cd frontend && npm run lint` before finishing frontend API changes.
- Run focused frontend tests when touching the API helper contract, such as `node --test tests/api-helpers.test.ts` when the local frontend test setup supports direct Node test execution.
- Use `rg "from [\"']axios|axios\\.|fetch\\(" frontend/src frontend/tests frontend/e2e` to confirm production app code is not importing direct transport outside the canonical boundary. Test harnesses and e2e support can use lower-level calls when they are setting up test state rather than implementing app behavior.
- Use `rg "apiClient" frontend/src -g '*.ts' -g '*.vue'` to confirm direct `apiClient` usage is limited to `frontend/src/utils/api.ts` and the startup CSRF seed in `frontend/src/main.ts`.
- Use `rg "localStorage.*token|access_token|authService|useApiClient|apiService" frontend/src` when refactoring auth or session flows.
- For guidance-only edits, also run a Markdown/frontmatter/fence check for the changed example and rebuild generated agent guidance when practical.

## Implementation Contract

- The shared `apiClient` owns Axios base URL, credentials, XSRF cookie and header names, timeout, and response interceptors.
- `get(...)`, `post(...)`, `put(...)`, and `delete(...)` return `response.data`, so callers should type methods as `Promise<ModelInterface>` or `Promise<ModelInterface[]>`.
- `post(...)` and `put(...)` convert plain JSON payload objects from camelCase to snake_case before sending them.
- `postForm(...)` and `putForm(...)` send `FormData` directly and leave `Content-Type` unset so Axios and the browser can set the multipart boundary.
- `buildParamsConfig(...)` converts camelCase query-param objects to snake_case and returns an Axios config object.
- Shared error helpers should parse standardized DRF errors after the API client has normalized error payload keys.

## Actual Helper Code

### Query Params

```typescript
import type { AxiosRequestConfig } from "axios";

import { camelToSnake } from "./caseConversion.ts";

export function buildParamsConfig<T>(params?: T): AxiosRequestConfig | undefined {
  if (!params) {
    return undefined;
  }

  return {
    params: camelToSnake(params),
  };
}
```

### Casing Conversion

```typescript
function isPlainObject(value: unknown): value is Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    return false;
  }

  return Object.getPrototypeOf(value) === Object.prototype;
}

function normalizeSnakeKeyToCamel(key: string) {
  return key.replace(/[-_]+([a-z0-9])/gi, (_, character: string) => character.toUpperCase());
}

function normalizeCamelKeyToSnake(key: string) {
  return key.replace(/([A-Z])/g, (segment) => `_${segment.toLowerCase()}`).replace(/([a-zA-Z])([0-9]+)/g, "$1_$2");
}

export function snakeToCamel<T>(value: T): T {
  if (Array.isArray(value)) {
    return value.map((item) => snakeToCamel(item)) as T;
  }

  if (!isPlainObject(value)) {
    return value;
  }

  const nextValue: Record<string, unknown> = {};

  Object.entries(value).forEach(([key, entryValue]) => {
    nextValue[normalizeSnakeKeyToCamel(key)] = snakeToCamel(entryValue);
  });

  return nextValue as T;
}

export function camelToSnake<T>(value: T): T {
  if (Array.isArray(value)) {
    return value.map((item) => camelToSnake(item)) as T;
  }

  if (!isPlainObject(value)) {
    return value;
  }

  const nextValue: Record<string, unknown> = {};

  Object.entries(value).forEach(([key, entryValue]) => {
    nextValue[normalizeCamelKeyToSnake(key)] = camelToSnake(entryValue);
  });

  return nextValue as T;
}

export function snakeFieldAttrToCamel(attr: string) {
  return normalizeSnakeKeyToCamel(attr);
}
```

## Helper Reference

| Helper | Location | Use |
|---|---|---|
| `apiClient.get(...)` | `src/utils/api.ts` | Read JSON resources and return unwrapped response data. |
| `apiClient.post(...)` | `src/utils/api.ts` | Send JSON create or action payloads after automatic camelCase-to-snake_case conversion. |
| `apiClient.put(...)` | `src/utils/api.ts` | Send JSON update payloads after automatic camelCase-to-snake_case conversion. |
| `apiClient.delete(...)` | `src/utils/api.ts` | Delete resources and return the typed empty or response payload. |
| `apiClient.postForm(...)` | `src/utils/api.ts` | Upload `FormData` without recursively converting the payload or forcing JSON headers. |
| `apiClient.putForm(...)` | `src/utils/api.ts` | Update with `FormData` without recursively converting the payload or forcing JSON headers. |
| `apiClient.setCsrfToken(...)` | `src/utils/api.ts` | Set a rendered CSRF token during shell/bootstrap setup. |
| `buildParamsConfig(...)` | `src/utils/apiParams.ts` | Convert camelCase query params to snake_case and return an Axios config object. |
| `extractFirstFieldErrors(...)` | `src/utils/errorHandling.ts` | Convert standardized API field errors into a one-message-per-field camelCase map for forms. |
| `extractFieldErrors(...)` | `src/utils/errorHandling.ts` | Convert standardized API field errors into a multi-message camelCase map. |
| `getFirstApiErrorMessage(...)` | `src/utils/errorHandling.ts` | Read the first standardized API error message with a caller-owned fallback. |
| `getFirstApiErrorCode(...)` | `src/utils/errorHandling.ts` | Read the first standardized API error code for code-specific handling. |
| `getApiErrorStatus(...)` | `src/utils/errorHandling.ts` | Read the response status for status-specific handling. |
| `parseApiError(...)` | `src/utils/errorHandling.ts` | Read the full standardized error object in shared helpers or specialized flows. |
| `camelToSnake(...)` | `src/utils/caseConversion.ts` | API-boundary conversion used by the client and query-param helper. |
| `snakeToCamel(...)` | `src/utils/caseConversion.ts` | API-boundary conversion used by the client response interceptor. |
| `snakeFieldAttrToCamel(...)` | `src/utils/caseConversion.ts` | Normalize standardized-error `attr` values for frontend field names. |

For feature work, prefer `apiClient`, `buildParamsConfig(...)`, `extractFirstFieldErrors(...)`, and `getFirstApiErrorMessage(...)`. Direct casing-helper calls should stay inside API-boundary utilities unless there is a clear integration reason.

## Why It Helps

- One client keeps Django session auth, CSRF, local split-origin development, same-origin production, casing conversion, and response unwrapping in one auditable place.
- Route code stays focused on item workflows instead of transport mechanics.
- API contracts become easier to type, refactor, and review because every endpoint family follows the same segment shape.
- Frontend camelCase state remains consistent while the backend can keep DRF and Django-native snake_case responses.
- Removing parallel clients prevents auth drift, missing credentials, broken CSRF headers, and inconsistent error parsing.
- Refactors are safer because `rg` can find all endpoint definitions in one file and all consumers through the unified `api` object.
