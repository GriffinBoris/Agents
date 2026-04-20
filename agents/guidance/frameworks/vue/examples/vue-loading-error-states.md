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

- Use this pattern when a page fetches data and needs a standard loading, error, and retry flow.

## Recommended Shape

### Good Example

```vue
<div v-if="loading && !rows.length" class="flex h-full items-center justify-center px-4 py-12">
  <StatusCard title="Loading records" description="Preparing the latest records for this view" />
</div>
<div v-else-if="error" class="flex h-full items-center justify-center px-4 py-12">
  <StatusCard
    title="Unable to load records"
    :error-message="error"
    :show-retry="true"
    @retry="refreshData"
  />
</div>
```

### Things To Notice

- Loading and error states use shared components instead of route-local markup.
- The retry action stays inside the shared status wrapper instead of being rebuilt in each page.
- The success path renders only after both blocking states are cleared.

## Why It Helps

- Users get a consistent loading and retry experience across the app.
