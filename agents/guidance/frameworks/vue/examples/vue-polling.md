---
id: framework-vue-example-polling
title: Vue Polling Example
description: Example component-scoped polling with lifecycle cleanup, explicit start and stop ownership, and guarded refresh callbacks.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - polling
applies_to:
  - vue
status: active
order: 11
---

# Vue Polling Example

## Scenario

- Use this pattern when a route view, route-local component, drawer, preview panel, or status card needs auto-refresh behavior tied to component lifecycle, visibility, or a user-controlled toggle.
- Use this pattern when the page already has a normal load or refresh action and the automatic refresh should call that same action on an interval.
- Use this pattern when polling should stop as soon as the required organization, workspace, route param, open state, or user toggle is no longer valid.
- Use a dedicated task-polling helper instead when the backend returns a `task_id` and the frontend must wait for a completed, failed, or timed-out task result.

## Why This Shape Exists

- Timers are easy to leak. A route component can unmount, a drawer can close, or an organization can change while a manually created `setInterval(...)` keeps firing in the background. `usePolling` centralizes interval creation and clears the interval through Vue lifecycle cleanup.
- Polling has two separate concerns: timer lifecycle and data loading. `usePolling` owns start, stop, interval scheduling, `autoStart`, `immediate`, `isPolling`, and unmount cleanup. The route view or route-local store still owns request guards, loading flags, errors, stale-response checks, and the actual API call.
- `shouldStop` is for durable stop conditions. Missing organization or workspace context, a closed drawer, a disabled toggle, or a completed status should stop the interval. A transient in-flight request should usually be guarded inside the callback so polling stays enabled and can try again on the next tick.
- The composable accepts async callbacks, but it does not serialize them for the caller. The callback must avoid starting a second load while the first one is still running.
- Explicit `startPolling()` and `stopPolling()` calls make visibility-driven polling readable. A reviewer should be able to see exactly which user action, route state, or component prop starts and stops the timer.
- Polling should refresh existing data, not replace shared retry and loading patterns. First-load blocking state, inline refresh errors, and retry buttons still belong to the page or table components described in the loading/error example.

## Recommended Shape

### Shared Composable Owns Timer Lifecycle

Keep timer mechanics inside `frontend/src/composables/usePolling.ts`. Components should not call `window.setInterval(...)` or `window.clearInterval(...)` directly when they need repeated refresh behavior.

```typescript
// frontend/src/composables/usePolling.ts
export function usePolling(
  callback: () => void | Promise<void>,
  shouldStop: () => boolean,
  intervalMs: number,
  options: UsePollingOptions = {},
): UsePollingReturn {
  const autoStart = options.autoStart ?? true;
  const immediate = options.immediate ?? true;
  const isPolling = ref(false);
  let intervalId: ReturnType<typeof window.setInterval> | null = null;

  function stopPolling() {
    if (intervalId !== null) {
      window.clearInterval(intervalId);
      intervalId = null;
    }

    isPolling.value = false;
  }

  function runPollingCallback() {
    if (shouldStop()) {
      stopPolling();
      return;
    }

    void callback();
  }

  function startPolling() {
    if (intervalId !== null) {
      return;
    }

    if (shouldStop()) {
      stopPolling();
      return;
    }

    isPolling.value = true;

    if (immediate) {
      runPollingCallback();
      if (shouldStop()) {
        stopPolling();
        return;
      }
    }

    intervalId = window.setInterval(runPollingCallback, intervalMs);
  }

  onBeforeUnmount(stopPolling);

  if (autoStart) {
    startPolling();
  }

  return {
    isPolling,
    startPolling,
    stopPolling,
  };
}
```

The composable is intentionally small. It does not know about organizations, route params, stores, API methods, or UI text. Callers provide those decisions through `callback`, `shouldStop`, and explicit start or stop wiring.

### Route-Local Store Still Owns The Refresh Action

The store or route view should expose one normal load action that both manual retry and polling can call. That load action still guards required scope, sets loading and error state, calls the canonical `api`, and ignores stale responses.

