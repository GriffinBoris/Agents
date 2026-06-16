---
id: framework-vue-example-multi-step-form
title: Vue Multi-Step Form Example
description: Standards for parent-owned multi-step Vue forms with step-local validation, preflight checks, and final submit ownership.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - forms
applies_to:
  - vue
status: active
order: 18
---

# Vue Multi-Step Form Example

## Scenario

Use this pattern when one user workflow spans multiple visible steps but still represents one coherent form request or one ordered backend runtime.

Good fits include:

- account registration split into identity and password steps
- organization or workspace onboarding that collects several groups of fields before one final create action
- checkout, enrollment, or survey flows where each screen gathers part of a shared request
- server-backed runtime flows where the frontend saves a page and asks the backend which page comes next

Do not split one form into a route query, local storage draft, child-local refs, and parent-local submit state just because the UI has several screens. The workflow needs one owner for the draft, one owner for the active step, and one obvious place where final submission happens.

## Why This Shape Exists

Multi-step forms are easy to make fragile because the UI encourages splitting state by screen. If each step owns its own request fragment, the final submit has to reconstruct the payload from several unrelated sources. Back and forward navigation can lose input, server errors may be hard to map back to fields, and reviews cannot tell which component owns the business action.

This pattern uses the pieces needed for a cleaner shape:

- `useSchemaValidation(...)` owns reactive form values, field errors, `validate()`, `setErrors(...)`, and `reset(...)`.
- Request types and Zod schemas live together under `frontend/src/types/...`.
- API calls go through `frontend/src/utils/api.ts`.
- DRF standardized errors map through `extractFirstFieldErrors(...)` and `getFirstApiErrorMessage(...)`.
- Simple route views can own isolated form workflows directly.
- Larger flows move shared business state into a route-local Pinia store, as in `frontend/src/views/publicSurvey/publicSurveyStore.ts`.

The standard tradeoff is that step components stay a little more explicit: they receive the shared DTO, validate only the fields they render, and emit simple navigation or submit events. That extra explicitness keeps ownership auditable and prevents accidental parallel state.

## Recommended Shape

### Request Type Owns The Full Draft

Keep the complete request shape in one type file. If step-level schemas are useful, derive them from the same full schema so defaults, validation, and submit payload stay aligned.

```typescript
// frontend/src/types/auth/RegisterInputInterface.ts
import { z } from "zod";

export const registerInputSchema = z.object({
  email: z.string().email("Must be a valid email").min(1, "Email is required"),
  firstName: z.string().min(1, "First name is required"),
  lastName: z.string().min(1, "Last name is required"),
  passwordOne: z.string().min(1, "Password is required"),
  passwordTwo: z.string().min(1, "Confirm password is required"),
});

export const registerIdentityStepSchema = registerInputSchema.pick({
  email: true,
  firstName: true,
  lastName: true,
});

export const registerPasswordStepSchema = registerInputSchema.pick({
  passwordOne: true,
  passwordTwo: true,
});

export type RegisterInputInterface = z.infer<typeof registerInputSchema>;

export function createDefaultRegisterInput(): RegisterInputInterface {
  return {
    email: "",
    firstName: "",
    lastName: "",
    passwordOne: "",
    passwordTwo: "",
  };
}
```

The step schemas are not separate DTOs. They are validation slices of the same request object that `api.auth.register(...)` receives at final submit.

### Parent View Owns Draft, Step, And Final Submit

The parent route or parent workflow component owns the shared DTO, active step, final submission state, general error message, and shell/session follow-up. Step components do not call the final create endpoint unless that step is the explicit final submit step.

