---
id: framework-vue-example-form-validation
title: Vue Form Validation Example
description: Example form flow that keeps Zod request validation, frontend field state, and DRF server errors aligned.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - forms
  - validation
applies_to:
  - vue
status: active
order: 7
---

# Vue Form Validation Example

## Scenario

Use this pattern when a Vue route view, route-local store, dialog, drawer, or form component submits user-entered data to the Django API.

Good triggers include:

- a create or edit form needs client-side validation before calling the API
- a backend serializer can return field-level DRF standardized errors after submit
- a form uses a request DTO that differs from the persisted resource interface
- a dialog or route store needs to reset stale field errors when the edited record changes
- a dependent select, such as item -> item variant, must clear a child field when the parent changes
- a form should show field errors beside inputs and a general form-level failure above the form

Do not use persisted API output interfaces as editable form state. Request DTOs, schemas, defaults, and validation should describe what the frontend can actually submit.

## Why This Shape Exists

The repository has three separate validation boundaries:

- Zod request schemas catch obvious client-side field problems before the browser sends a mutating request.
- Django serializers and views remain authoritative for ownership, uniqueness, cross-field rules, permissions, and organization or workspace scoping.
- Shared frontend error helpers translate DRF standardized errors into form field errors and form-level messages.

Keeping those boundaries separate prevents two common failures. The first is a form that only validates locally and then loses backend serializer errors in a toast. The second is a form that depends only on backend errors, forcing avoidable requests and giving users slower feedback for basic required fields.

This pattern keeps frontend state in camelCase while the backend keeps Django-native snake_case. The canonical API client converts request bodies and response objects at the transport boundary, and `errorHandling.ts` normalizes DRF error `attr` strings. Components and stores should never manually convert field names or parse raw Axios responses.

The standard shape accepts a little ceremony up front: a request type file contains the schema and default helper, the form uses one validation composable, submit code clears stale errors before each request, and server errors flow through shared helpers. In exchange, reviews can check one consistent contract for every form.

## Recommended Shape

### Request DTO, Schema, And Defaults

Colocate the Zod schema, inferred request type, and default helper in the request type file under `frontend/src/types/<domain>/`.

```typescript
// frontend/src/types/pricing/RateCardRequestInterface.ts
import { z } from "zod";

import { RateCardStatus } from "./RateCardInterface";

export const rateCardInputSchema = z.object({
  description: z.string(),
  name: z.string().min(1, "Rate card name is required"),
  status: z.nativeEnum(RateCardStatus),
});

export type RateCardRequestInterface = z.infer<typeof rateCardInputSchema>;

export function createDefaultRateCardInput(): RateCardRequestInterface {
  return {
    description: "",
    name: "",
    status: RateCardStatus.ACTIVE,
  };
}
```

This file is the form contract. It should include only writable fields the frontend can send. Backend-owned fields such as `id`, `createdTs`, `updatedTs`, derived counts, nested output objects, and read-only labels belong in the returned resource interface instead.

### Shared Form Fields

Form field components should receive the request DTO and typed field errors. They render shared `components/forms` wrappers and emit a full updated DTO or narrow field updates. They do not call the API, parse server errors, or own submit state.