```typescript
// frontend/src/views/organizationAccess/organizationAccessStore.ts
export const useOrganizationAccessStore = defineStore("organizationAccess", () => {
  const appShellStore = useAppShellStore();

  const accessErrorMessage = ref("");
  const isAccessLoading = ref(false);
  const memberships = ref<OrganizationMembershipInterface[]>([]);
  const invitations = ref<OrganizationInvitationInterface[]>([]);
  let refreshDataRequestId = 0;

  const organizationId = computed(() => appShellStore.selectedOrganizationId);

  async function refreshData() {
    const requestId = ++refreshDataRequestId;
    const activeOrganizationId = organizationId.value;
    accessErrorMessage.value = "";

    if (!activeOrganizationId) {
      isAccessLoading.value = false;
      memberships.value = [];
      invitations.value = [];
      return;
    }

    isAccessLoading.value = true;

    try {
      const nextAccess = await api.organizationAccess.list(activeOrganizationId);
      if (requestId !== refreshDataRequestId || organizationId.value !== activeOrganizationId) {
        return;
      }

      memberships.value = nextAccess.memberships;
      invitations.value = nextAccess.invitations;
    } catch (error) {
      if (requestId !== refreshDataRequestId || organizationId.value !== activeOrganizationId) {
        return;
      }

      accessErrorMessage.value = getFirstApiErrorMessage(error, "Unable to load organization access.");
    } finally {
      if (requestId === refreshDataRequestId && organizationId.value === activeOrganizationId) {
        isAccessLoading.value = false;
      }
    }
  }

  return {
    accessErrorMessage,
    isAccessLoading,
    refreshData,
    organizationId,
  };
});
```

Do not put interval state in the store just because the store owns the data. Stores do not have component lifecycle hooks, and many route stores can be created outside a visible component. Let the visible component own whether polling is active.

### Component Owns The Polling Toggle

Call `usePolling(...)` from `<script setup>` or another component-owned composable. Use `autoStart: false` when polling depends on a visible panel, a route-local toggle, or an enabled auto-refresh switch. Use `immediate: false` when the page already performs its first load through a route watch or `onMounted(...)`.

```typescript
// frontend/src/views/organizationAccess/components/OrganizationAccessAutoRefreshToggle.vue
const organizationAccessStore = useOrganizationAccessStore();

const autoRefreshEnabled = ref(false);
const countdownSeconds = ref(30);

const shouldStopAutoRefresh = () => {
  return !autoRefreshEnabled.value || !organizationAccessStore.organizationId;
};

const { isPolling, startPolling, stopPolling } = usePolling(
  () => {
    if (organizationAccessStore.isAccessLoading) {
      return;
    }

    if (countdownSeconds.value > 1) {
      countdownSeconds.value -= 1;
      return;
    }

    countdownSeconds.value = 30;
    void organizationAccessStore.refreshData();
  },
  shouldStopAutoRefresh,
  1000,
  { autoStart: false, immediate: false },
);

watch(autoRefreshEnabled, (enabled) => {
  countdownSeconds.value = 30;

  if (enabled) {
    startPolling();
    return;
  }

  stopPolling();
});

watch(
  () => organizationAccessStore.organizationId,
  () => {
    countdownSeconds.value = 30;

    if (autoRefreshEnabled.value && organizationAccessStore.organizationId) {
      startPolling();
      return;
    }

    stopPolling();
  },
);
```

This component does not call the API directly. It delegates the actual refresh to the route-local store so the same stale-response guard, loading state, error message, and table retry behavior apply to manual and automatic refreshes.

### Visibility-Driven Polling Starts And Stops From Props

For a drawer, preview panel, or detail card, use the visible/open prop as a stop condition. Keep `usePolling(...)` called unconditionally in setup, then start or stop polling from a watcher.

```typescript
const props = defineProps<{
  open: boolean;
  organizationId: number | null;
  templateId: number | null;
}>();

const isRefreshingPreview = ref(false);

const shouldStopPreviewPolling = () => {
  return !props.open || !props.organizationId || !props.templateId;
};

const { startPolling: startPreviewPolling, stopPolling: stopPreviewPolling } = usePolling(
  async () => {
    if (isRefreshingPreview.value) {
      return;
    }

    isRefreshingPreview.value = true;

    try {
      await notificationDetailStore.refreshPreview();
    } finally {
      isRefreshingPreview.value = false;
    }
  },
  shouldStopPreviewPolling,
  5_000,
  { autoStart: false, immediate: true },
);

watch(
  () => [props.open, props.organizationId, props.templateId],
  () => {
    if (shouldStopPreviewPolling()) {
      stopPreviewPolling();
      return;
    }

    startPreviewPolling();
  },
  { immediate: true },
);
```

`immediate: true` is useful when opening the panel should refresh the preview right away and then keep refreshing. The callback still guards concurrent loads because a slow request can overlap with the next tick.

### Manual Refresh And Retry Use The Same Load Path

Polling does not replace explicit user controls. The page should still expose manual refresh or retry through shared components, and those controls should call the same store action the poller calls.

```vue
<OrganizationAccessTable
  :rows="organizationAccessStore.accessRows"
  :loading="organizationAccessStore.isAccessLoading"
  :error-message="organizationAccessStore.accessErrorMessage"
  @retry="void organizationAccessStore.refreshData()"
/>

<OrganizationAccessAutoRefreshToggle />
```

Shared wrappers such as `PageStatusCard`, `AppTable`, and route-local table components remain responsible for first-load blocking state, empty state, inline refresh errors, and retry actions.

