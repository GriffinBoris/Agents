---
id: framework-vue-example-auth-shell
title: Vue Auth-Aware Shell Example
description: Example shared application shell that swaps between authenticated and guest layouts.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - shell
applies_to:
  - vue
status: active
order: 3
---

# Vue Auth-Aware Shell Example

## Scenario

- Use this pattern when the app should share one layout wrapper while still rendering different chrome for signed-in and signed-out users.

## Recommended Shape

### Good Example

```vue
<script setup lang="ts">
import ApplicationContentPane from '@/components/application/ApplicationContentPane.vue'
import ApplicationDesktopMenu from '@/components/application/ApplicationDesktopMenu.vue'
import ApplicationMobileMenu from '@/components/application/ApplicationMobileMenu.vue'
import GuestPageShell from '@/components/application/GuestPageShell.vue'
import { useAuthStore } from '@/views/application/authStore'
import { computed } from 'vue'
import { RouterView } from 'vue-router'

const authStore = useAuthStore()
const isAuthenticated = computed(() => authStore.isAuthenticated)
</script>

<template>
  <div v-if="isAuthenticated" class="flex h-screen w-screen flex-col gap-1 sm:flex-row sm:py-2">
    <ApplicationMobileMenu class="sm:hidden" />
    <ApplicationDesktopMenu class="hidden sm:block" />

    <ApplicationContentPane>
      <RouterView />
    </ApplicationContentPane>
  </div>

  <GuestPageShell v-else>
    <RouterView />
  </GuestPageShell>
</template>
```

### Things To Notice

- Auth state drives one shared shell decision instead of every page repeating layout logic.
- The authenticated shell can still own its own sidebar, bootstrap, and responsive layout internally.
- Guest pages stay inside one shared guest wrapper instead of reimplementing outer page spacing.

## Why It Helps

- Layout behavior stays centralized, responsive, and easier to evolve without touching every route component.
