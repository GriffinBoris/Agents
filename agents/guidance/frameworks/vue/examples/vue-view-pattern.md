---
id: framework-vue-example-view-pattern
title: Vue View Pattern Example
description: Example view pattern for simple route-owned fetches, computed collections, and stale-request guards.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - view
applies_to:
  - vue
status: active
order: 5
---

# Vue View Pattern Example

## Scenario

- Use this shape when a route view owns a small page workflow: one route-scoped fetch, one loaded collection or record, local loading/error flags, derived rows, and simple navigation actions.
- Use this shape when the route reads shell context such as selected organization or permissions, reads route params, and calls one domain API method through `api`.
- Use this shape when the page can stay readable as a route outline without introducing a route-local Pinia store.
- Graduate to the route-local feature-store example when several local sections, dialogs, forms, tables, or mutation workflows share the same data, errors, selected record, or reload behavior.

## Why This Shape Exists

- Simple route views should remain simple. A route-local store is useful when it clarifies shared ownership, but it adds another file and another public surface. For one-resource pages, local refs and computed values are easier to audit.
- The route view is the boundary between router state, shell context, and page composition. It can read `useRoute()`, `useRouter()`, `useAppShellStore()`, and small route helpers directly when that keeps the page obvious.
- The shell store owns authenticated session, organization, workspace, and access bootstrap state. Route views consume that state; they do not call bootstrap endpoints or duplicate shell loading logic.
- Django API calls must still flow through the canonical `api` object. A simple route view may call `api.orders.list(...)`, but it must not import `axios`, call `fetch`, build raw snake_case query params, or create a second transport helper.
- Async route changes are common in workspace screens. Organization, workspace, route params, filters, and refresh actions can change while a request is in flight, so route-owned fetch helpers must capture the active scope and ignore stale responses.
- Derived UI collections belong in `computed` getters. Keeping row labels, status tones, empty labels, and filtered collections derived from source data avoids manually synchronized duplicate refs.

## Recommended Shape

### Simple Route View Owns The Page Fetch

Use direct route-owned state when the page has one clear resource and a small set of actions. The page composes shared UI, loads through `api`, parses route params with the shared helper, reads organization context from the shell store, and exposes table-ready rows through a computed.

