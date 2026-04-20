---
id: framework-vue-example-composable-reactivity
title: Vue Composable Reactivity Example
description: Example top-level computed pattern for nested refs returned from composables.
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

- Use this shape when a composable returns nested refs or computeds and the template needs a stable top-level binding.

## Recommended Shape

### Good Example

```typescript
const pinnedCustomersList = computed(() => favorites.pinnedCustomers.value)
```

```vue
<CustomersPanel :pinned-customers="pinnedCustomersList" />
```

### Things To Notice

- The component unwraps the nested reactive value into a top-level computed.
- The template binds to the top-level computed instead of reaching into `.value` on a nested composable property.

## Why It Helps

- This keeps template reactivity more predictable and makes the dependency clearer to readers.
