---
id: framework-vue-example-standardized-error-helpers
title: Vue Standardized Error Helpers Example
description: Example shared helpers for parsing DRF standardized errors once and reusing them across forms and toasts.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - errors
applies_to:
  - vue
status: active
order: 9
---

# Vue Standardized Error Helpers Example

## Scenario

- Use this pattern when a Vue form, dialog, route-local store, or action needs to display validation errors returned by `drf-standardized-errors`.
- Use this pattern when a flow combines client validation from `useSchemaValidation(...)` with server validation from DRF serializers or views.
- Use this pattern when a component needs a form-level message, a toast, status-specific logic, or field-level input errors from the same failed API request.
- Do not use this pattern to justify local `AxiosError` parsing in components or stores. Components and stores consume shared frontend error helpers only.

## Why This Shape Exists

The backend intentionally returns standardized DRF error payloads. Serializer validation, view-level `ValidationError`, permission failures, and query-param validation should all travel through one response shape so frontend code does not need to know which backend layer raised the error.

The frontend also has one API client boundary. `frontend/src/utils/api.ts` owns Axios, CSRF, request casing, response casing, and error response casing. Components and stores should not import `axios`, narrow `AxiosError`, inspect `error.response.data.errors`, or repeat the same payload guards in every submit handler.

There is one extra casing detail to preserve: the API client converts response object keys from snake_case to camelCase, but a DRF error `attr` is a string value such as `valid_from`, `non_field_errors`, or `answers.contact_email`. Shared error helpers must normalize those attr strings with `snakeFieldAttrToCamel(...)` so field errors match frontend `camelCase` form DTO keys.

This pattern separates three concerns:

- Client validation runs before submission and prevents avoidable requests.
- Field-level server validation maps to input errors through `setErrors(extractFirstFieldErrors(error))`.
- General, non-field, permission, or transport-shaped failures render through a form banner, page error message, or shared notification.

## Recommended Shape

### Shared Error Helper

Keep DRF standardized-error parsing in `frontend/src/utils/errorHandling.ts`. This is the only frontend module that should understand the raw standardized payload.

```typescript
import type { ErrorResponseInterface } from "@/types/api/ErrorResponseInterface";
import { snakeFieldAttrToCamel } from "@/utils/caseConversion";

interface ApiErrorShape {
  response?: {
    data?: unknown;
    status?: number;
  };
}

export type FieldErrors = Record<string, string[]>;
export type FirstFieldErrors = Record<string, string>;

function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object";
}

function isErrorItem(value: unknown) {
  return isObject(value) && typeof value.detail === "string" && (value.attr === undefined || typeof value.attr === "string") && (value.code === undefined || typeof value.code === "string");
}

export function isApiError(error: unknown): error is ApiErrorShape {
  if (!isObject(error)) {
    return false;
  }

  return error.response === undefined || isObject(error.response);
}

export function isStandardizedErrorResponse(data: unknown): data is ErrorResponseInterface {
  return isObject(data) && Array.isArray(data.errors) && data.errors.every(isErrorItem);
}

export function parseApiError(error: unknown): ErrorResponseInterface | null {
  if (!isApiError(error)) {
    return null;
  }

  const data = error.response?.data;
  if (!isStandardizedErrorResponse(data)) {
    return null;
  }

  return data;
}

export function extractFieldErrors(error: unknown): FieldErrors {
  const fieldErrors: FieldErrors = {};
  const errorResponse = parseApiError(error);
  if (!errorResponse?.errors) {
    return fieldErrors;
  }

  for (const errorItem of errorResponse.errors) {
    if (!errorItem.attr) {
      continue;
    }

    const normalizedAttr = snakeFieldAttrToCamel(errorItem.attr);
    const messages = fieldErrors[normalizedAttr] ?? [];
    messages.push(errorItem.detail);
    fieldErrors[normalizedAttr] = messages;
  }

  return fieldErrors;
}

export function extractFirstFieldErrors(error: unknown): FirstFieldErrors {
  const firstFieldErrors: FirstFieldErrors = {};
  const fieldErrors = extractFieldErrors(error);

  for (const [key, values] of Object.entries(fieldErrors)) {
    const firstMessage = values[0];
    if (firstMessage) {
      firstFieldErrors[key] = firstMessage;
    }
  }

  return firstFieldErrors;
}

export function getApiErrorStatus(error: unknown): number | null {
  if (!isApiError(error)) {
    return null;
  }

  return typeof error.response?.status === "number" ? error.response.status : null;
}

export function getFirstApiErrorCode(error: unknown): string | null {
  return parseApiError(error)?.errors?.[0]?.code ?? null;
}

export function getFirstApiErrorMessage(error: unknown, fallbackMessage: string): string {
  const errorResponse = parseApiError(error);
  const firstError = errorResponse?.errors?.[0];

  return firstError?.detail || fallbackMessage;
}
```

