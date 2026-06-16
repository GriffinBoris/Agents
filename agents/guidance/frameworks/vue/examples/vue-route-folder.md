---
id: framework-vue-example-route-folder
title: Vue Route Folder Example
description: Example route-based `src/views/` structure where each route folder owns its local pieces.
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
order: 19
---

# Vue Route Folder Example

## Scenario

- Use this when adding or refactoring a Vue route under `frontend/src/views/`.
- Use this when a route has more than one local section, dialog, table, drawer, composable, or store-backed workflow.
- Use this when deciding whether code belongs in a route folder, shared `src/components/`, shared `src/types/<domain>/`, shared shell state under `src/views/application/`, or the canonical API client in `src/utils/api.ts`.
- Use this when removing modern route code from older top-level `src/features/`, `src/services/`, or `src/stores/` style layouts.

Route folders are the default ownership unit for modern frontend feature work in this architecture. The route tree should tell future readers where page-specific state, page-specific UI, and page-specific orchestration live.

## Why This Shape Exists

- Route-based ownership makes the frontend easier to audit. A reviewer can open `src/views/contactDetail/` or `src/views/rateCards/` and find the route entry view, local store, local components, and local helpers in one place.
- Shared folders stay honest. `src/components/` contains reusable, prop-driven UI; `src/types/<domain>/` contains reusable API and domain contracts; `src/utils/api.ts` contains transport. Route-only business behavior does not leak into those shared areas.
- Shell-level state has one home. Session, selected organization, selected workspace, permissions, notifications, and global bootstrap state belong under `src/views/application/`, not in route folders and not in a top-level `src/stores/` directory.
- Local development and production use the same frontend ownership model. The backend may serve the built app in production, but Vue route code still goes through the same router, shell store, API client, and route folders.
- The tradeoff is that a large route may contain several files. That is acceptable when those files are all part of the same route workflow and the folder name remains the clear ownership boundary.

## Recommended Shape

### Current Ownership Map

```text
frontend/src/
├── components/
│   ├── forms/              # Shared form field wrappers.
│   ├── layout/             # Shared shell and layout frames.
│   ├── navigation/         # Shared navigation primitives.
│   ├── page/               # Shared page sections, tables, and status states.
│   └── ui/                 # Shared low-level controls and surfaces.
├── router/
│   ├── guestRoutes.ts
│   ├── index.ts
│   ├── routeMeta.d.ts
│   ├── organizationRoutes.ts
│   └── workspaceRoutes.ts
├── types/
│   ├── auth/
│   ├── workspace/
│   ├── contact/
│   ├── catalogEntry/
│   └── pricing/
├── utils/
│   ├── api.ts
│   ├── apiParams.ts
│   ├── errorHandling.ts
│   ├── routeParams.ts
│   └── routeQuery.ts
└── views/
    ├── application/
    ├── contactDetail/
    ├── contacts/
    ├── rateCards/
    └── itemDetail/
```

Do not add a parallel modern architecture beside this map. New route work should not create top-level `src/features/`, `src/services/`, or `src/stores/` directories. If an older area already uses one of those patterns, migrate the touched route toward `src/views/` instead of expanding the older shape.

### Small Route

```text
frontend/src/
├── components/
│   └── page/
├── router/
│   └── index.ts
├── utils/
│   └── api.ts
└── views/
    ├── application/
    │   ├── appShellStore.ts
    │   └── themeStore.ts
    └── login/
        └── LoginView.vue
```

A small route can stay as one `PascalCase` view file when it only renders a focused screen and does not need route-local components, route-local store state, or route-specific helpers.

### Route Folder With Local Pieces

