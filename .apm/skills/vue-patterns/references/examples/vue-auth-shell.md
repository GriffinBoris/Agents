# Vue Auth-Aware Shell Example

## Scenario

- Use this pattern when Vue is backed by Django session authentication instead of bearer tokens.
- Use this pattern when local development runs Vite and Django on separate origins, but production serves the built frontend through Django on the same origin as `/api/`.
- Use this pattern when the app has protected workspace routes, guest-only auth routes, public routes that should skip operator-shell bootstrap, and permission-gated workspace routes.
- Use this pattern when login, registration, invitation acceptance, or logout can change the session or the access payload that route pages depend on.

## Why This Shape Exists

- Django owns the browser session, CSRF validation, password flows, login, logout, session rotation, and secure cookies.
- Vue owns the application shell, route metadata, user-facing redirect behavior, form state, and shell-level loading or retry states.
- Local split-origin development needs `withCredentials`, trusted frontend origins, and CSRF-aware unsafe requests. Production should avoid that complexity by using same-origin API calls from the Django-served frontend.
- The frontend needs one bootstrap call that asks the backend what the current browser session can access. That response hydrates the shell with current user, organization, workspace, and permission context before protected pages render.
- Route views should not each ask whether the user is authenticated. Repeating bootstrap or redirects in pages creates competing loading states, redirect races, stale organization or workspace selections, and inconsistent permission behavior.
- Login, registration, logout, and invitation acceptance should refresh the shared shell state from the backend instead of manually patching frontend auth fields. The backend bootstrap response is the source of truth.

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
  build: {
    assetsDir: "api",
  },
});
```

Production uses an empty `__API_URL__` so browser requests resolve against the same origin that served the app. Local development can point to a separate Django backend such as `http://localhost:8000`. Do not hardcode local API origins in route views, stores, or auth helpers.

### API Client Session Contract

```typescript
// frontend/src/utils/api.ts

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
}

export const apiClient = new ApiClient(__API_URL__);
```

The shared API client is the only place that configures Axios credentials and XSRF behavior. `withCredentials` lets the local Vite origin send Django session cookies to the local backend origin. `xsrfCookieName` and `xsrfHeaderName` must match the backend CSRF setup. Response interceptors convert normal payloads and DRF standardized-error payloads to camelCase before route code sees them.

### Django-Rendered CSRF Seed

```html
<!-- frontend/index.html, rendered by Django in production -->

<body>
  <!-- {% csrf_token %} -->
  <div id="app"></div>
  <script type="module" src="/src/main.ts"></script>
</body>
```

```typescript
// frontend/src/main.ts

import { apiClient } from "./utils/api";

const csrfTokenInput = document.querySelector<HTMLInputElement>('input[name="csrfmiddlewaretoken"]');
if (csrfTokenInput?.value) {
  apiClient.setCsrfToken(csrfTokenInput.value);
}
```

When Django renders the production SPA template, the build step can uncomment `{% csrf_token %}` before Vue mounts. Read that hidden input once at startup and seed the shared API client. This keeps production compatible with `CSRF_USE_SESSIONS = True`, where the CSRF secret lives in the server-side session instead of a JavaScript-readable cookie.

### Auth API Segment

