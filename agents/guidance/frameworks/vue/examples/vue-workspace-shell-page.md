---
id: framework-vue-example-workspace-shell-page
title: Vue Workspace Shell And Page Example
description: Example shared workspace shell and scoped page composition using app-owned wrappers, a shell store, and route-level page sections.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - shell
  - layout
applies_to:
  - vue
status: active
order: 19
---

# Vue Workspace Shell And Page Example

## Scenario

- Use this pattern when authenticated Vue routes need one shared workspace shell with navigation, organization and workspace selection, user identity, permissions, loading, onboarding, and theme controls.
- Use this pattern when route pages need current organization, workspace, user, and access context without re-fetching shell bootstrap data.
- Use this pattern when adding organization-scoped or workspace-scoped pages under `src/views/` that should compose shared page wrappers, shared table/status components, and route-local stores inside the application shell.
- Use this pattern when distinguishing public, guest-only, fullscreen, and protected workspace routes.

## Why This Shape Exists

- The workspace shell is the cross-route boundary. It owns chrome, navigation, route outlet placement, shell bootstrap loading, no-organization onboarding, organization switching, workspace switching, logout, global toasts, and the light or dark theme toggle.
- Route pages are domain workflow surfaces. They should load catalogEntries, workspaces, notifications, rate cards, contacts, or other feature data after the shell has established the authenticated session and selected scope.
- Django session auth makes bootstrap state authoritative. Pages should not call `api.auth.bootstrap()`, infer auth from local storage, or independently fetch current user, organizations, workspaces, or permissions.
- A single shell prevents duplicated sidebars, competing mobile drawers, redirect races, theme drift, and route pages that each invent a different loading branch for the same session state.
- Route metadata is the reviewable contract for where a page belongs. `requiresAuth`, `guestOnly`, `skipShellBootstrap`, `skipAppShell`, `fullscreenShell`, `globalNavKey`, and `requiredPermissions` explain how the shell and router guard should treat the route.
- Shared page wrappers make route views read as page outlines. A reviewer should be able to scan the view and see header, filters, table, status card, drawer, and route-local sections without parsing low-level shell markup.

## Recommended Shape

### App Root Chooses One Shell

{% raw %}
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
  import FullscreenPageShell from "@/components/layout/FullscreenPageShell.vue";
  import GuestPageShell from "@/components/layout/GuestPageShell.vue";
  import ApplicationShellView from "@/views/application/ApplicationShellView.vue";
  import ApplicationToastViewport from "@/views/application/components/ApplicationToastViewport.vue";
  import { useAppShellStore } from "@/views/application/appShellStore";
  import { computed } from "vue";
  import { RouterView, useRoute } from "vue-router";

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
{% endraw %}

`App.vue` is the only place that chooses between authenticated shell, guest shell, and fullscreen shell. It mounts the global toast viewport once. Route pages should not wrap themselves in `ApplicationShellView`, `GuestPageShell`, or a copied shell container.

### Route Metadata Declares Shell Behavior

```typescript
// frontend/src/router/routeMeta.d.ts

import type { AppPermission } from "@/views/application/permissions";

declare module "vue-router" {
  interface RouteMeta {
    breadcrumbLabel?: string;
    fullscreenShell?: boolean;
    globalNavKey?: string;
    guestOnly?: boolean;
    placeholderDescription?: string;
    placeholderStatus?: string;
    placeholderTitle?: string;
    requiredPermissions?: AppPermission[];
    requiresAuth?: boolean;
    skipAppShell?: boolean;
    skipShellBootstrap?: boolean;
    title?: string;
  }
}

export {};
```

```typescript
// frontend/src/router/organizationRoutes.ts

export const organizationRoutes: RouteRecordRaw[] = [
  {
    path: "rate-cards",
    name: "organization-rate-cards-list",
    component: () => import("@/views/rateCards/RateCardsView.vue"),
    meta: {
      requiresAuth: true,
      requiredPermissions: [APP_PERMISSIONS.organizationWorkspacesView],
      title: "Rate Cards",
      globalNavKey: "rate-cards",
    },
  },
];
```