{% raw %}
```vue
<!-- frontend/src/views/rateCards/components/RateCardFormFields.vue -->
<template>
  <div class="space-y-4">
    <AppTextField
      :model-value="modelValue.name"
      label="Rate card name"
      :error="errors.name"
      placeholder="Retail profile"
      test-id="rate-card-name"
      @update:model-value="emitPatch('name', $event)"
    />

    <AppSelectField
      :model-value="modelValue.status"
      label="Status"
      :error="errors.status"
      :options="statusOptions"
      option-label="label"
      option-value="value"
      placeholder="Select status"
      test-id="rate-card-status"
      @update:model-value="emitPatch('status', $event ?? modelValue.status)"
    />

    <AppTextareaField
      :model-value="modelValue.description"
      label="Description"
      optional-label="Optional"
      :error="errors.description"
      placeholder="Describe when this rate card should be used"
      :rows="4"
      test-id="rate-card-description"
      @update:model-value="emitPatch('description', $event)"
    />
  </div>
</template>

<script setup lang="ts">
  import AppSelectField from "@/components/forms/AppSelectField.vue";
  import AppTextField from "@/components/forms/AppTextField.vue";
  import AppTextareaField from "@/components/forms/AppTextareaField.vue";
  import type { RateCardRequestInterface } from "@/types/pricing/RateCardRequestInterface";
  import { RateCardStatus } from "@/types/pricing/RateCardInterface";

  interface Props {
    errors: Partial<Record<keyof RateCardRequestInterface, string>>;
    modelValue: RateCardRequestInterface;
  }

  const props = defineProps<Props>();

  const emit = defineEmits<{
    "update:modelValue": [value: RateCardRequestInterface];
  }>();

  const statusOptions = [
    { label: "Active", value: RateCardStatus.ACTIVE },
    { label: "Inactive", value: RateCardStatus.INACTIVE },
  ];

  function emitPatch<Key extends keyof RateCardRequestInterface>(key: Key, value: RateCardRequestInterface[Key]) {
    emit("update:modelValue", {
      ...props.modelValue,
      [key]: value,
    });
  }
</script>
```
{% endraw %}

This shape keeps shared input styling, labels, hints, and validation display in app-owned wrappers while the domain form stays focused on the fields it owns.

### Isolated Dialog Or Drawer Flow

An isolated dialog or drawer can own its own submit flow when it does not share form state with sibling route sections.

{% raw %}
```vue
<template>
  <AppDrawer
    :open="open"
    title="Create rate card"
    close-label="Close rate card drawer"
    @close="close"
  >
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
      <RateCardFormFields
        :model-value="formValues"
        :errors="fieldErrors"
        @update:model-value="reset($event)"
      />
    </form>

    <template #footer>
      <AppButton label="Cancel" tone="ghost" @click="close" />
      <AppButton
        button-type="submit"
        :form="formId"
        label="Create rate card"
        tone="primary"
        :disabled="isSubmitting"
      />
    </template>
  </AppDrawer>
</template>

<script setup lang="ts">
  import { ref } from "vue";

  import AlertBanner from "@/components/ui/AlertBanner.vue";
  import AppButton from "@/components/ui/AppButton.vue";
  import AppDrawer from "@/components/ui/AppDrawer.vue";
  import { useNotification } from "@/composables/useNotification";
  import { useSchemaValidation } from "@/composables/useSchemaValidation";
  import { createDefaultRateCardInput, rateCardInputSchema } from "@/types/pricing/RateCardRequestInterface";
  import { api } from "@/utils/api";
  import { extractFirstFieldErrors, getFirstApiErrorMessage } from "@/utils/errorHandling";
  import RateCardFormFields from "@/views/rateCards/components/RateCardFormFields.vue";

  interface Props {
    workspaceId: number | null;
    open?: boolean;
    organizationId: number | null;
  }

  const emit = defineEmits<{
    close: [];
    save: [];
  }>();

  const props = withDefaults(defineProps<Props>(), {
    open: false,
  });

  const notification = useNotification();
  const formId = "rate-card-form";
  const isSubmitting = ref(false);
  const errorMessage = ref("");
  const {
    clearErrors,
    errors: fieldErrors,
    reset,
    setErrors,
    validate,
    values: formValues,
  } = useSchemaValidation(rateCardInputSchema, createDefaultRateCardInput());

  function openForm() {
    reset();
    errorMessage.value = "";
  }

  function close() {
    emit("close");
  }

  async function submitForm() {
    if (!(await validate())) {
      return;
    }

    if (!props.organizationId || !props.workspaceId) {
      errorMessage.value = "Select an organization and workspace before creating this rate card.";
      return;
    }

    isSubmitting.value = true;
    errorMessage.value = "";
    clearErrors();

    try {
      await api.rateCards.create(props.organizationId, props.workspaceId, formValues);
      notification.success("Rate card created", "The rate card is ready to use.");
      emit("save");
    } catch (error) {
      setErrors(extractFirstFieldErrors(error));
      errorMessage.value = getFirstApiErrorMessage(error, "Unable to create this rate card.");
    } finally {
      isSubmitting.value = false;
    }
  }
</script>
```
{% endraw %}