```text
frontend/src/
├── components/
│   ├── page/
│   │   ├── PageHeader.vue
│   │   ├── PageStatusCard.vue
│   │   └── AppTable.vue
│   └── ui/
│       ├── AppButton.vue
│       └── AppDrawer.vue
├── router/
│   ├── index.ts
│   └── organizationRoutes.ts
├── types/
│   ├── contact/
│   │   ├── ContactRequestInterface.ts
│   │   └── ContactInterface.ts
│   └── pricing/
│       ├── RateCardRequestInterface.ts
│       └── RateCardInterface.ts
├── utils/
│   ├── api.ts
│   ├── errorHandling.ts
│   └── routeParams.ts
└── views/
    ├── application/
    │   ├── ApplicationShellView.vue
    │   ├── appShellStore.ts
    │   ├── notificationsStore.ts
    │   ├── permissions.ts
    │   ├── routeAccess.ts
    │   └── themeStore.ts
    ├── contacts/
    │   ├── ContactsView.vue
    │   ├── contactsStore.ts
    │   └── components/
    │       └── ContactTable.vue
    └── contactDetail/
        ├── ContactDetailView.vue
        ├── contactDetailStore.ts
        └── components/
            ├── ContactAddressDialog.vue
            ├── ContactFormSection.vue
            ├── ContactAddressesSection.vue
            └── ContactAddressesTable.vue
```

The route folder owns the route entry view, local store, local sections, dialogs, route-only tables, route-specific composables, and route-specific constants. Shared domain contracts stay under `src/types/<domain>/`, and shared page or UI primitives stay under `src/components/`.

### Larger Specialized Route Folder

```text
frontend/src/views/surveyFormBuilder/
├── SurveyFormBuilderView.vue
├── builderDrag.ts
├── builderInspectorDrafts.ts
├── builderPlacement.ts
├── builderRuntimeAdapter.ts
├── builderTypes.ts
├── surveyFormBuilderGraphState.ts
├── surveyFormBuilderLogicState.ts
├── surveyFormBuilderMappingsState.ts
├── surveyFormBuilderPageNodeState.ts
├── surveyFormBuilderStore.ts
├── surveyFormBuilderVersionState.ts
├── logicMapPresentation.ts
├── useNodeInspectorDrafts.ts
└── components/
    ├── BuilderAIPromptDialog.vue
    ├── BuilderCanvasPane.vue
    ├── BuilderComponentPalette.vue
    ├── BuilderInspectorPane.vue
    └── BuilderVersionToolbar.vue
```

This shape is acceptable for a route that is a real workspace with several coordinated panels and state modules. The boundary is still the route folder. The files are named by responsibility rather than `helpers.ts`, `utils.ts`, or `store.ts`.

### Router Wires Route Folders, Not Workflows

```typescript
// frontend/src/router/organizationRoutes.ts

import { APP_PERMISSIONS } from "@/views/application/permissions";
import type { RouteRecordRaw } from "vue-router";

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
  {
    path: "workspaces/:workspaceId/contacts/:contactId",
    name: "contact-detail",
    component: () => import("@/views/contactDetail/ContactDetailView.vue"),
    meta: {
      requiresAuth: true,
      requiredPermissions: [APP_PERMISSIONS.organizationWorkspacesView],
      title: "Contact Detail",
      globalNavKey: "contacts",
    },
  },
];
```

Router modules should import route metadata, route components, and permission constants. They should not own route fetching, route form state, local table filtering, or business workflows. Put that code in the route folder.

### Route View Reads Like Page Composition