### API Client Boundary

Keep Axios and casing conversion in the canonical API client. The rejected error is still an `unknown` to callers, but `error.response.data` has already passed through the same object-key casing conversion as successful responses.

```typescript
import axios, { type AxiosError, type AxiosInstance, type AxiosResponse } from "axios";

import { camelToSnake, snakeToCamel } from "@/utils/caseConversion";

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

  async post<TResponse, TBody>(url: string, body?: TBody): Promise<TResponse> {
    const { data } = await this.axios.post<TResponse>(url, camelToSnake(body));
    return data;
  }
}
```

### Form Or Dialog Submit Flow

The submit flow validates client-side first, clears stale server errors before the next request, then maps backend field errors and general errors separately.

```vue
<template>
  <AppDialog :open="open" title="Create rate card" @close="close">
    <AlertBanner v-if="errorMessage" :message="errorMessage" tone="warning" />

    <RateCardFormFields v-model="formValues" :errors="fieldErrors" />

    <template #footer>
      <AppButton label="Cancel" variant="secondary" @click="close" />
      <AppButton label="Create" :loading="isSubmitting" @click="void submit()" />
    </template>
  </AppDialog>
</template>

<script setup lang="ts">
import { ref } from "vue";

import { useSchemaValidation } from "@/composables/useSchemaValidation";
import { useNotification } from "@/composables/useNotification";
import { createDefaultRateCardInput, rateCardInputSchema } from "@/types/pricing/RateCardRequestInterface";
import { api } from "@/utils/api";
import { extractFirstFieldErrors, getFirstApiErrorMessage } from "@/utils/errorHandling";

const notification = useNotification();
const open = ref(false);
const isSubmitting = ref(false);
const errorMessage = ref("");
const { clearErrors, errors: fieldErrors, reset, setErrors, validate, values: formValues } = useSchemaValidation(rateCardInputSchema, createDefaultRateCardInput());

function openCreateDialog() {
  reset();
  clearErrors();
  errorMessage.value = "";
  open.value = true;
}

function close() {
  open.value = false;
}

async function submit() {
  if (!(await validate())) {
    return false;
  }

  isSubmitting.value = true;
  errorMessage.value = "";
  clearErrors();

  try {
    await api.rateCards.create(organizationId.value, workspaceId.value, formValues);
    notification.success("Rate card created", "The rate card is ready to use.");
    close();
    return true;
  } catch (error) {
    setErrors(extractFirstFieldErrors(error));
    errorMessage.value = getFirstApiErrorMessage(error, "Unable to create this rate card.");
    return false;
  } finally {
    isSubmitting.value = false;
  }
}
</script>
```

### Route-Local Store Shape

When several route-local sections share form state, the store owns the same helper flow and the component renders `store.fieldErrors` and `store.errorMessage`.

