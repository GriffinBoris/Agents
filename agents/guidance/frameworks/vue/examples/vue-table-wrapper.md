---
id: framework-vue-example-table-wrapper
title: Vue Table Wrapper Example
description: Standards for shared Vue table and list wrappers with loading, empty, retry, row keys, actions, and route-owned state.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - tables
applies_to:
  - vue
status: active
order: 17
---

# Vue Table Wrapper Example

## Scenario

Use this pattern when a route renders a repeated resource list such as workspaces, contacts, rate cards, orders, leads, organization access, notifications, or approved plans.

Good triggers include:

- several route screens need the same table surface, loading state, blocking error, inline retry, empty state, footer summary, or pagination placement
- a route-specific table repeats the same `<table>`, header-cell classes, row-cell classes, empty row, and retry UI already owned by `AppTable`
- index screens share common name/status/updated/actions columns and only need a few domain-specific columns around them
- filters, query params, row shaping, and data loading are route-local business state, while the table should stay prop-driven and presentational
- row actions need consistent icon-button placement, event names, permission-disabled states, and deterministic test ids

Do not use this pattern to hide domain workflow inside a shared component. Shared wrappers own table chrome and feedback states. Route views and route-local stores own filters, loaded records, row view models, permissions, navigation, mutations, and query state.

## Why This Shape Exists

Tables are one of the easiest places for frontend drift to accumulate. A copied table usually brings copied header classes, custom loading text, hand-rolled empty states, inconsistent retry placement, and one-off action columns. Once every route owns its own chrome, small visual or accessibility fixes require many edits.

This pattern keeps the table stack layered:

- `frontend/src/components/page/AppTable.vue` owns the reusable surface, horizontal scroll, loading, blocking error, inline error, empty state, empty action slot, footer summary, and pagination slot.
- `frontend/src/components/page/AppTableHeaderCell.vue` and `frontend/src/components/page/AppTableCell.vue` own repeated cell spacing, alignment, and stacked-vs-inline content layout.
- `frontend/src/components/page/EntityIndexTable.vue` owns the common resource-index shape for name, status, updated timestamp, and actions when a route can fit that convention.
- Route-local table components under `frontend/src/views/<route>/components/` own domain columns and emit narrow user actions.
- Route views and route-local stores own shell context, route params, query params, API calls, loaded records, derived rows, permission flags, and reload behavior.

That split keeps shared components reusable while still letting each domain table express real columns. The wrapper accepts props and slots instead of importing stores or APIs, so a table can be reused by unrelated route folders without dragging organization, workspace, auth, or route assumptions with it.

## Recommended Shape

### Shared Table Wrapper Owns Chrome And Feedback

Keep the lowest shared wrapper presentational. It should accept rows-state props, emit `retry`, and expose slots for header, rows, empty action, footer, and pagination. It should not import a route-local store, router, API client, or domain types.

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
      <AlertBanner
        v-if="showInlineError"
        :message="errorMessage || ''"
        tone="warning"
      />

      <AppSurface
        root-class="overflow-hidden shadow-none"
        content-class="p-0"
      >
        <div class="overflow-x-auto">
          <table class="divide-line min-w-full divide-y">
            <thead
              v-if="hasRows"
              class="bg-surface-muted/70"
            >
              <tr>
                <slot name="header" />
              </tr>
            </thead>

            <tbody
              v-if="hasRows"
              class="divide-line bg-surface divide-y"
            >
              <slot name="rows" />
            </tbody>

            <tbody
              v-else
              class="bg-surface"
            >
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

          <div
            v-if="showBottomBar"
            class="border-line flex flex-col gap-3 border-t px-4 py-3 sm:flex-row sm:items-center"
          >
            <slot name="footer" />
            <slot name="pagination" />
          </div>
        </div>
      </AppSurface>
    </template>
  </div>
</template>