```vue
<!-- frontend/src/views/contactDetail/ContactDetailView.vue -->

<template>
  <div class="space-y-4">
    <AppBreadcrumbs :items="breadcrumbs" />

    <PageHeader
      :eyebrow="pageEyebrow"
      :title="pageTitle"
      :description="pageDescription"
    />

    <PageStatusCard
      v-if="!contactDetailStore.isCreateMode && contactDetailStore.isLoading && !contactDetailStore.contact"
      title="Loading contact"
      description="Preparing this contact record for review"
      show-loading
    />

    <PageStatusCard
      v-else-if="!contactDetailStore.isCreateMode && contactDetailStore.errorMessage && !contactDetailStore.contact"
      title="Unable to load contact"
      :error-message="contactDetailStore.errorMessage"
      :show-retry="true"
      @retry="void contactDetailStore.load()"
    />

    <template v-else>
      <ContactFormSection />
      <ContactAddressesSection v-if="!contactDetailStore.isCreateMode" />
      <ContactEnrollmentHistorySection v-if="!contactDetailStore.isCreateMode" />
      <ContactApprovedPlansSection v-if="!contactDetailStore.isCreateMode" />
    </template>
  </div>
</template>

<script setup lang="ts">
  import AppBreadcrumbs from "@/components/navigation/AppBreadcrumbs.vue";
  import PageHeader from "@/components/page/PageHeader.vue";
  import PageStatusCard from "@/components/page/PageStatusCard.vue";
  import { getRouteNumberParam } from "@/utils/routeParams";
  import ContactFormSection from "@/views/contactDetail/components/ContactFormSection.vue";
  import ContactAddressesSection from "@/views/contactDetail/components/ContactAddressesSection.vue";
  import ContactApprovedPlansSection from "@/views/contactDetail/components/ContactApprovedPlansSection.vue";
  import ContactEnrollmentHistorySection from "@/views/contactDetail/components/ContactEnrollmentHistorySection.vue";
  import { useContactDetailStore } from "@/views/contactDetail/contactDetailStore";
  import { computed, watch } from "vue";
  import { useRoute } from "vue-router";

  const route = useRoute();
  const contactDetailStore = useContactDetailStore();

  const pageEyebrow = computed(() => (contactDetailStore.isCreateMode ? "Create contact" : "Contact detail"));
  const pageTitle = computed(() => contactDetailStore.formValues.email || "Contact detail");
  const pageDescription = computed(() => (
    contactDetailStore.canManage ? "Review and update this contact record" : "Review this contact record"
  ));
  const breadcrumbs = computed(() => [
    { label: "Contacts", to: { name: "contacts-list" } },
    { label: contactDetailStore.isCreateMode ? "Add Contact" : "Contact Detail" },
  ]);

  function syncRouteScope() {
    contactDetailStore.setRouteScope(
      getRouteNumberParam(route, "workspaceId"),
      getRouteNumberParam(route, "contactId"),
      route.name === "contact-create"
    );
  }

  watch(
    [() => route.name, () => route.params.workspaceId, () => route.params.contactId, () => contactDetailStore.organizationId],
    () => {
      syncRouteScope();
      void contactDetailStore.load();
    },
    { immediate: true }
  );
</script>
```

The route view composes shared page wrappers and route-local sections. It wires route params into the route-local store, then lets the store own the route workflow.

### Route-Local Store Owns Route Workflow State