```vue
<!-- frontend/src/views/register/RegisterWizardView.vue -->
<template>
  <AppSurface root-class="w-full max-w-md" content-class="space-y-6 p-6 sm:p-8">
    <PageFormHeader
      eyebrow="Example Platform"
      title="Create account"
      description="Create your operator account"
      :centered="true"
    />

    <AlertBanner v-if="errorMessage" :message="errorMessage" tone="warning" />

    <RegisterIdentityStep
      v-if="activeStep === 'identity'"
      :values="formValues"
      :errors="fieldErrors"
      :is-checking="isCheckingIdentity"
      @validation-errors="setErrors"
      @update-field="updateField"
      @continue="continueFromIdentity"
    />

    <RegisterPasswordStep
      v-else
      :values="formValues"
      :errors="fieldErrors"
      :is-submitting="isSubmitting"
      @back="activeStep = 'identity'"
      @validation-errors="setErrors"
      @update-field="updateField"
      @submit="submitRegister"
    />
  </AppSurface>
</template>

<script setup lang="ts">
  import AppSurface from "@/components/ui/AppSurface.vue";
  import AlertBanner from "@/components/ui/AlertBanner.vue";
  import PageFormHeader from "@/components/page/PageFormHeader.vue";
  import { useSchemaValidation } from "@/composables/useSchemaValidation";
  import {
    createDefaultRegisterInput,
    registerInputSchema,
    type RegisterInputInterface,
  } from "@/types/auth/RegisterInputInterface";
  import { api } from "@/utils/api";
  import { extractFirstFieldErrors, getFirstApiErrorMessage } from "@/utils/errorHandling";
  import { useAppShellStore } from "@/views/application/appShellStore";
  import RegisterIdentityStep from "@/views/register/components/RegisterIdentityStep.vue";
  import RegisterPasswordStep from "@/views/register/components/RegisterPasswordStep.vue";
  import { ref } from "vue";
  import { useRouter } from "vue-router";

  interface Props {
    invitationToken?: string;
  }

  type RegisterStep = "identity" | "password";

  const props = defineProps<Props>();
  const router = useRouter();
  const appShellStore = useAppShellStore();
  const activeStep = ref<RegisterStep>("identity");
  const errorMessage = ref("");
  const isCheckingIdentity = ref(false);
  const isSubmitting = ref(false);
  const { errors: fieldErrors, setErrors, validate, values: formValues } = useSchemaValidation(registerInputSchema, createDefaultRegisterInput());

  function updateField<FieldName extends keyof RegisterInputInterface>(fieldName: FieldName, value: RegisterInputInterface[FieldName]) {
    formValues[fieldName] = value;
  }

  async function continueFromIdentity() {
    errorMessage.value = "";

    isCheckingIdentity.value = true;

    try {
      if (props.invitationToken) {
        await api.auth.invitationDetail(props.invitationToken);
      }

      activeStep.value = "password";
    } catch (error) {
      setErrors(extractFirstFieldErrors(error));
      errorMessage.value = getFirstApiErrorMessage(error, "Unable to continue registration.");
    } finally {
      isCheckingIdentity.value = false;
    }
  }

  async function submitRegister() {
    errorMessage.value = "";

    if (!(await validate())) {
      return;
    }

    isSubmitting.value = true;

    try {
      await api.auth.register(formValues);
      appShellStore.resetState();
      await appShellStore.initialize();
      await router.replace({ name: "workspaces-list" });
    } catch (error) {
      setErrors(extractFirstFieldErrors(error));
      errorMessage.value = getFirstApiErrorMessage(error, "Unable to create your account.");
    } finally {
      isSubmitting.value = false;
    }
  }

</script>
```

The parent preserves state across back and forward because both steps render from the same `formValues` object. The parent also owns the authenticated-session follow-up after registration, matching the current `RegisterView.vue` pattern.

### Step Components Own Step-Local Validation And Advancement

Step components should render only their fields and own only the action for leaving that step. They can validate their local slice before emitting `continue`, but they should not create a second copy of the request.

