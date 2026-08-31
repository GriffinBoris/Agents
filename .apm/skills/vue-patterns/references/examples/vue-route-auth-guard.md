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
    skipAppShell?: boolean;
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
    meta: { skipAppShell: true, skipShellBootstrap: true, title: "Survey" },
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

Protected workspace routes set `requiresAuth: true`. Routes that need organization or workspace access also set `requiredPermissions`. Guest auth screens set `guestOnly: true`. Truly public routes that bypass all session admission set `skipShellBootstrap: true`; pair it with `skipAppShell: true` when they must not mount authenticated application chrome.

### Shell Store Contract

Use [Vue Auth-Aware Shell Example](vue-auth-shell.md) for the shell-store and bootstrap implementation. The route guard should depend on a narrow store contract:

- `hasInitialized`, `isLoading`, and `isAuthenticated` expose bootstrap state.
- `needsOrganizationOnboarding`, `getSelectedWorkspaceRouteParams()`, and permission helpers expose route-admission decisions derived from the backend payload.
- `initialize()` is idempotent and loads the current browser session once.
- `resetState()` clears session-derived state after logout or before initializing a newly authenticated session.
- `reload()` refreshes session-preserving access changes such as invitation acceptance.

Normal route views, dialogs, and route-local stores read shell state but do not call the bootstrap endpoint or initialize the shell themselves.

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

  if (to.meta.skipShellBootstrap) {
    return true;
  }

  if (!appShellStore.hasInitialized) {
    try {
      await appShellStore.initialize();
    } catch {
      return false;
    }
  }

  if (to.meta.requiresAuth && !appShellStore.isAuthenticated) {
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

The guard admits explicitly public routes without touching shell state. Every other route waits for the shared initialization promise, so concurrent navigations do not bypass unresolved session state. If bootstrap fails, abort navigation and let the shell's existing error or retry UI handle the failure; never admit a protected route with unknown session state. Anonymous protected-route visits are redirected to login with `redirect: to.fullPath`; guest-only routes honor that redirect after login only when it is app-local.

### Session Changes Use The Shell Lifecycle

The guard owns route admission, not session mutation. Use [Vue Auth-Aware Shell Example](vue-auth-shell.md) for login, registration, invitation acceptance, and logout. Those flows reset and initialize after creating a session, reload after session-preserving access changes, and reset after destroying a session before the guard admits the next route.

## Things To Notice

- Route access rules live in router metadata instead of being re-implemented inside page components.
- One global guard owns bootstrap timing, anonymous redirects, guest-only redirects, onboarding redirects, and permission redirects.
- `skipShellBootstrap` is explicit and rare. It bypasses session admission for truly public flows, and `skipAppShell` separately keeps authenticated application chrome from mounting.
- `requiredPermissions` is an array because a route may require more than one backend-provided permission.
- Permission redirects use `getRouteAccessRedirect(...)`, not hand-built role checks in the page.
- The app preserves the intended destination for anonymous users with `query.redirect`, then only honors local paths after login.
- Route-local stores may call `appShellStore.can(...)` for feature actions, but they do not own top-level route admission or shell bootstrap.

## Rules To Follow

- Keep session bootstrap in the repository's shared shell store.
- Keep route access and shell intent in typed route metadata: `requiresAuth`, `guestOnly`, `requiredPermissions`, `skipShellBootstrap`, `skipAppShell`, and `fullscreenShell`.
- Keep exactly one global `router.beforeEach(...)` responsible for auth and permission redirects.
- Await shell bootstrap before non-public routes render; abort navigation when bootstrap fails instead of admitting a route with unknown session state.
- Redirect anonymous protected-route visits to login with `query.redirect: to.fullPath`.
- Redirect authenticated users away from `guestOnly` routes, honoring only app-local redirect paths.
- Enforce route permissions through `getRouteAccessRedirect(...)` and `appShellStore.can(...)`; do not duplicate permission logic inside route views.
- Do not call `api.auth.bootstrap()` from route views, dialogs, public views, or route-local feature stores.
- Do not call `appShellStore.initialize()` from normal route views as a workaround for missing route metadata.
- Mark truly public routes with `skipShellBootstrap: true`; pair it with `skipAppShell: true` when they should not mount authenticated chrome. Do not combine `skipShellBootstrap` with protected or permission-gated metadata.
- Keep frontend redirects deterministic. Do not guess a destination from display labels, previous component state, or untrusted external URLs.

## Refactor Signals

- A non-auth route component imports `api.auth.bootstrap`, calls a session-status endpoint, or calls `appShellStore.initialize()`.
- A route component calls `router.replace({ name: "login" })` because the user is anonymous.
- A protected route is missing `requiresAuth: true` or a permission-gated route is missing `requiredPermissions`.
- A public route loads organization or workspace shell context even though it only needs a token or public payload.
- A route combines `skipShellBootstrap` with `requiresAuth` or `requiredPermissions`, leaving admission dependent on stale or missing shell state.
- A bootstrap failure admits navigation while authentication and permissions are unresolved.
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

- Add or update focused route-guard tests when behavior changes. Assert that the global guard owns redirects, route metadata expresses access, bootstrap failure aborts navigation, and route views do not bootstrap auth themselves.
- Add or update e2e coverage for public routes that skip shell bootstrap. A representative public route should render without mounting authenticated shell controls.
- Use `rg` as a structural check before finishing route-auth work:

```bash
rg "api\\.auth\\.bootstrap|appShellStore\\.initialize\\(" frontend/src
rg "requiresAuth|guestOnly|requiredPermissions|skipShellBootstrap|skipAppShell|fullscreenShell" frontend/src/router
rg "router\\.beforeEach" frontend/src/router
```

- `api.auth.bootstrap` should only appear in the shell store. `appShellStore.initialize()` in route views should be limited to session-changing auth flows that reset shell state first.

## Why It Helps

- Route admission stays predictable because every navigation passes through the same shell-backed guard.
- Protected pages do not render before the app knows whether the browser session is authenticated.
- Public pages stay lightweight and avoid loading unrelated operator shell state.
- Permission behavior is auditable in route records and one helper instead of scattered through pages.
- New routes need metadata and normal shell-store reads, not custom bootstrap and redirect plumbing.
