---
id: framework-vue-example-notification-system
title: Vue Notification System Example
description: Example shared application notification pattern with one root-mounted viewport, a shell-owned store, and route-safe feedback rules.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - notifications
applies_to:
  - vue
status: active
order: 16
---

# Vue Notification System Example

## Scenario

- Use this pattern when a Vue route, dialog, drawer, route-local store, or shared workflow needs transient success, error, info, or warning feedback that should be visible above the current page.
- Use this pattern for cross-feature outcomes such as saved records, sent invitations, completed destructive actions, background workflow failures, or retryable non-field action failures.
- Do not use notifications as a replacement for field validation, form banners, blocking page errors, empty states, shell bootstrap errors, or table retry UI. Those stay inline with the form, page, table, or shell that owns the problem.
- Do not render local one-off toast stacks. The application has one notification viewport mounted near the app root and one store-backed queue under `src/views/application/`.

## Why This Shape Exists

- Notifications are app-level feedback, not page layout. Mounting the viewport once from `App.vue` keeps toasts above authenticated, guest, and fullscreen shells without every page copying fixed-position markup.
- The shell-level store is the lifecycle boundary. It owns notification IDs, creation timestamps, dismiss timers, tone helpers, and removal. Feature code should ask for a notification, not manage queue arrays or timers.
- A small composable gives feature code a stable API. Dialogs and stores call `useNotification().success(...)` or `useNotification().error(...)` without importing the store path or knowing how the viewport renders.
- Inline errors still matter. A failed form submit needs field errors and a form-level `AlertBanner`; a failed table fetch needs `PageStatusCard` or `AppTable` retry UI. A toast alone disappears and leaves the user without a local recovery path.
- Tone consistency keeps feedback predictable. Success confirms completed user actions, warning calls out non-blocking risk, error reports failed background or destructive actions, and info is reserved for neutral status messages.
- Centralizing the queue makes review simple. A reviewer can search for local toast stacks, direct store imports, and duplicate containers instead of auditing every route for ad hoc overlay behavior.

## Recommended Shape

### App Root Mounts One Toast Viewport

Keep the notification viewport beside the root shell switch in `frontend/src/App.vue`. It should render once for the whole app, outside individual route views and outside `ApplicationShellView`.

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

The viewport belongs at the same level as the shell choice because notifications must survive route changes and layout changes. A route view should never import `ApplicationToastViewport` or mount a second notification container for its own feature.

### Shell Store Owns Notification Lifecycle

Keep the queue in `frontend/src/views/application/notificationsStore.ts`. This is shell-level state, so it belongs with the application shell stores instead of a top-level `src/stores/` directory.

```typescript
// frontend/src/views/application/notificationsStore.ts
import { defineStore } from "pinia";
import { ref } from "vue";

export type ApplicationNotificationTone = "error" | "info" | "success" | "warning";

export interface ApplicationNotification {
  createdAt: number;
  durationMs: number;
  id: string;
  message: string;
  title: string;
  tone: ApplicationNotificationTone;
}

interface ShowNotificationInput {
  durationMs?: number;
  message: string;
  title: string;
  tone: ApplicationNotificationTone;
}

const defaultDurationMs = 4000;

export const useNotificationsStore = defineStore("applicationNotifications", () => {
  const notifications = ref<ApplicationNotification[]>([]);
  const dismissTimers = new Map<string, ReturnType<typeof window.setTimeout>>();

  function clearDismissTimer(notificationId: string) {
    const timer = dismissTimers.get(notificationId);
    if (timer === undefined) {
      return;
    }

    window.clearTimeout(timer);
    dismissTimers.delete(notificationId);
  }

  function scheduleDismiss(notification: ApplicationNotification) {
    clearDismissTimer(notification.id);
    if (notification.durationMs <= 0) {
      return;
    }

    const timer = window.setTimeout(() => {
      dismiss(notification.id);
    }, notification.durationMs);

    dismissTimers.set(notification.id, timer);
  }

  function show({ durationMs = defaultDurationMs, message, title, tone }: ShowNotificationInput) {
    const notification: ApplicationNotification = {
      createdAt: Date.now(),
      durationMs,
      id: crypto.randomUUID(),
      message,
      title,
      tone,
    };

    notifications.value = [...notifications.value, notification];
    scheduleDismiss(notification);
    return notification.id;
  }

  function dismiss(notificationId: string) {
    clearDismissTimer(notificationId);
    notifications.value = notifications.value.filter((notification) => notification.id !== notificationId);
  }

  function pushError(title: string, message: string, durationMs = 5000) {
    return show({ durationMs, message, title, tone: "error" });
  }

  function pushInfo(title: string, message: string, durationMs = defaultDurationMs) {
    return show({ durationMs, message, title, tone: "info" });
  }

  function pushSuccess(title: string, message: string, durationMs = defaultDurationMs) {
    return show({ durationMs, message, title, tone: "success" });
  }

  function pushWarning(title: string, message: string, durationMs = 4500) {
    return show({ durationMs, message, title, tone: "warning" });
  }

  return {
    dismiss,
    notifications,
    pushError,
    pushInfo,
    pushSuccess,
    pushWarning,
    show,
  };
});
```