The request payload stays typed as `RateCardRequestInterface` through `formValues`. The component passes camelCase fields to `api.rateCards.create(...)`; `frontend/src/utils/api.ts` converts the body to snake_case before sending it to Django.

### Route-Local Store Flow

When multiple route-local sections share the record, editable DTO, errors, permissions, loading state, or save action, the route-local store should own the validation workflow.

```typescript
// frontend/src/views/workspaceDetail/workspaceDetailStore.ts
import { useNotification } from "@/composables/useNotification";
import { useSchemaValidation } from "@/composables/useSchemaValidation";
import { workspaceInputSchema, createDefaultWorkspaceInput } from "@/types/workspace/WorkspaceInputInterface";
import type { WorkspaceInterface } from "@/types/workspace/WorkspaceInterface";
import { api } from "@/utils/api";
import { extractFirstFieldErrors, getFirstApiErrorMessage } from "@/utils/errorHandling";
import { useAppShellStore } from "@/views/application/appShellStore";
import { APP_PERMISSIONS } from "@/views/application/permissions";
import { defineStore } from "pinia";
import { computed, ref } from "vue";

export const useWorkspaceDetailStore = defineStore("workspaceDetail", () => {
  const appShellStore = useAppShellStore();
  const notification = useNotification();

  const workspaceId = ref<number | null>(null);
  const workspaceRecord = ref<WorkspaceInterface | null>(null);
  const errorMessage = ref("");
  const isSaving = ref(false);
  const organizationId = computed(() => appShellStore.selectedOrganizationId);
  const {
    clearErrors,
    errors: fieldErrors,
    reset: resetFormValues,
    setErrors,
    validate,
    values: formValues,
  } = useSchemaValidation(workspaceInputSchema, createDefaultWorkspaceInput());

  const isCreateMode = computed(() => !workspaceId.value);
  const canManageWorkspaceRecord = computed(() => {
    if (isCreateMode.value) {
      return appShellStore.can(APP_PERMISSIONS.organizationWorkspacesCreate, { organizationId: organizationId.value });
    }

    return appShellStore.can(APP_PERMISSIONS.workspaceManage, { workspaceId: workspaceId.value });
  });

  function applyWorkspaceToForm(workspace: WorkspaceInterface) {
    workspaceRecord.value = workspace;
    resetFormValues({
      contactEmail: workspace.contactEmail,
      contactName: workspace.contactName,
      name: workspace.name,
      status: workspace.status,
      supportPhone: workspace.supportPhone,
    });
  }

  async function saveWorkspace() {
    if (!organizationId.value) {
      errorMessage.value = "Select an organization before saving workspace changes.";
      return false;
    }

    if (!canManageWorkspaceRecord.value) {
      errorMessage.value = isCreateMode.value ? "You do not have permission to create workspaces for the selected organization." : "You do not have permission to manage this workspace.";
      return false;
    }

    if (!(await validate())) {
      return false;
    }

    isSaving.value = true;
    errorMessage.value = "";
    clearErrors();

    try {
      const savedWorkspace = isCreateMode.value
        ? await api.workspaces.create(organizationId.value, formValues)
        : await api.workspaces.update(organizationId.value, workspaceId.value as number, formValues);

      await appShellStore.refreshWorkspaces();
      applyWorkspaceToForm(savedWorkspace);
      notification.success("Workspace saved", "Workspace details were saved.");
      return true;
    } catch (error) {
      setErrors(extractFirstFieldErrors(error));
      errorMessage.value = getFirstApiErrorMessage(error, isCreateMode.value ? "Unable to create this workspace." : "Unable to save workspace changes.");
      return false;
    } finally {
      isSaving.value = false;
    }
  }

  return {
    canManageWorkspaceRecord,
    errorMessage,
    fieldErrors,
    formValues,
    isSaving,
    saveWorkspace,
  };
});
```

