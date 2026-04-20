---
id: framework-vue-example-polling
title: Vue Polling Example
description: Example component-scoped polling with explicit start and stop ownership.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - polling
applies_to:
  - vue
status: active
order: 11
---

# Vue Polling Example

## Scenario

- Use this pattern when a component needs auto-refresh behavior tied to visibility or a user toggle.

## Recommended Shape

### Good Example

```typescript
const shouldStopAutoRefresh = () => !autoRefreshEnabled.value
const { startPolling: startAutoRefresh, stopPolling: stopAutoRefresh } = usePolling(
  () => {
    if (isLoading.value || isRefreshing.value) {
      return
    }

    if (countdownSeconds.value <= 1) {
      resetCountdown()
      void handleRefresh(true)
    } else {
      countdownSeconds.value -= 1
    }
  },
  shouldStopAutoRefresh,
  1000,
  { autoStart: false, immediate: false },
)
```

### Things To Notice

- `usePolling` lives in the component, where Vue lifecycle hooks are available.
- `autoStart: false` keeps ownership explicit for visibility-driven polling.
- `shouldStop` handles the durable stop condition while the callback guards transient loading states.

## Why It Helps

- Polling behavior is consistent and easy to shut down cleanly.
