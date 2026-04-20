---
id: framework-vue-example-notification-system
title: Vue Notification System Example
description: Example shared store-backed notification stack mounted once near the app root.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - notifications
applies_to:
  - vue
status: active
order: 16
---

# Vue Notification System Example

## Scenario

- Use this pattern when multiple pages need the same success, error, info, or warning feedback channel.

## Recommended Shape

### Shared Store

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Notification {
  id: string
  message: string
  type: 'success' | 'error' | 'info' | 'warning'
  duration: number
  createdAt: number
}

export const useNotificationStore = defineStore('notification', () => {
  const notifications = ref<Notification[]>([])

  function addNotification(notification: Omit<Notification, 'id' | 'createdAt'>) {
    const id = crypto.randomUUID()
    const createdAt = Date.now()

    notifications.value.push({ ...notification, id, createdAt })

    setTimeout(() => {
      removeNotification(id)
    }, notification.duration)

    return id
  }

  function removeNotification(id: string) {
    notifications.value = notifications.value.filter((notification) => notification.id !== id)
  }

  return { notifications, addNotification, removeNotification }
})
```

### Root-Level Container

```vue
<script setup lang="ts">
import NotificationItem from '@/components/ui/NotificationItem.vue'
import { useNotificationStore } from '@/stores/notification'

const notificationStore = useNotificationStore()
</script>

<template>
  <Teleport to="body">
    <div class="fixed right-4 top-4 z-50 flex flex-col space-y-2">
      <TransitionGroup name="notification">
        <NotificationItem
          v-for="notification in notificationStore.notifications"
          :key="notification.id"
          :notification="notification"
        />
      </TransitionGroup>
    </div>
  </Teleport>
</template>
```

### Things To Notice

- One store owns the notification queue instead of every page rendering its own success or error banner.
- The container mounts once near the app root and uses `Teleport` so overlays stay outside page layout flow.
- Feature views can call shared notification helpers without depending on where the UI is rendered.

## Why It Helps

- Feedback stays consistent across the app, and cross-route notification styling only needs to be updated in one place.