```typescript
import { defineStore } from "pinia";
import { ref } from "vue";

import { useSchemaValidation } from "@/composables/useSchemaValidation";
import { useNotification } from "@/composables/useNotification";
import { createDefaultContactAddressInput, contactAddressInputSchema } from "@/types/contact/ContactAddressInputInterface";
import { api } from "@/utils/api";
import { extractFirstFieldErrors, getFirstApiErrorMessage } from "@/utils/errorHandling";

export const useContactDetailStore = defineStore("contactDetail", () => {
  const notification = useNotification();
  const isAddressSubmitting = ref(false);
  const addressErrorMessage = ref("");
  const { clearErrors: clearAddressErrors, errors: addressFieldErrors, reset: resetAddressFormValues, setErrors: setAddressErrors, validate: validateAddress, values: addressFormValues } = useSchemaValidation(
    contactAddressInputSchema,
    createDefaultContactAddressInput()
  );

  function openAddressDialog() {
    resetAddressFormValues();
    clearAddressErrors();
    addressErrorMessage.value = "";
  }

  async function saveAddress() {
    if (!(await validateAddress())) {
      return false;
    }

    isAddressSubmitting.value = true;
    addressErrorMessage.value = "";
    clearAddressErrors();

    try {
      await api.contactAddresses.create(organizationId.value, workspaceId.value, contactId.value, addressFormValues);
      notification.success("Address added", "The contact address is now available for orders.");
      return true;
    } catch (error) {
      setAddressErrors(extractFirstFieldErrors(error));
      addressErrorMessage.value = getFirstApiErrorMessage(error, "Unable to add this address.");
      return false;
    } finally {
      isAddressSubmitting.value = false;
    }
  }

  return {
    addressErrorMessage,
    addressFieldErrors,
    addressFormValues,
    isAddressSubmitting,
    openAddressDialog,
    saveAddress,
  };
});
```

### Field Errors Versus General Errors

Use field errors only for fields the user can edit in the current form. Use the form-level `errorMessage`, a page-level error state, or a notification for everything else.

```typescript
async function saveOrganization() {
  if (!(await validate())) {
    return false;
  }

  errorMessage.value = "";
  clearErrors();

  try {
    await api.organizations.update(organizationId.value, formValues);
    notification.success("Organization updated", "Organization settings were saved.");
    return true;
  } catch (error) {
    setErrors(extractFirstFieldErrors(error));
    errorMessage.value = getFirstApiErrorMessage(error, "Unable to save organization settings.");
    return false;
  }
}
```

For a DRF response like this:

```json
{
  "errors": [
    { "attr": "support_email", "detail": "Enter a valid email address.", "code": "invalid" },
    { "attr": "non_field_errors", "detail": "This organization domain is already in use.", "code": "invalid" }
  ]
}
```

The helper maps `support_email` to `supportEmail` for the field. The non-field message still belongs in the form banner through `getFirstApiErrorMessage(...)` or a workflow-specific general error slot, not in a random input just to make it visible.

## Things To Notice

- Unknown errors are type-checked before field extraction logic runs.
- `extractFieldErrors(...)` preserves arrays for surfaces that need every message, while `extractFirstFieldErrors(...)` feeds `useSchemaValidation(...).setErrors(...)`.
- `getFirstApiErrorMessage(...)` is the form banner and notification helper. It handles attr-less errors, permission failures, non-field validation, and non-standard failures with the supplied fallback.
- `getApiErrorStatus(...)` and `getFirstApiErrorCode(...)` exist for flows that need behavior differences, such as draft-resume or expired-token handling. Components still do not inspect `error.response`.
- Client validation and server validation are both present. Client validation runs first; server validation remains authoritative and is displayed when the backend rejects the request.
- `clearErrors()` runs when opening/resetting a form and immediately before a new submit request so stale backend errors do not survive after the user fixes input.
- The API client converts response keys, but the helper converts `attr` string values. Do not manually convert backend attrs in a component.
- Success feedback belongs in `useNotification()` for cross-feature consistency. Inline banners should be reserved for the active form or page failure.
- Route-local stores can own the same flow as isolated dialogs when the form state is shared with sibling sections.

