---
id: framework-vue-example-route-auth-guard
title: Vue Route Auth Guard Example
description: Example route metadata, app shell bootstrap, and one global router guard for session-backed Vue auth.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - routing
  - auth
  - shell
applies_to:
  - vue
status: active
order: 6
---

# Vue Route Auth Guard Example

## Scenario

- Use this pattern when a Vue route map has protected workspace routes, guest-only auth routes, permission-gated routes, and public routes that must not initialize the operator shell.
- Use this pattern when route pages need current user, organization, workspace, and permission context from the shared application shell store.
- Use this pattern when login, registration, invitation acceptance, or logout can change the browser session and the route guard must see the new shell state before sending the user onward.

## Why This Shape Exists

- Browser authentication is Django session-backed, so Vue should ask the backend for the current session once through the shell bootstrap endpoint instead of keeping tokens or guessing auth state locally.
- Route access is a shell concern. If every route view bootstraps auth, checks permissions, or redirects on its own, the app gets competing loading states, redirect loops, stale organization state, and different behavior for the same session.
- The route map is the cleanest review boundary for access intent. A reviewer should see `requiresAuth`, `guestOnly`, `skipShellBootstrap`, and `requiredPermissions` on the route record instead of searching page components for auth code.
- The global guard is the cleanest enforcement boundary. It can initialize the shell exactly once before protected routes render, preserve the intended destination for anonymous users, redirect signed-in users away from guest-only routes, and delegate permission redirects to one route-access helper.
- Public flows such as survey need an explicit escape hatch. `skipShellBootstrap` prevents those routes from loading operator organization, workspace, and permission context they do not need.

## Recommended Shape

### Route Meta Contract

```typescript
// frontend/src/router/routeMeta.d.ts

import type { AppPermission } from "@/views/application/permissions";

declare module "vue-router" {
  interface RouteMeta {
    breadcrumbLabel?: string;
    fullscreenShell?: boolean;
    globalNavKey?: string;
    guestOnly?: boolean;
    requiredPermissions?: AppPermission[];
    requiresAuth?: boolean;
    skipShellBootstrap?: boolean;
    title?: string;
  }
}

export {};
```

Route metadata is the access contract. Keep the keys typed so route files cannot drift into stringly typed flags or local one-off conventions.

### Route Records Declare Intent

```typescript
// frontend/src/router/guestRoutes.ts

import type { RouteRecordRaw } from "vue-router";

export const guestRoutes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "login",
    component: () => import("@/views/login/LoginView.vue"),
    meta: { guestOnly: true, title: "Sign In" },
  },
  {
    path: "/register",
    name: "register",
    component: () => import("@/views/register/RegisterView.vue"),
    meta: { guestOnly: true, title: "Register" },
  },
  {
    path: "/survey/:token",
    name: "public-survey",
    component: () => import("@/views/publicSurvey/PublicSurveyView.vue"),
    meta: { skipShellBootstrap: true, title: "Survey" },
  },
];
```

```typescript
// frontend/src/router/organizationRoutes.ts

import { APP_PERMISSIONS } from "@/views/application/permissions";
import type { RouteRecordRaw } from "vue-router";

export const organizationRoutes: RouteRecordRaw[] = [
  {
    path: "",
    name: "dashboard",
    redirect: { name: "workspaces-list" },
    meta: {
      requiresAuth: true,
      requiredPermissions: [APP_PERMISSIONS.organizationWorkspacesView],
      title: "Dashboard",
      globalNavKey: "dashboard",
    },
  },
  {
    path: "access",
    name: "organization-access",
    component: () => import("@/views/organizationAccess/OrganizationAccessView.vue"),
    meta: {
      requiresAuth: true,
      requiredPermissions: [APP_PERMISSIONS.organizationAccessManage],
      title: "Organization Access",
      globalNavKey: "access",
    },
  },
];
```

```typescript
// frontend/src/router/workspaceRoutes.ts

import { APP_PERMISSIONS } from "@/views/application/permissions";
import type { RouteRecordRaw } from "vue-router";

export const workspaceRoutes: RouteRecordRaw = {
  path: "workspaces",
  component: () => import("@/views/workspaces/WorkspacesRouteView.vue"),
  meta: {
    requiresAuth: true,
    requiredPermissions: [APP_PERMISSIONS.organizationWorkspacesView],
    globalNavKey: "workspaces",
  },
  children: [
    {
      path: "",
      name: "workspaces-list",
      component: () => import("@/views/workspaces/WorkspacesView.vue"),
      meta: {
        requiresAuth: true,
        requiredPermissions: [APP_PERMISSIONS.organizationWorkspacesView],
        title: "Workspaces",
        globalNavKey: "workspaces",
      },
    },
    {
      path: ":workspaceId",
      name: "workspace-detail",
      component: () => import("@/views/workspaceDetail/WorkspaceDetailView.vue"),
      meta: {
        requiresAuth: true,
        requiredPermissions: [APP_PERMISSIONS.workspaceView],
        title: "Workspace Detail",
        globalNavKey: "workspaces",
      },
    },
  ],
};
```

