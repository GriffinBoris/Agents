---
id: framework-vue-example-composable-reactivity
title: Vue Composable Reactivity Example
description: Standards for readable reactive aliases, computed view models, and safe store or composable access in Vue.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - reactivity
applies_to:
  - vue
status: active
order: 4
---

# Vue Composable Reactivity Example

## Scenario

Use this pattern when a Vue route view, route-local component, or composable needs to read reactive state from another composable, Pinia store, route params, or shell store and then expose that state to the template or to another composable.

Common triggers include:

- a composable returns refs, computeds, reactive form values, or nested reactive state
- a route view reads shell state such as `appShellStore.selectedOrganizationId` and route params such as `workspaceId`
- a route-local component consumes a route-local Pinia store and needs table rows, labels, disabled flags, or option lists
- a component is about to put `.value`, chained ternaries, repeated store paths, or lookup work directly in the template
- a composable needs ongoing access to a reactive value instead of a one-time primitive snapshot

Do not create top-level aliases just to rename every field. Use them when they clarify ownership, preserve reactivity across a boundary, or keep templates readable.

## Why This Shape Exists

Vue templates are easiest to review when they read like markup plus named state, not like inline reactive plumbing. The repo already leans on this shape: route views and stores keep source records in `ref(...)`, derive page labels and row models in `computed(...)`, and pass plain props into shared components.

The main failure modes are subtle:

- destructuring Pinia setup-store state can lose reactive access or hide where state is owned
- passing `someComputed.value` into a composable gives the composable a snapshot, not a live reactive dependency
- placing `.value` chains, nested composable paths, or dense lookup expressions in templates makes reactivity and ownership harder to audit
- duplicating derived refs by manually assigning labels, rows, or options creates synchronization bugs when the source record changes
- using helper functions for reactive view models can recompute at surprising times and makes dependencies less explicit than `computed(...)`

The standard is to keep source state close to the owner, expose top-level computed aliases for values the template or another composable needs, and build view models with computed getters. This accepts a few extra named bindings so templates, stores, and composables stay easier to scan.

## Recommended Shape

### Alias Shell, Route, And Store State At The Boundary

Route views can read stores and route params directly, then expose stable top-level computed bindings for values that are reused by API calls, guards, child props, or composables.

```vue
<script setup lang="ts">
  import { useSchemaValidation } from "@/composables/useSchemaValidation";
  import { createDefaultItemInput, itemInputSchema } from "@/types/item/ItemRequestInterface";
  import { getRouteNumberParam } from "@/utils/routeParams";
  import { useAppShellStore } from "@/views/application/appShellStore";
  import { APP_PERMISSIONS } from "@/views/application/permissions";
  import { useItemDetailForm } from "@/views/itemDetail/useItemDetailForm";
  import { computed } from "vue";
  import { useRoute, useRouter } from "vue-router";

  const route = useRoute();
  const router = useRouter();
  const appShellStore = useAppShellStore();
  const schemaValidation = useSchemaValidation(itemInputSchema, createDefaultItemInput());

  const selectedOrganizationId = computed(() => appShellStore.selectedOrganizationId);
  const workspaceId = computed(() => getRouteNumberParam(route, "workspaceId"));
  const catalogEntryId = computed(() => getRouteNumberParam(route, "catalogEntryId"));
  const itemId = computed(() => getRouteNumberParam(route, "itemId"));
  const isCreateMode = computed(() => route.name === "items-create" || !itemId.value);
  const canManageItems = computed(() => appShellStore.can(APP_PERMISSIONS.workspaceManage, { workspaceId: workspaceId.value }));

  const itemForm = useItemDetailForm({
    canManageItems,
    workspaceId,
    isCreateMode,
    catalogEntryId,
    itemId,
    router,
    schemaValidation,
    selectedOrganizationId,
  });
</script>
```

The composable receives reactive objects with a `.value` contract, not primitive snapshots:

```typescript
interface ItemDetailFormParams {
  canManageItems: { value: boolean };
  workspaceId: { value: number | null };
  isCreateMode: { value: boolean };
  catalogEntryId: { value: number | null };
  itemId: { value: number | null };
  selectedOrganizationId: { value: number | null };
}

export function useItemDetailForm(params: ItemDetailFormParams) {
  watch(
    [params.selectedOrganizationId, params.workspaceId, params.itemId, params.catalogEntryId],
    () => {
      void loadItem();
    },
    { immediate: true }
  );

  async function loadItem() {
    const organizationId = params.selectedOrganizationId.value;
    const activeWorkspaceId = params.workspaceId.value;
    const activeCatalogEntryId = params.catalogEntryId.value;

    if (!organizationId || !activeWorkspaceId || !activeCatalogEntryId) {
      return;
    }

    // Load through the canonical api client here.
  }

  return {
    loadItem,
  };
}
```

Avoid passing a raw value when the composable must react to later changes:

```typescript
// Avoid: this is a one-time snapshot.
useItemDetailForm({
  workspaceId: workspaceId.value,
  selectedOrganizationId: selectedOrganizationId.value,
});
```

### Use Top-Level Computed Aliases For Nested Composable Refs

When a composable returns a grouped object with nested refs or computeds, unwrap the value through a top-level computed before the template uses it.

```typescript
const favorites = useFavoriteContacts();

const pinnedContactRows = computed(() => favorites.pinnedContacts.value);
const hasPinnedContacts = computed(() => pinnedContactRows.value.length > 0);
```

```vue
<ContactsPanel
  :rows="pinnedContactRows"
  :show-empty-state="!hasPinnedContacts"
/>
```

Avoid making the template reach into the nested reactive shape:

```vue
<!-- Avoid -->
<ContactsPanel
  :rows="favorites.pinnedContacts.value"
  :show-empty-state="favorites.pinnedContacts.value.length === 0"
/>
```

The alias gives the nested dependency one clear name. If the composable later changes from `pinnedContacts` to `favoriteRows`, the template remains insulated from that internal shape.

### Keep Pinia Store Access Direct

For route-local stores, prefer direct access through the store object. Pinia setup stores already expose state, getters, and actions through that object, and the guidance prefers direct store access over destructuring.

```vue
<template>
  <PageStatusCard
    v-if="!contactDetailStore.isCreateMode && contactDetailStore.isLoading && !contactDetailStore.contact"
    title="Loading contact"
    description="Preparing this contact record for review"
    show-loading
  />

  <ContactFormSection />

  <PageActionFooter @cancel="handleCancel()">
    <AppButton
      :label="submitLabel"
      tone="primary"
      :disabled="!contactDetailStore.canManage || contactDetailStore.isSaving || contactDetailStore.isLoading"
      @click="void submitForm()"
    />
  </PageActionFooter>
</template>

<script setup lang="ts">
  import { useContactDetailStore } from "@/views/contactDetail/contactDetailStore";
  import { computed } from "vue";

  const contactDetailStore = useContactDetailStore();

  const submitLabel = computed(() => (contactDetailStore.isCreateMode ? "Create contact" : "Save changes"));
  const pageTitle = computed(() => {
    if (contactDetailStore.isCreateMode) {
      return "Create contact";
    }

    const fullName = `${contactDetailStore.formValues.firstName} ${contactDetailStore.formValues.lastName}`.trim();
    return fullName || contactDetailStore.formValues.email || "Contact detail";
  });
</script>
```

Avoid destructuring store state and getters into loose variables by default:

```typescript
// Avoid for store state/getters in route components.
const { canManage, isLoading, isSaving, formValues } = useContactDetailStore();
```

If a legacy file already uses `storeToRefs(...)`, keep the local file internally consistent while touching it. Do not introduce `storeToRefs(...)` into modern route code merely to shorten property names.

### Build Computed View Models For Templates

Templates should receive table rows, select options, status labels, and card models from named computed values. Source API data stays in the store or local ref; display shape is derived.

