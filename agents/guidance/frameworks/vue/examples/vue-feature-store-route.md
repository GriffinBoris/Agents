---
id: framework-vue-example-feature-store-route
title: Vue Feature Store Route Example
description: Example route-local Pinia store that owns shared business state while the route view and local components stay UI-focused.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - stores
  - route
applies_to:
  - vue
status: active
order: 6
---

# Vue Feature Store Route Example

## Scenario

Use this pattern when a route folder has enough shared workflow state that the page, local sections, dialogs, tables, and mutations should read from one route-local source of truth.

Good triggers include:

- three or more route-local components share the same record, loading state, selected row, form DTO, field errors, or mutation workflow
- the route view passes the same organization, workspace, record id, permission flag, loading flag, error message, and reload callback through several child layers
- a route-local dialog owns API calls and submit state while the parent route also owns related selection, reload, or error state
- a detail page has sibling sections such as profile fields, addresses, access management, related records, and dialogs that all operate on the same route scope
- a list page has route query state, loading state, drawer form state, and table rows that must stay synchronized across the page

Do not create a route-local store by default for every route. Simple pages can keep direct `ref`, `computed`, and `load...()` helpers in the route view when the state is not shared with sibling route-local components. Current direct-state routes are intentionally covered by `frontend/tests/feature-store-route-guidance.test.ts` so deleted legacy stores are not recreated just for symmetry.

## Why This Shape Exists

Route-local stores give route workflows one clear owner without turning shell state into a giant app store.

The repository has three separate frontend state boundaries:

- `frontend/src/views/application/appShellStore.ts` owns cross-route session, organization, workspace, bootstrap, and permission context.
- Route-local stores under `frontend/src/views/<route>/` own business state for that route folder, such as records, rows, loading flags, dialog state, form DTOs, field errors, mutations, and route-scope synchronization.
- Shared components under `frontend/src/components/` stay prop-driven and store-agnostic so they can be reused by unrelated routes.

Without that split, route views become manual dependency-injection hubs. They pass the same ids, flags, records, errors, and callbacks through multiple local components. The real state machine gets scattered across a route view, several sections, and one or more dialogs, which makes reviews and refactors harder.

The route-local store accepts a small amount of indirection to make ownership obvious. New sibling sections can consume the same store directly, mutation workflows reload through one action, permissions derive from the shell store in one place, and stale async responses can be ignored before they overwrite newer organization, workspace, or route state.

## Recommended Shape

### Route Folder

Name the store after the route or workflow. Do not use a generic `store.ts` filename.

```text
frontend/src/views/
└── contactDetail/
    ├── ContactDetailView.vue
    ├── contactDetailStore.ts
    └── components/
        ├── ContactFormSection.vue
        ├── ContactAddressesSection.vue
        ├── ContactAddressesTable.vue
        └── ContactAddressDialog.vue
```

The route folder owns the route entry view, the route-local store, and route-specific sections or dialogs. Shared table wrappers, inputs, buttons, page sections, alerts, and shell primitives stay under `frontend/src/components/`.

### Route-Local Store Owns The Workflow