<script setup lang="ts">
  import { computed } from "vue";

  interface Props {
    emptyMessage?: string;
    emptyTitle?: string;
    errorMessage?: string;
    hasRows: boolean;
    loading?: boolean;
    loadingLabel?: string;
    totalCount?: number;
    visibleCount?: number;
  }

  const props = withDefaults(defineProps<Props>(), {
    emptyMessage: "There is nothing to show yet",
    emptyTitle: "No records found",
    errorMessage: undefined,
    loading: false,
    loadingLabel: "records",
    totalCount: undefined,
    visibleCount: undefined,
  });

  const emit = defineEmits<{
    retry: [];
  }>();

  const showBlockingLoading = computed(() => props.loading && !props.hasRows);
  const showBlockingError = computed(() => !props.loading && Boolean(props.errorMessage) && !props.hasRows);
  const showInlineError = computed(() => Boolean(props.errorMessage) && props.hasRows);
  const loadingTitle = computed(() => `Loading ${props.loadingLabel}`);
  const loadingDescription = computed(() => `Preparing the latest ${props.loadingLabel} for this view`);
  const errorTitle = computed(() => `Unable to load ${props.loadingLabel}`);
  const showBottomBar = computed(() => props.hasRows && (props.visibleCount || props.totalCount));
</script>
```

The real `AppTable` also wires `TableFooterSummary` and slot detection. Keep those details inside the shared wrapper so route tables only choose the content.

### Cell Wrappers Own Alignment And Density

Route-specific tables should use `AppTableHeaderCell` and `AppTableCell` instead of repeating low-level `<th>` and `<td>` classes. That keeps table density, alignment, stacked labels, and action columns consistent.

```vue
<!-- frontend/src/components/page/AppTableCell.vue -->
<template>
  <td :class="cellClass">
    <div :class="contentClass">
      <slot />
    </div>
  </td>
</template>

<script setup lang="ts">
  import { cn } from "@/utils/className";
  import { computed } from "vue";

  interface Props {
    align?: "left" | "right";
    layout?: "stack" | "inline";
    rootClass?: string;
    wrapperClass?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    align: "left",
    layout: "inline",
    rootClass: undefined,
    wrapperClass: undefined,
  });

  const cellClass = computed(() => {
    return cn("text-base-body px-3 py-3 align-middle", props.align === "right" ? "text-right" : undefined, props.rootClass);
  });

  const contentClass = computed(() => {
    return cn("min-h-9", props.layout === "stack" ? "flex flex-col justify-center space-y-0.5" : "flex items-center", props.align === "right" ? "justify-end" : undefined, props.wrapperClass);
  });
</script>
```

Use `layout="stack"` for primary/secondary labels, `align="right"` for action columns and numeric summaries, and `wrapper-class="gap-1.5 pr-2"` for compact action groups. Do not inline a new spacing system inside every route table.

### Use EntityIndexTable For Common Resource Indexes

When a route fits the common name/status/updated/actions pattern, use `EntityIndexTable` and fill only the route-specific column slots. This is the shape used by rate cards.

```vue
<!-- frontend/src/components/page/EntityIndexTable.vue -->
<template>
  <AppTable
    :has-rows="rows.length > 0"
    :loading="loading"
    :error-message="errorMessage"
    :visible-count="rows.length"
    :total-count="rows.length"
    :summary-label="summaryLabel"
    :empty-title="emptyTitle"
    :empty-message="emptyMessage"
    :loading-label="loadingLabel"
    @retry="emit('retry')"
  >
    <template #header>
      <AppTableHeaderCell>{{ nameHeader }}</AppTableHeaderCell>
      <slot name="headerPrefix" />
      <AppTableHeaderCell>{{ statusHeader }}</AppTableHeaderCell>
      <slot name="headerSuffix" />
      <AppTableHeaderCell>{{ updatedHeader }}</AppTableHeaderCell>
      <AppTableHeaderCell
        align="right"
        :root-class="actionsWidthClass"
      >
        {{ actionsHeader }}
      </AppTableHeaderCell>
    </template>

    <template #rows>
      <tr
        v-for="row in rows"
        :key="row.id"
        class="hover:bg-background/70 transition-colors"
      >
        <AppTableCell layout="stack">
          <p class="text-body text-sm font-medium">{{ row.primaryLabel }}</p>
          <p
            v-if="row.secondaryLabel"
            class="text-secondary text-sm"
          >
            {{ row.secondaryLabel }}
          </p>
        </AppTableCell>

        <slot
          name="rowPrefix"
          :row="row"
        />

        <AppTableCell>
          <AppTag
            :tone="row.statusTone"
            :value="row.statusLabel"
          />
        </AppTableCell>

        <slot
          name="rowSuffix"
          :row="row"
        />

        <AppTableCell root-class="text-sm text-secondary">{{ row.updatedLabel }}</AppTableCell>
        <AppTableCell
          align="right"
          wrapper-class="gap-1.5 pr-2"
        >
          <slot
            name="actions"
            :row="row"
          >
            <AppIconButton
              icon="eye"
              :label="viewLabel"
              :test-id="viewTestIdPrefix ? `${viewTestIdPrefix}-${row.id}` : undefined"
              @click="emit('select', row.id)"
            />
          </slot>
        </AppTableCell>
      </tr>
    </template>
  </AppTable>