```typescript
const rateCardRows = computed<RateCardsTableRow[]>(() => {
  return rateCards.value.map((profile) => ({
    workspaceName: workspaceNameById.value.get(profile.workspace),
    description: profile.description,
    id: profile.id,
    linkedPlanCountLabel: String(profile.linkedPlanCount),
    linkedCatalogEntryCountLabel: String(profile.linkedCatalogEntryCount),
    primaryLabel: profile.name,
    secondaryLabel: `${profile.linkedCatalogEntryCount} catalogEntries linked`,
    statusLabel: formatEnumLabel(profile.status),
    statusTone: profile.status === RateCardStatus.ACTIVE ? "success" : "neutral",
    updatedLabel: formatDate(profile.updatedTs),
  }));
});
```

```vue
<RateCardsTable
  :rows="rateCardRows"
  :loading="isLoading"
  :error-message="errorMessage"
  @retry="void load()"
/>
```

For larger transforms, use a clear loop inside the computed instead of a dense chain.

```typescript
const visibleActionRows = computed<ActionRow[]>(() => {
  const rows: ActionRow[] = [];

  for (const action of actions.value) {
    if (!action.isVisible) {
      continue;
    }

    rows.push({
      id: action.id,
      label: action.label,
      tone: action.isDestructive ? "danger" : "neutral",
    });
  }

  return rows;
});
```

### Use Helpers For Pure Formatting, Computed For Reactive State

Use helper functions when the helper is pure and depends only on its arguments. Use computed values when the output depends on refs, store state, props, or route state.

```typescript
const addressRows = computed<ContactAddressesTableRow[]>(() => {
  return (contactDetailStore.contact?.addresses ?? []).map((address) => ({
    addressLineOne: address.addressLineOne,
    addressLineTwo: buildAddressLine(address),
    defaultLabel: address.isDefault ? "Default" : "Optional",
    defaultTone: address.isDefault ? "success" : "neutral",
    fullName: address.fullName || "No name",
    id: address.id,
    phoneLabel: address.phone || "No phone",
    typeLabel: formatEnumLabel(address.addressType),
    updatedLabel: formatDate(address.updatedTs),
  }));
});

function buildAddressLine(address: ContactAddressInterface) {
  const parts = [address.addressLineTwo, `${address.city}, ${address.state} ${address.postalCode}`.trim(), address.countryCode];
  return parts.filter(Boolean).join(" - ");
}
```

Do not turn reactive state derivation into plain functions called from the template:

```vue
<!-- Avoid -->
<ContactAddressesTable :rows="buildAddressRows()" />
```

### Keep Templates Free Of `.value` And Heavy Lookups

`<script setup>` templates unwrap top-level refs and computeds. Templates should bind to named state rather than spelling out `.value`, map lookups, or chained conditional logic.

```vue
<template>
  <PageHeader
    :title="pageTitle"
    :description="pageDescription"
  />

  <AppTabStrip
    :items="itemTabs"
    :model-value="activeItemTab"
    @update:model-value="handleItemTabChange"
  />
</template>
```

```typescript
const itemTabs = computed<AppTabStripItem[]>(() => {
  if (isCreateMode.value) {
    return [];
  }

  return [
    { key: "overview", label: "Overview" },
    { key: "variants", label: "Variants", count: variantRecords.value.length },
    { key: "pricing", label: "Pricing", count: pricingPlanRows.value.length },
  ];
});
```

Avoid this shape:

```vue
<!-- Avoid -->
<AppTabStrip
  :items="[
    { key: 'variants', label: 'Variants', count: variantRecords.value.length },
    { key: 'pricing', label: 'Pricing', count: pricingPlanRows.value.length }
  ]"
  :model-value="itemTabs.activeTab.value"
/>
```

## Things To Notice