```typescript
// frontend/src/utils/api.ts

const auth = {
  acceptInvitation: (token: string) =>
    apiClient.post<OrganizationInvitationInterface, undefined>(`api/invitations/${token}/accept/`),
  bootstrap: () => apiClient.get<AppBootstrapResponseInterface>("api/user/bootstrap/"),
  changePassword: (payload: ChangePasswordInterface) =>
    apiClient.post<EmptyResponseInterface, ChangePasswordInterface>("api/user/change-password/", payload),
  invitationDetail: (token: string) =>
    apiClient.get<InvitationDetailInterface>(`api/invitations/${token}/`),
  invitationRegister: (token: string, payload: InvitationRegisterRequestInterface) =>
    apiClient.post<AuthUserInterface, InvitationRegisterRequestInterface>(
      `api/invitations/${token}/register/`,
      payload
    ),
  login: (payload: LoginRequestInterface) =>
    apiClient.post<EmptyResponseInterface, LoginRequestInterface>("api/user/login/", payload),
  logout: () => apiClient.post<EmptyResponseInterface, undefined>("api/user/logout/"),
  onboardingCreateOrganization: (payload: OrganizationInputInterface) =>
    apiClient.post<OrganizationInterface, OrganizationInputInterface>("api/user/onboarding/create-organization/", payload),
  passwordResetConfirm: (payload: ResetPasswordConfirmInterface) =>
    apiClient.post<EmptyResponseInterface, ResetPasswordConfirmInterface>(
      "api/user/password-reset/confirm/",
      payload
    ),
  passwordResetRequest: (payload: ForgotPasswordRequestInterface) =>
    apiClient.post<EmptyResponseInterface, ForgotPasswordRequestInterface>(
      "api/user/password-reset/request/",
      payload
    ),
  register: (payload: RegisterInputInterface) =>
    apiClient.post<AuthUserInterface, RegisterInputInterface>("api/user/register/", payload),
};

export const api = {
  auth,
  // other domain segments...
};
```

Auth calls are normal domain methods in the canonical API module. Login, logout, registration, invitation, password reset, and bootstrap all use the same credentialed client, casing conversion, CSRF setup, and standardized error conversion as the rest of the app. Do not create `authService`, `authClient`, direct `axios`, direct `fetch`, or local-storage token helpers for browser auth.

### Shell Store Owns Bootstrap State

```typescript
// frontend/src/views/application/appShellStore.ts

export const useAppShellStore = defineStore("appShell", () => {
  const access = ref<AppAccessInterface>({
    workspacePermissions: {},
    permissions: [],
    organizationPermissions: {},
  });
  const hasInitialized = ref(false);
  const isLoading = ref(false);
  const errorMessage = ref("");
  const isAuthenticated = ref(false);
  const currentUser = ref<AuthUserInterface | null>(null);
  const organizations = ref<OrganizationInterface[]>([]);
  const selectedOrganizationId = ref<number | null>(null);
  const workspaces = ref<WorkspaceInterface[]>([]);
  const selectedWorkspaceId = ref<number | null>(null);
  const isWorkspacesLoading = ref(false);
  const workspacesErrorMessage = ref("");
  let initializationPromise: Promise<void> | null = null;

  const selectedOrganization = computed(() => {
    return organizations.value.find((organization) => organization.id === selectedOrganizationId.value) ?? null;
  });
  const selectedWorkspace = computed(() => {
    return workspaces.value.find((workspace) => workspace.id === selectedWorkspaceId.value) ?? null;
  });
  const hasOrganizations = computed(() => organizations.value.length > 0);
  const needsOrganizationOnboarding = computed(() => isAuthenticated.value && hasInitialized.value && !hasOrganizations.value);

  function getSelectedWorkspaceRouteParams() {
    if (!selectedOrganizationId.value || !selectedWorkspaceId.value) {
      return null;
    }

    return {
      organizationId: selectedOrganizationId.value,
      workspaceId: selectedWorkspaceId.value,
    };
  }

  function can(permission: AppPermission, scope?: AccessScope) {
    if (scope && "workspaceId" in scope) {
      if (!scope.workspaceId) {
        return false;
      }

      const workspace = getWorkspaceById(scope.workspaceId);
      if (!workspace) {
        return false;
      }

      return getWorkspacePermissions(workspace.id).includes(permission) || getOrganizationPermissions(workspace.organization).includes(permission);
    }

    if (scope && "organizationId" in scope) {
      if (!scope.organizationId) {
        return false;
      }

      return getOrganizationPermissions(scope.organizationId).includes(permission);
    }

    return access.value.permissions.includes(permission);
  }

  function resetState() {
    hasInitialized.value = false;
    isLoading.value = false;
    errorMessage.value = "";
    isAuthenticated.value = false;
    currentUser.value = null;
    access.value = {
      workspacePermissions: {},
      permissions: [],
      organizationPermissions: {},
    };
    organizations.value = [];
    selectedOrganizationId.value = null;
    workspaces.value = [];
    selectedWorkspaceId.value = null;
    isWorkspacesLoading.value = false;
    workspacesErrorMessage.value = "";
  }

  async function loadBootstrapState() {
    const bootstrap = await api.auth.bootstrap();

    access.value = bootstrap.access;
    isAuthenticated.value = bootstrap.isAuthenticated;
    currentUser.value = bootstrap.user;
    organizations.value = bootstrap.organizations;
    selectedOrganizationId.value = bootstrap.currentOrganizationId;
    workspaces.value = bootstrap.workspaces;
    selectedWorkspaceId.value = bootstrap.currentWorkspaceId;
    workspacesErrorMessage.value = "";
    hasInitialized.value = true;

    await selectFirstAvailableWorkspace();

    return bootstrap;
  }

  async function initialize() {
    if (hasInitialized.value) {
      return;
    }

    if (!initializationPromise) {
      initializationPromise = (async () => {
        isLoading.value = true;
        errorMessage.value = "";

        try {
          await loadBootstrapState();
        } catch (error) {
          errorMessage.value = "Unable to load the workspace shell.";
          throw error;
        } finally {
          isLoading.value = false;
        }
      })();
    }

    try {
      await initializationPromise;
    } finally {
      initializationPromise = null;
    }
  }

  async function reload() {
    if (isLoading.value) {
      return;
    }

    isLoading.value = true;
    errorMessage.value = "";

    try {
      await loadBootstrapState();
    } catch (error) {
      errorMessage.value = "Unable to load the workspace shell.";
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  return {
    can,
    workspaces,
    currentUser,
    errorMessage,
    getSelectedWorkspaceRouteParams,
    hasInitialized,
    initialize,
    isAuthenticated,
    isLoading,
    needsOrganizationOnboarding,
    reload,
    resetState,
    selectedWorkspace,
    selectedWorkspaceId,
    selectedOrganization,
    selectedOrganizationId,
    organizations,
  };
});
```

