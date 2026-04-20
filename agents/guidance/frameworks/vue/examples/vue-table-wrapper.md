---
id: framework-vue-example-table-wrapper
title: Vue Table Wrapper Example
description: Example shared table wrapper with slots for actions, rows, loading, empty state, and pagination.
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

- Use this pattern when multiple route screens render resource lists with the same page chrome, loading state, empty state, and pagination controls.

## Recommended Shape

### Shared Wrapper

{% raw %}
```vue
<script setup lang="ts">
defineProps<{
  header: string
  description: string
  hasRows: boolean
  loading?: boolean
}>()
</script>

<template>
  <div class="px-4 sm:px-6 lg:px-8">
    <div class="md:flex md:items-center">
      <div class="md:flex-auto">
        <h1 class="text-base font-semibold text-slate-900">{{ header }}</h1>
        <p class="mt-2 text-sm text-slate-600">{{ description }}</p>
      </div>
      <div class="mt-4 md:ml-16 md:mt-0">
        <slot name="actions" />
      </div>
    </div>

    <div class="mt-8 overflow-x-auto">
      <table class="min-w-full divide-y divide-slate-200">
        <thead>
          <tr v-if="!loading">
            <slot name="header" />
          </tr>
        </thead>

        <tbody class="divide-y divide-slate-200 bg-white">
          <slot
            v-if="hasRows && !loading"
            name="rows"
          />

          <tr v-else-if="!loading">
            <td
              colspan="100"
              class="px-4 py-8 text-center italic text-slate-500"
            >
              No data
            </td>
          </tr>

          <tr v-else>
            <td
              colspan="100"
              class="px-4 py-8 text-center text-slate-500"
            >
              Loading...
            </td>
          </tr>
        </tbody>
      </table>

      <div class="mt-4 flex justify-end">
        <slot name="pagination" />
      </div>
    </div>
  </div>
</template>
```
{% endraw %}

### Route Usage

{% raw %}
```vue
<AppTable
  header="Profiles"
  description="A list of all profiles in the system"
  :has-rows="filteredProfiles.length > 0"
  :loading="isLoading"
>
  <template #actions>
    <AppTextField v-model="profileFilter" placeholder="Search..." />
  </template>

  <template #header>
    <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.14em] text-secondary">Name</th>
    <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.14em] text-secondary">Status</th>
  </template>

  <template #rows>
    <tr v-for="profile in filteredProfiles" :key="profile.id">
      <td class="px-4 py-3 text-sm text-body">{{ profile.name }}</td>
      <td class="px-4 py-3 text-sm text-body">{{ profile.statusLabel }}</td>
    </tr>
  </template>

  <template #pagination>
    <AppPagination
      :current-page="currentPage"
      :items-per-page="itemsPerPage"
      :total-items="filteredProfiles.length"
      @select-page="setPage"
    />
  </template>
</AppTable>
```
{% endraw %}

### Things To Notice

- The wrapper owns repetitive list chrome, not the route component.
- Loading and empty states stay consistent across screens.
- Route code stays focused on filters, row rendering, and resource-specific actions.

## Why It Helps

- Shared list behavior becomes easier to maintain, and new resource screens can stay small and consistent.