- The owner of the source state remains clear: shell state lives in `appShellStore`, route business state lives in route-local stores, and form state lives in `useSchemaValidation(...)` or the owning route-local store.
- Top-level computed aliases mark the reactive boundary where route params, shell state, and composables are handed into local logic.
- Templates consume stable names such as `pageTitle`, `submitLabel`, `addressRows`, and `rateCardRows` instead of reaching through nested refs or doing work inline.
- Composables that need live state accept refs or computed values through a small `{ value: ... }` contract.
- Store state and getters are accessed through the store object, which makes ownership visible at every call site.
- Derived UI data is recomputed from source records instead of manually synchronized with extra mutable refs.
- Helper functions stay pure. They format a single row or value; they do not read route, store, or composable state behind the caller's back.

## Rules To Follow

- Do not use `.value` in Vue templates. Expose a top-level computed or ref with a readable name instead.
- Do not put nested composable paths such as `favorites.pinnedContacts.value` in templates.
- Do not destructure Pinia store state or getters in modern route code. Use `const store = useThingStore()` and access `store.field`, `store.getter`, and `store.action()` directly.
- Do not pass `computedValue.value` into a composable when that composable must react to future changes. Pass the computed or ref itself.
- Keep route params and shell state behind named computed aliases when they are reused by watchers, API calls, permission checks, or composables.
- Build table rows, select options, tabs, page labels, disabled flags, and status labels with `computed(...)`.
- Use helper functions for pure formatting only. If a helper reads refs, store state, route state, or props, make the reactive dependency explicit through a computed getter or function argument.
- Keep shared components prop-driven. Do not make shared components import route-local stores just to avoid passing computed view models.
- Avoid duplicate mutable state for derived labels, counts, rows, and options. Store the source data once and derive the display shape.
- When touching legacy code, keep the file internally consistent, but do not copy legacy destructuring or template-heavy patterns into modern route folders.

## Refactor Signals

Move code toward this pattern when you see:

- `.value` inside a `.vue` template
- template bindings that reach through nested composables, such as `thing.state.items.value.length`
- a route view repeatedly using `appShellStore.selectedOrganizationId`, `route.params.foo`, or `store.record?.nested?.field` inline instead of naming the dependency once
- destructured Pinia state or getters such as `const { isLoading, rows } = useContactsStore()`
- a composable receiving `organizationId.value`, `workspaceId.value`, or `isCreateMode.value` and then trying to watch those values
- a template calling `buildRows()`, `formatSomething(store.record)`, `new Map(...)`, or several chained ternaries
- manually assigned derived refs such as `statusLabel.value = ...` after every load or save
- repeated row-building logic in multiple components that should be one computed view model in the route-local owner
- shared components importing route-local stores instead of accepting computed props
- helper functions that silently read global route, shell, or store state

## Verification

For guidance or refactor work touching this pattern, run the smallest relevant checks:

```bash
rg -n "\\.value" frontend/src --glob "*.vue"
rg -n "const \\{[^}]+\\} = use[A-Z].*Store\\(" frontend/src/views --glob "*.vue" --glob "*.ts"
rg -n "storeToRefs" frontend/src/views --glob "*.vue" --glob "*.ts"
rg -n ":[a-zA-Z0-9-]+=\".*\\.value|v-if=\".*\\.value|v-for=\".*\\.value" frontend/src --glob "*.vue"
```

Use the hits as review prompts, not automatic failures. Some `.value` hits are expected inside `<script setup>` blocks, composables, stores, and render-function style code. Template `.value` usage, destructured store state, and nested reactive chains in modern route code should be cleaned up.

When TypeScript or Vue code changes, also run the frontend checks that match the touched area:

```bash
cd frontend
npm run type-check
npm run lint
```

For this authored guidance file, also verify the generated agent output:

```bash
python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean
```

## Why It Helps

This pattern keeps Vue reactivity visible without making templates noisy. Route views read as page outlines, route-local stores remain the owner of business state, composables receive live dependencies when they need them, and shared components stay prop-driven.

The result is easier review: a reviewer can see what owns the data, where the reactive dependency enters the flow, which values are derived, and whether a refactor accidentally turned live state into a stale snapshot.
