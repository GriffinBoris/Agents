---
id: framework-vue-example-task-polling
title: Vue Task Polling Example
description: Example helper that polls task endpoints with timeout and progress callbacks.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - tasks
applies_to:
  - vue
status: active
order: 12
---

# Vue Task Polling Example

## Scenario

- Use this pattern when a backend endpoint returns a `task_id` and the frontend should wait for completion predictably.

## Recommended Shape

### Good Example

```typescript
export function waitForTaskCompletion(taskId: number, options: WaitForTaskCompletionOptions = {}) {
  const intervalMs = options.intervalMs ?? DEFAULT_POLL_INTERVAL_MS
  const maxAttempts = options.maxAttempts ?? DEFAULT_MAX_ATTEMPTS

  return new Promise<Task>((resolve, reject) => {
    let attempts = 0
    let scheduler: ReturnType<typeof createPollingScheduler> | null = null

    scheduler = createPollingScheduler(
      async () => {
        if (attempts >= maxAttempts) {
          reject(new Error('Timed out while waiting for the task to finish.'))
          return
        }

        attempts += 1

        const task = await api.task.get(taskId)
        options.onProgress?.(task)

        if (isTaskCompleted(task.status)) {
          scheduler?.stop()
          resolve(task)
          return
        }

        if (isTaskFailed(task.status)) {
          scheduler?.stop()
          reject(new Error(task.progressMessage || 'Task failed.'))
        }
      },
      {
        intervalMs,
        logErrors: false,
        onError: reject,
      },
    )

    scheduler.start()
  })
}
```

### Things To Notice

- Status helpers keep task-state checks readable.
- Progress callbacks and timeout behavior stay inside one reusable helper.
- Features can wait for tasks without reinventing scheduler logic.

## Why It Helps

- Task-backed flows stay consistent across the frontend.