Protected workspace routes set `requiresAuth: true`. Routes that need organization or workspace access also set `requiredPermissions`. Guest auth screens set `guestOnly: true`. Public routes that should not touch the operator shell set `skipShellBootstrap: true`.

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

  const hasOrganizations = computed(() => organizations.value.length > 0);
  const needsOrganizationOnboarding = computed(() => isAuthenticated.value && hasInitialized.value && !hasOrganizations.value);

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
    hasInitialized.value = true;

    await selectFirstAvailableWorkspace();

    return bootstrap;
  }

  async function initialize() {
    if (isLoading.value || hasInitialized.value) {
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
    selectedWorkspaceId,
    selectedOrganizationId,
  };
});
```

The router guard calls `initialize()`. Route views, dialogs, and route-local stores read shell state, but they do not call `api.auth.bootstrap()` or initialize the shell for themselves. `reload()` exists for session-preserving changes, such as accepting an invitation into another organization, where the store should refresh from the backend without clearing every field first.

### Permission Redirect Helper

```typescript
// frontend/src/views/application/routeAccess.ts

type AppShellStore = ReturnType<typeof useAppShellStore>;

type GuardableRoute = Pick<RouteLocationNormalizedLoaded, "name" | "params" | "meta"> & {
  meta: {
    requiredPermissions?: AppPermission[];
  };
};

export function getRouteAccessRedirect(route: GuardableRoute, appShellStore: AppShellStore): RouteLocationRaw | null {
  const requiredPermissions = route.meta.requiredPermissions ?? [];
  if (requiredPermissions.length === 0) {
    return null;
  }

  const workspaceId = getRouteWorkspaceId(route);

  if (workspaceId) {
    return getWorkspaceRouteAccessRedirect(route, appShellStore, workspaceId);
  }

  if (route.name === "dashboard") {
    const selectedWorkspaceRouteParams = appShellStore.getSelectedWorkspaceRouteParams();
    if (selectedWorkspaceRouteParams) {
      return { name: "workspace-dashboard", params: selectedWorkspaceRouteParams };
    }
  }

  return getOrganizationRouteAccessRedirect(route, appShellStore);
}
```

Keep permission-specific redirects in a small app-shell helper instead of spreading them through the guard or route views. The helper can interpret route params, selected organization or workspace state, and the backend-provided permission payload in one place.

### One Global Router Guard

```typescript
// frontend/src/router/index.ts

import { guestRoutes } from "@/router/guestRoutes";
import { workspaceRoutes } from "@/router/workspaceRoutes";
import { useAppShellStore } from "@/views/application/appShellStore";
import { getRouteAccessRedirect } from "@/views/application/routeAccess";
import { createRouter, createWebHashHistory } from "vue-router";

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  routes: [
    ...workspaceRoutes,
    ...guestRoutes,
    {
      path: "/:pathMatch(.*)*",
      redirect: { name: "dashboard" },
    },
  ],
});

router.beforeEach(async (to) => {
  const appShellStore = useAppShellStore();
  const shouldInitializeShell = !to.meta.skipShellBootstrap;

  if (shouldInitializeShell && !appShellStore.hasInitialized && !appShellStore.isLoading) {
    try {
      await appShellStore.initialize();
    } catch {
      return true;
    }
  }

  if (to.meta.requiresAuth && appShellStore.hasInitialized && !appShellStore.isAuthenticated) {
    return { name: "login", query: { redirect: to.fullPath } };
  }

  if (appShellStore.needsOrganizationOnboarding) {
    if (to.name === "workspaces-list") {
      return true;
    }

    return { name: "workspaces-list" };
  }

  const accessRedirect = getRouteAccessRedirect(to, appShellStore);
  if (accessRedirect) {
    return accessRedirect;
  }

  if (to.meta.guestOnly && appShellStore.isAuthenticated) {
    const redirect = typeof to.query.redirect === "string" ? to.query.redirect : null;
    if (redirect && redirect.startsWith("/")) {
      return redirect;
    }

    return { name: "dashboard" };
  }

  return true;
});

export default router;
```

The guard initializes shell state once for every route that has not opted out. Protected route checks wait for `hasInitialized` so a page does not render before the browser session has been resolved. Anonymous protected-route visits are redirected to login with `redirect: to.fullPath`; guest-only routes honor that redirect after login only when it is app-local.

### Session-Changing Flows Reset Or Rebootstrap

```vue
<!-- frontend/src/views/login/LoginView.vue -->

<script setup lang="ts">
  const route = useRoute();
  const router = useRouter();
  const appShellStore = useAppShellStore();

  async function submitLogin() {
    if (!(await validate())) {
      return;
    }

    await api.auth.login(formValues);
    appShellStore.resetState();
    await appShellStore.initialize();

    const redirect = typeof route.query.redirect === "string" ? route.query.redirect : null;
    if (redirect && redirect.startsWith("/")) {
      await router.replace(redirect);
      return;
    }

    await router.replace({ name: "workspaces-list" });
  }
