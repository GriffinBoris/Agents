---
id: framework-vue-example-route-folder
title: Vue Route Folder Example
description: Example route-based `src/views/` structure where each route folder owns its local pieces.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - structure
applies_to:
  - vue
status: active
order: 19
---

# Vue Route Folder Example

## Scenario

- Use this fake file structure when a route needs more than one component and should keep its local pieces together under `src/views/`.

## Recommended Shape

### Small Route

```text
src/
├── components/
│   └── ui/
├── router/
│   └── index.ts
├── utils/
│   └── api.ts
└── views/
    ├── Application/
    │   ├── baseStore.ts
    │   └── themeStore.ts
    └── Login/
        └── LoginView.vue
```

### Route Folder With Local Pieces

```text
src/
├── components/
│   └── ui/
├── router/
│   └── index.ts
├── utils/
│   └── api.ts
└── views/
    ├── application/
    │   ├── baseStore.ts
    │   ├── tenantStore.ts
    │   └── themeStore.ts
    ├── customers/
    │   ├── CustomersView.vue
    │   ├── customersStore.ts
    │   ├── CustomerFiltersInterface.ts
    │   ├── constants.ts
    │   └── components/
    │       ├── CustomerFilters.vue
    │       └── CustomerTable.vue
    └── customerDetail/
        ├── CustomerDetailView.vue
        ├── customerDetailStore.ts
        ├── useCustomerDetail.ts
        └── components/
            ├── CustomerActions.vue
            └── CustomerSummary.vue
```

### Things To Notice

- `src/views/` is the route-based home for page-specific code.
- In this repository, shared shell-level stores should live under `src/views/application/` instead of a top-level `src/stores/` folder.
- In this repository, the canonical API client should live under `src/utils/api.ts` instead of a top-level `src/services/` folder.
- Small routes can stay as a single view file.
- Larger routes can keep a descriptively named local store file, subcomponents, constants, and helpers beside the route view.
- Shared UI primitives still belong in `src/components`, but modern route state should stay in `src/views/` and shared transport helpers should stay in `src/utils/`.

## Why It Helps

- Route logic stays easy to find, and the global folders stay reserved for code that is actually shared.