```vue
<template>
  <div class="space-y-4">
    <PageHeader
      title="Orders"
      description="Review order records created from approved plans for this workspace"
    >
      <template #actions>
        <AppButton
          label="Refresh"
          tone="ghost"
          icon="refresh"
          :disabled="isLoading || !organizationId || !workspaceId"
          @click="void loadOrders()"
        />
      </template>
    </PageHeader>

    <PageStatusCard
      v-if="!organizationId || !workspaceId"
      title="Select a workspace"
      description="Choose a workspace from the workspace selector before viewing orders"
    />

    <OrdersTable
      v-if="organizationId && workspaceId"
      :rows="orderRows"
      :loading="isLoading"
      :error-message="errorMessage"
      @retry="void loadOrders()"
      @select="openOrder"
    />
  </div>
</template>

<script setup lang="ts">
  import PageHeader from "@/components/page/PageHeader.vue";
  import PageStatusCard from "@/components/page/PageStatusCard.vue";
  import AppButton from "@/components/ui/AppButton.vue";
  import { useDateFormat } from "@/composables/useDateFormat";
  import type { OrderInterface } from "@/types/order/OrderInterface";
  import { OrderStatus } from "@/types/order/OrderInterface";
  import { api } from "@/utils/api";
  import { getFirstApiErrorMessage } from "@/utils/errorHandling";
  import { formatEnumLabel } from "@/utils/formatEnumLabel";
  import { getRouteNumberParam } from "@/utils/routeParams";
  import { useAppShellStore } from "@/views/application/appShellStore";
  import OrdersTable, { type OrdersTableRow } from "@/views/orders/components/OrdersTable.vue";
  import { computed, onMounted, ref, watch } from "vue";
  import { useRoute, useRouter } from "vue-router";

  const appShellStore = useAppShellStore();
  const route = useRoute();
  const router = useRouter();
  const { formatDate } = useDateFormat();

  const errorMessage = ref("");
  const isLoading = ref(false);
  const orders = ref<OrderInterface[]>([]);
  let loadOrdersRequestId = 0;

  const organizationId = computed(() => appShellStore.selectedOrganizationId);
  const workspaceId = computed(() => getRouteNumberParam(route, "workspaceId"));
  const orderRows = computed<OrdersTableRow[]>(() => {
    return orders.value.map((order) => ({
      workspaceName: order.workspaceName,
      couponCode: order.couponCode,
      contactEmail: order.contactEmail,
      contactName: order.contactFullName,
      id: order.id,
      priceLabel:
        order.discountAmount !== "0.00"
          ? `${order.resolvedPriceAmount} after ${order.discountAmount} off`
          : order.resolvedPriceAmount,
      pricingPlanName: order.catalogEntrySubscriptionPlanName,
      itemName: order.itemName,
      itemVariantName: order.itemVariantName,
      statusLabel: formatEnumLabel(order.status),
      statusTone: resolveStatusTone(order.status),
      updatedLabel: formatDate(order.updatedTs),
    }));
  });

  onMounted(() => {
    void loadOrders();
  });

  watch(
    () => [organizationId.value, workspaceId.value],
    () => {
      void loadOrders();
    }
  );

  async function loadOrders() {
    const requestId = ++loadOrdersRequestId;
    const activeOrganizationId = organizationId.value;
    const activeWorkspaceId = workspaceId.value;

    if (!activeOrganizationId || !activeWorkspaceId) {
      orders.value = [];
      errorMessage.value = "";
      isLoading.value = false;
      return;
    }

    isLoading.value = true;
    errorMessage.value = "";

    try {
      const nextOrders = await api.orders.list(activeOrganizationId, activeWorkspaceId);
      if (requestId !== loadOrdersRequestId || organizationId.value !== activeOrganizationId || workspaceId.value !== activeWorkspaceId) {
        return;
      }

      orders.value = nextOrders;
    } catch (error) {
      if (requestId !== loadOrdersRequestId || organizationId.value !== activeOrganizationId || workspaceId.value !== activeWorkspaceId) {
        return;
      }

      orders.value = [];
      errorMessage.value = getFirstApiErrorMessage(error, "Unable to load orders for this workspace.");
    } finally {
      if (requestId === loadOrdersRequestId && organizationId.value === activeOrganizationId && workspaceId.value === activeWorkspaceId) {
        isLoading.value = false;
      }
    }
  }

  function openOrder(orderId: number) {
    if (!workspaceId.value) {
      return;
    }

    void router.push({ name: "order-detail", params: { workspaceId: workspaceId.value, orderId } });
  }

  function resolveStatusTone(status: OrderStatus): "info" | "neutral" | "success" | "warning" {
    if (status === OrderStatus.FULFILLED) {
      return "success";
    }

    if (status === OrderStatus.SUBMITTED) {
      return "info";
    }

    if (status === OrderStatus.CANCELLED || status === OrderStatus.ERROR) {
      return "warning";
    }

    return "neutral";
  }
</script>
```

### Keep Helpers Narrow And Named

Route-owned helpers should be small enough that their ownership is obvious. `loadOrders()` loads orders. `openOrder()` navigates to an order. `resolveStatusTone()` turns a backend enum into a table tone. Avoid a generic `loadPage()` helper that fetches unrelated resources, computes permissions, updates query strings, opens dialogs, and performs navigation.

When a page must load a parent record and a child collection, prefer separate helpers unless the two requests are one coherent page fetch:

```typescript
async function loadCatalogEntry() {
  const activeOrganizationId = organizationId.value;
  const activeWorkspaceId = workspaceId.value;
  const activeCatalogEntryId = catalogEntryId.value;
  if (!activeOrganizationId || !activeWorkspaceId || !activeCatalogEntryId) {
    catalogEntryRecord.value = null;
    return;
  }

  catalogEntryRecord.value = await api.catalogEntries.detail(activeOrganizationId, activeWorkspaceId, activeCatalogEntryId);
}

async function loadItems() {
  const activeOrganizationId = organizationId.value;
  const activeWorkspaceId = workspaceId.value;
  const activeCatalogEntryId = catalogEntryId.value;
  if (!activeOrganizationId || !activeWorkspaceId || !activeCatalogEntryId) {
    items.value = [];
    return;
  }

  items.value = await api.items.list(activeOrganizationId, activeWorkspaceId, activeCatalogEntryId);
}
```