## Rules To Follow

- Keep `axios`, `AxiosError`, interceptors, CSRF handling, and casing conversion inside `frontend/src/utils/api.ts`.
- Keep standardized-error parsing inside `frontend/src/utils/errorHandling.ts`.
- Components, dialogs, and stores must call shared helpers such as `extractFirstFieldErrors(...)`, `getFirstApiErrorMessage(...)`, `getApiErrorStatus(...)`, or `getFirstApiErrorCode(...)` instead of reading `error.response`.
- Do not parse `error.response.data.errors`, flatten error arrays, or check `response.status` ad hoc in a component or store.
- Use `validate()` before mutating API calls when the form has a schema.
- Use `setErrors(extractFirstFieldErrors(error))` for field-level server validation.
- Use `getFirstApiErrorMessage(error, fallbackMessage)` for form-level, non-field, permission, and general API failures.
- Clear stale field errors when opening a dialog, resetting a form, changing the edited record, and before a submit request.
- Keep backend attrs in snake_case and let `snakeFieldAttrToCamel(...)` normalize them once in the shared helper.
- Do not manually translate backend field names in submit handlers.
- Show successful mutations with `useNotification().success(...)` when the result is cross-route or persists after a dialog closes.
- Keep failed submit feedback close to the form through `errorMessage` plus field errors; use `notification.error(...)` for destructive or background actions that do not have an active form surface.
- Add helper coverage before adding a new exported error helper, especially for status, code, attr casing, and field-array behavior.
- Remove obsolete local parsing helpers when migrating a flow to the shared helpers.

## Refactor Signals

- A component or store imports `AxiosError`, `isAxiosError`, or `axios`.
- A submit handler reads `error.response`, `error.response?.data`, `error.response?.status`, or `error.response?.data?.errors`.
- A route has repeated code such as `apiFieldErrors.email?.[0]`, `Object.fromEntries(...)`, local array flattening, or manual `snake_case` to `camelCase` attr mapping.
- A component maps backend attrs one field at a time when `setErrors(extractFirstFieldErrors(error))` would match the form DTO.
- Field errors remain visible after reopening a dialog, changing the edited record, or submitting corrected input.
- A form only validates client-side and drops backend serializer errors into a generic toast.
- A form only displays backend field errors and skips local schema validation before submission.
- Non-field backend errors are assigned to an unrelated input instead of a form-level banner or notification.
- A route-local parent passes field errors, error messages, loading flags, and submit callbacks through several child layers when a route-local store should own the workflow.
- A new API client or service module starts duplicating Axios response casing or error parsing.
- Tests assert raw standardized error payload details in a component instead of asserting use of shared helper behavior.

## Verification

- For helper changes, run the targeted frontend guidance/helper tests, such as:

```bash
cd frontend
node --test tests/standardized-error-helpers-guidance.test.ts
```

- For form, dialog, or store migrations, run the relevant focused tests for that feature area when they exist.
- Run the frontend typecheck after changing helper signatures or call sites:

```bash
cd frontend
npm run type-check
```

- Run lint on modified frontend files before completion:

```bash
cd frontend
npm run lint
```

- When editing guidance examples, also check the Markdown fences and rebuild generated guidance when practical:

```bash
python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean
```

- Manual review should confirm there are no component/store `AxiosError` imports, no direct `error.response` parsing outside the API/helper boundary, and no stale field errors after dialog reopen or resubmit.

## Why It Helps

- Users see field-specific messages where they can act and general messages where they understand the failed workflow.
- Backend validation stays authoritative without forcing every component to understand DRF internals.
- Casing stays consistent across the API client, error helper, form DTOs, and input components.
- Dialogs, route-local stores, and forms stay small because they all consume the same helper surface.
- Refactors become safer because changing the standardized-error contract or attr normalization happens in one place.
- Reviews can quickly reject duplicated parsing, stale error state, and hidden Axios coupling.