</template>
```

Do not force every route into `EntityIndexTable`. Use it when the table is a resource index. Use `AppTable` directly when the domain columns are materially different, such as contact identity, orders, organization access rows, approved plans, or analytics drop-off rows.

### Route-Specific Table Owns Domain Columns Only

Route-local table components should accept already-shaped rows plus narrow flags and emit user actions. They should not import `api`, `useRoute`, `useRouter`, `useAppShellStore`, or a route-local store unless the component is explicitly route-local and store-aware for a larger workflow. For tables, prop-driven is usually clearer.

```vue
<!-- frontend/src/views/contacts/components/ContactsTable.vue -->
<template>
  <AppTable
    :has-rows="rows.length > 0"
    :loading="loading"
    :error-message="errorMessage"
    :visible-count="rows.length"
    :total-count="rows.length"
    summary-label="contacts"
    empty-title="No contacts yet"
    empty-message="Create the first contact record for this organization to start linking survey submissions into enrollments"
    loading-label="contacts"
    @retry="emit('retry')"
  >
    <template #header>
      <AppTableHeaderCell>Contact</AppTableHeaderCell>
      <AppTableHeaderCell>Status</AppTableHeaderCell>
      <AppTableHeaderCell>Phone</AppTableHeaderCell>
      <AppTableHeaderCell>Date of birth</AppTableHeaderCell>
      <AppTableHeaderCell>Insurance</AppTableHeaderCell>
      <AppTableHeaderCell>Updated</AppTableHeaderCell>
      <AppTableHeaderCell
        align="right"
        root-class="w-[10rem]"
      >
        Actions
      </AppTableHeaderCell>
    </template>

    <template #rows>
      <tr
        v-for="contact in rows"
        :key="contact.id"
        class="hover:bg-background/70 transition-colors"
      >
        <AppTableCell layout="stack">
          <p class="text-body text-sm font-medium">{{ contact.name }}</p>
          <p class="text-secondary text-sm">{{ contact.email }}</p>
        </AppTableCell>
        <AppTableCell>
          <AppTag
            :tone="contact.statusTone"
            :value="contact.statusLabel"
          />
        </AppTableCell>
        <AppTableCell root-class="text-sm text-body">{{ contact.phoneLabel }}</AppTableCell>
        <AppTableCell root-class="text-sm text-body">{{ contact.dateOfBirthLabel }}</AppTableCell>
        <AppTableCell root-class="text-sm text-body">{{ contact.insuranceProviderLabel }}</AppTableCell>
        <AppTableCell root-class="text-sm text-secondary">{{ contact.updatedLabel }}</AppTableCell>
        <AppTableCell
          align="right"
          wrapper-class="gap-2 pr-2"
        >
          <AppIconButton
            icon="eye"
            label="View contact"
            :test-id="`contact-view-${contact.id}`"
            @click="emit('select', contact.id)"
          />
          <AppIconButton
            :disabled="!canDelete"
            danger
            icon="trash"
            label="Delete contact"
            :test-id="`contact-delete-${contact.id}`"
            @click="emit('delete', contact.id)"
          />
        </AppTableCell>
      </tr>
    </template>

    <template #emptyAction>
      <AppButton
        v-if="canCreate"
        label="Create contact"
        tone="primary"
        icon="plus"
        @click="emit('create')"
      />
    </template>
  </AppTable>