```vue
<!-- frontend/src/views/register/components/RegisterIdentityStep.vue -->
<template>
  <form class="space-y-4" @submit.prevent="continueToNextStep()">
    <AppTextField
      :model-value="values.firstName"
      label="First name"
      :error="errors.firstName"
      placeholder="Alex"
      autocomplete="given-name"
      @update:model-value="emit('update-field', 'firstName', $event)"
    />
    <AppTextField
      :model-value="values.lastName"
      label="Last name"
      :error="errors.lastName"
      placeholder="Morgan"
      autocomplete="family-name"
      @update:model-value="emit('update-field', 'lastName', $event)"
    />
    <AppTextField
      :model-value="values.email"
      label="Email"
      type="email"
      :error="errors.email"
      placeholder="operator@example.com"
      autocomplete="email"
      @update:model-value="emit('update-field', 'email', $event)"
    />

    <AppButton button-type="submit" label="Continue" tone="primary" :disabled="isChecking" />
  </form>
</template>

<script setup lang="ts">
  import AppTextField from "@/components/forms/AppTextField.vue";
  import AppButton from "@/components/ui/AppButton.vue";
  import { registerIdentityStepSchema, type RegisterInputInterface } from "@/types/auth/RegisterInputInterface";

  interface Props {
    errors: Partial<Record<keyof RegisterInputInterface, string>>;
    isChecking?: boolean;
    values: RegisterInputInterface;
  }

  const props = withDefaults(defineProps<Props>(), {
    isChecking: false,
  });

  const emit = defineEmits<{
    continue: [];
    "validation-errors": [errors: Partial<Record<keyof RegisterInputInterface, string>>];
    "update-field": [fieldName: keyof RegisterInputInterface, value: string];
  }>();

  function continueToNextStep() {
    const result = registerIdentityStepSchema.safeParse(props.values);
    if (!result.success) {
      emit("validation-errors", buildStepErrors(result.error.issues));
      return;
    }

    emit("continue");
  }

  function buildStepErrors(issues: Array<{ message: string; path: Array<PropertyKey> }>) {
    const nextErrors: Partial<Record<keyof RegisterInputInterface, string>> = {};

    for (const issue of issues) {
      const fieldName = issue.path[0];
      if (typeof fieldName === "string" && !nextErrors[fieldName as keyof RegisterInputInterface]) {
        nextErrors[fieldName as keyof RegisterInputInterface] = issue.message;
      }
    }

    return nextErrors;
  }
</script>
```

The step does not know how registration is submitted, where the user goes after success, or how shell state is reinitialized. Those are workflow concerns owned by the parent.

### Final Step Submits Through The Parent

The final step can emit `submit`, but it still does not call the API directly unless the step component is the workflow owner. This keeps all loading, server errors, navigation, and shell follow-up in one place.

```vue
<!-- frontend/src/views/register/components/RegisterPasswordStep.vue -->
<template>
  <form class="space-y-4" @submit.prevent="submitStep()">
    <AppTextField
      :model-value="values.passwordOne"
      label="Password"
      type="password"
      :error="errors.passwordOne"
      autocomplete="new-password"
      @update:model-value="emit('update-field', 'passwordOne', $event)"
    />
    <AppTextField
      :model-value="values.passwordTwo"
      label="Confirm password"
      type="password"
      :error="errors.passwordTwo"
      autocomplete="new-password"
      @update:model-value="emit('update-field', 'passwordTwo', $event)"
    />

    <div class="flex flex-col gap-3 sm:flex-row sm:justify-between">
      <AppButton label="Back" tone="secondary" @click="emit('back')" />
      <AppButton button-type="submit" label="Create account" tone="primary" :disabled="isSubmitting" />
    </div>
  </form>
</template>

<script setup lang="ts">
  import AppTextField from "@/components/forms/AppTextField.vue";
  import AppButton from "@/components/ui/AppButton.vue";
  import { registerPasswordStepSchema, type RegisterInputInterface } from "@/types/auth/RegisterInputInterface";

  interface Props {
    errors: Partial<Record<keyof RegisterInputInterface, string>>;
    isSubmitting?: boolean;
    values: RegisterInputInterface;
  }

  const props = withDefaults(defineProps<Props>(), {
    isSubmitting: false,
  });

  const emit = defineEmits<{
    back: [];
    submit: [];
    "validation-errors": [errors: Partial<Record<keyof RegisterInputInterface, string>>];
    "update-field": [fieldName: keyof RegisterInputInterface, value: string];
  }>();

  function submitStep() {
    const result = registerPasswordStepSchema.safeParse(props.values);
    if (!result.success) {
      emit("validation-errors", buildStepErrors(result.error.issues));
      return;
    }

    emit("submit");
  }

  function buildStepErrors(issues: Array<{ message: string; path: Array<PropertyKey> }>) {
    const nextErrors: Partial<Record<keyof RegisterInputInterface, string>> = {};

    for (const issue of issues) {
      const fieldName = issue.path[0];
      if (typeof fieldName === "string" && !nextErrors[fieldName as keyof RegisterInputInterface]) {
        nextErrors[fieldName as keyof RegisterInputInterface] = issue.message;
      }
    }

    return nextErrors;
  }
</script>
```

