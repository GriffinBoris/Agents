---
id: framework-vue-example-route-query-state
title: Vue Route Query State Example
description: Standards for URL query driven filters, sort, pagination, tabs, and API filter handoff in Vue route views.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - routing
  - query-state
applies_to:
  - vue
status: active
order: 10
---

# Vue Route Query State Example

## Scenario

Use this pattern when route views need shareable, refresh-safe view state such as:

- search text, status filters, workspace filters, sort keys, page numbers, or active tabs
- organization-wide list filters that should reopen the same view from a shared link
- detail-page tabs where the selected tab is UI state, not backend state

Do not use the query string for business records, form drafts, permission state, loaded API data, or sensitive values. Those belong in the route-local store, the shared shell store, or the backend.

## Why This Shape Exists

The URL is the contract for "what view am I looking at?" Query params make list and tab state bookmarkable without turning filters into hidden component state. They also let refresh, browser navigation, and shared links restore the same view without relying on local storage.

The tradeoff is that query values arrive as untrusted strings. Route views or route-local stores must parse them into typed frontend state, omit defaults when serializing, and normalize invalid values back to a clean URL. API calls should still receive camelCase filter objects and let the canonical API client convert them for the Django backend.

This keeps three boundaries clear:

- Route path params identify required resources such as `workspaceId`, `catalogEntryId`, or `itemId`.
- Route query params describe optional view state such as `search`, `status`, `page`, `sort`, or `tab`.
- Stores and API modules own business state, loaded rows, mutations, permissions, and backend filter handoff.

## Recommended Shape

### Shared Query Replacement Helper

Keep query replacement deterministic and avoid repeated router writes. Reuse `replaceRouteQuery(...)` from `src/utils/routeQuery.ts` when possible; if a local helper already exists in touched code, migrate toward this shared shape.

```typescript
import type { RouteLocationNormalizedLoaded, Router } from "vue-router";

export function replaceRouteQuery(router: Router, route: RouteLocationNormalizedLoaded, query: Record<string, string>) {
  const currentEntries = Object.entries(route.query).filter((entry): entry is [string, string] => typeof entry[1] === "string");
  const nextEntries = Object.entries(query);

  if (currentEntries.length === nextEntries.length && nextEntries.every(([key, value]) => route.query[key] === value)) {
    return;
  }

  void router.replace({ query: nextEntries.length > 0 ? query : undefined });
}
```

### Route-Local Store Owns Typed View State

Use camelCase in frontend state. Parse raw query strings at the route/store boundary, and serialize typed state back into string params. Defaults should be omitted so the URL stays clean.