The queue uses generated IDs instead of array indexes, immutable array replacement instead of mutating captured raw references, and a timer map so manual dismissal also clears the pending timeout. The current implementation does not dedupe by message or title. If item behavior later requires deduping, add that rule inside this store so every caller gets the same behavior.

### Composable Is The Feature-Facing API

Feature code should import `useNotification(...)`, not the store. The composable preserves one simple API and hides the shell-store location from route-local stores, dialogs, drawers, and components.

```typescript
// frontend/src/composables/useNotification.ts
import { useNotificationsStore } from "@/views/application/notificationsStore";

export function useNotification() {
  const notificationsStore = useNotificationsStore();

  return {
    error: (title: string, message: string, durationMs?: number) => notificationsStore.pushError(title, message, durationMs),
    info: (title: string, message: string, durationMs?: number) => notificationsStore.pushInfo(title, message, durationMs),
    success: (title: string, message: string, durationMs?: number) => notificationsStore.pushSuccess(title, message, durationMs),
    warning: (title: string, message: string, durationMs?: number) => notificationsStore.pushWarning(title, message, durationMs),
  };
}
```

Do not create feature-specific wrappers such as `useWorkspaceToast`, `usePricingToast`, or `apiNotificationService`. If a shared behavior belongs to every notification, add it to the store or composable. If it is only a copy variation, keep the title and message at the call site.

### Viewport Owns Overlay Markup And Accessibility

Keep positioning, transitions, ARIA behavior, tone icons, surfaces, and dismiss controls in `frontend/src/views/application/components/ApplicationToastViewport.vue`.

```vue
<!-- frontend/src/views/application/components/ApplicationToastViewport.vue -->
<template>
  <Teleport to="body">
    <div
      class="pointer-events-none fixed inset-x-4 top-4 z-[70] flex justify-end sm:inset-x-6"
      aria-live="polite"
      aria-relevant="additions text"
    >
      <TransitionGroup
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="translate-y-2 opacity-0"
        enter-to-class="translate-y-0 opacity-100"
        leave-active-class="transition duration-150 ease-in"
        leave-from-class="translate-y-0 opacity-100"
        leave-to-class="translate-y-2 opacity-0"
        move-class="transition duration-200 ease-out"
        tag="div"
        class="flex w-full max-w-sm flex-col gap-3"
      >
        <div
          v-for="notification in notificationsStore.notifications"
          :key="notification.id"
          class="pointer-events-auto"
          :role="notification.tone === 'error' ? 'alert' : 'status'"
        >
          <AppSurface
            :root-class="toastRootClass(notification.tone)"
            content-class="p-4"
          >
            <div class="flex items-start gap-3">
              <div
                class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full"
                :class="toastIconWrapperClass(notification.tone)"
              >
                <AppIcon
                  :icon="toastIcon(notification.tone)"
                  class="h-4 w-4"
                />
              </div>

              <div class="min-w-0 flex-1 space-y-1">
                <p class="text-body text-sm font-semibold">{{ notification.title }}</p>
                <p class="text-secondary text-sm leading-6">{{ notification.message }}</p>
              </div>

              <AppIconButton
                icon="close"
                label="Dismiss notification"
                tone="ghost"
                root-class="h-8 w-8 shrink-0 hover:bg-line/50"
                @click="notificationsStore.dismiss(notification.id)"
              />
            </div>
          </AppSurface>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
  import type { AppIconName } from "@/components/ui/appIcons";

  import AppIcon from "@/components/ui/AppIcon.vue";
  import AppIconButton from "@/components/ui/AppIconButton.vue";
  import AppSurface from "@/components/ui/AppSurface.vue";
  import type { ApplicationNotificationTone } from "@/views/application/notificationsStore";
  import { useNotificationsStore } from "@/views/application/notificationsStore";

  const notificationsStore = useNotificationsStore();

  function toastRootClass(tone: ApplicationNotificationTone) {
    if (tone === "success") {
      return "border-success/20";
    }

    if (tone === "warning") {
      return "border-warning/20";
    }

    if (tone === "info") {
      return "border-info/20";
    }

    return "border-error/20";
  }

  function toastIcon(tone: ApplicationNotificationTone): AppIconName {
    if (tone === "success") {
      return "success";
    }

    if (tone === "warning") {
      return "warning";
    }

    if (tone === "info") {
      return "info";
    }

    return "close";
  }

  function toastIconWrapperClass(tone: ApplicationNotificationTone) {
    if (tone === "success") {
      return "bg-success/12 text-success";
    }

    if (tone === "warning") {
      return "bg-warning/12 text-warning";
    }

    if (tone === "info") {
      return "bg-info/12 text-info";
    }

    return "bg-error/12 text-error";
  }
</script>
```