This is the shape used by `frontend/src/views/contactDetail/contactDetailStore.ts`: shell context is read from `useAppShellStore()`, route scope is set by the route view, API calls go through `api`, form state comes from `useSchemaValidation(...)`, DRF field errors are parsed by shared helpers, and late responses are ignored when scope changes.

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
  const isLoading = ref(false);
  const isSaving = ref(false);
  const errorMessage = ref("");
  const {
    clearErrors,
    errors: fieldErrors,
    reset: resetFormValues,
    setErrors,
    validate,
    values: formValues,
  } = useSchemaValidation(contactInputSchema, createDefaultContactInput());

  const workspaceId = ref<number | null>(null);
  const contactId = ref<number | null>(null);
  const isCreateRoute = ref(false);
  const organizationId = computed(() => appShellStore.selectedOrganizationId);
  const isCreateMode = computed(() => isCreateRoute.value || contactId.value === null);
  const canManage = computed(() => {
    return appShellStore.can(APP_PERMISSIONS.organizationAccessManage, { organizationId: organizationId.value });
  });

  function setRouteScope(nextWorkspaceId: number | null, nextContactId: number | null, nextIsCreateRoute: boolean) {
    workspaceId.value = nextWorkspaceId;
    contactId.value = nextContactId;
    isCreateRoute.value = nextIsCreateRoute;
  }

  function applyContact(nextContact: ContactInterface) {
    contact.value = nextContact;
    resetFormValues({
      biologicalSex: nextContact.biologicalSex,
      dateOfBirth: nextContact.dateOfBirth,
      email: nextContact.email,
      firstName: nextContact.firstName,
      genderIdentity: nextContact.genderIdentity,
      heightInches: nextContact.heightInches,
      insuranceMemberId: nextContact.insuranceMemberId,
      insuranceProvider: nextContact.insuranceProvider,
      lastName: nextContact.lastName,
      phone: nextContact.phone,
      status: nextContact.status,
      weightPounds: nextContact.weightPounds,
    });
  }

  async function load() {
    clearErrors();
    errorMessage.value = "";

    const activeOrganizationId = organizationId.value;
    const activeWorkspaceId = workspaceId.value;
    const activeContactId = contactId.value;
    const activeIsCreateMode = isCreateMode.value;

    if (activeIsCreateMode) {
      contact.value = null;
      isLoading.value = false;
      resetFormValues();
      return;
    }

    if (!activeOrganizationId || !activeWorkspaceId || !activeContactId) {
      contact.value = null;
      resetFormValues();
      errorMessage.value = "Select a workspace before opening a contact record.";
      return;
    }

    isLoading.value = true;

    try {
      const nextContact = await api.contacts.detail(activeOrganizationId, activeWorkspaceId, activeContactId);
      if (organizationId.value !== activeOrganizationId || workspaceId.value !== activeWorkspaceId || contactId.value !== activeContactId || isCreateMode.value !== activeIsCreateMode) {
        return;
      }

      applyContact(nextContact);
    } catch (error) {
      if (organizationId.value !== activeOrganizationId || workspaceId.value !== activeWorkspaceId || contactId.value !== activeContactId || isCreateMode.value !== activeIsCreateMode) {
        return;
      }

      contact.value = null;
      resetFormValues();
      errorMessage.value = getFirstApiErrorMessage(error, "Unable to load this contact.");
    } finally {
      if (organizationId.value === activeOrganizationId && workspaceId.value === activeWorkspaceId && contactId.value === activeContactId && isCreateMode.value === activeIsCreateMode) {
        isLoading.value = false;
      }
    }
  }

  async function save() {
    if (!organizationId.value || !workspaceId.value) {
      errorMessage.value = "Select a workspace before saving contact changes.";
      return false;
    }

    if (!canManage.value) {
      errorMessage.value = "You do not have permission to manage contact records for this organization.";
      return false;
    }

    if (!(await validate())) {
      return false;
    }

    isSaving.value = true;
    errorMessage.value = "";

    try {
      const savedContact = isCreateMode.value
        ? await api.contacts.create(organizationId.value, workspaceId.value, formValues)
        : await api.contacts.update(organizationId.value, workspaceId.value, contactId.value as number, formValues);

      applyContact(savedContact);
      contactId.value = savedContact.id;
      return true;
    } catch (error) {
      setErrors(extractFirstFieldErrors(error));
      errorMessage.value = getFirstApiErrorMessage(error, isCreateMode.value ? "Unable to create this contact." : "Unable to save contact changes.");
      return false;
    } finally {
      isSaving.value = false;
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
    isCreateMode,
    isLoading,
    isSaving,
    load,
    save,
    setRouteScope,
    organizationId,
  };
});
```

The store can also own shared dialog workflows. In the current contact detail route, address dialog state, address form values, address field errors, submit loading, and `saveAddress()` belong in the same store because the address section and dialog are part of the same route workflow.

### Route View Wires Route Scope And Composes Sections

The route view should read like a page outline. It can parse route params, call `setRouteScope(...)`, trigger loading, handle navigation after create, and render blocking status states. It should not mirror every form field or route-local dialog callback.

```vue
<!-- frontend/src/views/contactDetail/ContactDetailView.vue -->
<script setup lang="ts">
  import PageStatusCard from "@/components/page/PageStatusCard.vue";
  import AppButton from "@/components/ui/AppButton.vue";
  import { getRouteNumberParam } from "@/utils/routeParams";
  import ContactFormSection from "@/views/contactDetail/components/ContactFormSection.vue";
  import ContactAddressesSection from "@/views/contactDetail/components/ContactAddressesSection.vue";
  import { useContactDetailStore } from "@/views/contactDetail/contactDetailStore";
  import { computed, watch } from "vue";
  import { useRoute, useRouter } from "vue-router";

  const route = useRoute();
  const router = useRouter();
  const contactDetailStore = useContactDetailStore();

  const submitLabel = computed(() => (contactDetailStore.isCreateMode ? "Create contact" : "Save changes"));

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

  async function submitForm() {
    const shouldRedirectToDetail = route.name === "contact-create";
    const hasSaved = await contactDetailStore.save();
    if (hasSaved && shouldRedirectToDetail && contactDetailStore.contactId) {
      await router.replace({
        name: "contact-detail",
        params: {
          workspaceId: contactDetailStore.workspaceId,
          contactId: contactDetailStore.contactId,
        },
      });
    }
  }
