---
id: framework-vue-example-route-auth-guard
title: Vue Route Auth Guard Example
description: Example route meta plus a global router guard backed by shared auth state.
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
order: 6
---

# Vue Route Auth Guard Example

## Scenario

- Use this pattern when some routes require authentication and redirect rules should stay centralized.

## Recommended Shape

### Good Example

```typescript
import { useAuthStore } from '@/views/application/authStore'
import DashboardView from '@/views/dashboard/DashboardView.vue'
import LoginView from '@/views/login/LoginView.vue'
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: { name: 'dashboard' } },
    { path: '/dashboard', name: 'dashboard', component: DashboardView, meta: { requiresAuth: true } },
    { path: '/login', name: 'login', component: LoginView, meta: { guestOnly: true } },
  ],
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore()

  if (!authStore.hasInitialized && !authStore.isLoading) {
    await authStore.initialize()
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.meta.guestOnly && authStore.isAuthenticated) {
    return { name: 'dashboard' }
  }
})
```

### Things To Notice

- Route access rules live in router metadata instead of being re-implemented inside page components.
- One global guard owns redirect behavior for both protected routes and guest-only routes.
- The guard reads shared auth state instead of making every route fetch its own session status.

## Why It Helps

- Auth routing stays predictable, and new protected routes only need metadata instead of duplicated gatekeeping code.