The viewport can import the notification store directly because it renders the queue. Feature views should not. Keeping this split lets the rendering change from a custom surface to a PrimeVue wrapper later without changing feature workflows.

### Success Notifications Confirm Completed Mutations

Use success notifications after the backend mutation succeeds and the local state has been updated or scheduled for reload. The notification should name the completed action and explain the outcome in one short sentence.

```vue
<!-- frontend/src/views/vendors/components/VendorDialog.vue -->
<script setup lang="ts">
  import { useNotification } from "@/composables/useNotification";
  import { useSchemaValidation } from "@/composables/useSchemaValidation";
  import { createDefaultVendorInput, vendorPartnerInputSchema } from "@/types/partner/VendorInputInterface";
  import type { VendorInterface } from "@/types/partner/VendorInterface";
  import { api } from "@/utils/api";
  import { extractFirstFieldErrors, getFirstApiErrorMessage } from "@/utils/errorHandling";
  import { ref } from "vue";

  interface Props {
    open?: boolean;
    vendor?: VendorInterface | null;
    organizationId: number | null;
  }

  const emit = defineEmits<{
    close: [];
    save: [];
  }>();

  const props = defineProps<Props>();
  const notification = useNotification();
  const { clearErrors, errors: validationErrors, setErrors, validate, values: formValues } = useSchemaValidation(vendorPartnerInputSchema, createDefaultVendorInput());
  const errorMessage = ref("");
  const isSubmitting = ref(false);

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

The failed submit stays inline through `validationErrors` and `errorMessage`. The user needs to see which field or form problem blocks progress inside the dialog. A toast would be easy to miss and would not attach the error to the failing inputs.

### Route-Local Stores Can Emit Workflow Success

When a route-local store owns the mutation, it can call the composable directly. This keeps the parent route focused on page composition and avoids forwarding `onSuccess` callbacks through several local components.

```typescript
// frontend/src/views/notificationDetail/notificationDetailStore.ts
import { useNotification } from "@/composables/useNotification";
import { useSchemaValidation } from "@/composables/useSchemaValidation";
import { createDefaultNotificationTemplateInput, notificationTemplateInputSchema } from "@/types/notification/NotificationTemplateInputInterface";
import { api } from "@/utils/api";
import { extractFirstFieldErrors, getFirstApiErrorMessage } from "@/utils/errorHandling";
import { useAppShellStore } from "@/views/application/appShellStore";
import { defineStore } from "pinia";
import { computed, ref } from "vue";

