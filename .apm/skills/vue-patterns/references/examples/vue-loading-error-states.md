---
id: framework-vue-example-loading-error-states
title: Vue Loading And Error States Example
description: Example shared loading, error, and retry UI for page-level fetch states.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - ui
applies_to:
  - vue
status: active
order: 8
---

# Vue Loading And Error States Example

## Scenario

- Use this pattern when a Vue route, route-local store, shell store, table, drawer, or panel fetches data and needs predictable loading, error, retry, and empty behavior.
- Use this pattern when a route changes organization, workspace, route params, or filters while a previous request may still be in flight.
- Use this pattern when a page already has rows and a refresh fails: keep the useful stale rows visible, show the error inline, and let the shared retry action reload the same store action.
- Use this pattern when a shell-level bootstrap request must finish before authenticated route content renders.

## Why This Shape Exists

- Loading, error, empty, and retry states are part of the app's shared interaction language. Rebuilding them route by route creates visual drift, duplicate spinners, inconsistent retry tone, and unclear screen-reader behavior.
- Shell bootstrap loading is different from route loading. The shell owns user, organization, workspace, and access context before route pages render; route-local stores should not call the bootstrap endpoint or invent their own session-loading branch.
- Route-local loading state is different from mutation loading state. A page fetch uses `isLoading` and `errorMessage`; a save button or drawer uses `isSaving`, `isSubmitting`, or a similarly narrow flag so the page does not blank itself during a mutation.
- Empty state is not an error state. Empty means the request succeeded and returned no rows. Error means the request failed and needs a warning-toned message plus retry behavior.
- Stale async responses are a real workspace risk because organization, workspace, route params, and filters can change while a request is pending. Stores must capture the active scope before awaiting and ignore late responses that no longer match.
- Waiting or optimistic UI should have one owner. If a shared waiting card, table loading state, optimistic row, or assistant waiting message is already visible, do not render a second local placeholder for the same pending work.

## Recommended Shape

### Shared Status Card Owns Blocking Feedback

Keep the shared status component responsible for the spinner, warning alert, and retry button. Route views should pass `title`, `description`, `errorMessage`, and `showRetry`; they should not rebuild the same centered layout, spinner, alert, and retry classes locally.

```vue
<!-- frontend/src/components/page/PageStatusCard.vue -->
<template>
  <AppSurface
    root-class="mx-auto w-full max-w-lg"
    content-class="space-y-3 p-6 text-center"
  >
    <div
      v-if="showLoading"
      class="flex justify-center"
    >
      <AppLoadingSpinner size="lg" />
    </div>

    <p class="text-body text-heading-sm font-medium">{{ title }}</p>
    <p
      v-if="description"
      class="text-secondary text-base-body"
    >
      {{ description }}
    </p>

    <AppProgressBar
      v-if="showLoading"
      mode="indeterminate"
      root-class="mx-auto max-w-xs"
    />

    <AlertBanner
      v-if="errorMessage"
      :message="errorMessage"
      tone="warning"
    />

    <div
      v-if="showRetry"
      class="pt-2"
    >
      <AppButton
        :label="retryLabel"
        tone="warning"
        @click="emit('retry')"
      />
    </div>

    <slot />
  </AppSurface>
</template>
```

If the button wrapper does not yet expose a warning tone, add that tone to the shared `AppButton` wrapper first. Do not work around it by styling one-off retry buttons inside route views.

### Shared Table Owns Loading, Empty, Inline Error, And Retry

Use the shared table wrapper for repeated resource lists. It should block on first load, show a blocking error when no rows can be displayed, show an inline warning when stale rows still exist, and show the empty state only after a successful non-loading request with no rows.