</script>

<template>
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

    <AppButton
      :label="submitLabel"
      :disabled="!contactDetailStore.canManage || contactDetailStore.isSaving || contactDetailStore.isLoading || !contactDetailStore.organizationId"
      @click="void submitForm()"
    />
  </template>
</template>
```

### Route-Local Components Can Import The Colocated Store

A route-local section under `frontend/src/views/<route>/components/` can import the route-local store directly when doing so removes prop drilling and keeps the component API smaller.

```vue
<!-- frontend/src/views/contactDetail/components/ContactFormSection.vue -->
<script setup lang="ts">
  import AppTextField from "@/components/forms/AppTextField.vue";
  import { useContactDetailStore } from "@/views/contactDetail/contactDetailStore";

  const contactDetailStore = useContactDetailStore();
</script>

<template>
  <AppTextField
    v-model="contactDetailStore.formValues.firstName"
    label="First name"
    :disabled="!contactDetailStore.canManage"
    :error="contactDetailStore.fieldErrors.firstName"
  />

  <AppTextField
    v-model="contactDetailStore.formValues.lastName"
    label="Last name"
    :disabled="!contactDetailStore.canManage"
    :error="contactDetailStore.fieldErrors.lastName"
  />
</template>
```

This is not a license for shared components to import route stores. Store-aware components should be route-local.

### Store-Aware Sections Can Shape View Models

Keep table wrappers and low-level components prop-driven. Put route-specific row shaping in a route-local section or the store.

```vue
<!-- frontend/src/views/contactDetail/components/ContactAddressesSection.vue -->
<script setup lang="ts">
  import ContactAddressDialog from "@/views/contactDetail/components/ContactAddressDialog.vue";
  import ContactAddressesTable, { type ContactAddressesTableRow } from "@/views/contactDetail/components/ContactAddressesTable.vue";
  import { useContactDetailStore } from "@/views/contactDetail/contactDetailStore";
  import { computed } from "vue";

  const contactDetailStore = useContactDetailStore();

  const addressRows = computed<ContactAddressesTableRow[]>(() => {
    return (contactDetailStore.contact?.addresses ?? []).map((address) => ({
      addressLineOne: address.addressLineOne,
      addressLineTwo: `${address.city}, ${address.state} ${address.postalCode}`.trim(),
      defaultLabel: address.isDefault ? "Default" : "Optional",
      defaultTone: address.isDefault ? "success" : "neutral",
      fullName: address.fullName || "No name",
      id: address.id,
      phoneLabel: address.phone || "No phone",
      typeLabel: address.addressType,
      updatedLabel: address.updatedTs,
    }));
  });
</script>

