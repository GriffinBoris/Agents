---
id: framework-vue-example-route-query-state
title: Vue Route Query State Example
description: Example query-string-driven tab and filter state for deep-linkable views.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - routing
applies_to:
  - vue
status: active
order: 10
---

# Vue Route Query State Example

## Scenario

- Use this pattern when a view needs deep-linkable filter or tab state that should survive refreshes and shared URLs.

## Recommended Shape

### Good Example

```typescript
const route = useRoute()
const router = useRouter()
const activeTab = ref('breakdown')

const applyQueryParamsToStore = () => {
  const query = route.query

  if (query.tab && ['breakdown', 'schedules', 'excel', 'results'].includes(query.tab as string)) {
    activeTab.value = query.tab as string
  }
}

const syncStoreToUrl = () => {
  const query: Record<string, string> = {}

  if (activeTab.value !== 'breakdown') {
    query.tab = activeTab.value
  }

  router.replace({ query: Object.keys(query).length > 0 ? query : undefined })
}
```

### Things To Notice

- Query params are applied during initialization and normalized back into the URL as state changes.
- Default values are omitted so the URL stays clean.
- The component keeps top-level view state in the route while the store still owns the underlying data.

## Why It Helps

- Bookmarks and shared links reopen the same filtered view.