### Preflight Checks Belong At The Advancement Boundary

Some steps need a backend check before the user can continue. Examples include invitation-token lookup, email availability, quote calculation, runtime session creation, or validating a draft survey form before preview. Put that preflight at the boundary between the current step and the next step.

The code should make the state change conditional on the preflight succeeding:

```typescript
async function continueFromIdentity() {
  errorMessage.value = "";

  const result = registerIdentityStepSchema.safeParse(formValues);
  if (!result.success) {
    setErrors(buildStepErrors(result.error.issues));
    return;
  }

  isCheckingIdentity.value = true;

  try {
    await api.auth.invitationDetail(invitationToken.value);
    activeStep.value = "password";
  } catch (error) {
    setErrors(extractFirstFieldErrors(error));
    errorMessage.value = getFirstApiErrorMessage(error, "Unable to verify this invitation.");
  } finally {
    isCheckingIdentity.value = false;
  }
}
```

Do not advance first and hope the next step handles a failed preflight. The step transition is the user-visible contract that the current screen is complete.

### Server-Backed Page Flows Graduate To A Route-Local Store

When the backend owns session state, page order, saved progress, or the next page decision, use a route-local store instead of pushing that workflow through parent and child emits. `frontend/src/views/publicSurvey/publicSurveyStore.ts` is the current example.

```typescript
// frontend/src/views/publicSurvey/publicSurveyStore.ts
import { useNotification } from "@/composables/useNotification";
import type { SurveyRuntimeStateInterface } from "@/types/survey/SurveyRuntimeStateInterface";
import { api } from "@/utils/api";
import { extractFirstFieldErrors, getFirstApiErrorMessage } from "@/utils/errorHandling";
import { defineStore } from "pinia";
import { computed, ref } from "vue";

export const usePublicSurveyStore = defineStore("publicSurvey", () => {
  const notification = useNotification();

  const isLoading = ref(false);
  const isSaving = ref(false);
  const isCompletingPage = ref(false);
  const errorMessage = ref("");
  const fieldErrors = ref<Record<string, string>>({});
  const runtimeState = ref<SurveyRuntimeStateInterface | null>(null);
  const runtimeToken = ref<string | null>(null);
  const sessionToken = ref<string | null>(null);
  const successMessage = ref("");
  let loadRequestId = 0;

  const currentPageKey = computed(() => runtimeState.value?.currentPageKey ?? "");
  const isComplete = computed(() => (runtimeState.value?.session.percentComplete ?? 0) >= 100);

  function setGuestRoute(token: string | null) {
    runtimeToken.value = token;
  }

  async function load() {
    const requestId = ++loadRequestId;
    resetRuntimeState();

    if (!runtimeToken.value) {
      errorMessage.value = "This survey link is missing.";
      return;
    }

    isLoading.value = true;
    const activeToken = runtimeToken.value;

    try {
      const startedSession = await api.surveyRuntime.startSession(activeToken);
      if (!isCurrentGuestScope(requestId, activeToken)) {
        return;
      }

      sessionToken.value = startedSession.publicToken;
      runtimeState.value = await api.surveyRuntime.state(startedSession.publicToken);
    } catch (error) {
      if (!isCurrentGuestScope(requestId, activeToken)) {
        return;
      }

      errorMessage.value = getFirstApiErrorMessage(error, "Unable to load this survey.");
    } finally {
      if (isCurrentGuestScope(requestId, activeToken)) {
        isLoading.value = false;
      }
    }
  }

  async function continueCurrentPage() {
    if (!sessionToken.value || !runtimeState.value) {
      return false;
    }

    isSaving.value = true;
    errorMessage.value = "";
    fieldErrors.value = {};

    try {
      const savedState = await api.surveyRuntime.saveAnswers(sessionToken.value, {
        answers: normalizeAnswers(runtimeState.value.answers),
      });
      runtimeState.value = await api.surveyRuntime.completePage(sessionToken.value, {
        pageKey: savedState.currentPageKey,
      });

      if (isComplete.value) {
        successMessage.value = "Survey completed";
        notification.success("Survey completed", "Your answers were saved successfully.");
      }

      return true;
    } catch (error) {
      fieldErrors.value = extractFirstFieldErrors(error);
      errorMessage.value = getFirstApiErrorMessage(error, "Complete the required fields before continuing.");
      return false;
    } finally {
      isSaving.value = false;
    }
  }

  function updateLocalAnswer(fieldKey: string, value: boolean | number | string | string[] | null) {
    if (!runtimeState.value) {
      return;
    }

    runtimeState.value = {
      ...runtimeState.value,
      answers: {
        ...runtimeState.value.answers,
        [fieldKey]: value,
      },
    };

    const nextFieldErrors = { ...fieldErrors.value };
    delete nextFieldErrors[`answers.${fieldKey}`];
    fieldErrors.value = nextFieldErrors;
  }

  function resetRuntimeState() {
    isLoading.value = false;
    isSaving.value = false;
    isCompletingPage.value = false;
    errorMessage.value = "";
    fieldErrors.value = {};
    runtimeState.value = null;
    sessionToken.value = null;
    successMessage.value = "";
  }

  function normalizeAnswers(source: Record<string, boolean | number | string | string[] | null>) {
    const normalizedAnswers: Record<string, boolean | number | string | string[]> = {};

    for (const [fieldKey, value] of Object.entries(source)) {
      if (value === "" || value === null || (Array.isArray(value) && value.length === 0)) {
        continue;
      }

      normalizedAnswers[fieldKey] = value;
    }

    return normalizedAnswers;
  }

  function isCurrentGuestScope(requestId: number, activeToken: string) {
    return requestId === loadRequestId && runtimeToken.value === activeToken;
  }

  return {
    continueCurrentPage,
    currentPageKey,
    errorMessage,
    fieldErrors,
    isCompletingPage,
    isLoading,
    isSaving,
    load,
    runtimeState,
    setGuestRoute,
    successMessage,
    updateLocalAnswer,
  };
});
```

