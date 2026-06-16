---
id: framework-vue-example-dialog-form
title: Vue Dialog Form Example
description: Example self-contained dialog pattern for form submission and success handling.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - dialog
  - form
applies_to:
  - vue
status: active
order: 2
---

# Vue Dialog Form Example

## Scenario

Use this pattern when a Vue route needs a focused create or edit form inside an `AppDrawer` or dialog while the parent route keeps the list, detail page, navigation, and route lifecycle context.

Good isolated-dialog triggers include:

- an admin list page opens a create or edit drawer for one small resource
- the dialog submits one request and then asks the parent to reload the list
- no sibling route-local components need the same draft values, field errors, or submit state
- success feedback can be shown through the shared notification system after the mutation succeeds
- the parent only needs a small `save` or `close` signal

Do not use this pattern for larger route workflows where the dialog is only one part of a shared state machine. If the route has sibling sections, a table, filters, selected records, multiple drawers, shared errors, or a reload workflow that several components need, move the form DTO, field errors, open state, and submit action into a route-local feature store.

## Why This Shape Exists

Dialog forms sit at a boundary between page composition and mutation workflow. If the boundary is unclear, route views become callback hubs, dialogs duplicate validation and API handling, and stale field errors leak between create and edit sessions.

This pattern uses three frontend ownership levels:

- The shell store under `frontend/src/views/application/` owns session, organization, workspace, bootstrap, permissions, and notifications.
- Route views under `frontend/src/views/<route>/` own page composition, route params, and simple page-local state.
- Route-local stores under `frontend/src/views/<route>/` own shared route workflows when several local components need the same records, forms, errors, loading flags, or mutation actions.

An isolated dialog may own its own `useSchemaValidation(...)`, `isSubmitting`, `errorMessage`, `api` call, and success notification because those details do not need to be shared. The parent opens the dialog, passes the route-owned scope such as `organizationId`, and reloads after a successful save.

A route-workflow dialog should not own the mutation independently. In that case the route-local store owns the drawer open state, form values, DRF server errors, submit action, reload, and success notification. The dialog renders fields and delegates actions to the store. That keeps sibling sections, tables, filters, and drawers synchronized through one source of truth.

## Recommended Shape

### Isolated Dialog Owns The Form

Use this shape for a focused create or edit drawer like `frontend/src/views/vendors/components/VendorDialog.vue`. The parent page owns list loading and edit selection. The drawer owns the small form workflow.