### Avoid Manual Intervals In Components

```typescript
// Avoid
let intervalId: ReturnType<typeof window.setInterval> | null = null;

onMounted(() => {
  intervalId = window.setInterval(() => {
    void organizationAccessStore.refreshData();
  }, 30_000);
});

onBeforeUnmount(() => {
  if (intervalId) {
    window.clearInterval(intervalId);
  }
});
```

This shape spreads lifecycle mechanics across the component and makes every caller re-solve duplicate start, stop, double-start, and cleanup behavior. Prefer `usePolling(...)` so those mechanics stay in one tested composable.

## Things To Notice

- `usePolling` lives in the component, where Vue lifecycle hooks are available.
- The store or route view owns the actual load action, loading flags, error messages, stale-response guards, and canonical `api` call.
- `autoStart: false` keeps ownership explicit for visibility-driven or toggle-driven polling.
- `immediate: false` avoids duplicate first loads when the route already loads through `watch(..., { immediate: true })` or `onMounted(...)`.
- `immediate: true` is appropriate when opening a visible panel should refresh immediately before the first interval tick.
- `shouldStop` handles durable stop conditions such as disabled toggles, closed panels, missing IDs, completed statuses, or lost organization context.
- The polling callback guards transient busy states such as `isLoading`, `isRefreshing`, or `isSubmitting` so it does not overlap requests.
- Manual refresh, retry buttons, and automatic polling call the same load action.
- Task completion polling is a separate pattern because it needs completion, failure, progress, timeout, and Promise resolution semantics.

## Rules To Follow

- Use `usePolling` for Vue component auto-refresh behavior. Do not add manual `setInterval(...)` or `clearInterval(...)` calls in route views or route-local components.
- Call `usePolling(...)` from component setup or a composable that is only used by components. Do not call it inside Pinia stores, API modules, router guards, or non-Vue utility files.
- Keep `shouldStop` deterministic and cheap. It should read existing refs, props, route params, or store state; it should not make API calls or mutate state.
- Guard concurrent work inside the callback. If the callback can start an API request, return early when the relevant `isLoading`, `isRefreshing`, `isSaving`, or `isSubmitting` flag is already true.
- Prefer `autoStart: false` when polling depends on visibility, a user toggle, selected workspace context, or route params.
- Prefer `immediate: false` when the normal route load already runs immediately. Prefer `immediate: true` only when starting polling should also perform an immediate refresh.
- Stop polling when a panel closes, a toggle turns off, a route id disappears, organization or workspace context becomes invalid, or the backend state reaches a terminal status.
- Keep polling intervals named or obvious. Avoid magic one-off intervals scattered across components; use readable constants such as `AUTO_REFRESH_INTERVAL_MS` for repeated or item-significant intervals.
- Do not clear existing rows just because an automatic refresh fails. Let the shared loading/error pattern keep stale useful rows visible and show an inline warning or retry action.
- Do not use polling for one-time delayed UI feedback, copy confirmations, debounced search, or task completion flows. Use the dedicated composable for those concerns.

## Refactor Signals

- A component declares `let intervalId`, calls `window.setInterval(...)`, or calls `window.clearInterval(...)`.
- A Pinia store starts an interval or tries to use Vue lifecycle hooks directly.
- A polling callback can launch overlapping API requests because it never checks the relevant loading or refreshing flag.
- `shouldStop` includes transient loading state, causing polling to permanently stop during normal requests.
- A route has separate manual-refresh and auto-refresh implementations that call different API methods or update different error flags.
- A visible drawer, modal, or preview keeps polling after it closes.
- Polling continues after organization, workspace, route param, selected record, or access context changes.
- Automatic refresh failures blank out the table or page even though stale rows are still useful.
- A backend task wait loop is implemented in a component instead of a focused task helper with timeout and success/failure handling.

## Verification

- Run the composable test when changing `usePolling` behavior:

```bash
node --test frontend/tests/use-polling.test.ts
```

- Run frontend type checking when adding or changing a polling consumer:

```bash
cd frontend
npm run type-check
```

- Search for manual intervals before finishing polling work:

```bash
rg -n "setInterval|clearInterval|usePolling|startPolling|stopPolling" frontend/src
```

- For guidance changes, rebuild generated agent output instead of editing generated files:

```bash
python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean
```

## Why It Helps

- Polling behavior is consistent, lifecycle-safe, and easy to shut down cleanly.
- Route views and stores keep one source of truth for loading, retry, stale-response, and error behavior.
- Components stay readable because timer ownership, visibility wiring, and refresh ownership are separate.
- Reviews can quickly spot leaked intervals, overlapping refreshes, stale organization or workspace context, and task-polling logic in the wrong layer.