```typescript
import { defineStore } from "pinia";
import { ref } from "vue";

export type ContactStatusFilterValue = "active" | "all" | "paused";
export type ContactSortValue = "created-desc" | "name-asc";
export type ContactWorkspaceFilterValue = "all" | number;

export function isContactStatusFilterValue(value: string): value is ContactStatusFilterValue {
  return value === "active" || value === "all" || value === "paused";
}

export function isContactSortValue(value: string): value is ContactSortValue {
  return value === "created-desc" || value === "name-asc";
}

export const useContactsStore = defineStore("contacts", () => {
  const searchTerm = ref("");
  const statusFilter = ref<ContactStatusFilterValue>("all");
  const workspaceFilter = ref<ContactWorkspaceFilterValue>("all");
  const sort = ref<ContactSortValue>("created-desc");
  const page = ref(1);

  function applyQueryParamsToState(query: Record<string, unknown>) {
    const searchValue = typeof query.search === "string" ? query.search.trim() : "";
    const statusValue = typeof query.status === "string" && isContactStatusFilterValue(query.status) ? query.status : "all";
    const workspaceValue = parseQueryId(query.workspaceId) ?? "all";
    const sortValue = typeof query.sort === "string" && isContactSortValue(query.sort) ? query.sort : "created-desc";
    const pageValue = parsePositivePage(query.page);

    if (searchTerm.value !== searchValue) {
      searchTerm.value = searchValue;
    }

    if (statusFilter.value !== statusValue) {
      statusFilter.value = statusValue;
    }

    if (workspaceFilter.value !== workspaceValue) {
      workspaceFilter.value = workspaceValue;
    }

    if (sort.value !== sortValue) {
      sort.value = sortValue;
    }

    if (page.value !== pageValue) {
      page.value = pageValue;
    }
  }

  function buildQuery() {
    const query: Record<string, string> = {};
    const activeSearch = searchTerm.value.trim();

    if (activeSearch) {
      query.search = activeSearch;
    }

    if (statusFilter.value !== "all") {
      query.status = statusFilter.value;
    }

    if (workspaceFilter.value !== "all") {
      query.workspaceId = String(workspaceFilter.value);
    }

    if (sort.value !== "created-desc") {
      query.sort = sort.value;
    }

    if (page.value !== 1) {
      query.page = String(page.value);
    }

    return query;
  }

  function buildApiFilters() {
    return {
      workspaceId: workspaceFilter.value === "all" ? undefined : workspaceFilter.value,
      page: page.value,
      search: searchTerm.value.trim() || undefined,
      sort: sort.value,
      status: statusFilter.value === "all" ? undefined : statusFilter.value,
    };
  }

  function parseQueryId(value: unknown) {
    if (typeof value !== "string") {
      return null;
    }

    const numericValue = Number(value);
    return Number.isInteger(numericValue) && numericValue > 0 ? numericValue : null;
  }

  function parsePositivePage(value: unknown) {
    if (typeof value !== "string") {
      return 1;
    }

    const numericValue = Number(value);
    return Number.isInteger(numericValue) && numericValue > 0 ? numericValue : 1;
  }

  return {
    applyQueryParamsToState,
    buildApiFilters,
    buildQuery,
    workspaceFilter,
    page,
    searchTerm,
    sort,
    statusFilter,
  };
});
```

### Route View Wires Query, Store, And Loading

Initialize from the URL before loading. Watch the query for browser navigation, and watch state changes to normalize the URL. Debounce noisy inputs such as search; use immediate route updates for discrete controls such as tab, status, sort, page, and workspace.

```vue
<script setup lang="ts">
  import { useDebounce } from "@/composables/useDebounce";
  import { replaceRouteQuery } from "@/utils/routeQuery";
  import { useContactsStore } from "@/views/contacts/contactsStore";
  import { watch } from "vue";
  import { useRoute, useRouter } from "vue-router";

  const route = useRoute();
  const router = useRouter();
  const contactsStore = useContactsStore();

  contactsStore.applyQueryParamsToState(route.query);
  syncStateToUrl();
  void contactsStore.load();

  const { debounced: debouncedLoadContacts } = useDebounce(() => {
    void contactsStore.load();
  }, 250);

  watch(
    () => route.query,
    () => {
      contactsStore.applyQueryParamsToState(route.query);
      syncStateToUrl();
      void contactsStore.load();
    }
  );

  watch(
    () => contactsStore.searchTerm,
    () => {
      contactsStore.page = 1;
      syncStateToUrl();
      debouncedLoadContacts();
    }
  );

  watch(
    [() => contactsStore.statusFilter, () => contactsStore.workspaceFilter, () => contactsStore.sort],
    () => {
      contactsStore.page = 1;
      syncStateToUrl();
      void contactsStore.load();
    }
  );

  watch(
    () => contactsStore.page,
    () => {
      syncStateToUrl();
      void contactsStore.load();
    }
  );

  function syncStateToUrl() {
    replaceRouteQuery(router, route, contactsStore.buildQuery());
  }
</script>
```

### API Client Receives CamelCase Filters

Route query keys may be camelCase in the frontend URL, but the backend still receives snake_case because `buildParamsConfig(...)` converts params inside the canonical API client.

```typescript
import { buildParamsConfig } from "@/utils/apiParams";

type ContactListFilters = {
  workspaceId?: number;
  page?: number;
  search?: string;
  sort?: "created-desc" | "name-asc";
  status?: "active" | "paused";
};

const contacts = {
  list: (organizationId: number, filters?: ContactListFilters) =>
    apiClient.get<ContactInterface[]>(`api/organizations/${organizationId}/contacts/list/`, buildParamsConfig(filters)),
};
```

The store passes frontend names:

```typescript
async function load() {
  const activeOrganizationId = organizationId.value;
  if (!activeOrganizationId) {
    contacts.value = [];
    return;
  }

  contacts.value = await api.contacts.list(activeOrganizationId, buildApiFilters());
}
```

`buildParamsConfig({ workspaceId: 4, searchTerm: "main catalogEntry" })` sends:

```typescript
{
  params: {
    workspace_id: 4,
    search_term: "main catalogEntry",
  },
}
```

### Detail Tabs Use Query, Not Extra Paths

Use route params for the resource identity and a `tab` query param for the selected section. Do not create separate sibling paths only to represent tabs unless each tab is a separately owned route with its own route component, permissions, and lifecycle.

```typescript
import { computed, ref, watch } from "vue";
import type { RouteLocationNormalizedLoaded, Router } from "vue-router";

export type CatalogEntryTabKey = "overview" | "items" | "pricing" | "survey-forms";

const CATALOG_ENTRY_TABS: CatalogEntryTabKey[] = ["overview", "items", "pricing", "survey-forms"];

export function useCatalogEntryDetailTabs(route: RouteLocationNormalizedLoaded, router: Router, isCreateMode: { value: boolean }) {
  const activeCatalogEntryTab = ref<CatalogEntryTabKey>("overview");

  applyTabQueryToState();
  syncTabToUrl();

  watch(
    () => route.query,
    () => {
      applyTabQueryToState();
      syncTabToUrl();
    }
  );

  watch(activeCatalogEntryTab, () => {
    syncTabToUrl();
  });

  const isOverviewTab = computed(() => isCreateMode.value || activeCatalogEntryTab.value === "overview");

  function applyTabQueryToState() {
    if (isCreateMode.value) {
      activeCatalogEntryTab.value = "overview";
      return;
    }

    const nextTab = typeof route.query.tab === "string" && isCatalogEntryTabKey(route.query.tab) ? route.query.tab : "overview";
    if (activeCatalogEntryTab.value !== nextTab) {
      activeCatalogEntryTab.value = nextTab;
    }
  }

  function syncTabToUrl() {
    const query: Record<string, string> = {};

    if (!isCreateMode.value && activeCatalogEntryTab.value !== "overview") {
      query.tab = activeCatalogEntryTab.value;
    }

    replaceRouteQuery(router, route, query);
  }

  function handleCatalogEntryTabChange(value: string) {
    activeCatalogEntryTab.value = isCatalogEntryTabKey(value) ? value : "overview";
  }

  function isCatalogEntryTabKey(value: string): value is CatalogEntryTabKey {
    return CATALOG_ENTRY_TABS.includes(value as CatalogEntryTabKey);
  }

  return {
    activeCatalogEntryTab,
    handleCatalogEntryTabChange,
    isOverviewTab,
  };
}
```

### Guard Optional Route And Query IDs

Route params that identify required resources should use shared route-param parsing and return early when missing. Optional query IDs should be parsed locally or through a small route-query helper when the shape repeats.

```typescript
import { getRouteNumberParam } from "@/utils/routeParams";

const workspaceId = computed(() => getRouteNumberParam(route, "workspaceId"));
const versionId = computed(() => parseQueryId(route.query.versionId));

async function loadBuilder() {
  const activeOrganizationId = appShellStore.selectedOrganizationId;
  const activeWorkspaceId = workspaceId.value;

  if (!activeOrganizationId || !activeWorkspaceId) {
    builder.value = null;
    return;
  }

  builder.value = await api.surveyForms.detail(activeOrganizationId, activeWorkspaceId, {
    versionId: versionId.value ?? undefined,
  });
}

function parseQueryId(value: unknown) {
  if (typeof value !== "string") {
    return null;
  }

  const numericValue = Number(value);
  return Number.isInteger(numericValue) && numericValue > 0 ? numericValue : null;
}
```

## Things To Notice