```vue
<!-- frontend/src/views/vendors/components/VendorDialog.vue -->
<template>
  <AppDrawer
    :open="open"
    size="md"
    :title="dialogTitle"
    :description="dialogDescription"
    close-label="Close vendor drawer"
    @close="emit('close')"
  >
    <div class="space-y-6">
      <AlertBanner
        v-if="errorMessage"
        :message="errorMessage"
        tone="warning"
      />

      <form
        :id="formId"
        class="space-y-4"
        @submit.prevent="void submitForm()"
      >
        <AppTextField
          v-model="formValues.name"
          label="Name"
          :error="validationErrors.name"
          placeholder="Acme Vendor"
        />

        <AppSelectField
          v-model="formValues.status"
          label="Status"
          :error="validationErrors.status"
          :options="statusOptions"
          option-label="label"
          option-value="value"
          placeholder="Select status"
        />

        <AppTextareaField
          v-model="formValues.description"
          label="Description"
          :error="validationErrors.description"
          placeholder="Optional fulfillment notes"
          :rows="4"
        />
      </form>
    </div>

    <template #footer>
      <div class="flex justify-end gap-2">
        <AppButton
          label="Cancel"
          tone="ghost"
          :disabled="isSubmitting"
          @click="emit('close')"
        />
        <AppButton
          button-type="submit"
          :form="formId"
          :label="submitLabel"
          tone="primary"
          :loading="isSubmitting"
        />
      </div>
    </template>
  </AppDrawer>
</template>

<script setup lang="ts">
  import AppSelectField from "@/components/forms/AppSelectField.vue";
  import AppTextField from "@/components/forms/AppTextField.vue";
  import AppTextareaField from "@/components/forms/AppTextareaField.vue";
  import AppDrawer from "@/components/ui/AppDrawer.vue";
  import AlertBanner from "@/components/ui/AlertBanner.vue";
  import AppButton from "@/components/ui/AppButton.vue";
  import { useNotification } from "@/composables/useNotification";
  import { useSchemaValidation } from "@/composables/useSchemaValidation";
  import { createDefaultVendorInput, vendorPartnerInputSchema } from "@/types/partner/VendorInputInterface";
  import type { VendorInterface } from "@/types/partner/VendorInterface";
  import { PartnerStatus } from "@/types/partner/PartnerStatus";
  import { api } from "@/utils/api";
  import { extractFirstFieldErrors, getFirstApiErrorMessage } from "@/utils/errorHandling";
  import { computed, ref, watch } from "vue";

  interface Props {
    open?: boolean;
    vendor?: VendorInterface | null;
    organizationId: number | null;
  }

  const emit = defineEmits<{
    close: [];
    save: [];
  }>();

  const props = withDefaults(defineProps<Props>(), {
    open: false,
    vendor: null,
  });

  const { clearErrors, errors: validationErrors, reset, setErrors, validate, values: formValues } = useSchemaValidation(vendorPartnerInputSchema, createDefaultVendorInput());
  const notification = useNotification();

  const errorMessage = ref("");
  const formId = "vendor-form";
  const isSubmitting = ref(false);

  const dialogTitle = computed(() => (props.vendor ? "Edit vendor" : "Create vendor"));
  const dialogDescription = computed(() => (props.vendor ? "Review and update this organization vendor." : "Add an organization-scoped vendor that catalogEntries can link to."));
  const submitLabel = computed(() => (props.vendor ? "Save changes" : "Create vendor"));

  const statusOptions = [
    { label: "Active", value: PartnerStatus.ACTIVE },
    { label: "Inactive", value: PartnerStatus.INACTIVE },
  ];

  watch(
    () => props.open,
    (isOpen) => {
      if (!isOpen) {
        return;
      }

      if (props.vendor) {
        reset({
          description: props.vendor.description,
          name: props.vendor.name,
          status: props.vendor.status,
        });
      } else {
        reset();
      }

      errorMessage.value = "";
      clearErrors();
    }
  );

  async function submitForm() {
    if (!(await validate())) {
      return;
    }

    if (!props.organizationId) {
      errorMessage.value = "Select an organization before saving a vendor.";
      return;
    }

    isSubmitting.value = true;
    errorMessage.value = "";
    clearErrors();

    try {
      if (props.vendor) {
        await api.vendors.update(props.organizationId, props.vendor.id, formValues);
        notification.success("Vendor updated", "Changes to the vendor were saved.");
      } else {
        await api.vendors.create(props.organizationId, formValues);
        notification.success("Vendor created", "The vendor is ready to link to catalogEntries.");
      }

      emit("save");
    } catch (error) {
      setErrors(extractFirstFieldErrors(error));
      errorMessage.value = getFirstApiErrorMessage(error, props.vendor ? "Unable to save this vendor." : "Unable to create this vendor.");
    } finally {
      isSubmitting.value = false;
    }
  }
</script>
```

### Parent Route Owns Opening, Selection, And Reload

The parent route passes only route-owned context and the selected resource. It does not receive form values from the dialog or forward every field through events.