The shell store owns the authenticated session view of the world. It should load current user, organization choices, workspace choices, selected scope, and permissions through one backend bootstrap response. Route-local stores can read shell context and call `can(...)` for feature actions, but they should not call `api.auth.bootstrap()` or duplicate shell fields.

Use `initialize()` for first route-guard bootstrap, `resetState()` plus `initialize()` after login or registration creates a new session, `reload()` after session-preserving access changes such as invitation acceptance, and `resetState()` immediately after logout.

### Route Admission Uses The Shared Guard

Define typed route metadata for access and shell selection, including `requiresAuth`, `guestOnly`, `requiredPermissions`, `skipShellBootstrap`, `skipAppShell`, and `fullscreenShell`. Enforce route admission in one global router guard backed by the shell store.

Invitation acceptance should remain accessible to anonymous invited users and signed-in users. Do not mark it guest-only or skip shell bootstrap when accepting it can change the current session's access.

Use [Vue Route Auth Guard Example](vue-route-auth-guard.md) for route records, permission redirects, the global guard, and route-admission tests. Keep this example focused on the session, CSRF, bootstrap, shell, and session-changing flows.

### App Shell Boundary

```vue
<!-- frontend/src/App.vue -->

<template>
  <FullscreenPageShell v-if="showFullscreenShell">
    <RouterView :key="routerViewKey" />
  </FullscreenPageShell>

  <ApplicationShellView v-else-if="showApplicationShell">
    <RouterView :key="routerViewKey" />
  </ApplicationShellView>

  <GuestPageShell v-else>
    <RouterView />
  </GuestPageShell>

  <ApplicationToastViewport />
</template>

<script setup lang="ts">
  const appShellStore = useAppShellStore();
  const route = useRoute();

  const showFullscreenShell = computed(() => Boolean(route.meta.fullscreenShell));
  const showApplicationShell = computed(() => {
    return appShellStore.isAuthenticated && !route.meta.skipAppShell && !route.meta.fullscreenShell;
  });

  const routerViewKey = computed(() => {
    if (route.params.workspaceId) {
      return `workspace-${String(route.params.workspaceId)}-${String(route.name ?? route.fullPath)}`;
    }

    return String(route.name ?? route.fullPath);
  });
</script>
```