The route view and route-local form sections then bind to `workspaceDetailStore.formValues`, `workspaceDetailStore.fieldErrors`, and `workspaceDetailStore.saveWorkspace()` instead of passing every field, error, and callback through several component layers.

### Cascading Selects

When one field controls another, reset the dependent field through the form validation API instead of directly assigning raw values in several watchers. This keeps value reset, field errors, touched state, and dirty state aligned when the form library tracks those concepts.

```typescript
watch(
  () => selectedItemId.value,
  async (itemId, previousItemId) => {
    if (!props.open) {
      return;
    }

    if (!itemId) {
      variants.value = [];
      resetField("itemVariant");
      return;
    }

    if (isInitializingForm.value) {
      return;
    }

    if (itemId !== previousItemId) {
      resetField("itemVariant");
    }

    await loadVariants(itemId);
  }
);
```

If the current local helper does not expose `resetField(...)`, add that helper at the validation boundary before spreading cascading select logic across many forms. The standard is the behavior: the child value and its field error reset together without marking the field touched or dirty. Do not repeatedly write `formValues.itemVariant = null` while leaving stale `validationErrors.itemVariant` behind.

### Server Errors

Use `extractFirstFieldErrors(...)` for fields the current form can edit, and use `getFirstApiErrorMessage(...)` for form-level, non-field, permission, or transport failures.

```typescript
async function submitInvite() {
  if (!(await validateInvite())) {
    return false;
  }

  if (!organizationId.value || !workspaceId.value) {
    inviteErrorMessage.value = "Select a workspace before sending an invitation.";
    return false;
  }

  isInviteSubmitting.value = true;
  inviteErrorMessage.value = "";
  clearInviteErrors();

  try {
    await api.workspaces.invitationsCreate(organizationId.value, workspaceId.value, { ...inviteFormValues });
    notification.success("Invitation sent", "The workspace invitation email was sent.");
    closeInviteDialog();
    await loadInvitations();
    return true;
  } catch (error) {
    setInviteErrors(extractFirstFieldErrors(error));
    inviteErrorMessage.value = getFirstApiErrorMessage(error, "Unable to send this invitation.");
    return false;
  } finally {
    isInviteSubmitting.value = false;
  }
}
```

Do not map backend fields one at a time unless the form intentionally presents a different field surface than the request DTO. Most forms should call `setErrors(extractFirstFieldErrors(error))` directly because the helper already normalizes DRF `attr` values such as `contact_email` to frontend keys such as `contactEmail`.

## Things To Notice

- The schema, request type, and default helper live together in `frontend/src/types/<domain>/...InputInterface.ts` or `...RequestInterface.ts`.
- The schema is the source of the submit type through `z.infer`; the form does not duplicate an interface by hand.
- The default helper returns valid initial form state without placeholder output IDs.
- Form values stay camelCase from field components through stores and API calls.
- The canonical API client converts JSON request bodies to snake_case; components and stores do not.
- Shared field wrappers receive `error` strings and handle consistent label, hint, input, and error display.
- Client validation runs before checking expensive mutation behavior unless the route scope itself is missing.
- Submit handlers clear stale field errors and form-level errors before a new request.
- Server field errors flow through `extractFirstFieldErrors(...)` and `setErrors(...)`.
- General server errors flow through `getFirstApiErrorMessage(...)` into an inline form banner or a workflow-specific message.
- Isolated dialogs can own validation and submit state; route-local stores own validation when sibling route sections share the workflow.
- Dependent selects reset child fields through validation reset behavior so stale child values and stale field errors do not survive parent changes.

## Rules To Follow