```typescript
// frontend/src/router/guestRoutes.ts

export const guestRoutes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "login",
    component: () => import("@/views/login/LoginView.vue"),
    meta: { guestOnly: true, title: "Sign In" },
  },
  {
    path: "/survey/:token",
    name: "public-survey",
    component: () => import("@/views/publicSurvey/PublicSurveyView.vue"),
    meta: { skipShellBootstrap: true, title: "Survey" },
  },
];
```

Workspace pages set `requiresAuth` and permissions. Guest auth screens set `guestOnly`. Public routes that should not load the operator shell set `skipShellBootstrap`. Fullscreen tools set `fullscreenShell` and `skipAppShell` when they need the app root but not workspace chrome.

### Shell Store Owns Bootstrap Context

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

  const selectedOrganization = computed(() => {
    return organizations.value.find((organization) => organization.id === selectedOrganizationId.value) ?? null;
  });
  const selectedWorkspace = computed(() => {
    return workspaces.value.find((workspace) => workspace.id === selectedWorkspaceId.value) ?? null;
  });
  const needsOrganizationOnboarding = computed(() => {
    return isAuthenticated.value && hasInitialized.value && organizations.value.length === 0;
  });

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

  return {
    workspaces,
    workspacesErrorMessage,
    currentUser,
    errorMessage,
    hasInitialized,
    initialize,
    isAuthenticated,
    isWorkspacesLoading,
    isLoading,
    needsOrganizationOnboarding,
    selectedWorkspace,
    selectedWorkspaceId,
    selectedOrganization,
    selectedOrganizationId,
    organizations,
  };
});
```

The shell store is the only frontend store that bootstraps current session, user, organizations, workspaces, selected scope, and permission maps. Route-local stores can read `selectedOrganizationId`, `selectedWorkspaceId`, `currentUser`, and `can(...)`, but they should not call `api.auth.bootstrap()` or duplicate these fields.

### Application Shell Owns Navigation And Outlet Placement

{% raw %}
```vue
<!-- frontend/src/views/application/ApplicationShellView.vue -->
<template>
  <AppContainer>
    <AppShellFrame ref="shellFrameRef">
      <template #sidebar="{ isSidebarCollapsed, sidebarMode, closeSidebar }">
        <SidebarNav
          :sections="navSections"
          :active-key="activeNavKey"
          :collapsed="isSidebarCollapsed"
          @select="handleSelect($event, closeSidebar)"
        >
          <template #header>
            <ApplicationSidebarHeader
              :collapsed="isSidebarCollapsed"
              :disabled="appShellStore.isLoading || isWorkspaceSwitching"
              :selected-workspace-id="appShellStore.selectedWorkspaceId"
              :subtitle="shellSubtitle"
              :workspaces="appShellStore.workspaces"
              :action-mode="sidebarMode === 'mobile' ? 'close' : 'collapse'"
              @select-workspace="handleWorkspaceChange"
            />
          </template>

          <template #footer>
            <ApplicationSidebarFooter
              :collapsed="isSidebarCollapsed"
              :user-name="userName"
              :user-meta="userMeta"
              @action="void handleSidebarFooterAction($event)"
            />
          </template>
        </SidebarNav>
      </template>

      <WorkspaceSwitchDialog
        :open="isWorkspaceDialogOpen"
        :organizations="appShellStore.organizations"
        :selected-organization-id="appShellStore.selectedOrganizationId"
        :is-loading="appShellStore.isWorkspacesLoading"
        @close="isWorkspaceDialogOpen = false"
        @select="void handleOrganizationChange($event)"
      />

      <MainContentPane
        v-if="appShellStore.hasInitialized && !appShellStore.needsOrganizationOnboarding"
        content-class="flex min-h-full flex-col gap-4 p-4 sm:p-5 lg:px-6 lg:py-5"
      >
        <slot :key="workspaceContentKey" />
      </MainContentPane>

      <MainContentPane
        v-else-if="appShellStore.needsOrganizationOnboarding"
        content-class="flex min-h-full items-center justify-center p-4 sm:p-5 lg:px-6 lg:py-5"
      >
        <ApplicationShellOnboardingPanel @success="void handleCreateInitialOrganization()" />
      </MainContentPane>

      <MainContentPane
        v-else
        content-class="flex min-h-full items-center justify-center p-4 sm:p-5 lg:px-6 lg:py-5"
      >
        <ApplicationShellLoadingState
          :error-message="appShellStore.errorMessage"
          @retry="void handleRetryInitialize()"
        />
      </MainContentPane>
    </AppShellFrame>
  </AppContainer>