This is not just a "big form" version of the small registration wizard. The store owns a backend session token, stale-load guards, saved answers, page completion, server field errors, and completion notifications. That is route workflow state, so colocating it in the route folder is clearer than pushing it through every runtime component.

### Runtime Component Stays Presentational

The runtime form renders the current page and emits small events. It does not own the session, page transition, or API calls.

```vue
<!-- frontend/src/views/publicSurvey/components/PublicSurveyRuntimeForm.vue -->
<template>
  <SurveyRuntimeSurface :content-class="surfaceContentClass">
    <AlertBanner v-if="errorMessage" :message="errorMessage" tone="warning" />

    <RuntimePageRenderer
      :answers="answers"
      :current-page="currentPage"
      :field-errors="fieldErrors"
      :page-theme="resolvedTheme"
      :update-answer="(fieldKey, value) => emit('update-answer', fieldKey, value)"
    />

    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <p class="text-secondary text-xs">Your progress is saved as you continue</p>
      <SurveyRuntimeButton label="Continue" tone="primary" :loading="isBusy" :disabled="isBusy" @click="emit('continue')" />
    </div>
  </SurveyRuntimeSurface>
</template>

<script setup lang="ts">
  import AlertBanner from "@/components/ui/AlertBanner.vue";
  import RuntimePageRenderer from "@/core/survey/runtime/pageRenderer/RuntimePageRenderer.vue";
  import SurveyRuntimeButton from "@/core/survey/runtime/ui/SurveyRuntimeButton.vue";
  import SurveyRuntimeSurface from "@/core/survey/runtime/ui/SurveyRuntimeSurface.vue";
  import type { SurveyRuntimePageInterface } from "@/types/survey/SurveyRuntimeSnapshotInterface";

  type RuntimeFieldValue = boolean | number | string | string[] | null;

  interface Props {
    answers: Record<string, RuntimeFieldValue>;
    currentPage: SurveyRuntimePageInterface;
    errorMessage?: string;
    fieldErrors: Record<string, string>;
    isBusy?: boolean;
  }

  withDefaults(defineProps<Props>(), {
    errorMessage: undefined,
    isBusy: false,
  });

  const emit = defineEmits<{
    continue: [];
    "update-answer": [fieldKey: string, value: RuntimeFieldValue];
  }>();
</script>
```

