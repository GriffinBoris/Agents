---
id: framework-vue-example-app-layout
title: Vue App Layout Example
description: Example small-app and workspace-route layout shapes for Vue repositories using src/views as the main modern frontend boundary.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - structure
applies_to:
  - vue
status: active
order: 18
---

# Vue App Layout Example

## Scenario

Use this pattern when deciding where new Vue code belongs, when moving legacy frontend code toward the modern layout, or when reviewing a route that has started to accumulate shell state, domain API calls, local components, and shared UI concerns in one place.

This example covers two acceptable shapes:

- A small app layout for a few routes with minimal shared workflow state.
- A workspace layout for authenticated operator surfaces with shared shell state, route folders, domain types, canonical API utilities, and app-owned wrapper components.

The important decision is not folder count. The important decision is ownership. Shared shell state, shared UI wrappers, route-local workflow state, domain API contracts, and transport utilities each need one obvious home so future route work does not recreate parallel structures.

## Why This Shape Exists

- `src/views/` is the route ownership map. A contributor should be able to find a page, its route-local components, and its route-local store without searching unrelated feature roots.
- `src/views/application/` is the shell-state boundary. Auth bootstrap, selected organization, selected workspace, permissions, theme, notifications, and app-shell loading belong there because they cross route boundaries.
- `src/components/` is the shared UI boundary. Components here should be reusable wrappers or primitives, not domain workflows that import route-local stores.
- `src/types/<domain>/` is the frontend API contract boundary. Returned resources, request DTOs, options bundles, enum files, and action responses should be grouped by domain instead of scattered through route views.
- `src/utils/api.ts` is the transport boundary. Axios, CSRF/session behavior, casing conversion, and domain API segments belong there instead of in views, stores, or a parallel services folder.
- Legacy `features/`, `services/`, and top-level `stores/` layouts create second sources of truth. They hide whether a module is shared, route-local, transport-level, or shell-level. Modern work should migrate toward `views/`, `utils/`, `types/`, and focused shared component families as touched.

The tradeoff is that larger routes may have more files in one route folder. That is intentional: colocated route files make ownership clearer than spreading one workflow across abstract global folders.

## Recommended Shape

### Small App With A Few Routes

Use the small shape when the app has a handful of route views, a single shell store, simple auth screens, and shared UI primitives that are not yet large enough to justify every wrapper family.

```text
src/
├── assets/
├── components/
│   ├── layout/
│   │   ├── GuestPageShell.vue
│   │   └── FullscreenPageShell.vue
│   └── ui/
│       ├── AppButton.vue
│       ├── AppInputText.vue
│       └── AppLoadingSpinner.vue
├── router/
│   ├── guestRoutes.ts
│   ├── index.ts
│   └── routeMeta.d.ts
├── types/
│   ├── api/
│   │   ├── EmptyResponseInterface.ts
│   │   └── ErrorResponseInterface.ts
│   └── auth/
│       ├── AppBootstrapResponseInterface.ts
│       ├── AuthUserInterface.ts
│       ├── ForgotPasswordRequestInterface.ts
│       ├── LoginRequestInterface.ts
│       ├── RegisterInputInterface.ts
│       └── ResetPasswordConfirmInterface.ts
├── utils/
│   ├── api.ts
│   ├── apiParams.ts
│   ├── caseConversion.ts
│   └── errorHandling.ts
└── views/
    ├── application/
    │   ├── appShellStore.ts
    │   ├── notificationsStore.ts
    │   └── themeStore.ts
    ├── login/
    │   └── LoginView.vue
    ├── register/
    │   └── RegisterView.vue
    ├── resetPassword/
    │   └── ResetPasswordView.vue
    └── overview/
        └── OverviewView.vue
```

This shape can stay compact because route-local state has not outgrown the route views. It still keeps the API client in `utils/`, auth and error contracts in `types/`, and shell state in `views/application/` so the app can grow without changing its boundaries later.

### Workspace App With Route Ownership

Use the workspace shape when the app has authenticated workspace routes, a shell with navigation and selected workspace context, repeated page composition, shared wrappers around PrimeVue or lower-level controls, route-local stores, and domain models.

