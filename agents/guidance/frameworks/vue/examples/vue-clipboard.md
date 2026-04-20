---
id: framework-vue-example-clipboard
title: Vue Clipboard Example
description: Example shared clipboard composable that wraps browser clipboard access.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - clipboard
applies_to:
  - vue
status: active
order: 13
---

# Vue Clipboard Example

## Scenario

- Use this pattern when components need copy-to-clipboard behavior and should not call the browser API directly.

## Recommended Shape

### Good Example

```typescript
export function useClipboard() {
  const copiedText = ref<string | null>(null)

  const copyToClipboard = async (text: string) => {
    if (!text) {
      return false
    }

    try {
      await navigator.clipboard.writeText(text)
      copiedText.value = text
      setTimeout(() => {
        if (copiedText.value === text) {
          copiedText.value = null
        }
      }, 2000)
      return true
    } catch (err) {
      console.error('Failed to copy text', err)
      return false
    }
  }

  return {
    copiedText,
    copyToClipboard,
  }
}
```

### Things To Notice

- Clipboard access is centralized instead of repeated in each component.
- The composable exposes a tiny success state alongside the copy function.
- Failures surface as `false`, so callers can decide whether to show success UI.

## Why It Helps

- Clipboard behavior stays consistent and easy to replace or extend.