If later requests depend on earlier metadata, call helpers sequentially. If they are independent and the page treats them as one blocking state, `Promise.all(...)` is acceptable as long as the stale-response guard covers the combined scope.

### Derived Collections Stay Computed

Build table rows, filtered rows, grouped data, status labels, and formatted dates in computed getters. Keep the source API data in one ref and derive display rows from that source.

```typescript
const itemRows = computed<ItemsTableRow[]>(() => {
  return items.value.map((item) => ({
    id: item.id,
    primaryLabel: item.name,
    secondaryLabel: item.slug,
    sortOrderLabel: String(item.sortOrder),
    statusLabel: formatEnumLabel(item.status),
    statusTone: item.status === ItemStatus.ACTIVE ? "success" : "neutral",
    summary: item.summary,
    updatedLabel: formatDate(item.updatedTs),
  }));
});
```

Use a plain loop instead of a dense `map` / `filter` / `reduce` chain when the transformation has several steps and a loop is easier to read.

```typescript
const visibleItems = computed<ItemInterface[]>(() => {
  const itemsToShow: ItemInterface[] = [];

  for (const item of items.value) {
    if (statusFilter.value === "all" || item.status === statusFilter.value) {
      itemsToShow.push(item);
    }
  }

  return itemsToShow;
});
```

### Shared UI Owns Loading And Error Surfaces

Route views should compose shared page and table components rather than rebuilding local loading and retry UI.

```vue
<PageStatusCard
  v-if="!organizationId || !workspaceId"
  title="Select a workspace"
  description="Choose a workspace from the workspace selector before viewing this page"
/>

<OrdersTable
  v-if="organizationId && workspaceId"
  :rows="orderRows"
  :loading="isLoading"
  :error-message="errorMessage"
  @retry="void loadOrders()"
/>
```

`PageStatusCard`, `AppTable`, `EntityIndexTable`, and route-local table wrappers already know how to present loading, empty, blocking error, inline error, and retry states. Add missing behavior to the shared wrapper when the pattern is broadly needed.

### Graduate To A Route-Local Store When The View Becomes A Hub

Keep state local only while the route view still reads like a page outline. Move orchestration into a route-local store when the page starts coordinating shared forms, dialogs, table selection, delete confirmation, field errors, permission-derived actions, or several sibling sections.

```typescript
const contactsStore = useContactsStore();

watch(
  [() => route.params.workspaceId, () => contactsStore.organizationId],
  () => {
    contactsStore.setRouteWorkspaceId(getRouteNumberParam(route, "workspaceId"));
    void contactsStore.load();
  },
  { immediate: true }
);
```

```vue
<ContactsTable
  :rows="contactsStore.contactRows"
  :loading="contactsStore.isLoading"
  :error-message="contactsStore.errorMessage"
  :can-create="contactsStore.canManageContacts"
  :can-delete="contactsStore.canDeleteContacts"
  @create="handleCreateContact"
  @delete="contactsStore.requestDeleteContact($event)"
  @retry="void contactsStore.load()"
  @select="handleOpenContact"
/>
```

In that shape, the route view keeps route lifecycle wiring and navigation, while the store owns shared business state and mutation workflow.

## Things To Notice

- The view reads route params through `getRouteNumberParam(...)`, not by casting `route.params` inline in several places.
- The view reads selected organization and permissions from `useAppShellStore()`. It does not call `api.auth.bootstrap()` or duplicate shell initialization.
- The fetch helper captures `organizationId`, route params, and a request id before awaiting. It only writes rows, errors, and loading flags if the response still belongs to the latest request and current route scope.
- Source data stays in one ref such as `orders`; table-ready data stays in a computed such as `orderRows`.
- Formatting and enum-to-tone decisions happen in named helpers or computed transformers instead of long inline template ternaries.
- The template composes `PageHeader`, `PageStatusCard`, table wrappers, and local route components. It does not rebuild shared chrome, spinner, empty, retry, or error markup.
- Navigation helpers guard required params before pushing to child routes.
- A route-local store is an escalation path, not the default for every simple route.