- Use request DTOs for form state. Do not edit persisted output interfaces in place.
- Colocate `z.object(...)`, `z.infer`, and `createDefault...()` in the request type file.
- Use `useSchemaValidation(schema, createDefault...())` for forms with a Zod schema.
- Pass `errors.<fieldName>` into shared form wrappers such as `AppTextField`, `AppSelectField`, `AppTextareaField`, `AppDateField`, and `AppCheckboxField`.
- Call `validate()` before mutating API requests.
- Return early when client validation fails.
- Clear stale field errors when opening a form, changing the edited record, resetting a form, and before submitting a new request.
- Use `setErrors(extractFirstFieldErrors(error))` for DRF field-level server validation.
- Use `getFirstApiErrorMessage(error, fallbackMessage)` for form-level messages.
- Keep success feedback in `useNotification().success(...)` when the mutation result persists after the form closes.
- Keep API calls routed through `api` from `frontend/src/utils/api.ts`; do not import Axios, `apiClient`, or `fetch` in form components, route views, or route-local stores.
- Keep request payload keys camelCase at call sites.
- Use `buildParamsConfig(...)` only for query params, not form bodies.
- For cascading selects, reset dependent fields through `resetField(...)` or the local validation helper equivalent. Do not leave stale child errors or invalid child IDs after a parent field changes.
- Keep shared `src/components/forms/` wrappers presentational. They should not import route stores, call APIs, or parse server errors.
- Move validation state into a route-local store when multiple route-local components need the same form values, errors, submit flag, or save action.
- Keep isolated one-off dialog validation inside the dialog when no sibling route workflow shares it.

## Refactor Signals

- A form initializes from a returned resource interface and fills fake `id`, timestamp, or nested object values just to satisfy TypeScript.
- A request type file defines an interface but no schema or default helper.
- A form schema lives inside a component while the request type lives under `frontend/src/types/`.
- Several submit handlers repeat the same required-field checks that should live in a Zod schema.
- A submit handler calls the API before `validate()`.
- A component or store reads `error.response`, `error.response.data.errors`, or imports `AxiosError`.
- Server field errors are manually mapped with repeated `apiFieldErrors.email?.[0]` style code when the DTO keys already match.
- A backend snake_case field name appears in frontend form state or a submit payload.
- Field errors remain visible after reopening a dialog, switching from edit to create mode, or changing the edited record.
- A dependent select clears its child value with direct assignment while the old child field error remains visible.
- A route view passes form values, field errors, loading flags, save callbacks, and dialog state through multiple route-local components.
- A shared form field wrapper imports a route-local store or owns domain-specific submit logic.
- Success and failure feedback appear only as generic notifications even though the active form has fields that can show targeted errors.

## Verification

- For guidance-only edits, check Markdown fences and rebuild generated guidance:

```bash
rg -c '^```' agents/guidance/frameworks/vue/examples/vue-form-validation.md
git diff --check -- agents/guidance/frameworks/vue/examples/vue-form-validation.md
python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean
```

- For form implementation changes, run the frontend typecheck and lint:

```bash
cd frontend
npm run type-check
npm run lint
```

- For validation helper or error helper changes, run focused tests when they exist, such as:

```bash
cd frontend
node --test tests/standardized-error-helpers-guidance.test.ts
```

- Use targeted scans during review:

```bash
rg "error\\.response|AxiosError|from [\"']axios|fetch\\(" frontend/src/views frontend/src/components frontend/src/composables
rg "snake_case|workspace_id|item_option" frontend/src/views frontend/src/components
rg "useSchemaValidation" frontend/src/views frontend/src/types
```

- Manual verification should cover client validation failure, server field validation failure, non-field server failure, successful submit, dialog reopen, edit-record switch, and dependent select parent changes.

## Why It Helps

- Users get fast client-side feedback and still see authoritative backend validation where they can act on it.
- Request DTOs, default form state, validation rules, and API payloads stay aligned.
- Django can keep serializer, permission, uniqueness, and organization-scoping validation without leaking backend response parsing into every component.
- Form components stay readable because field rendering, submit orchestration, API transport, and error parsing each have one owner.
- Route-local stores can refactor complex forms without changing shared components.
- Reviews can reject stale errors, raw Axios parsing, output-interface form state, snake_case frontend payloads, and scattered cascading-select logic with concrete rules.