```typescript
// frontend/src/views/contactDetail/contactDetailStore.ts

import { useSchemaValidation } from "@/composables/useSchemaValidation";
import { createDefaultContactInput, contactInputSchema } from "@/types/contact/ContactRequestInterface";
import type { ContactInterface } from "@/types/contact/ContactInterface";
import { api } from "@/utils/api";
import { extractFirstFieldErrors, getFirstApiErrorMessage } from "@/utils/errorHandling";
import { useAppShellStore } from "@/views/application/appShellStore";
import { APP_PERMISSIONS } from "@/views/application/permissions";
import { defineStore } from "pinia";
import { computed, ref } from "vue";

export const useContactDetailStore = defineStore("contactDetail", () => {
  const appShellStore = useAppShellStore();
  const contact = ref<ContactInterface | null>(null);
  const workspaceId = ref<number | null>(null);
  const contactId = ref<number | null>(null);
  const errorMessage = ref("");
  const isLoading = ref(false);
  const { errors: fieldErrors, reset, setErrors, validate, values: formValues } = useSchemaValidation(
    contactInputSchema,
    createDefaultContactInput()
  );

  const organizationId = computed(() => appShellStore.selectedOrganizationId);
  const canManage = computed(() => appShellStore.can(APP_PERMISSIONS.organizationAccessManage, { organizationId: organizationId.value }));

  function setRouteScope(nextWorkspaceId: number | null, nextContactId: number | null) {
    workspaceId.value = nextWorkspaceId;
    contactId.value = nextContactId;
  }

  async function load() {
    const activeOrganizationId = organizationId.value;
    const activeWorkspaceId = workspaceId.value;
    const activeContactId = contactId.value;

    if (!activeOrganizationId || !activeWorkspaceId || !activeContactId) {
      contact.value = null;
      reset();
      return;
    }

    isLoading.value = true;
    errorMessage.value = "";

    try {
      contact.value = await api.contacts.detail(activeOrganizationId, activeWorkspaceId, activeContactId);
    } catch (error) {
      contact.value = null;
      reset();
      errorMessage.value = getFirstApiErrorMessage(error, "Unable to load this contact.");
    } finally {
      isLoading.value = false;
    }
  }

  async function save() {
    if (!canManage.value || !(await validate()) || !organizationId.value || !workspaceId.value || !contactId.value) {
      return false;
    }

    try {
      contact.value = await api.contacts.update(organizationId.value, workspaceId.value, contactId.value, formValues);
      return true;
    } catch (error) {
      setErrors(extractFirstFieldErrors(error));
      errorMessage.value = getFirstApiErrorMessage(error, "Unable to save contact changes.");
      return false;
    }
  }

  return {
    canManage,
    workspaceId,
    contact,
    contactId,
    errorMessage,
    fieldErrors,
    formValues,
    isLoading,
    load,
    save,
    setRouteScope,
    organizationId,
  };
});
```

The store file name is descriptive: `contactDetailStore.ts`, not `store.ts`. It can read shell state, permission helpers, shared validation helpers, shared types, and the canonical API object. It does not create Axios clients, duplicate bootstrap state, or move shell-level state into the route.

### Route-Local Component Can Read Its Colocated Store

```vue
<!-- frontend/src/views/contactDetail/components/ContactFormSection.vue -->

<script setup lang="ts">
  import AppTextField from "@/components/forms/AppTextField.vue";
  import { useContactDetailStore } from "@/views/contactDetail/contactDetailStore";

  const contactDetailStore = useContactDetailStore();
</script>

<template>
  <div class="grid gap-4 md:grid-cols-2">
    <AppTextField
      v-model="contactDetailStore.formValues.firstName"
      label="First name"
      :error="contactDetailStore.fieldErrors.firstName"
      :disabled="!contactDetailStore.canManage"
    />
    <AppTextField
      v-model="contactDetailStore.formValues.lastName"
      label="Last name"
      :error="contactDetailStore.fieldErrors.lastName"
      :disabled="!contactDetailStore.canManage"
    />
  </div>
</template>
```

This is route-local UI, so it can import the route-local store directly when that removes prop drilling. A shared component under `src/components/forms/` or `src/components/page/` should stay prop-driven and store-agnostic.

### Shared Types Stay Under `src/types/<domain>/`

```typescript
// frontend/src/types/contact/ContactInterface.ts

export interface ContactInterface {
  id: number;
  workspace: number;
  email: string;
  firstName: string;
  lastName: string;
  status: string;
  createdTs: string;
  updatedTs: string;
}
```

```typescript
// frontend/src/types/contact/ContactRequestInterface.ts

import { z } from "zod";

export const contactInputSchema = z.object({
  email: z.string().email(),
  firstName: z.string().min(1),
  lastName: z.string().min(1),
  status: z.string(),
});

export type ContactRequestInterface = z.infer<typeof contactInputSchema>;

export function createDefaultContactInput(): ContactRequestInterface {
  return {
    email: "",
    firstName: "",
    lastName: "",
    status: "active",
  };
}
```