<template>
  <ContactAddressesTable
    :rows="addressRows"
    :loading="contactDetailStore.isLoading"
    :can-manage="contactDetailStore.canManage"
    @create="contactDetailStore.openCreateAddressDialog()"
    @edit="contactDetailStore.openEditAddressDialogById($event)"
  />

  <ContactAddressDialog />
</template>
```

### Shared Components Stay Store-Agnostic

Shared or reusable table components should receive rows, loading flags, error messages, permissions, and events as props and emits. They should not import `useContactDetailStore()`, `useRateCardsStore()`, or any other route-local store.

```vue
<!-- frontend/src/views/contactDetail/components/ContactAddressesTable.vue -->
<script setup lang="ts">
  export interface ContactAddressesTableRow {
    addressLineOne: string;
    addressLineTwo: string;
    defaultLabel: string;
    defaultTone: "neutral" | "success";
    fullName: string;
    id: number;
    phoneLabel: string;
    typeLabel: string;
    updatedLabel: string;
  }

  interface Props {
    canManage?: boolean;
    loading?: boolean;
    rows: ContactAddressesTableRow[];
  }

  const emit = defineEmits<{
    create: [];
    edit: [addressId: number];
  }>();

  withDefaults(defineProps<Props>(), {
    canManage: false,
    loading: false,
  });
</script>
```

This table is route-local but presentational. The same rule applies even more strongly to shared components under `frontend/src/components/`.

### List Routes Can Share Query, Drawer, And Table State

List routes also benefit from route-local stores when filters, table rows, drawer state, form validation, and mutations are shared. `frontend/src/views/rateCards/rateCardsStore.ts` is the current model.

```typescript
// frontend/src/views/rateCards/rateCardsStore.ts
export const useRateCardsStore = defineStore("rateCards", () => {
  const appShellStore = useAppShellStore();
  const { clearErrors, errors: drawerFieldErrors, reset, setErrors, validate, values: drawerFormValues } = useSchemaValidation(
    rateCardInputSchema,
    createDefaultRateCardInput()
  );

  const workspaceId = ref<number | null>(null);
  const workspaceFilter = ref<"all" | number>("all");
  const drawerErrorMessage = ref("");
  const drawerOpen = ref(false);
  const errorMessage = ref("");
  const isDrawerSubmitting = ref(false);
  const isLoading = ref(false);
  const rateCards = ref<RateCardInterface[]>([]);
  let loadRateCardsRequestId = 0;

  const organizationId = computed(() => appShellStore.selectedOrganizationId);
  const selectedWorkspaceId = computed(() => workspaceId.value ?? (workspaceFilter.value === "all" ? null : workspaceFilter.value));
  const canManageRateCards = computed(() => {
    return Boolean(selectedWorkspaceId.value) && appShellStore.can(APP_PERMISSIONS.workspaceManage, { workspaceId: selectedWorkspaceId.value });
  });

  const rateCardRows = computed<RateCardsTableRow[]>(() => {
    return rateCards.value.map((profile) => ({
      description: profile.description,
      id: profile.id,
      linkedPlanCountLabel: String(profile.linkedPlanCount),
      linkedCatalogEntryCountLabel: String(profile.linkedCatalogEntryCount),
      primaryLabel: profile.name,
      secondaryLabel: `${profile.linkedCatalogEntryCount} catalogEntries linked`,
      statusLabel: formatEnumLabel(profile.status),
      statusTone: profile.status === RateCardStatus.ACTIVE ? "success" : "neutral",
      updatedLabel: formatDate(profile.updatedTs),
    }));
  });

  async function load() {
    const requestId = ++loadRateCardsRequestId;
    errorMessage.value = "";

    const activeOrganizationId = organizationId.value;
    const activeWorkspaceId = selectedWorkspaceId.value;
    if (!activeOrganizationId || !activeWorkspaceId) {
      isLoading.value = false;
      rateCards.value = [];
      errorMessage.value = !activeOrganizationId ? "Select an organization before viewing rate cards." : "Select a workspace before viewing rate cards.";
      return;
    }

    isLoading.value = true;

    try {
      const nextProfiles = await api.rateCards.list(activeOrganizationId, activeWorkspaceId);
      if (requestId !== loadRateCardsRequestId) {
        return;
      }

      rateCards.value = nextProfiles;
    } catch (error) {
      if (requestId !== loadRateCardsRequestId) {
        return;
      }

      rateCards.value = [];
      errorMessage.value = getFirstApiErrorMessage(error, "Unable to load rate cards for this workspace.");
    } finally {
      if (requestId === loadRateCardsRequestId) {
        isLoading.value = false;
      }
    }
  }

  async function submitDrawer() {
    if (!(await validate())) {
      return false;
    }

    if (!organizationId.value || !selectedWorkspaceId.value) {
      drawerErrorMessage.value = "Select an organization and workspace before saving this rate card.";
      return false;
    }

    isDrawerSubmitting.value = true;
    drawerErrorMessage.value = "";
    clearErrors();

    try {
      await api.rateCards.create(organizationId.value, selectedWorkspaceId.value, drawerFormValues);
      drawerOpen.value = false;
      await load();
      return true;
    } catch (error) {
      setErrors(extractFirstFieldErrors(error));
      drawerErrorMessage.value = getFirstApiErrorMessage(error, "Unable to create this rate card.");
      return false;
    } finally {
      isDrawerSubmitting.value = false;
    }
  }

  return {
    canManageRateCards,
    workspaceFilter,
    drawerErrorMessage,
    drawerFieldErrors,
    drawerFormValues,
    drawerOpen,
    errorMessage,
    isDrawerSubmitting,
    isLoading,
    load,
    rateCardRows,
    submitDrawer,
    organizationId,
  };
});
```

### Avoid Prop-Drilled Route Workflows

This is a route-local workflow pretending to be a reusable component API:

```vue
<ContactFormSection
  :first-name="formValues.firstName"
  :last-name="formValues.lastName"
  :email="formValues.email"
  :phone="formValues.phone"
  :errors="fieldErrors"
  :error-message="errorMessage"
  :is-loading="isLoading"
  :is-read-only="!canManage"
  @update:first-name="formValues.firstName = $event"
  @update:last-name="formValues.lastName = $event"
  @update:email="formValues.email = $event"
  @update:phone="formValues.phone = $event"