`App.vue` chooses between the authenticated application shell, guest shell, and full-screen shell from shared shell state and route metadata. It also mounts global feedback UI once. Route pages should not recreate this outer layout logic or mount their own copy of the workspace shell.

### Login And Registration Rebootstrap

```vue
<!-- frontend/src/views/login/LoginView.vue -->

<script setup lang="ts">
  const route = useRoute();
  const router = useRouter();
  const appShellStore = useAppShellStore();

  const errorMessage = ref("");
  const isSubmitting = ref(false);
  const { errors: fieldErrors, setErrors, validate, values: formValues } = useSchemaValidation(
    loginRequestSchema,
    createDefaultLoginRequest()
  );

  async function submitLogin() {
    errorMessage.value = "";

    if (!(await validate())) {
      return;
    }

    isSubmitting.value = true;

    try {
      await api.auth.login(formValues);
      appShellStore.resetState();
      await appShellStore.initialize();

      const redirect = typeof route.query.redirect === "string" ? route.query.redirect : null;
      if (redirect && redirect.startsWith("/")) {
        await router.replace(redirect);
        return;
      }

      await router.replace({ name: "workspaces-list" });
    } catch (error) {
      const apiFieldErrors = extractFirstFieldErrors(error);
      setErrors(apiFieldErrors);
      errorMessage.value = getFirstApiErrorMessage(error, "Unable to sign in.");
    } finally {
      isSubmitting.value = false;
    }
  }
</script>
```

After login or standalone registration, reset stale shell state and re-bootstrap from the backend. Do not manually set `isAuthenticated`, `currentUser`, organizations, workspaces, or permission arrays from the auth response. The bootstrap response is the shell contract.

### Invitation Access Refresh

```typescript
// frontend/src/views/acceptInvitation/AcceptInvitationView.vue

async function acceptInvitation() {
  if (!invitation.value) {
    return;
  }

  isAccepting.value = true;
  acceptErrorMessage.value = "";

  try {
    await api.auth.acceptInvitation(token.value);
    await appShellStore.reload();
    acceptSuccessMessage.value = `Access has been granted for ${invitation.value.organizationName}.`;
    invitation.value = await api.auth.invitationDetail(token.value);
  } catch (error) {
    acceptErrorMessage.value = getFirstApiErrorMessage(error, "Unable to accept this invitation.");
  } finally {
    isAccepting.value = false;
  }
}

async function handleOpenWorkspace() {
  if (shouldRefreshShellOnWorkspaceOpen.value) {
    await appShellStore.reload();
    shouldRefreshShellOnWorkspaceOpen.value = false;
  }

  await router.push({ name: "workspaces-list" });
}
```

Invitation acceptance changes the access available to the current browser session. A signed-in user can reload the shell immediately after accepting. A newly registered invited user may defer the reload until opening the workspace, but the route must still refresh the shell before sending the user to pages that rely on the new organization or workspace permissions.

### Logout Clears Shell State

```typescript
// frontend/src/views/application/ApplicationShellView.vue

async function handleSidebarFooterAction(action: "logout" | "settings" | "theme" | "workspace") {
  if (action !== "logout") {
    return;
  }

  await api.auth.logout();
  appShellStore.resetState();
  await router.replace({ name: "login", query: { redirect: route.fullPath } });
}
```

After logout, clear shell state and send the user to a guest route. Do not leave organization, workspace, permission, or current-user state in memory after the backend session has been cleared.

## Things To Notice

- The frontend does not store auth tokens. Django session cookies are sent by the browser, and CSRF is handled by the shared API client.
- Local split-origin development and production same-origin serving use the same frontend API client contract. Only `__API_URL__` changes by environment.
- The production CSRF seed happens once in `main.ts`. Route views, stores, and auth components do not scrape CSRF tokens.
- The shell store owns bootstrap state and exposes it to the router, shell, and route views.
- Guest-only routes still use the shared API client so login, registration, and password flows get credentials and CSRF handling.
- Login and registration reset shell state before initializing because they create a new authenticated session.
- Invitation acceptance reloads shell state because it can add organization or workspace access to an existing session.
- Logout resets shell state immediately because the browser session is no longer authenticated.
- Route views consume shell state when they need it, but they do not call `api.auth.bootstrap()` or `appShellStore.initialize()` themselves.
- The shared route guard consumes this store contract. Its metadata, redirects, and admission tests live in [Vue Route Auth Guard Example](vue-route-auth-guard.md).