Reusable API and form contracts belong in `src/types/<domain>/` because API methods, route stores, dialogs, tests, and future routes may need the same contract. Do not hide shared request or response interfaces inside a route folder just because the first consumer is one route.

### API Methods Stay In The Canonical Client

```typescript
// frontend/src/utils/api.ts

const contacts = {
  detail: (organizationId: number, workspaceId: number, contactId: number) =>
    apiClient.get<ContactInterface>(
      `api/organizations/${organizationId}/workspaces/${workspaceId}/contacts/${contactId}/`
    ),
  update: (organizationId: number, workspaceId: number, contactId: number, payload: ContactRequestInterface) =>
    apiClient.put<ContactInterface, ContactRequestInterface>(
      `api/organizations/${organizationId}/workspaces/${workspaceId}/contacts/${contactId}/`,
      payload
    ),
};

export const api = {
  contacts,
};
```

Route folders should consume `api.contacts.detail(...)` and `api.contacts.update(...)`. They should not create `contactService.ts`, import `axios`, call `fetch(...)`, or configure transport headers.

### Avoid Parallel Top-Level Feature And Service Trees

```text
frontend/src/
├── features/
│   └── contacts/
│       ├── ContactDetailPage.vue
│       ├── contactService.ts
│       └── store.ts
├── services/
│   └── contactService.ts
├── stores/
│   └── contactStore.ts
└── views/
    └── contactDetail/
        └── ContactDetailView.vue
```

Do not add this shape for modern code. It makes ownership ambiguous: router code points at `views/`, workflow state lives in `stores/`, transport lives in `services/`, and route-local UI lives in `features/`. Collapse route-owned pieces into the route folder, keep transport in `src/utils/api.ts`, and keep genuinely shared UI or types in their shared homes.

## Things To Notice

- `src/views/` is the route-based home for page-specific code.
- Small routes can stay as a single view file.
- Larger routes can keep local sections, dialogs, route-only tables, route-specific composables, route-specific constants, and a descriptively named local store beside the route view.
- Route folder names are lower camel case, such as `contactDetail`, `rateCards`, and `surveyFormBuilder`.
- Vue component filenames are PascalCase, such as `ContactDetailView.vue`, `ContactFormSection.vue`, and `RateCardsTable.vue`.
- Store filenames are descriptive lower camel case, such as `contactDetailStore.ts`, `rateCardsStore.ts`, and `appShellStore.ts`; do not name route stores `store.ts`.
- Route-specific composables use the `use` prefix and stay in the route folder when they are not shared, such as `useItemDetailTabs.ts`.
- Shared shell state lives under `src/views/application/` and is read by route stores or route views.
- Shared components under `src/components/` stay prop-driven and do not import route-local stores.
- Shared API and form contracts live under `src/types/<domain>/`.
- The canonical API client lives in `src/utils/api.ts`, and query-param helpers live in `src/utils/`.
- Router modules wire paths, route names, metadata, guards, and component imports. They do not own route workflows.
- Import paths should use `@/views/...`, `@/components/...`, `@/types/...`, and `@/utils/...` instead of deep relative traversal.

## Rules To Follow