```vue
<!-- frontend/src/views/vendors/VendorsView.vue -->
<template>
  <VendorTable
    :rows="vendorRows"
    :loading="isLoading"
    :error-message="errorMessage"
    :can-edit="canManage"
    :can-create="canManage"
    @create="openCreateDialog"
    @edit="openEditDialog"
    @retry="void loadVendors()"
  />

  <VendorDialog
    :open="isDialogOpen"
    :organization-id="organizationId"
    :vendor="editingVendor"
    @close="closeDialog"
    @save="void handleSaved()"
  />
</template>

<script setup lang="ts">
  import type { VendorInterface } from "@/types/partner/VendorInterface";
  import { api } from "@/utils/api";
  import { getFirstApiErrorMessage } from "@/utils/errorHandling";
  import { useAppShellStore } from "@/views/application/appShellStore";
  import { APP_PERMISSIONS } from "@/views/application/permissions";
  import VendorDialog from "@/views/vendors/components/VendorDialog.vue";
  import VendorTable from "@/views/vendors/components/VendorTable.vue";
  import { computed, ref } from "vue";

  const appShellStore = useAppShellStore();

  const editingVendor = ref<VendorInterface | null>(null);
  const errorMessage = ref("");
  const isDialogOpen = ref(false);
  const isLoading = ref(false);
  const vendors = ref<VendorInterface[]>([]);

  const organizationId = computed(() => appShellStore.selectedOrganizationId);
  const canManage = computed(() => appShellStore.can(APP_PERMISSIONS.organizationAccessManage, { organizationId: organizationId.value }));

  function closeDialog() {
    editingVendor.value = null;
    isDialogOpen.value = false;
  }

  async function handleSaved() {
    closeDialog();
    await loadVendors();
  }

  function openCreateDialog() {
    if (!canManage.value) {
      return;
    }

    editingVendor.value = null;
    isDialogOpen.value = true;
  }

  function openEditDialog(vendorId: number) {
    if (!canManage.value) {
      return;
    }

    editingVendor.value = vendors.value.find((vendor) => vendor.id === vendorId) ?? null;
    isDialogOpen.value = true;
  }

  async function loadVendors() {
    const activeOrganizationId = organizationId.value;
    errorMessage.value = "";

    if (!activeOrganizationId) {
      vendors.value = [];
      isLoading.value = false;
      return;
    }

    isLoading.value = true;

    try {
      const nextVendors = await api.vendors.list(activeOrganizationId);
      if (organizationId.value !== activeOrganizationId) {
        return;
      }

      vendors.value = nextVendors;
    } catch (error) {
      if (organizationId.value !== activeOrganizationId) {
        return;
      }

      vendors.value = [];
      errorMessage.value = getFirstApiErrorMessage(error, "Unable to load vendors for the selected organization.");
    } finally {
      if (organizationId.value === activeOrganizationId) {
        isLoading.value = false;
      }
    }
  }
</script>
```

### Route-Local Store Owns Shared Drawer Workflows

When the drawer is part of a larger route workflow, move ownership into the route-local store. The drawer renders the form and delegates state changes to the store.

```typescript
// frontend/src/views/rateCards/rateCardsStore.ts
import { useNotification } from "@/composables/useNotification";
import { useSchemaValidation } from "@/composables/useSchemaValidation";
import { createDefaultRateCardInput, rateCardInputSchema } from "@/types/pricing/RateCardRequestInterface";
import { api } from "@/utils/api";
import { extractFirstFieldErrors, getFirstApiErrorMessage } from "@/utils/errorHandling";
import { useAppShellStore } from "@/views/application/appShellStore";
import { APP_PERMISSIONS } from "@/views/application/permissions";
import { defineStore } from "pinia";
import { computed, ref } from "vue";

export const useRateCardsStore = defineStore("rateCards", () => {
  const appShellStore = useAppShellStore();
  const notification = useNotification();
  const { clearErrors, errors: drawerFieldErrors, reset, setErrors, validate, values: drawerFormValues } = useSchemaValidation(rateCardInputSchema, createDefaultRateCardInput());

  const workspaceId = ref<number | null>(null);
  const workspaceFilter = ref<"all" | number>("all");
  const drawerErrorMessage = ref("");
  const drawerOpen = ref(false);
  const isDrawerSubmitting = ref(false);

  const organizationId = computed(() => appShellStore.selectedOrganizationId);
  const selectedWorkspaceId = computed(() => {
    if (workspaceId.value) {
      return workspaceId.value;
    }

    return workspaceFilter.value === "all" ? null : workspaceFilter.value;
  });
  const canManageRateCards = computed(() => {
    if (!selectedWorkspaceId.value) {
      return false;
    }

    return appShellStore.can(APP_PERMISSIONS.workspaceManage, { workspaceId: selectedWorkspaceId.value });
  });

  function openCreateDrawer() {
    reset();
    clearErrors();
    drawerErrorMessage.value = "";
    drawerOpen.value = true;
  }

  function closeDrawer() {
    drawerOpen.value = false;
  }

  function setDrawerFormValues(nextValues: Partial<typeof drawerFormValues>) {
    reset(nextValues);
  }

  async function submitDrawer() {
    if (!(await validate())) {
      return false;
    }

    const activeOrganizationId = organizationId.value;
    const activeWorkspaceId = selectedWorkspaceId.value;
    if (!activeOrganizationId || !activeWorkspaceId) {
      drawerErrorMessage.value = "Select an organization and workspace before saving this rate card.";
      return false;
    }

    if (!canManageRateCards.value) {
      drawerErrorMessage.value = "You do not have permission to manage rate cards for this workspace.";
      return false;
    }

    isDrawerSubmitting.value = true;
    drawerErrorMessage.value = "";
    clearErrors();

    try {
      await api.rateCards.create(activeOrganizationId, activeWorkspaceId, drawerFormValues);
      notification.success("Rate card created", "The rate card is ready to use.");
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

  async function load() {
    // The same route-local store owns table/list reload state.
  }

  return {
    closeDrawer,
    drawerErrorMessage,
    drawerFieldErrors,
    drawerFormValues,
    drawerOpen,
    isDrawerSubmitting,
    openCreateDrawer,
    setDrawerFormValues,
    submitDrawer,
  };
});
```