## Rules To Follow

- Keep browser auth session-backed; do not add local-storage tokens, bearer-token helpers, or a parallel auth client.
- Keep Axios credential and XSRF configuration inside the canonical API client.
- Keep auth API methods in the shared `api.auth` segment in `frontend/src/utils/api.ts`.
- Keep production API calls same-origin by leaving production `__API_URL__` empty.
- Keep the production CSRF handoff in Django-rendered HTML plus `apiClient.setCsrfToken(...)` in `main.ts`.
- Keep session bootstrap in the repository's shared shell store.
- Do not bootstrap auth state inside route views, dialogs, public views, or route-local stores.
- Reset and re-bootstrap shell state after login, registration, invitation registration, or any flow that creates a new authenticated session before entering the workspace.
- Reload shell state after session-preserving access changes, such as accepting an invitation while signed in.
- Reset shell state immediately after logout.
- Test the shell lifecycle across anonymous bootstrap, login, registration, access refresh, and logout.

## Refactor Signals

- A route view, dialog, or route-local store imports `api.auth.bootstrap()` or calls a custom session-status endpoint.
- A normal route view calls `appShellStore.initialize()` as a workaround for missing route metadata or guard behavior.
- More than one file creates an Axios instance, sets XSRF names, sets `axios.defaults`, or handles CSRF token scraping.
- Login, registration, invitation, password, or logout code lives in `authService.ts`, `apiService.ts`, `useApiClient.ts`, or a local-storage token module.
- A frontend file reads or writes `access_token`, `refresh_token`, or auth state in local storage.
- Login, logout, registration, or invitation flows manually assign `isAuthenticated`, `currentUser`, organization arrays, workspace arrays, or permission arrays.
- Production config points the frontend bundle at a hard-coded local or cross-origin API URL.
- Tests cover only happy-path page rendering and do not assert session bootstrap, refresh, or reset behavior after auth changes.

## Verification

- Run the frontend typecheck after changing auth API methods, route metadata, the router guard, shell store, or auth views:

```bash
cd frontend
npm run type-check
```

- Run the frontend lint command after editing TypeScript or Vue files:

```bash
cd frontend
npm run lint
```

- Run focused shell-store and auth-flow tests when bootstrap or session-changing behavior changes. Cover anonymous bootstrap, login or registration, access refresh, and logout using the repository's existing test commands.

- Use `rg` checks to keep the auth shape centralized:

```bash
rg "api\\.auth\\.bootstrap" frontend/src
rg "appShellStore\\.initialize\\(" frontend/src
rg "from [\"']axios|axios\\.|fetch\\(" frontend/src frontend/tests frontend/e2e
rg "localStorage.*token|access_token|refresh_token|authService|authClient|useApiClient|apiService" frontend/src
```

- Expected structural results:
  - `api.auth.bootstrap` appears only in the repository's shared shell store.
  - `appShellStore.initialize()` in route views is limited to session-changing auth flows that reset shell state first.
  - Direct Axios runtime usage is limited to the canonical API client, with test harness exceptions only for setup code.
  - Token-storage and parallel auth-client searches return no modern app implementation.

## Why It Helps

- The app has one source of truth for current user, organization, workspace, and permission state.
- Split-origin local development works without weakening the production session and CSRF model.
- Production deployment stays simple because Django serves the SPA and API from one origin.
- Login, logout, registration, and invitation flows cannot leave stale organization or permission data behind.
- The route guard receives a small, stable store contract instead of owning a second copy of session state.
- Reviewers can audit session security, CSRF handling, and shell ownership with targeted searches instead of reading every page component.