</template>
```
{% endraw %}

```typescript
// frontend/src/views/application/ApplicationShellView.vue

const navSections = computed<SidebarNavSection[]>(() => {
  const selectedWorkspaceRouteParams = appShellStore.getSelectedWorkspaceRouteParams() ?? undefined;
  const isWorkspaceRouteDisabled = !appShellStore.canNavigateToWorkspaceRoute();

  const coreItems: SidebarNavItem[] = [
    {
      key: "dashboard",
      label: "Dashboard",
      icon: "dashboard",
      routeName: "workspace-dashboard",
      routeParams: selectedWorkspaceRouteParams,
      disabled: isWorkspaceRouteDisabled,
    },
    {
      key: "contacts",
      label: "Contacts",
      icon: "contacts",
      routeName: "contacts-list",
      routeParams: selectedWorkspaceRouteParams,
      disabled: isWorkspaceRouteDisabled,
    },
  ];

  return [
    { key: "core", label: "Core", items: coreItems },
  ];
});

const activeNavKey = computed(() => {
  return typeof route.meta.globalNavKey === "string" ? route.meta.globalNavKey : "dashboard";
});
```

The shell renders `AppContainer`, `AppShellFrame`, `SidebarNav`, the workspace switch dialog, shell loading, organization onboarding, and `MainContentPane`. Route pages arrive through the slot from `App.vue`; they never place their own router outlet or sidebar.

### Theme Store Applies Light And Dark Mode At The Root

```typescript
// frontend/src/views/application/themeStore.ts

export type ThemePreference = "dark" | "light";

const themeStorageKey = "marketing-platform.theme";

function applyThemePreference(theme: ThemePreference) {
  const rootElement = document.documentElement;
  rootElement.dataset.theme = theme;
  rootElement.style.colorScheme = theme;
}

export const useThemeStore = defineStore("theme", () => {
  const theme = ref<ThemePreference>("light");
  const isDark = computed(() => theme.value === "dark");

  function setTheme(nextTheme: ThemePreference) {
    theme.value = nextTheme;
    applyThemePreference(nextTheme);
    window.localStorage.setItem(themeStorageKey, nextTheme);
  }

  function toggleTheme() {
    setTheme(isDark.value ? "light" : "dark");
  }

  return {
    isDark,
    setTheme,
    theme,
    toggleTheme,
  };
});
```

The theme store is shell-level state. It applies `data-theme` and `color-scheme` to `document.documentElement`. Pages and shared wrappers should use semantic tokens such as `bg-background`, `bg-surface`, `text-body`, `text-secondary`, and `border-line` instead of toggling page-local theme classes or reading organization branding fields for the internal operator shell.

### Route Pages Compose Shared Page Wrappers

{% raw %}
```vue
<template>
  <div class="space-y-3">
    <PageHeader
      title="Workspaces"
      description="View and manage workspaces for the selected organization"
    >
      <template #actions>
        <AppButton
          label="New workspace"
          tone="primary"
          icon="plus"
          :disabled="!appShellStore.selectedOrganization || !workspacesStore.canCreate"
          @click="handleCreateWorkspace"
        />
        <AppButton
          label="Refresh"
          tone="ghost"
          icon="refresh"
          :disabled="!appShellStore.selectedOrganization || appShellStore.isWorkspacesLoading"
          @click="void appShellStore.refreshWorkspaces()"
        />
      </template>
    </PageHeader>

    <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
      <AppInputText
        v-model="workspacesStore.searchTerm"
        type="search"
        placeholder="Search workspaces..."
      />

      <AppSelect
        v-model="workspacesStore.statusFilter"
        :options="workspacesStore.statusOptions"
        option-label="label"
        option-value="value"
      />
    </div>

    <PageStatusCard
      v-if="!appShellStore.selectedOrganization"
      title="Select a workspace"
      description="Choose an organization workspace from the user menu before managing workspaces"
    />

    <WorkspacesTable
      v-else
      :rows="workspacesStore.workspaceRows"
      :loading="appShellStore.isWorkspacesLoading"
      :error-message="appShellStore.workspacesErrorMessage"
      :can-create="workspacesStore.canCreate"
      @create="handleCreateWorkspace"
      @retry="void appShellStore.refreshWorkspaces()"
      @select="handleOpenWorkspace"
    />
  </div>