export const useNotificationDetailStore = defineStore("notificationDetail", () => {
  const appShellStore = useAppShellStore();
  const notification = useNotification();

  const errorMessage = ref("");
  const isSaving = ref(false);
  const templateId = ref<number | null>(null);
  const { errors: fieldErrors, setErrors, validate, values: formValues } = useSchemaValidation(notificationTemplateInputSchema, createDefaultNotificationTemplateInput());

  const organizationId = computed(() => appShellStore.selectedOrganizationId);
  const isCreateMode = computed(() => !templateId.value);

  async function save() {
    if (!organizationId.value) {
      errorMessage.value = "Select an organization before saving notification template changes.";
      return false;
    }

    if (!(await validate())) {
      return false;
    }

    isSaving.value = true;
    errorMessage.value = "";

    try {
      const wasCreateMode = isCreateMode.value;
      const savedTemplate = isCreateMode.value
        ? await api.notificationTemplates.create(organizationId.value, formValues)
        : await api.notificationTemplates.update(organizationId.value, templateId.value as number, formValues);

      templateId.value = savedTemplate.id;

      if (wasCreateMode) {
        notification.success("Template created", "The notification template is ready to use.");
      } else {
        notification.success("Template updated", "Changes to the notification template were saved.");
      }

      return true;
    } catch (error) {
      setErrors(extractFirstFieldErrors(error));
      errorMessage.value = getFirstApiErrorMessage(error, isCreateMode.value ? "Unable to create this notification template." : "Unable to save notification template changes.");
      return false;
    } finally {
      isSaving.value = false;
    }
  }

  return {
    errorMessage,
    fieldErrors,
    formValues,
    isSaving,
    save,
    templateId,
    organizationId,
  };
});
```

The store still separates local UI state from global feedback. Form errors stay in `fieldErrors` and `errorMessage`; the toast confirms the save after the record is persisted.

### Use Error Notifications For Destructive Or Background Failures

Use an error notification when the failed action is not naturally tied to a visible form banner, or when the user just confirmed a destructive or background action and needs immediate global feedback.

```typescript
// frontend/src/views/catalogEntryDetail/components/CatalogEntryVendorsSection.vue
import { useNotification } from "@/composables/useNotification";
import { api } from "@/utils/api";
import { getFirstApiErrorMessage } from "@/utils/errorHandling";
import { ref } from "vue";

const notification = useNotification();
const assignmentPendingRemoval = ref<CatalogVendorInterface | null>(null);

async function handleConfirmedUnlink() {
  if (!props.organizationId || !props.workspaceId || !props.catalogEntryId || !assignmentPendingRemoval.value) {
    assignmentPendingRemoval.value = null;
    return;
  }

  try {
    await api.catalogEntryVendors.unlink(props.organizationId, props.workspaceId, props.catalogEntryId, assignmentPendingRemoval.value.id);
    notification.success("Vendor unlinked", "The vendor was removed from the catalog entry.");
    assignmentPendingRemoval.value = null;
    await loadVendors();
  } catch (error) {
    notification.error("Unable to unlink vendor", getFirstApiErrorMessage(error, "The vendor could not be removed from this catalog entry."));
  }
}
```

The unlink action happens after a confirmation flow and does not have a field-level recovery path. A global error notification is appropriate because the table remains visible and the message describes the failed action. If the table reload itself fails, use the table or page error state instead of only showing a toast.

### Keep Page And Form Errors Inline

Use `AlertBanner`, `PageStatusCard`, `AppTable`, and form field errors for blocking or recoverable local failures. Notifications should supplement these flows only when there is a cross-route outcome to confirm.

```vue
<template>
  <AppDrawer
    :open="open"
    title="Create vendor"
    @close="emit('close')"
  >
    <AlertBanner
      v-if="errorMessage"
      :message="errorMessage"
      tone="warning"
    />

    <form @submit.prevent="void submitForm()">
      <AppTextField
        v-model="formValues.name"
        label="Name"
        :error="validationErrors.name"
      />

      <AppButton
        button-type="submit"
        label="Create vendor"
        :disabled="isSubmitting"
      />
    </form>
  </AppDrawer>