```text
src/
├── assets/
├── components/
│   ├── forms/
│   │   ├── AppAutocompleteField.vue
│   │   ├── AppDateField.vue
│   │   ├── AppSelectField.vue
│   │   ├── AppTextField.vue
│   │   └── AppTextareaField.vue
│   ├── layout/
│   │   ├── AppContainer.vue
│   │   ├── AppMobileSidebarDrawer.vue
│   │   ├── AppShellFrame.vue
│   │   ├── FullscreenPageShell.vue
│   │   ├── GuestPageShell.vue
│   │   └── MainContentPane.vue
│   ├── navigation/
│   │   ├── AppBreadcrumbs.vue
│   │   ├── AppSidebarNavItem.vue
│   │   └── SidebarNav.vue
│   ├── page/
│   │   ├── AppTable.vue
│   │   ├── EntityIndexTable.vue
│   │   ├── PageCenteredState.vue
│   │   ├── PageHeader.vue
│   │   ├── PageSection.vue
│   │   └── PageStatusCard.vue
│   └── ui/
│       ├── AlertBanner.vue
│       ├── AppButton.vue
│       ├── AppConfirmationDialog.vue
│       ├── AppDrawer.vue
│       ├── AppInputText.vue
│       ├── AppSelect.vue
│       ├── AppSurface.vue
│       ├── AppTabStrip.vue
│       ├── AppTag.vue
│       └── ThemeToggleButton.vue
├── composables/
│   ├── useClipboard.ts
│   ├── useNotification.ts
│   └── useSchemaValidation.ts
├── core/
│   └── survey/
├── router/
│   ├── workspaceRoutes.ts
│   ├── guestRoutes.ts
│   ├── index.ts
│   ├── routeMeta.d.ts
│   ├── organizationRoutes.ts
│   └── workspaceRoutes.ts
├── styles/
├── types/
│   ├── api/
│   │   ├── EmptyResponseInterface.ts
│   │   └── ErrorResponseInterface.ts
│   ├── auth/
│   │   ├── AppAccessInterface.ts
│   │   ├── AppBootstrapResponseInterface.ts
│   │   ├── AuthUserInterface.ts
│   │   └── LoginRequestInterface.ts
│   ├── workspace/
│   │   ├── WorkspaceInputInterface.ts
│   │   └── WorkspaceInterface.ts
│   ├── catalogEntry/
│   │   ├── CatalogEntryRequestInterface.ts
│   │   ├── CatalogEntryInterface.ts
│   │   └── CatalogEntryOrganizationListFiltersInterface.ts
│   ├── pricing/
│   │   ├── RateCardRequestInterface.ts
│   │   └── RateCardInterface.ts
│   └── organization/
│       ├── OrganizationInputInterface.ts
│       └── OrganizationInterface.ts
├── utils/
│   ├── api.ts
│   ├── apiParams.ts
│   ├── caseConversion.ts
│   ├── errorHandling.ts
│   ├── routeParams.ts
│   └── routeQuery.ts
└── views/
    ├── application/
    │   ├── ApplicationShellView.vue
    │   ├── appShellStore.ts
    │   ├── notificationsStore.ts
    │   ├── permissions.ts
    │   ├── routeAccess.ts
    │   ├── themeStore.ts
    │   └── components/
    │       ├── ApplicationShellLoadingState.vue
    │       ├── ApplicationShellOnboardingPanel.vue
    │       ├── ApplicationSidebarFooter.vue
    │       ├── ApplicationSidebarHeader.vue
    │       ├── ApplicationToastViewport.vue
    │       └── WorkspaceSwitchDialog.vue
    ├── workspaces/
    │   ├── WorkspacesRouteView.vue
    │   ├── WorkspacesView.vue
    │   ├── workspacesStore.ts
    │   └── components/
    │       └── WorkspacesTable.vue
    ├── contacts/
    │   ├── ContactsView.vue
    │   ├── contactsStore.ts
    │   └── components/
    │       └── ContactsTable.vue
    ├── contactDetail/
    │   ├── ContactDetailView.vue
    │   ├── contactDetailStore.ts
    │   └── components/
    │       ├── ContactFormSection.vue
    │       └── ContactAddressesSection.vue
    ├── rateCards/
    │   ├── RateCardsView.vue
    │   ├── rateCardsStore.ts
    │   └── components/
    │       ├── RateCardDrawer.vue
    │       ├── RateCardFormFields.vue
    │       └── RateCardsTable.vue
    ├── login/
    │   └── LoginView.vue
    └── publicSurvey/
        ├── PublicSurveyView.vue
        ├── publicSurveyStore.ts
        └── components/
            └── PublicSurveyRuntimeForm.vue
```