</template>

<script setup lang="ts">
  import PageHeader from "@/components/page/PageHeader.vue";
  import PageStatusCard from "@/components/page/PageStatusCard.vue";
  import AppButton from "@/components/ui/AppButton.vue";
  import AppInputText from "@/components/ui/AppInputText.vue";
  import AppSelect from "@/components/ui/AppSelect.vue";
  import { useAppShellStore } from "@/views/application/appShellStore";
  import WorkspacesTable from "@/views/workspaces/components/WorkspacesTable.vue";
  import { useWorkspacesStore } from "@/views/workspaces/workspacesStore";
  import { useRouter } from "vue-router";

  const appShellStore = useAppShellStore();
  const workspacesStore = useWorkspacesStore();
  const router = useRouter();

  function handleCreateWorkspace() {
    void router.push({ name: "workspaces-create" });
  }

  function handleOpenWorkspace(workspaceId: number) {
    void router.push({ name: "workspace-detail", params: { workspaceId } });
  }
</script>
```
{% endraw %}

The page reads as page composition: header, actions, filters, status, table. It consumes shell-level organization and workspace state, uses a route-local store for page filters and rows, and delegates loading/error/empty display to shared components.

### Route-Local Stores Add Domain State On Top Of Shell State

```typescript
// frontend/src/views/notifications/notificationsStore.ts