- Query parsing happens once at the boundary with `applyQueryParamsToState(...)`; components should not keep reading `route.query` inline.
- Query serialization happens through `buildQuery()` and `replaceRouteQuery(...)`; defaults are omitted and empty query objects become `undefined`.
- Frontend state, URL query keys, API filter objects, and TypeScript types stay camelCase. The API client converts backend params to snake_case through `buildParamsConfig(...)`.
- Required resource identity stays in path params. Optional view state stays in query params. The same concept should not be represented in both places at once.
- Business data stays out of the URL. Loaded rows, selected records, form DTOs, mutation state, permissions, and loading errors belong in stores or local component state.
- Search input uses a debounced load after writing the route. Discrete filter, sort, page, and tab changes can update the route and reload immediately.
- Invalid query values normalize to defaults instead of creating partial or fallback business behavior.
- Query-driven tabs use a finite union and a guard such as `isCatalogEntryTabKey(...)`; unrecognized tab values fall back to the default tab and are removed from the URL on the next sync.
- Route views can own simple query state, but route-local stores should own it when multiple local components share filters, loading state, rows, drawers, or mutations.

## Rules To Follow

- Use query params for shareable view state: filters, search, sort, page, and active tabs.
- Use path params for required resource identity: `organizationId`, `workspaceId`, `catalogEntryId`, `contactId`, and similar IDs.
- Do not mix path and query for the same state. If a workspace is route-scoped by `/workspaces/:workspaceId`, do not also preserve a conflicting `workspaceId` query filter.
- Do not use `localStorage` for shareable route state. Local storage is appropriate for durable user preferences such as theme, not filters or tabs that need to travel with a URL.
- Parse query values before putting them into typed state. Never assign raw `route.query` values directly into number refs or string-union refs.
- Omit defaults from `buildQuery()` so clean default views do not carry noisy query params.
- Use `replaceRouteQuery(...)` or the same equality guard before calling `router.replace(...)`.
- Reset dependent state intentionally. For example, when `search`, `status`, `workspaceFilter`, or `sort` changes, set `page` back to `1` before serializing the query.
- Keep API filter payloads camelCase and pass them through `buildParamsConfig(...)` in `src/utils/api.ts`.
- Do not import `axios` or manually convert casing in route views, stores, or components.
- Guard optional route/query IDs before using them. Return early when required route IDs or selected organization context are missing.
- Test query-driven routes with initialization, query normalization, browser navigation, and API filter expectations when the behavior affects visible state or backend calls.

## Refactor Signals

- A route view reads `route.query.foo` in several computed values, watchers, templates, or child props instead of centralizing parsing.
- A component uses `localStorage` to remember a filter, sort, page, selected tab, or selected row that should be shareable in a URL.
- A list view stores filters only in component refs, so refresh or shared links lose the active view.
- A route uses both `/workspaces/:workspaceId/...` and `?workspaceId=...` for the same active workspace.
- API calls send query params built from snake_case keys such as `workspace_id` or `search_term` outside the API client.
- `router.replace(...)` is called on every watcher tick without comparing the current and next query.
- Search triggers an API call on every keystroke without debounce or an explicit Apply action.
- A route tab is modeled as several almost-identical paths even though only the selected section changes.
- Query IDs are converted with `Number(route.query.id)` inline and no guard for arrays, missing values, or non-numeric strings.
- Loaded rows, form drafts, selected records, or permission-derived actions are serialized into query params.
- Adding another filter requires changing several components because query state is split across parent props and child-local refs.

## Verification

Use the smallest checks that prove the contract for the touched area:

```bash
cd frontend
npm run type-check
node --test tests/route-query-state-guidance.test.ts
node --test tests/api-helpers.test.ts
```

For feature-specific changes, add or update focused tests that cover:

- initial route query values populate typed state before the first load
- invalid query values normalize to defaults and are removed from the URL
- search, status, workspace, sort, page, and tab updates write the expected query
- search reloads are debounced or require an explicit Apply action
- API filters are camelCase at the call site and converted by `buildParamsConfig(...)`
- required path params and optional query IDs are guarded before API calls

For guidance-only edits, also run a focused markdown/frontmatter/fence check for this file when practical.

## Why It Helps

- Shared links, refreshes, and browser navigation reopen the same view without hidden state.
- URL state stays small and reviewable because only view state goes into query params.
- Store ownership stays clear: the URL says what to show, while stores own loaded data and business workflows.
- The API boundary stays consistent because frontend code remains camelCase and the client handles backend casing.
- Query parsing and serialization become easy to test, refactor, and audit across list and detail routes.