This shape keeps shared app structure broad and route workflows narrow. If a component is reusable across routes and has no route-store dependency, promote it to `src/components/<family>/`. If it imports a route-local store, depends on route params, or renders one domain workflow, keep it under `src/views/<route>/components/`.

### App Root Chooses The Shell

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
  import { useRoute } from "vue-router";
  import { RouterView } from "vue-router";

  const appShellStore = useAppShellStore();
  const route = useRoute();

  const showFullscreenShell = computed(() => Boolean(route.meta.fullscreenShell));
  const showApplicationShell = computed(() => {
    return appShellStore.isAuthenticated && !route.meta.skipAppShell && !route.meta.fullscreenShell;
  });

  const routerViewKey = computed(() => {
    return route.params.workspaceId
      ? `workspace-${String(route.params.workspaceId)}-${String(route.name ?? route.fullPath)}`
      : String(route.name ?? route.fullPath);
  });
</script>
```

`App.vue` chooses between shell families and mounts global feedback once. It should not own domain data, query params, API orchestration, page filters, or route-specific mutation workflows.

### Shell State Lives Under `views/application`

```typescript
// frontend/src/views/application/appShellStore.ts

export const useAppShellStore = defineStore("appShell", () => {
  const hasInitialized = ref(false);
  const isLoading = ref(false);
  const errorMessage = ref("");
  const isAuthenticated = ref(false);
  const currentUser = ref<AuthUserInterface | null>(null);
  const organizations = ref<OrganizationInterface[]>([]);
  const selectedOrganizationId = ref<number | null>(null);
  const workspaces = ref<WorkspaceInterface[]>([]);
  const selectedWorkspaceId = ref<number | null>(null);

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

    isAuthenticated.value = bootstrap.isAuthenticated;
    currentUser.value = bootstrap.user;
    organizations.value = bootstrap.organizations;
    selectedOrganizationId.value = bootstrap.currentOrganizationId;
    workspaces.value = bootstrap.workspaces;
    selectedWorkspaceId.value = bootstrap.currentWorkspaceId;
    hasInitialized.value = true;

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
    currentUser,
    errorMessage,
    hasInitialized,
    initialize,
    isAuthenticated,
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

The application store owns cross-route bootstrap state. Route-local stores may read selected organization, selected workspace, current user, and permissions from this store, but they should not duplicate bootstrap calls or maintain a second authenticated-session model.

### Route Modules Wire Route Folders

```typescript
// frontend/src/router/index.ts

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
    await appShellStore.initialize();
  }

  if (to.meta.requiresAuth && appShellStore.hasInitialized && !appShellStore.isAuthenticated) {
    return { name: "login", query: { redirect: to.fullPath } };
  }

  return getRouteAccessRedirect(to, appShellStore) ?? true;
});
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

Router modules should describe navigation, route metadata, and route-folder entrypoints. They should not fetch page data, parse route-specific filters, or decide local UI state beyond route metadata.

### Route Folders Own Route Workflows

```text
src/views/rateCards/
├── RateCardsView.vue
├── rateCardsStore.ts
└── components/
    ├── RateCardDrawer.vue
    ├── RateCardFormFields.vue
    └── RateCardsTable.vue
```

```vue
<!-- frontend/src/views/rateCards/RateCardsView.vue -->

<template>
  <div class="space-y-3">
    <PageHeader
      title="Rate cards"
      :description="rateCardsStore.pageDescription"
    >
      <template #actions>
        <AppButton
          label="New rate card"
          tone="primary"
          icon="plus"
          :disabled="!rateCardsStore.canManageRateCards"
          @click="rateCardsStore.openCreateDrawer()"
        />
      </template>
    </PageHeader>

    <RateCardsTable
      :rows="rateCardsStore.rateCardRows"
      :loading="rateCardsStore.isLoading"
      :error-message="rateCardsStore.errorMessage"
      :can-create="rateCardsStore.canManageRateCards"
      @create="rateCardsStore.openCreateDrawer()"
      @retry="void rateCardsStore.load()"
    />

    <RateCardDrawer />
  </div>
</template>

<script setup lang="ts">
  import PageHeader from "@/components/page/PageHeader.vue";
  import AppButton from "@/components/ui/AppButton.vue";
  import RateCardDrawer from "@/views/rateCards/components/RateCardDrawer.vue";
  import RateCardsTable from "@/views/rateCards/components/RateCardsTable.vue";
  import { useRateCardsStore } from "@/views/rateCards/rateCardsStore";

  const rateCardsStore = useRateCardsStore();
</script>
```

The route view reads like a page outline. Shared `page/` and `ui/` wrappers handle repeated shell, button, table, and status presentation. Route-local components can import `useRateCardsStore()` directly when they participate in the same route workflow and that avoids prop-heavy forwarding.

### Route-Local Stores Own Business State

```typescript
// frontend/src/views/rateCards/rateCardsStore.ts

export const useRateCardsStore = defineStore("rateCards", () => {
  const appShellStore = useAppShellStore();
  const workspaceFilter = ref<"all" | number>("all");
  const errorMessage = ref("");
  const isLoading = ref(false);
  const rateCards = ref<RateCardInterface[]>([]);

  const organizationId = computed(() => appShellStore.selectedOrganizationId);
  const selectedWorkspaceId = computed(() => {
    return workspaceFilter.value === "all" ? null : workspaceFilter.value;
  });
  const rateCardRows = computed(() => {
    return rateCards.value.map((profile) => ({
      id: profile.id,
      primaryLabel: profile.name,
      secondaryLabel: `${profile.linkedCatalogEntryCount} catalogEntries linked`,
    }));
  });

  async function load() {
    const activeOrganizationId = organizationId.value;
    const activeWorkspaceId = selectedWorkspaceId.value;
    if (!activeOrganizationId || !activeWorkspaceId) {
      rateCards.value = [];
      errorMessage.value = "Select a workspace before viewing rate cards.";
      return;
    }

    isLoading.value = true;
    errorMessage.value = "";

    try {
      rateCards.value = await api.rateCards.list(activeOrganizationId, activeWorkspaceId);
    } catch (error) {
      rateCards.value = [];
      errorMessage.value = getFirstApiErrorMessage(error, "Unable to load rate cards for this workspace.");
    } finally {
      isLoading.value = false;
    }
  }

  return {
    workspaceFilter,
    errorMessage,
    isLoading,
    load,
    rateCardRows,
    selectedWorkspaceId,
    organizationId,
  };
});
```

Use a route-local store when several route-local sections share the same records, loading state, filters, dialogs, form state, permissions, or mutations. Keep the shell store for shell state and keep reusable shared components store-agnostic.

### Domain Types Stay Under `types/<domain>`

```text
src/types/pricing/
├── CatalogSubscriptionPlanInputInterface.ts
├── CatalogSubscriptionPlanInterface.ts
├── RateCardRequestInterface.ts
├── RateCardInterface.ts
├── RateCardCatalogEntryLinkInputInterface.ts
├── RateCardPlanOverrideInputInterface.ts
└── RateCardPlanOverrideInterface.ts
```

```typescript
// frontend/src/types/pricing/RateCardInterface.ts

export enum RateCardStatus {
  ACTIVE = "ACTIVE",
  ARCHIVED = "ARCHIVED",
}

export interface RateCardInterface {
  workspace: number;
  createdTs: string;
  description: string;
  id: number;
  linkedCatalogEntryCount: number;
  linkedPlanCount: number;
  name: string;
  status: RateCardStatus;
  updatedTs: string;
}
```

Returned resources include backend-owned fields such as `id`, timestamps, statuses, and read-only counts. Request interfaces belong in separate files when write shape differs from returned shape.

### Transport And Casing Stay Under `utils`

```typescript
// frontend/src/utils/api.ts

export class ApiClient {
  private axios: AxiosInstance;

  constructor(baseURL: string) {
    this.axios = axios.create({
      baseURL,
      xsrfHeaderName: "X-CSRFTOKEN",
      xsrfCookieName: "csrftoken",
      withCredentials: true,
      withXSRFToken: true,
    });

    this.axios.interceptors.response.use((response: AxiosResponse) => {
      response.data = snakeToCamel(response.data);
      return response;
    });
  }

  async get<TResponse>(url: string, config?: AxiosRequestConfig): Promise<TResponse> {
    const { data } = await this.axios.get<TResponse>(url, config);
    return data;
  }

  async post<TResponse, TBody>(url: string, body?: TBody): Promise<TResponse> {
    const { data } = await this.axios.post<TResponse>(url, camelToSnake(body));
    return data;
  }
}

const rateCards = {
  list: (organizationId: number, workspaceId: number) => {
    return apiClient.get<RateCardInterface[]>(
      `api/organizations/${organizationId}/workspaces/${workspaceId}/rate-cards/list/`
    );
  },
};

export const api = {
  rateCards,
};
```

```typescript
// frontend/src/utils/routeQuery.ts

export function replaceRouteQuery(router: Router, route: RouteLocationNormalizedLoaded, query: Record<string, string>) {
  const currentEntries = Object.entries(route.query).filter((entry): entry is [string, string] => {
    return typeof entry[1] === "string";
  });
  const nextEntries = Object.entries(query);

  if (currentEntries.length === nextEntries.length && nextEntries.every(([key, value]) => route.query[key] === value)) {
    return;
  }

  void router.replace({ query: nextEntries.length > 0 ? query : undefined });
}
```

Use `utils/` for genuinely shared technical boundaries: API transport, casing conversion, standardized error parsing, route param parsing, route query replacement, formatting, and class-name helpers. Do not put domain workflow orchestration in `utils/`.

### Migration From Legacy Buckets

Avoid expanding legacy or parallel roots:

```text
src/
├── features/
│   └── rateCards/
│       ├── RateCardsView.vue
│       ├── components/
│       └── store.ts
├── services/
│   ├── apiService.ts
│   └── rateCardService.ts
└── stores/
    ├── authStore.ts
    └── rateCardsStore.ts
```

Prefer the modern ownership map:

```text
src/
├── types/
│   └── pricing/
│       ├── RateCardRequestInterface.ts
│       └── RateCardInterface.ts
├── utils/
│   └── api.ts
└── views/
    ├── application/
    │   └── appShellStore.ts
    └── rateCards/
        ├── RateCardsView.vue
        ├── rateCardsStore.ts
        └── components/
            └── RateCardsTable.vue
```

When touching a legacy route, migrate the piece you are editing toward the modern structure. Do not create churn-only moves across the whole app unless the task is specifically a structural migration.

## Things To Notice

- `src/views/` is the page and route workflow boundary, not a dumping ground for all frontend code.
- `src/views/application/` is intentionally lower-case and owns shell stores, shell components, permissions, route access helpers, notifications, and theme state.
- Shared wrapper families are split by responsibility: `forms/` for labeled field wrappers, `layout/` for shells and panes, `navigation/` for sidebar and breadcrumb primitives, `page/` for route composition blocks, and `ui/` for low-level controls and surfaces.
- Shared components under `src/components/` stay prop-driven and should not import route-local stores.
- Route-local components under `src/views/<route>/components/` can import their colocated route store when the component belongs to that route workflow.
- Route stores should be descriptively named, such as `rateCardsStore.ts` or `contactDetailStore.ts`; avoid generic `store.ts`.
- Domain types live under `src/types/<domain>/`, not beside every component and not in one catch-all `types.ts`.
- `src/utils/api.ts` owns API modules, Axios configuration, CSRF behavior, casing conversion, and typed unwrapped responses.
- `src/utils/routeParams.ts` and `src/utils/routeQuery.ts` are acceptable technical helpers because they are cross-route routing utilities.
- Router modules wire route folders and access metadata. They should remain thin.
- Small apps can use fewer component families, but they should still keep the same boundaries so growth is easy.

## Rules To Follow

- Put modern route surfaces under `src/views/<route>/`.
- Keep shell-level state, permissions, theme, notifications, and app-shell components under `src/views/application/`.
- Keep route-only stores, local composables, constants, and route-specific components in the owning route folder.
- Keep shared UI wrappers under `src/components/forms/`, `src/components/layout/`, `src/components/navigation/`, `src/components/page/`, or `src/components/ui/` based on responsibility.
- Do not let shared `src/components/` files import route-local stores, route params, or domain API modules directly.
- Use fully qualified imports such as `@/views/...`, `@/types/...`, and `@/utils/...`.
- Keep the canonical API client and domain API segments in `src/utils/api.ts`; do not add `src/services/` for modern frontend work.
- Keep shared shell stores under `src/views/application/`; do not add a top-level `src/stores/` directory for modern work.
- Do not add new route surfaces under `src/features/`; migrate legacy feature folders toward `src/views/` as they are touched.
- Name store files by domain or workflow, such as `workspacesStore.ts`, `rateCardsStore.ts`, or `surveyFormBuilderStore.ts`.
- Put returned resources, request DTOs, action responses, and option bundles under `src/types/<domain>/` with explicit filenames.
- Keep frontend field names camelCase and let the API client handle snake_case conversion.
- Split a route view into local components once it mixes several distinct sections, responsive variants, drawers, tables, or loading branches.
- Promote a route-local component into `src/components/` only after real cross-route reuse exists and the component has no route-store dependency.

## Refactor Signals

- A new file appears under `src/features/`, `src/services/`, or top-level `src/stores/`.
- A shared component under `src/components/` imports `@/views/<route>/...`, reads route params, or calls `api.<domain>` directly.
- A route view owns bootstrap auth, organization, workspace, permission, theme, or global notification state instead of reading `useAppShellStore()` or the relevant application store.
- A route folder has multiple sibling components passing the same records, loading flags, field errors, and mutation callbacks through several layers instead of using a route-local store.
- Several route folders define the same local button, table, status card, drawer, field wrapper, or layout shell.
- A router module contains data-fetching, query parsing, workflow state, or view-model construction.
- Domain interfaces are declared inside `.vue` files, local stores, or catch-all `types.ts` files.
- API calls are split between `utils/api.ts`, direct Axios imports, direct `fetch`, or a new service file.
- Query-param replacement or route-param parsing is copied across views instead of using the shared route utilities.
- A route folder contains unrelated item areas that cannot be summarized in one sentence.

## Verification

Use structural checks when changing layout, moving files, or reviewing a new route:

```bash
rg -n "from ['\"]axios['\"]" frontend/src --glob '!utils/api.ts'
rg --files frontend/src | rg '^frontend/src/(features|services|stores)(/|$)'
rg -n '@/views/' frontend/src/components
rg -n 'defineStore\(' frontend/src/components
rg --files frontend/src/views | rg '/store\.ts$'
rg -n 'interface .*Interface' frontend/src/views --glob '*.vue' --glob '*.ts'
rg -n '\b[a-z]+_[a-z_]+\b' frontend/src/views frontend/src/components
```

Run normal frontend verification when code changes:

```bash
cd frontend
npm run type-check
npm run lint
```

For guidance edits, rebuild generated agent output instead of editing generated files:

```bash
python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean
```

## Why It Helps

- New route work lands where reviewers expect it.
- Shared shell behavior stays consistent across authenticated, guest, fullscreen, and public routes.
- Route-local stores make workflow ownership clear without inflating the app shell store.
- Shared component families stay reusable because they do not know about route stores or domain API calls.
- Domain types and API methods remain easy to audit against backend contracts.
- Legacy structure disappears incrementally as touched work moves to the modern ownership map.
- Structural checks catch drift before it becomes another frontend architecture migration.