/>
```

Prefer the route-local section importing the colocated store directly:

```vue
<ContactFormSection />
```

Then inside `ContactFormSection.vue`, bind fields to `contactDetailStore.formValues` and `contactDetailStore.fieldErrors`.

## Things To Notice

- The shell store is read by the route-local store; route-local stores do not call the bootstrap endpoint.
- Permissions derive from `appShellStore.can(...)` in the route-local store so route sections and dialogs share the same action availability.
- Route params are parsed in the route view with `getRouteNumberParam(...)` and passed into the store through a small `setRouteScope(...)` action.
- The route view triggers loading and handles navigation, but the store owns loaded records, form DTOs, field errors, mutation flags, dialog state, and reloads.
- API calls go through the canonical `api` object from `frontend/src/utils/api.ts`.
- Standardized DRF errors are mapped through `extractFirstFieldErrors(...)` and `getFirstApiErrorMessage(...)`; stores and components do not parse Axios errors directly.
- Fetch actions capture organization, workspace, route id, create mode, or request id before awaiting and ignore late responses when the active scope has changed.
- Store-aware components live under the route folder. Shared components under `frontend/src/components/` remain prop-driven.
- Presentational route-local tables can stay prop-driven when their job is only to render rows and emit row actions.
- A route-local store is a tool for real shared workflow state, not a blanket replacement for simple route-local refs.

## Rules To Follow

- Keep shared shell-level stores under `frontend/src/views/application/`.
- Keep route-only stores under the owning route folder in `frontend/src/views/<route>/`.
- Name route-local stores descriptively, such as `contactDetailStore.ts`, `workspaceDetailStore.ts`, or `rateCardsStore.ts`; do not name them `store.ts`.
- Use a route-local store when multiple route-local sections, drawers, dialogs, or tables share the same route workflow state.
- Do not recreate deleted legacy stores for simple pages that are clearer with direct view-local state.
- Let route views compose page sections, parse route params, synchronize query state, trigger store loads, and handle navigation.
- Let route-local stores own records, rows, form DTOs, validation errors, loading flags, mutation flags, dialog state, permission-derived booleans, API calls, reloads, and stale-response guards.
- Let route-local components import their colocated route store when that removes prop drilling.
- Keep shared components in `frontend/src/components/` store-agnostic, prop-driven, and free of route params, API calls, and route-local store imports.
- Keep presentational tables and cards prop-driven even inside route folders when they only render rows and emit row actions.
- Use `useAppShellStore()` for organization, workspace, current user, and permission context; do not duplicate shell bootstrap state in route-local stores.
- Use `api` from `frontend/src/utils/api.ts`; do not import Axios or direct `fetch` in route views, route-local stores, or route-local components.
- Use shared loading and error UI such as `PageStatusCard`, `AppTable`, and `EntityIndexTable` instead of rebuilding spinners and retry panels locally.
- Use `useSchemaValidation(...)` and shared error helpers for form validation and server-side field errors when the form workflow is shared across route-local sections or dialogs.
- Guard required route ids before making API calls and return early with a clear route-level error message when the route cannot load.
- After a successful create from a create route, replace the route with the created record's detail route so the URL matches store state.
- Access store state and actions directly on the store object in components instead of destructuring them.

## Refactor Signals

- A route view imports many local sections and also passes the same ids, rows, loading flags, errors, permissions, and callbacks into each section.
- A route-local form section has many `update:*` emits for fields that belong to one DTO.
- A route-local dialog owns its own API call and field errors while sibling sections also need to reload or react to the same mutation.
- A parent route reads like event wiring instead of page composition.
- A route-local component accepts `organizationId`, `workspaceId`, `recordId`, `canManage`, `isLoading`, `errorMessage`, `selectedRecord`, `open`, `onReload`, and `onSave` from the same parent.
- Several sibling components calculate the same permission or selected organization/workspace state.
- A route keeps duplicate `isLoading`, `isSaving`, `errorMessage`, or field-error refs in both parent and child components for the same workflow.
- A shared component under `frontend/src/components/` imports a route-local store or calls the API directly.
- A route-local store starts owning shell bootstrap, global navigation, theme, organization selection UI, or cross-route session state.
- A store has grown to unrelated workflows that do not share route scope; split the route or extract a narrower store.
- A route-local table imports the store even though it only needs rows, loading, and row-action emits.

## Verification

For guidance-only edits, verify the authored Markdown and generated guidance output:

```bash
rg -c '^```' agents/guidance/frameworks/vue/examples/vue-feature-store-route.md
git diff --check -- agents/guidance/frameworks/vue/examples/vue-feature-store-route.md
python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean
```

For frontend implementation changes that follow this pattern, run the relevant frontend checks:

```bash
cd frontend
npm run type-check
npm run lint
node --test tests/feature-store-route-guidance.test.ts
```

Add or update focused tests when the route-store boundary changes. At minimum, tests should prove:

- the route folder still has the intended colocated store when the store simplifies sibling coordination
- route-local components that should consume the store directly do so
- shared components remain prop-driven and store-agnostic
- deleted legacy route stores stay deleted when direct state is now the clearer shape
- permissions, loading states, error states, and stale-response guards still match the route workflow

Use existing E2E coverage for high-value user paths, such as contact detail, workspace access, organization access, rate cards, leads, and survey builder workflows, when a refactor changes behavior rather than only moving state.

## Why It Helps

This pattern keeps ownership reviewable. The shell store owns cross-route context, the route-local store owns the route workflow, route views read like page outlines, route-local components can be store-aware when that removes prop drilling, and shared components stay reusable.

The result is easier refactoring: forms, dialogs, tables, permissions, loading state, standardized errors, and reload behavior move together instead of being split across several prop chains. It also keeps organization and workspace scoping safer because API calls and stale-response guards are centralized at the route workflow boundary.