## Rules To Follow

- Use `<script setup lang="ts">` for new route views.
- Let simple route views own local refs, computed rows, and one-resource fetch helpers when no sibling component needs to share the state.
- Read organization, workspace, current user, bootstrap, and permission context from `useAppShellStore()` or the established shell store. Do not fetch shell context from route views.
- Parse route params with shared route helpers such as `getRouteNumberParam(...)`.
- Guard optional identifiers before API calls and before navigation. Return early when the route or shell context is incomplete.
- Route every backend request through `api` from `@/utils/api`. Do not import `axios` or call `fetch` in route views.
- Keep frontend state and API call arguments camelCase. Let the API client and `buildParamsConfig(...)` handle backend casing.
- Keep each fetch helper focused on one resource or one coherent page load.
- Clear stale errors before a new load and use `getFirstApiErrorMessage(...)` for standardized DRF errors.
- Add stale-response guards when organization, workspace, route params, filters, or refresh actions can change during an async request.
- Store source API records separately from computed display rows.
- Put derived collections, grouped rows, labels, and view models in computed getters.
- Use shared loading, empty, error, table, and retry components before adding local status markup.
- Move state into a route-local feature store when three or more local components share records, loading flags, selected rows, forms, errors, mutation state, or reload behavior.
- Keep shared `src/components/` components prop-driven and store-agnostic. Route-local components under `src/views/<route>/components/` may consume a colocated route store when that removes prop chains.

## Refactor Signals

- A route view imports `axios`, calls `fetch`, creates an `apiService`, or manually converts payload keys to snake_case.
- A route view calls the auth bootstrap endpoint or maintains its own current-user, selected-organization, or selected-workspace source of truth.
- The same loaded record, loading flag, error string, selected row, or save/delete workflow is passed through several local components.
- The route view template contains repeated loading spinners, empty-state markup, retry buttons, or error banners that duplicate shared page/table components.
- The template contains heavy ternaries, date formatting, enum formatting, row filtering, or route-param parsing inline.
- A fetch helper writes response data after `await` without checking that the current organization, workspace, route params, query params, or request id still match.
- A page keeps both `orders` and manually assigned `orderRows` refs in sync instead of deriving rows through `computed`.
- A helper named `loadPage`, `initialize`, or `refreshEverything` fetches unrelated resources and mutates several independent workflow states.
- A route view has grown into a prop-heavy workflow hub instead of a short page outline.
- A route-local store exists for a page that only has one fetch, one table, and no shared sibling workflow. Consider inlining it unless the store is preparing real shared ownership.

## Verification

- Run `npm run type-check` after changing Vue route views, route-local stores, shared components, route helpers, or API interfaces.
- Run `npm run lint` after changing frontend source files.
- Exercise route changes manually or with tests when a fetch depends on route params, selected organization, selected workspace, filters, or query state. Confirm stale responses cannot overwrite the current view.
- Verify incomplete shell or route context shows shared status UI instead of firing invalid API requests.
- Verify table pages show loading, empty, blocking error, inline error, and retry through shared wrappers.
- For guidance-only updates, run the agents build command so the authored example compiles into generated `AGENTS.md` output:

```bash
python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean
```

## Why It Helps

- Route views stay readable because they describe the page instead of hiding simple work behind unnecessary stores or scattered helpers.
- Shell state remains centralized, so auth, organization, workspace, and permission decisions stay consistent across the workspace.
- API usage remains auditable through the canonical client, preserving CSRF, session credentials, typed responses, and casing conversion.
- Computed view models prevent duplicate state from drifting out of sync with source API data.
- Stale-response guards prevent late requests from showing rows for the wrong organization, workspace, route, or filter.
- Shared loading and error components keep the workspace interaction model consistent.
- The store graduation rule gives reviewers a concrete standard: keep one-resource pages simple, and move real shared workflows into route-local stores before prop chains take over.