## Things To Notice

- One shared request object is created from the same default helper that the final submit uses.
- Step-level schemas are slices of the full schema, not parallel request contracts.
- The parent owns `activeStep`, `errorMessage`, submit loading, final API call, post-submit navigation, and shell re-bootstrap.
- Step components render fields and emit small events such as `continue`, `back`, `submit`, and `update-field`.
- Back and forward navigation does not reset inputs because the DTO lives above the step components.
- Preflight API calls run before advancing and keep their loading and error state at the step transition boundary.
- Server errors are mapped with shared standardized-error helpers.
- API payloads stay camelCase and flow through the canonical `api` client.
- Route query is not used for drafts. It can restore view state, but form drafts are workflow state.
- Local storage is not used for drafts unless item requirements intentionally call for resumable drafts and define cleanup, privacy, and backend reconciliation rules.
- Backend-owned page/session flows move into a route-local store when the flow needs session tokens, saved progress, route-scope guards, or several sibling runtime components.

## Rules To Follow

- Keep the full multi-step form DTO in one parent view, parent workflow component, or route-local store.
- Keep the active step in that same owner unless the backend returns the active page or step.
- Do not let each step own a separate request fragment that the parent later stitches together.
- Do not duplicate form defaults in step components. Use the shared `createDefault...()` helper.
- Do not define independent step request types when the final submit uses one request contract. Use schema slices or typed field lists from the full contract.
- Let steps validate only the fields they render, then emit advancement or submission events.
- Run final full-form validation before the create/update API call.
- Map server field errors with `extractFirstFieldErrors(error)` and general messages with `getFirstApiErrorMessage(error, "...")`.
- Put preflight API calls at the step advancement boundary and advance only after success.
- Keep final submit ownership in the workflow owner, not in an arbitrary child step.
- Use a route-local Pinia store when the flow has shared runtime state across several local components, backend sessions, saved progress, route-scope guards, or repeated mutation actions.
- Do not store form drafts in route query params.
- Do not use local storage for drafts unless the feature explicitly requires resumable drafts and the implementation defines retention, clearing, and privacy behavior.
- Do not introduce a separate API service for a multi-step form. Add methods to the canonical `api` object in `frontend/src/utils/api.ts`.

## Refactor Signals

- A final submit builds its payload by merging `stepOneValues`, `stepTwoValues`, and `stepThreeValues`.
- Step components call unrelated final create/update endpoints while the parent also owns navigation or success handling.
- Back navigation clears previously entered fields because each step is mounted with private local defaults.
- A route query contains draft form values such as `email`, `firstName`, `answers`, or `password`.
- A component writes a form draft to local storage without a item requirement for resumable drafts.
- The same server error parsing appears in several step components.
- A parent forwards form values, errors, loading flags, and callbacks through several sibling step wrappers.
- A backend runtime flow keeps session token, current page, answers, and save state split across the view and several children.
- A preflight request runs after the UI has already advanced to the next step.
- A multi-step flow imports `axios`, creates a feature-specific API service, or bypasses `api`.
- Step schemas drift from the final request schema because they are maintained as separate contracts.

## Verification

For guidance-only changes, run the guidance builder and structural checks:

```bash
rg -c '^```' agents/guidance/frameworks/vue/examples/vue-multi-step-form.md
git diff --check -- agents/guidance/frameworks/vue/examples/vue-multi-step-form.md
python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean
```

For implementation work that follows this pattern, use focused frontend verification:

```bash
cd frontend
npm run type-check
npm run lint
```

Add or update component tests when the multi-step behavior is complex enough to regress. Cover at least:

- entering values on one step, moving forward, moving back, and preserving values
- client validation blocking advancement for step-local fields
- preflight errors blocking advancement and mapping field/general errors
- final submit validating the full request before the API call
- successful submit triggering the expected reload, redirect, toast, or shell re-bootstrap
- backend session flows ignoring stale load responses when route scope changes

## Why It Helps

This shape keeps the form's real state machine visible. Reviewers can find the draft owner, the active-step owner, the preflight boundary, and the final submit boundary without tracing several child-local refs. Users get stable back/forward behavior and consistent error messages, while future refactors can move a growing workflow into a route-local store without changing the request contract or inventing a second API path.