```vue
<!-- frontend/src/components/page/AppTable.vue -->
<template>
  <div class="space-y-3">
    <div
      v-if="showBlockingLoading"
      class="flex justify-center px-4 py-6"
    >
      <PageStatusCard
        :title="loadingTitle"
        :description="loadingDescription"
        show-loading
      />
    </div>

    <div
      v-else-if="showBlockingError"
      class="flex justify-center px-4 py-6"
    >
      <PageStatusCard
        :title="errorTitle"
        :error-message="errorMessage"
        :show-retry="true"
        @retry="emit('retry')"
      />
    </div>

    <template v-else>
      <div
        v-if="showInlineError"
        class="max-w-3xl"
      >
        <AlertBanner
          :message="errorMessage || ''"
          tone="warning"
        />
      </div>

      <AppSurface
        root-class="overflow-hidden shadow-none"
        content-class="p-0"
      >
        <table class="divide-line min-w-full divide-y">
          <tbody v-if="hasRows">
            <slot name="rows" />
          </tbody>

          <tbody v-else>
            <tr>
              <td
                colspan="100"
                class="px-4 py-9 text-center"
              >
                <p class="text-body text-heading-sm font-medium">{{ emptyTitle }}</p>
                <p class="text-secondary text-base-body">{{ emptyMessage }}</p>
                <slot name="emptyAction" />
              </td>
            </tr>
          </tbody>
        </table>
      </AppSurface>
    </template>
  </div>
</template>

<script setup lang="ts">
  const showBlockingLoading = computed(() => props.loading && !props.hasRows);
  const showBlockingError = computed(() => !props.loading && Boolean(props.errorMessage) && !props.hasRows);
  const showInlineError = computed(() => Boolean(props.errorMessage) && props.hasRows);
  const loadingTitle = computed(() => `Loading ${props.loadingLabel}`);
  const loadingDescription = computed(() => `Preparing the latest ${props.loadingLabel} for this view`);
  const errorTitle = computed(() => `Unable to load ${props.loadingLabel}`);
</script>
```

### Route-Local Store Owns Fetch State And Stale Guards

Keep route-local loading and error flags in the route-local Pinia store when multiple local components share the state. Capture the active organization, workspace, route param, and request id before awaiting. Only write rows, errors, and loading flags if the response still belongs to the current scope.

```typescript
// frontend/src/views/rateCards/rateCardsStore.ts
export const useRateCardsStore = defineStore("rateCards", () => {
  const appShellStore = useAppShellStore();

  const workspaceId = ref<number | null>(null);
  const workspaceFilter = ref<"all" | number>("all");
  const errorMessage = ref("");
  const isLoading = ref(false);
  const rateCards = ref<RateCardInterface[]>([]);
  let loadRateCardsRequestId = 0;

  const organizationId = computed(() => appShellStore.selectedOrganizationId);
  const selectedWorkspaceId = computed(() => {
    if (workspaceId.value) {
      return workspaceId.value;
    }

    return workspaceFilter.value === "all" ? null : workspaceFilter.value;
  });

  const rateCardRows = computed<RateCardsTableRow[]>(() => {
    return rateCards.value.map((profile) => ({
      id: profile.id,
      primaryLabel: profile.name,
      secondaryLabel: `${profile.linkedCatalogEntryCount} catalogEntries linked`,
      statusLabel: formatEnumLabel(profile.status),
      statusTone: profile.status === RateCardStatus.ACTIVE ? "success" : "neutral",
      updatedLabel: formatDate(profile.updatedTs),
      description: profile.description,
      linkedCatalogEntryCountLabel: String(profile.linkedCatalogEntryCount),
      linkedPlanCountLabel: String(profile.linkedPlanCount),
    }));
  });

  async function load() {
    const requestId = ++loadRateCardsRequestId;
    const activeOrganizationId = organizationId.value;
    const activeWorkspaceId = selectedWorkspaceId.value;
    errorMessage.value = "";

    if (!activeOrganizationId || !activeWorkspaceId) {
      isLoading.value = false;
      rateCards.value = [];
      errorMessage.value = !activeOrganizationId
        ? "Select an organization before viewing rate cards."
        : "Select a workspace before viewing rate cards.";
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

  return {
    errorMessage,
    isLoading,
    load,
    rateCardRows,
    selectedWorkspaceId,
    organizationId,
  };
});
```

Use scope comparisons instead of a request counter when the route state itself is enough to prove freshness. Use a request counter when the same scope can be reloaded repeatedly and only the latest response should win.

### Route View Wires Shared Components To Store Actions