</script>
```

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

Login and registration create a new authenticated session, so reset stale shell state and initialize from the backend before redirecting into the workspace. Logout destroys the session, so reset immediately before navigating to a guest route. Invitation acceptance or similar flows that add access to an existing session should call `appShellStore.reload()` before sending the user to a workspace that depends on the new access payload.

## Things To Notice

- Route access rules live in router metadata instead of being re-implemented inside page components.
- One global guard owns bootstrap timing, anonymous redirects, guest-only redirects, onboarding redirects, and permission redirects.
- `skipShellBootstrap` is explicit and rare. It belongs on public flows that should not initialize organization, workspace, or operator shell context.
- `requiredPermissions` is an array because a route may require more than one backend-provided permission.
- Permission redirects use `getRouteAccessRedirect(...)`, not hand-built role checks in the page.
- The app preserves the intended destination for anonymous users with `query.redirect`, then only honors local paths after login.
- Session-changing flows refresh shell state from the backend instead of manually assigning `isAuthenticated`, `currentUser`, organization arrays, workspace arrays, or permission arrays.
- Route-local stores may call `appShellStore.can(...)` for feature actions, but they do not own top-level route admission or shell bootstrap.

## Rules To Follow

- Keep session bootstrap in `frontend/src/views/application/appShellStore.ts`.
- Keep route access intent in typed route metadata: `requiresAuth`, `guestOnly`, `skipShellBootstrap`, and `requiredPermissions`.
- Keep exactly one global `router.beforeEach(...)` responsible for auth and permission redirects.
- Bootstrap the shell before protected routes render unless the route explicitly sets `skipShellBootstrap`.
- Redirect anonymous protected-route visits to login with `query.redirect: to.fullPath`.
- Redirect authenticated users away from `guestOnly` routes, honoring only app-local redirect paths.
- Enforce route permissions through `getRouteAccessRedirect(...)` and `appShellStore.can(...)`; do not duplicate permission logic inside route views.
- Do not call `api.auth.bootstrap()` from route views, dialogs, public views, or route-local feature stores.
- Do not call `appShellStore.initialize()` from normal route views as a workaround for missing route metadata. Session-changing auth views may reset and initialize after login or registration.
- Mark truly public routes with `skipShellBootstrap: true`; do not leave them implicit.
- Reset and re-bootstrap shell state after login, registration, or another flow that creates a new authenticated session.
- Reset shell state immediately after logout.
- Re-bootstrap or reload shell state after session-preserving access changes, such as accepting an invitation.
- Keep frontend redirects deterministic. Do not guess a destination from display labels, previous component state, or untrusted external URLs.

## Refactor Signals

- A non-auth route component imports `api.auth.bootstrap`, calls a session-status endpoint, or calls `appShellStore.initialize()`.
- A route component calls `router.replace({ name: "login" })` because the user is anonymous.
- A login, register, logout, or invitation flow manually assigns shell fields instead of calling `resetState()`, `initialize()`, or `reload()`.
- A protected route is missing `requiresAuth: true` or a permission-gated route is missing `requiredPermissions`.
- A public route loads organization or workspace shell context even though it only needs a token or public payload.
- Several routes repeat the same permission redirect branch instead of using `getRouteAccessRedirect(...)`.
- A route-local store decides whether the route is allowed to render instead of exposing local action permissions.
- Route metadata uses ad hoc keys such as `auth`, `public`, `roles`, or `permissions` instead of the typed contract.
- Tests only cover successful page rendering and never assert anonymous redirects, guest-only redirects, permission redirects, or public-route shell skipping.

## Verification

- Run the frontend typecheck after changing route metadata, route files, the shell store, or route-access helpers:

```bash
cd frontend
npm run type-check
```

- Run the frontend lint command after editing TypeScript or Vue files:

```bash
cd frontend
npm run lint
```

- Add or update focused route-guard tests when behavior changes. The repository uses `frontend/tests/route-auth-guard-guidance.test.ts` to assert that the global guard owns redirects, route metadata expresses access, and route views do not bootstrap auth themselves.
- Add or update e2e coverage for public routes that skip shell bootstrap. The public survey flow should prove the survey route renders without mounting authenticated shell controls.
- Use `rg` as a structural check before finishing route-auth work:

```bash
rg "api\\.auth\\.bootstrap|appShellStore\\.initialize\\(" frontend/src/views
rg "requiresAuth|guestOnly|skipShellBootstrap|requiredPermissions" frontend/src/router
rg "router\\.beforeEach" frontend/src/router
```

- `api.auth.bootstrap` should only appear in the shell store. `appShellStore.initialize()` in route views should be limited to session-changing auth flows that reset shell state first.
- For guidance-only changes, also verify the Markdown source is structurally valid and that fenced code blocks are balanced.

## Why It Helps

- Route admission stays predictable because every navigation passes through the same shell-backed guard.
- Protected pages do not render before the app knows whether the browser session is authenticated.
- Public pages stay lightweight and avoid loading unrelated operator shell state.
- Permission behavior is auditable in route records and one helper instead of scattered through pages.
- Login, logout, registration, and invitation flows cannot leave stale organization, workspace, or permission state behind.
- New routes need metadata and normal shell-store reads, not custom bootstrap and redirect plumbing.