</template>
```

Do not add `notification.error(...)` to every caught form submit. The inline banner and field messages are the durable recovery UI. Reserve error notifications for failures where the current surface otherwise has no obvious place to show the problem.

## Things To Notice

- `ApplicationToastViewport` is mounted once in `App.vue`, not inside `ApplicationShellView`, route views, dialogs, or drawers.
- The notification store lives under `src/views/application/` because notifications are shell-level application feedback.
- Feature code imports `useNotification` from `@/composables/useNotification`; only the viewport should import `useNotificationsStore` for rendering.
- The store owns `crypto.randomUUID()`, `createdAt`, `durationMs`, timer cleanup, tone-specific helpers, and manual dismissal.
- The current lifecycle removes notifications by timer or explicit dismiss. There is no feature-local queue cleanup and no current dedupe behavior.
- Success notifications happen after successful API calls, not before optimistic persistence unless the optimistic workflow has a separate rollback rule.
- Server validation errors still flow through `extractFirstFieldErrors(...)` and `getFirstApiErrorMessage(...)` so field errors and form banners stay close to the failing form.
- Blocking fetch errors stay in shared page or table components with retry behavior. A disappearing toast is not enough for a page that cannot render data.
- Tone names are semantic: `success`, `warning`, `info`, and `error`. Do not introduce one-off visual severities such as `danger`, `critical`, or `positive` unless the shared store and viewport are deliberately extended.

## Rules To Follow

- Mount exactly one `ApplicationToastViewport` near the app root.
- Do not create top-level `src/stores/notification.ts`, route-local toast stores, local toast arrays, or route-local notification containers.
- Do not import `useNotificationsStore` from feature routes, dialogs, or route-local stores. Use `useNotification`.
- Keep notification title and message strings short, concrete, and action-oriented.
- Show success notifications only after a mutation, background action, or generated workflow has actually completed.
- Use inline field errors and an inline `AlertBanner` for form submit failures.
- Use `PageStatusCard` or `AppTable` error and retry props for blocking list/detail fetch failures.
- Use error notifications for destructive-action failures, background task failures, or action failures that do not have a better local error surface.
- Use warning notifications for non-blocking risk or partial completion. Do not use warning as a generic failed-submit tone.
- Use info notifications sparingly for neutral background status. Do not use info as marketing copy or page instructions.
- Keep timer, dismissal, dedupe, max-stack, and accessibility changes centralized in the store or viewport.
- Do not parse Axios errors in notification call sites. Use shared standardized-error helpers such as `getFirstApiErrorMessage(...)`.
- Do not show duplicate feedback for the same event, such as an inline success banner and a success notification, unless item requirements explicitly need both.

## Refactor Signals

- A route view contains `Teleport to="body"` for a toast, a fixed top-right notification container, or a local `TransitionGroup` for messages.
- A feature file imports `useNotificationsStore` instead of `useNotification`.
- A modern feature adds or expands a top-level `src/stores/` or `src/services/` notification module.
- Catch blocks call `notification.error(...)` for every form submit while also setting field errors and `errorMessage`.
- A page fetch failure only shows a toast and leaves the page blank, with no `PageStatusCard`, `AppTable`, or retry action.
- Multiple components copy the same notification duration, icon, or tone classes instead of using the shared viewport.
- Notifications use vague titles such as `Success`, `Error`, or `Done` when the action can be named.
- Destructive actions fail silently or only log to the console after the user confirms the action.
- A component manually clears old notification timers, filters local toast arrays, or dedupes messages outside `notificationsStore.ts`.

## Verification

- Run the guidance build after editing this example:

```bash
python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean
```

- Check the authored example for balanced code fences and generated-output presence:

```bash
rg -c '^```' agents/guidance/frameworks/vue/examples/vue-notification-system.md
rg -n "Vue Notification System Example" /tmp/guidance-examples-build/codex/AGENTS.md /tmp/guidance-examples-build/opencode/AGENTS.md
```

- Check the frontend structure when changing notification behavior:

```bash
rg -n "<ApplicationToastViewport" frontend/src
rg -n "useNotificationsStore" frontend/src
rg -n "useNotification" frontend/src/views frontend/src/components frontend/src/composables
```

- A healthy structure has one `ApplicationToastViewport` mount in `frontend/src/App.vue`, direct `useNotificationsStore` usage in the viewport and composable/store implementation, and feature call sites routed through `useNotification`.
- When changing TypeScript or Vue code, also run:

```bash
cd frontend
npm run lint
npm run type-check
```

- Preserve or update focused tests such as `frontend/tests/notification-system-guidance.test.ts` when changing the store, composable, or root-mounted viewport contract.

## Why It Helps

- Users get consistent feedback across route changes, shell modes, and dialog workflows.
- Route views stay focused on page composition instead of owning global overlay infrastructure.
- Forms remain usable because validation and recovery errors stay next to the fields that need attention.
- Reviewers get clear search targets for duplicate toast stacks, stale store paths, missing inline errors, and incorrect tone usage.
- Future changes to animation, accessibility, max stack behavior, timeout policy, or visual styling happen in one shell-owned place instead of across many pages.