export const useNotificationsStore = defineStore("notifications", () => {
  const appShellStore = useAppShellStore();

  const errorMessage = ref("");
  const isLoading = ref(false);
  const templates = ref<NotificationTemplateInterface[]>([]);

  const organizationId = computed(() => appShellStore.selectedOrganizationId);
  const canManage = computed(() => {
    return appShellStore.can(APP_PERMISSIONS.organizationAccessManage, {
      organizationId: organizationId.value,
    });
  });

  async function load() {
    if (!organizationId.value) {
      templates.value = [];
      return;
    }

    isLoading.value = true;
    errorMessage.value = "";

    try {
      templates.value = await api.notifications.list(organizationId.value);
    } catch (error) {
      templates.value = [];
      errorMessage.value = getFirstApiErrorMessage(error, "Unable to load notification templates.");
    } finally {
      isLoading.value = false;
    }
  }

  return {
    canManage,
    errorMessage,
    isLoading,
    load,
    organizationId,
    templates,
  };
});
```

Route-local stores can derive organization or workspace scope from `useAppShellStore()` and then call domain API methods. They own route-specific loading, error, rows, filters, dialogs, and permission-derived actions. They should not move those domain concerns into `appShellStore`, and they should not ask the backend for bootstrap context again.

## Things To Notice

- `App.vue` chooses the shell once, and `ApplicationShellView` owns authenticated workspace chrome. Route pages do not recreate shell structure.
- `ApplicationShellView` receives route content through a slot. It places content inside `MainContentPane` only after bootstrap has completed and organization onboarding is not required.
- `appShellStore` owns user, organization, workspace, selected scope, access maps, shell loading, workspace loading, and onboarding state.
- Route-local stores derive scope from `appShellStore` and own only domain workflow state such as rows, filters, dialogs, mutations, and page-level errors.
- Route metadata is the contract for shell behavior and navigation identity. `globalNavKey` drives active sidebar state; `requiredPermissions` drives access checks; `skipShellBootstrap` keeps public routes out of the operator shell.
- Theme state lives under `src/views/application/themeStore.ts` and is applied at the root HTML element. Workspace pages should stay token-driven and should not toggle their own theme roots.
- Shared shell and page components live under `src/components/layout/`, `src/components/navigation/`, `src/components/page/`, and `src/components/ui/`. Route-specific panels and tables live under the owning route folder.
- Shell loading is not page loading. Shell bootstrap prepares session and scope. Page loading fetches feature records after scope exists.

## Rules To Follow

- Keep exactly one authenticated workspace shell. Do not add per-route sidebars, mobile drawers, workspace switchers, logout menus, or theme toggles.
- Keep shell-level state in `src/views/application/`; do not introduce a top-level `src/stores/` directory for shared app shell state.
- Do not call `api.auth.bootstrap()` outside `appShellStore` and the router guard flow.
- Do not make route pages fetch current user, organization lists, workspace lists, or global permission maps for themselves.
- Declare route access and shell behavior through typed route metadata instead of route-local redirect code.
- Protected workspace routes must set `requiresAuth: true`; permission-gated routes must set `requiredPermissions`.
- Guest auth routes should set `guestOnly`; public routes that should avoid operator bootstrap must set `skipShellBootstrap`.
- Use `globalNavKey` on workspace routes that should highlight a sidebar item.
- Let `ApplicationShellView` own `AppContainer`, `AppShellFrame`, `SidebarNav`, `WorkspaceSwitchDialog`, `MainContentPane`, shell loading, onboarding, organization switching, workspace switching, logout, and theme actions.
- Let route views compose shared page wrappers such as `PageHeader`, `PageSection`, `PageStatusCard`, `AppTable`, and app-owned `ui/` controls.
- Put route-specific tables, drawers, panels, and route-local stores inside the owning `src/views/<route>/` folder.
- Keep shared `src/components/` primitives store-agnostic and prop-driven. They must not import route-local stores or domain APIs.
- Use semantic Tailwind tokens and CSS-variable backed classes for light and dark mode. Do not add page-local theme systems or branded shell palettes unless item requirements change.
- Reset or reload shell state after session-changing flows such as login, logout, registration, and invitation acceptance so the shell and route guard see the backend's latest session state.

## Refactor Signals

- A route page imports `AppShellFrame`, `SidebarNav`, `MainContentPane`, `GuestPageShell`, or `ApplicationShellView`.
- A route page or route-local store calls `api.auth.bootstrap()` or stores its own `currentUser`, organization list, workspace list, or permission map.
- Multiple pages have their own bootstrap loading UI for session, organization, workspace, or access context.
- A page owns an organization switcher, workspace switcher, logout button, mobile sidebar drawer, or theme toggle that should be shared shell chrome.
- Route records omit `requiresAuth`, `requiredPermissions`, or `globalNavKey` and the page compensates with local redirects or active-nav logic.
- Public routes trigger shell bootstrap even though they do not need operator organization or workspace context.
- Route pages use raw cards and ad hoc spacing for repeated page structure instead of `PageHeader`, `PageSection`, shared table wrappers, or status components.
- Shared components under `src/components/` import route stores, `useRoute()`, `useRouter()`, or domain API modules.
- Theme toggles or theme CSS variables appear in individual pages instead of the root theme store and shared tokens.
- Feature loading and shell loading are conflated, such as blanking the whole shell while only a table is refreshing.

## Verification

- Inspect `frontend/src/App.vue` when changing shell selection, route outlet keys, guest layout behavior, fullscreen behavior, or global toast placement.
- Inspect `frontend/src/views/application/ApplicationShellView.vue` and `frontend/src/views/application/appShellStore.ts` when changing shell bootstrap, organization or workspace switching, onboarding, navigation sections, logout, or theme actions.
- Inspect `frontend/src/router/routeMeta.d.ts`, `frontend/src/router/guestRoutes.ts`, `frontend/src/router/organizationRoutes.ts`, `frontend/src/router/workspaceRoutes.ts`, and `frontend/src/router/index.ts` when adding or changing route access behavior.
- Run `npm run type-check` and `npm run lint` from `frontend/` for frontend code changes.
- For route or shell behavior changes, add or update route-guard, store, or component tests when the local test structure exists.
- For guidance-only edits, run `python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean` and confirm the generated output includes this example.

## Why It Helps

- The shell stays consistent across every protected route, including desktop and mobile navigation.
- Session, user, organization, workspace, and permission state have one owner, which reduces stale scope bugs and duplicated auth checks.
- Route pages stay readable because they focus on domain workflow composition instead of app chrome.
- Public and guest routes have explicit escape hatches, so they do not accidentally load operator context.
- Shared wrappers keep spacing, loading states, retry behavior, theme tokens, and page structure consistent.
- Reviewers can enforce the pattern quickly by checking route metadata, shell-store ownership, and whether pages compose shared components instead of rebuilding shell concerns.