- Put modern route entry components under `frontend/src/views/<routeFolder>/<RouteName>View.vue`.
- Keep route-only components under `frontend/src/views/<routeFolder>/components/`.
- Keep route-local Pinia stores in the route folder with descriptive names such as `contactsStore.ts` or `contactDetailStore.ts`.
- Keep shared shell-level stores and shell helpers under `frontend/src/views/application/`.
- Keep shared UI primitives and page-composition components under `frontend/src/components/`, split by responsibility such as `forms/`, `layout/`, `navigation/`, `page/`, and `ui/`.
- Keep reusable API, request, response, enum, and Zod-backed form contracts under `frontend/src/types/<domain>/`.
- Keep the canonical API client and domain API segments in `frontend/src/utils/api.ts`.
- Do not add top-level `frontend/src/features/`, `frontend/src/services/`, or `frontend/src/stores/` for modern route work.
- Do not put route-local business logic in `src/components/`.
- Do not let shared components import route-local stores, route params, or domain API methods.
- Do not create generic `helpers.ts`, `utils.ts`, or `store.ts` files when a more specific filename explains the responsibility.
- Use route-local `constants.ts` only when the constants are a small cohesive set for that route. Prefer a specific name such as `themeEditorSections.ts` or `surveyFormBuilderScopes.ts` when the file owns a distinct concern.
- Do not move a route-specific section into shared `src/components/` until at least two real route folders need the same prop-driven component.
- Do not define shared domain interfaces inside route views, route stores, or route-local components.
- Do not import `axios`, call `fetch(...)`, or configure transport from a route folder; use `api.<domain>.<method>(...)`.
- Do not duplicate shell bootstrap, current user, selected organization, selected workspace, or permission state inside route folders.

## Refactor Signals

- A route folder contains a `store.ts`, `helpers.ts`, or `utils.ts` file whose filename does not reveal its responsibility.
- A route folder's `constants.ts` grows into several unrelated concerns that would be clearer as named files.
- A route has several local components but they are split across `src/features/`, `src/components/`, `src/stores/`, and `src/services/`.
- A shared component under `src/components/` imports `@/views/<route>/...`, a route-local store, route params, or a domain API method.
- A route-local component under `src/views/<route>/components/` has a large prop and emit surface for values that all come from the same route workflow.
- A route view imports many sibling dialogs and tables and passes the same IDs, loading flags, permissions, errors, and callbacks through several layers.
- A route view or route store imports `axios`, `apiClient`, or `fetch(...)` directly.
- A new endpoint family appears in `src/services/` instead of the domain segment in `src/utils/api.ts`.
- A route duplicates app-shell state such as current user, selected organization, selected workspace, permission maps, or bootstrap loading.
- Reusable API contracts are declared inline inside a `.vue` file or route store.
- Route components use long relative imports such as `../../../types/...` instead of `@/...`.
- A route folder grows multiple unrelated workflows that cannot be summarized as one route or workspace. Split the route area or promote truly shared pieces.

## Verification

- Use `rg --files frontend/src/views/<routeFolder>` to confirm the route view, local components, local store, and route-specific helpers are colocated.
- Use `rg --files frontend/src/components frontend/src/types frontend/src/utils frontend/src/router` to confirm shared UI, shared types, transport, and router code stayed in their expected homes.
- Use `rg "from [\"']@/views/.*/.*Store|use[A-Z].*Store" frontend/src/components` when moving components into `src/components/`; shared components should not import route-local stores.
- Use `rg "from [\"']axios|axios\\.|fetch\\(" frontend/src/views frontend/src/components` after route refactors; modern route code should use `api.<domain>.<method>(...)`.
- Use `rg "src/features|src/services|src/stores" frontend/src` when removing legacy architecture or reviewing a new route rollout.
- Run `cd frontend && npm run type-check` after moving route files, route imports, shared types, or API method signatures.
- Run `cd frontend && npm run lint` before finishing frontend code changes.
- For guidance-only edits, check Markdown code fences, run `git diff --check -- agents/guidance/frameworks/vue/examples/vue-route-folder.md`, and rebuild generated guidance with `python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean`.

## Why It Helps

- Route folders become the frontend ownership map. New contributors can find the view, local state, and local UI for a workflow without tracing through several top-level abstractions.
- Shared folders stay smaller and more reusable because they contain code that is actually shared.
- Reviews get easier because file placement reveals intent: page code in `views/`, reusable UI in `components/`, contracts in `types/`, transport in `utils/api.ts`, and shell state in `views/application/`.
- Refactors are safer because route-local changes have a clear boundary and shared contracts remain in predictable places.
- The codebase avoids parallel architectures where old feature, service, and store trees compete with route-based ownership.