The route view should read like page composition: header actions, gating state, shared table, route-local dialogs. It should pass the store's state to shared components and wire retry back to the same store action.

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
          label="Refresh"
          tone="ghost"
          icon="refresh"
          :disabled="rateCardsStore.isLoading"
          @click="void rateCardsStore.load()"
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
      @select="handleOpenRateCard"
    />

    <RateCardDrawer />
  </div>
</template>
```

Do not add a second page-level spinner above `RateCardsTable`; the table already owns first-load blocking state, blocking error state, inline refresh error state, empty state, and retry behavior.

### Shell Bootstrap Has Its Own Loading And Error State

Keep shell bootstrap state under `src/views/application/`. The application shell renders a single shell-level loading or error surface until user, organization, workspace, and access context are ready.

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
    errorMessage,
    hasInitialized,
    initialize,
    isAuthenticated,
    isLoading,
    selectedWorkspaceId,
    selectedOrganizationId,
  };
});
```

```vue
<!-- frontend/src/views/application/ApplicationShellView.vue -->
<template>
  <MainContentPane v-if="appShellStore.hasInitialized">
    <slot />
  </MainContentPane>

  <MainContentPane v-else>
    <ApplicationShellLoadingState
      :error-message="appShellStore.errorMessage"
      @retry="void appShellStore.reload()"
    />
  </MainContentPane>
</template>
```

```vue
<!-- frontend/src/views/application/components/ApplicationShellLoadingState.vue -->
<template>
  <PageStatusCard
    title="Loading workspace"
    description="Preparing organization context, user access, and the first workspace view"
    :error-message="errorMessage"
    :show-loading="!errorMessage"
    :show-retry="Boolean(errorMessage)"
    @retry="emit('retry')"
  />
</template>
```

Route views should consume the initialized shell store. They should not call `api.auth.bootstrap()`, create their own `isBootstrapping` flag, or show another full-page bootstrap loading state inside the router outlet.

### Do Not Render Duplicate Waiting Or Optimistic States

Use one visible pending state per workflow. If a shared table is already blocking on `loading`, do not add a second local spinner beside it. If a chat, assistant, import, or generation workflow already renders a waiting card, do not append another empty optimistic item for the same request.

```vue
<template>
  <AssistantMessages :messages="messages" />

  <AssistantWaitingCard
    v-if="isAssistantWaiting"
    title="Generating response"
  />
</template>
```

```typescript
async function submitPrompt(prompt: string) {
  isAssistantWaiting.value = true;

  try {
    const response = await api.assistant.submit({ prompt });
    messages.value = [...messages.value, response.message];
  } finally {
    isAssistantWaiting.value = false;
  }
}
```

Do not also push a blank assistant message before the response arrives if `AssistantWaitingCard` already communicates that the request is pending.

## Things To Notice

- `PageStatusCard`, `PageCenteredState`, `AppTable`, and `EntityIndexTable` are the first choices for shared loading, error, retry, and empty UI.
- The retry action calls the same store action that performed the original load. Retry does not duplicate API logic inside the component.
- Warning presentation is centralized: error copy goes through `AlertBanner tone="warning"`, and retry button tone belongs in the shared status component rather than in each route.
- Blocking loading and blocking error states are only used when there are no rows or usable page data.
- Inline errors are used when stale rows still exist after a refresh failure, so users can continue reading the last successful data.
- Empty state appears only when loading is false, error is empty, and the loaded collection is empty.
- Route-local stores expose narrow flags such as `isLoading`, `errorMessage`, `isSaving`, `isDrawerSubmitting`, and `detailErrorMessage` instead of one vague `busy` flag.
- The shell store owns `hasInitialized`, `isLoading`, and `errorMessage` for application bootstrap. Route stores own route data loading after shell context exists.
- Stale request guards write state only when the current organization, workspace, route params, filters, or request id still match the captured values.
- Components do not destructure store state; they access `rateCardsStore.isLoading`, `rateCardsStore.errorMessage`, and `rateCardsStore.load()` directly.

## Rules To Follow