</template>

<script setup lang="ts">
  export interface ContactsTableRow {
    dateOfBirthLabel: string;
    email: string;
    id: number;
    insuranceProviderLabel: string;
    name: string;
    phoneLabel: string;
    statusLabel: string;
    statusTone: "neutral" | "success" | "warning";
    updatedLabel: string;
  }

  interface Props {
    canCreate?: boolean;
    canDelete?: boolean;
    errorMessage?: string;
    loading?: boolean;
    rows: ContactsTableRow[];
  }

  const emit = defineEmits<{
    create: [];
    delete: [contactId: number];
    retry: [];
    select: [contactId: number];
  }>();

  withDefaults(defineProps<Props>(), {
    canCreate: false,
    canDelete: false,
    errorMessage: undefined,
    loading: false,
  });
</script>
```

The row interface is a table view model. It contains labels, tones, and ids needed to render and emit actions. It is not the raw API model and should not include form DTOs, backend-only fields, or unrelated route state.

### Store Or Route View Owns Rows, Filters, And Query State

Build rows in a route-local store when the list has shared filters, permissions, dialogs, deletion workflows, or route query state. The table receives `rows`, `loading`, `errorMessage`, permission flags, and callbacks from the route view.

```typescript
// frontend/src/views/workspaces/workspacesStore.ts
export const useWorkspacesStore = defineStore("workspaces", () => {
  const appShellStore = useAppShellStore();
  const { formatDate } = useDateFormat();

  const searchTerm = ref("");
  const statusFilter = ref<WorkspaceFilterValue>("all");

  const workspaceRows = computed<WorkspacesTableRow[]>(() => {
    return appShellStore.workspaces
      .filter((workspace) => matchesSearch(workspace) && matchesStatusFilter(workspace))
      .map((workspace) => ({
        contactLabel: workspace.contactName || "Contact details still need setup",
        contactSubLabel: workspace.contactEmail || "No contact email on file",
        id: workspace.id,
        name: workspace.name,
        roleLabel: resolveWorkspaceRoleLabel(workspace),
        slug: workspace.slug,
        statusLabel: resolveWorkspaceStatusLabel(workspace),
        statusTone: resolveWorkspaceTone(workspace),
        supportPhoneLabel: workspace.supportPhone || "Not provided",
        updatedLabel: formatDate(workspace.updatedTs),
      }));
  });

  function applyQueryParamsToState(query: Record<string, unknown>) {
    const searchValue = typeof query.search === "string" ? query.search.trim() : "";
    const statusValue = typeof query.status === "string" && isWorkspaceFilterValue(query.status) ? query.status : "all";

    if (searchTerm.value !== searchValue) {
      searchTerm.value = searchValue;
    }

    if (statusFilter.value !== statusValue) {
      statusFilter.value = statusValue;
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

    return query;
  }

  return {
    applyQueryParamsToState,
    buildQuery,
    workspaceRows,
    searchTerm,
    statusFilter,
  };
});
```

```vue
<!-- frontend/src/views/workspaces/WorkspacesView.vue -->
<template>
  <div class="space-y-3">
    <PageHeader
      title="Workspaces"
      description="View and manage workspaces for the selected organization"
    />

    <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
      <AppInputText
        v-model="workspacesStore.searchTerm"
        type="search"
        placeholder="Search workspaces..."
      />
      <AppSelect
        v-model="workspacesStore.statusFilter"
        :options="workspacesStore.statusOptions"
        option-label="label"
        option-value="value"
      />
    </div>

    <WorkspacesTable
      :rows="workspacesStore.workspaceRows"
      :loading="appShellStore.isWorkspacesLoading"
      :error-message="appShellStore.workspacesErrorMessage"
      :can-create="workspacesStore.canCreate"
      @create="handleCreateWorkspace"
      @open-catalogEntries="handleOpenCatalogEntries"
      @retry="void appShellStore.refreshWorkspaces()"
      @select="handleOpenWorkspace"
    />
  </div>
</template>

<script setup lang="ts">
  import { replaceRouteQuery } from "@/utils/routeQuery";
  import { useAppShellStore } from "@/views/application/appShellStore";
  import { useWorkspacesStore } from "@/views/workspaces/workspacesStore";
  import { watch } from "vue";
  import { useRoute, useRouter } from "vue-router";

  const appShellStore = useAppShellStore();
  const route = useRoute();
  const router = useRouter();
  const workspacesStore = useWorkspacesStore();

  workspacesStore.applyQueryParamsToState(route.query);
  syncStateToUrl();

  watch(
    () => route.query,
    () => {
      workspacesStore.applyQueryParamsToState(route.query);
      syncStateToUrl();
    }
  );

  watch(
    () => [workspacesStore.searchTerm, workspacesStore.statusFilter],
    () => {
      syncStateToUrl();
    }
  );

  function syncStateToUrl() {
    replaceRouteQuery(router, route, workspacesStore.buildQuery());
  }
</script>
```

Filters belong above the table because they are route view state. The table should not parse the route query or decide which backend filters to send. If a future list adds server pagination, keep `page`, `pageSize`, `totalCount`, and API filter handoff in the route-local store, then pass counts into `AppTable` and pagination controls through the wrapper's `pagination` slot.

### Use Stable Row Keys And Explicit Action Events

Prefer numeric ids returned by the backend. When a row combines multiple record types or multiple ids, create an explicit composite key in the row view model and use that key everywhere the table needs identity.

```typescript
interface OrganizationAccessInvitationRow {
  id: number;
  key: string;
  kind: "invitation";
  primaryLabel: string;
}

interface OrganizationAccessMembershipRow {
  id: number;
  key: string;
  kind: "membership";
  primaryLabel: string;
}

export type OrganizationAccessTableRow = OrganizationAccessInvitationRow | OrganizationAccessMembershipRow;

const rows = computed<OrganizationAccessTableRow[]>(() => [
  ...memberships.value.map((membership) => ({
    id: membership.id,
    key: `membership-${membership.id}`,
    kind: "membership" as const,
    primaryLabel: membership.userFullName,
  })),
  ...invitations.value.map((invitation) => ({
    id: invitation.id,
    key: `invitation-${invitation.id}`,
    kind: "invitation" as const,
    primaryLabel: invitation.email,
  })),
]);
```

```vue
<tr
  v-for="row in rows"
  :key="row.key"
  :data-testid="`organization-access-row-${row.key}`"
>
  <AppTableCell layout="stack">
    {{ row.primaryLabel }}
  </AppTableCell>
  <AppTableCell align="right">
    <AccessInvitationActions
      v-if="row.kind === 'invitation'"
      :invitation-id="row.id"
      @resend="emit('resend', $event)"
      @revoke="emit('revoke', $event)"
    />
    <AccessMembershipActions
      v-else
      :membership-id="row.id"
      @toggle-active="emit('toggle-active', $event)"
      @toggle-role="emit('toggle-role', $event)"
    />
  </AppTableCell>
</tr>
```

Do not key rows by display names, emails, array indexes, or formatted labels. If uniqueness depends on two fields, build the key from those fields explicitly. Action events should pass ids or narrow payloads, not raw rows, unless the parent genuinely needs the whole row view model.

## Things To Notice

- `AppTable` owns the repeated table surface and state branches. Route tables supply content through slots.
- Blocking loading appears only when no rows can be displayed. Inline errors allow stale rows to stay visible after a refresh failure.
- Empty state appears only after a successful non-loading request with no rows. It is not a substitute for error handling.
- `EntityIndexTable` is a second shared layer for common resource-index screens, not the only acceptable table shape.
- Table row interfaces are view models. Stores or route views derive them from API models with `computed` getters.
- Query params and filters are owned outside the table. The table receives the resulting rows and count props.
- Shared table wrappers stay store-agnostic. Route-local components may be route-specific, but they should still prefer props and emits when that keeps boundaries clear.
- Action columns use `AppIconButton` labels, stable test ids, permission-disabled states, and narrow emitted events.
- Row keys are deterministic ids or explicit composite keys. Display names are not identity.

## Rules To Follow

- Use `AppTable` for repeated resource tables before building new table chrome.
- Use `AppTableHeaderCell` and `AppTableCell` for table headers and cells unless a component is deliberately outside the app-owned table system.
- Use `EntityIndexTable` when the route matches the common name/status/updated/actions index shape.
- Keep shared table wrappers under `frontend/src/components/page/` prop-driven and free of route params, router calls, API calls, and domain-store imports.
- Keep domain-specific table components under `frontend/src/views/<route>/components/` unless the table is genuinely reusable across route domains.
- Keep filters, sort, pagination state, query parsing, loaded API records, and row view-model construction in the route view or route-local store.
- Pass `loading`, `errorMessage`, `visibleCount`, `totalCount`, `emptyTitle`, `emptyMessage`, and `loadingLabel` into the table instead of recreating those branches locally.
- Use the `emptyAction` slot for permission-aware create buttons. Do not place a second empty card below the table.
- Use the `pagination` slot when a list adds pagination controls. Do not fork `AppTable` or place pagination in unrelated page chrome.
- Emit narrow action events such as `select`, `create`, `delete`, `resend`, `toggle-active`, or `retry`.
- Use stable ids for `:key` and test ids. Use explicit composite keys for mixed row types.
- Stop event propagation for row-level icon buttons when the whole row is clickable.
- Do not import `axios`, `fetch`, `api`, `useRoute`, `useRouter`, or `useAppShellStore` into shared table wrappers.
- Do not pass snake_case backend data into table props. The API client and store/view layer should expose camelCase row view models.
- Do not add ad hoc hex colors, local table CSS, custom spinner rows, or one-off retry buttons when shared wrappers already cover the state.

## Refactor Signals

- A route view repeats `<table class="divide-line min-w-full divide-y">`, empty rows, loading rows, or retry alert markup instead of using `AppTable`.
- A route-specific table imports `api`, `axios`, `fetch`, `useRoute`, `useRouter`, or the shell store just to load rows.
- A shared component under `src/components/page/` imports a route-local store or a route-specific type.
- Several tables repeat the same name/status/updated/actions columns instead of using or extending `EntityIndexTable`.
- A table receives raw API models and performs heavy formatting, permission checks, route-query parsing, or filtering inline in the template.
- Row keys use `index`, `name`, `email`, `statusLabel`, or another non-unique display value.
- Action buttons emit raw row objects when only an id is needed.
- Loading, empty, and error UI appear in both the route view and the table for the same request.
- A table renders pagination controls outside the shared footer area or creates a second summary count.
- A list route stores filter state only in component refs when the same state should survive refresh through route query params.
- A route passes rows, loading flags, errors, and callbacks through multiple wrapper layers that could be simplified with a route-local store plus a prop-driven table.

## Verification

For guidance-only edits, run the guidance builder and Markdown checks:

```bash
rg -c '^```' agents/guidance/frameworks/vue/examples/vue-table-wrapper.md
git diff --check -- agents/guidance/frameworks/vue/examples/vue-table-wrapper.md
python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean
```

For frontend table changes, run the relevant local checks:

```bash
cd frontend
npm run type-check
npm run lint
```

Use focused searches during review to catch drift:

```bash
rg -n "<table|<th|<td|Loading\\.\\.\\.|No data|No records" frontend/src/views frontend/src/components/page
rg -n "axios|fetch\\(|useRoute\\(|useRouter\\(|useAppShellStore\\(" frontend/src/components/page
rg -n ":key=\"(index|row\\.name|.*Label|.*email)" frontend/src/views frontend/src/components/page
rg -n "#pagination|visible-count|total-count|TableFooterSummary" frontend/src/views frontend/src/components/page
```

When behavior changes, add or update component tests where the feature area already has frontend tests. Cover:

- blocking loading with no rows
- blocking error with no rows and `retry`
- inline warning with stale rows
- empty state and empty action
- row action event payloads
- deterministic row keys for mixed row types
- query-driven filters and pagination state when the route owns them

## Why It Helps

This pattern makes tables boring in the right way. Shared wrappers keep loading, error, empty, footer, and pagination behavior consistent. Route-local stores keep business state and query state auditable. Route-specific table components stay focused on columns and actions. Stable row keys and narrow events make refactors safer, and reviewers can quickly tell whether a new list is following the app's table system or drifting into one-off chrome.
