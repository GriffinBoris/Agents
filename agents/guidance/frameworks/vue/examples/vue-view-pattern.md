---
id: framework-vue-example-view-pattern
title: Vue View Pattern Example
description: Example view pattern for computed collections, focused fetch helpers, and stale-request guards.
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

- Use this shape when a workspace view derives collections from loaded data and must ignore stale async responses.

## Recommended Shape

### Good Example

```typescript
const selectedWorkspaceId = computed(() => workspaceStore.selectedWorkspaceId)
const rows = ref<Order[]>([])
const isLoading = ref(false)

const filteredRows = computed(() => {
  const items: Order[] = []

  for (const row of rows.value) {
    if (row.status === selectedStatus.value) {
      items.push(row)
    }
  }

  return items
})

async function fetchOrders() {
  const activeWorkspaceId = selectedWorkspaceId.value
  if (!activeWorkspaceId) {
    rows.value = []
    return
  }

  isLoading.value = true

  try {
    const response = await api.orders.list(activeWorkspaceId)
    if (selectedWorkspaceId.value !== activeWorkspaceId) {
      return
    }

    rows.value = response
  } finally {
    if (selectedWorkspaceId.value === activeWorkspaceId) {
      isLoading.value = false
    }
  }
}
```

### Things To Notice

- Derived rows live in a computed instead of a manually synchronized ref.
- The fetch helper owns one resource.
- The request captures the active workspace ID before awaiting so late responses do not overwrite newer state.

## Why It Helps

- This keeps workspace views deterministic, easier to debug, and less prone to stale-data bugs.