- Reuse shared loading and error UI before adding a route-local spinner, alert, retry button, or empty-state layout.
- Keep shell bootstrap loading and route-local loading separate. Route views must not call the auth bootstrap endpoint directly.
- Put route loading and error flags in a route-local store when three or more local components share the data, retry action, route scope, or error state.
- Name page fetch flags `isLoading` and `errorMessage` unless the route already has a clearer established convention.
- Name mutation flags by the mutation, such as `isSaving`, `isSubmitting`, `isDeleting`, `isDrawerSubmitting`, or `isRecoveringLead`.
- Clear `errorMessage` before starting a load. Set it from `getFirstApiErrorMessage(error, fallbackMessage)` in the catch block.
- Do not catch errors only to ignore them. If a failed request affects UI, set a visible shared error state.
- When required organization, workspace, route, or filter scope is missing, clear route rows and stop loading. Use an empty or selection state for user-actionable missing context, not a retry error.
- Add stale request guards for loads tied to organization, workspace, route params, search, filters, polling, or drawer selection.
- Keep stale rows visible on refresh failure when they are still valid for the current scope.
- Do not show empty state while `isLoading` is true or `errorMessage` is set.
- Do not render two waiting states for one request, such as a local spinner plus a table loading state, or a waiting card plus an empty optimistic item.
- Do not style retry buttons locally. Add or fix the tone in the shared wrapper, then use the shared component everywhere.
- Keep shared components store-agnostic. They receive `loading`, `errorMessage`, `rows`, and `@retry`; route-local stores and route-local sections own the business state.

## Refactor Signals

- A route view contains repeated `flex items-center justify-center`, local spinner markup, local retry buttons, or hand-built alert banners around page fetch state.
- A table component manually branches through loading, error, empty, and rows even though `AppTable` or `EntityIndexTable` can own that structure.
- A route renders both a page-level spinner and a table-level loading state for the same first-load request.
- Empty state appears when the request failed, or error state appears when the request succeeded with zero rows.
- A route-local child receives `organizationId`, `workspaceId`, `rows`, `loading`, `errorMessage`, `canManage`, and `onRetry` together from a parent that is acting as a prop-forwarding hub.
- Several sibling sections read the same page data but each owns its own API call, loading flag, or retry branch.
- A store writes response data after `await` without checking that organization, workspace, route params, filters, selected record, or request id are still current.
- A retry button uses custom Tailwind classes or a one-off tone instead of the shared warning-toned retry surface.
- A mutation sets the page `isLoading` flag and blanks the whole route while saving a form or drawer.
- A chat, AI generation, import, or polling workflow appends both a placeholder row and a separate waiting card for the same pending request.
- Tests assert only the happy path and do not cover load failure, retry, empty state, or stale-response behavior.

## Verification

- Run `cd frontend && npm run type-check` after changing loading/error store logic, component props, or shared UI contracts.
- Run `cd frontend && npm run lint` for modified Vue or TypeScript files.
- Add or update focused component tests when the route area already has frontend tests. Cover blocking loading, blocking error with retry, inline error with stale rows, empty state after a successful empty response, and no duplicate pending placeholders.
- Add or update store tests when changing stale-request guards. Prove a late response from an old organization, workspace, route param, filter, or request id does not overwrite the current state.
- Manually verify shell bootstrap failure by forcing the bootstrap endpoint to fail and confirming the shell shows one centered retry state instead of partially rendering route content.
- Manually verify route refresh failure with existing rows and confirm the rows remain visible with one inline warning and one retry action.
- For guidance-only edits, check Markdown frontmatter and code fences, then run the guidance builder when practical.

## Why It Helps

- Users see one consistent loading, empty, error, and retry language across workspace pages.
- Route views stay readable because shared components own feedback chrome and stores own data orchestration.
- Stale request guards prevent old organization, workspace, or filter data from flashing into the current workspace.
- Empty states remain trustworthy because they mean "the request succeeded and there is no data," not "something failed."
- Retry behavior is easy to audit because it flows through shared warning-toned UI back into the original store action.
- Tests and typecheck failures catch duplicated state, stale writes, and broken shared component contracts before the same mistake spreads across route folders.