The drawer stays small because the route-local store owns the workflow.

```vue
<!-- frontend/src/views/rateCards/components/RateCardDrawer.vue -->
<template>
  <AppDrawer
    :open="rateCardsStore.drawerOpen"
    size="md"
    title="Create rate card"
    description="Add a new workspace-scoped rate card."
    close-label="Close rate card drawer"
    @close="rateCardsStore.closeDrawer()"
  >
    <div class="space-y-6">
      <AlertBanner
        v-if="rateCardsStore.drawerErrorMessage"
        :message="rateCardsStore.drawerErrorMessage"
        tone="warning"
      />

      <form
        :id="formId"
        class="space-y-4"
        @submit.prevent="void submitForm()"
      >
        <RateCardFormFields
          :model-value="rateCardsStore.drawerFormValues"
          :errors="rateCardsStore.drawerFieldErrors"
          @update:model-value="rateCardsStore.setDrawerFormValues($event)"
        />
      </form>
    </div>

    <template #footer>
      <div class="flex justify-end gap-2">
        <AppButton
          label="Cancel"
          tone="ghost"
          :disabled="rateCardsStore.isDrawerSubmitting"
          @click="rateCardsStore.closeDrawer()"
        />
        <AppButton
          button-type="submit"
          :form="formId"
          label="Create rate card"
          tone="primary"
          :loading="rateCardsStore.isDrawerSubmitting"
        />
      </div>
    </template>
  </AppDrawer>
</template>

<script setup lang="ts">
  import AppDrawer from "@/components/ui/AppDrawer.vue";
  import AlertBanner from "@/components/ui/AlertBanner.vue";
  import AppButton from "@/components/ui/AppButton.vue";
  import RateCardFormFields from "@/views/rateCards/components/RateCardFormFields.vue";
  import { useRateCardsStore } from "@/views/rateCards/rateCardsStore";

  const formId = "rate-card-form";
  const rateCardsStore = useRateCardsStore();

  async function submitForm() {
    await rateCardsStore.submitDrawer();
  }
</script>
```

## Things To Notice

- The isolated dialog receives `open`, the edit record, and route-owned scope such as `organizationId` through props.
- The isolated dialog resets form values and clears stale errors every time it opens.
- The submit flow validates client-side first, then checks required route scope, then sets submit state, clears stale server errors, and calls the canonical `api` object.
- DRF field errors go through `extractFirstFieldErrors(error)` and `setErrors(...)`; the form-level banner uses `getFirstApiErrorMessage(...)` with a clear fallback.
- Success feedback goes through `useNotification()` instead of a view-local toast implementation.
- The parent receives a minimal `save` event and reloads its list. It does not receive the whole saved record unless the parent truly needs it.
- The route-local store version moves drawer state, form DTO, field errors, submit state, notification, and reload into one route-owned workflow.
- Shared components such as `AppDrawer`, `AlertBanner`, `AppButton`, `AppTextField`, `AppSelectField`, and field-group components keep dialog markup consistent.
- Cancel and close actions do not manually clear every field when the dialog is closing. Reset happens on the next open so stale state is not visible to the user.

## Rules To Follow

- Use `AppDrawer` or the existing shared dialog wrapper for modal form surfaces. Do not build new modal chrome in route-local components.
- Use shared form wrappers from `frontend/src/components/forms/` and shared UI controls from `frontend/src/components/ui/`.
- Keep the canonical API path: dialogs and stores call `api.<domain>...`; they do not import `axios`, use `fetch`, or create an `apiService`.
- Use request DTOs and schemas from `frontend/src/types/<domain>/...RequestInterface.ts` or the existing input-contract file for that domain.
- Use `useSchemaValidation(...)` for client validation when the form has a schema. Do not duplicate the same field validation in the component.
- Clear stale field errors and the form-level error before each submit attempt.
- Reset create and edit form values when the dialog opens so old edit values never appear in a new create session.
- Keep emits minimal. Prefer `close` and `save`; avoid emitting every field, server error, loading flag, or the same domain object the parent can reload.
- Disable or show loading on submit controls while `isSubmitting` is true. Do not allow double submits.
- Use `extractFirstFieldErrors(...)` and `getFirstApiErrorMessage(...)` for DRF server errors. Do not parse `error.response.data` in dialogs.
- Use `useNotification().success(...)` for successful mutations that need global feedback.
- Check required route-owned scope such as `organizationId`, `workspaceId`, and permission-derived `canManage` before submitting.
- If three or more route-local components need the same form state, selected record, field errors, loading flag, or reload action, move the workflow into a route-local store.
- Keep shared `src/components/` primitives store-agnostic. A shared dialog shell should not import a route-local store or domain API.

## Refactor Signals

Move an existing dialog toward the isolated-dialog shape when:

- the parent route forwards many field-level props and callbacks that only the dialog uses
- the dialog has stale validation messages after closing and reopening
- every submit handler locally parses `AxiosError` or inspects `error.response.data.errors`
- the submit button can be clicked repeatedly while a request is pending
- success feedback is implemented with one-off local banners instead of shared notifications
- create and edit sessions share accidental state because the form is not reset on open

Move an existing dialog into a route-local feature store when:

- the parent route, table, detail section, and dialog all need the same selected record or reload state
- sibling drawers repeat nearly identical submit, error, notification, and reload logic
- the route view mostly exists to pass `organizationId`, `workspaceId`, errors, rows, submit flags, and callbacks through child layers
- a mutation should update several route-local sections after saving
- the dialog needs route query state, filters, selected tab, or permission-derived actions from the same workflow
- multiple local components need to know whether the drawer is open or submitting

## Verification

For guidance-only changes, verify the generated agent output:

```bash
python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean
```

For code changes that add or refactor dialog forms, run the relevant frontend checks:

```bash
cd frontend
npm run type-check
npm run lint
```

Use focused structural checks during review:

```bash
rg -n "axios|fetch|apiService|error\\.response" frontend/src/views
rg -n "defineEmits|isSubmitting|useSchemaValidation|extractFirstFieldErrors" frontend/src/views/<route>
rg -n "AppDrawer|AppButton|AlertBanner" frontend/src/views/<route>
```

When behavior changes, add or update component tests if the route area already has tests for forms, drawers, or stores. Cover at least:

- opening create mode resets defaults and clears errors
- opening edit mode maps the selected record into form values
- client validation blocks submit before the API call
- server field errors render on the correct shared field wrappers
- successful submit emits `save` or closes the store-owned drawer and reloads the route data
- double-submit protection disables or loads the submit button while the request is pending

## Why It Helps

- Parent route views stay readable because they compose pages, open dialogs, and reload data instead of owning every form detail.
- Isolated dialogs stay self-contained when the workflow is truly small.
- Larger route workflows have one source of truth for drawer state, form values, validation, mutation, notification, and reload behavior.
- Users get consistent loading, field errors, warning banners, and success notifications.
- Reviews become easier because ownership boundaries are visible: shell context comes from the shell store, transport goes through `api`, validation goes through `useSchemaValidation(...)`, and DRF errors go through shared helpers.
