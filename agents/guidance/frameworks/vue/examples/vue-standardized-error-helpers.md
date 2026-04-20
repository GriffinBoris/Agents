---
id: framework-vue-example-standardized-error-helpers
title: Vue Standardized Error Helpers Example
description: Example shared helpers for parsing DRF standardized errors once and reusing them across forms and toasts.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - errors
applies_to:
  - vue
status: active
order: 9
---

# Vue Standardized Error Helpers Example

## Scenario

- Use this pattern when frontend code needs one consistent way to parse DRF standardized error responses.

## Recommended Shape

### Good Example

```typescript
export function parseApiError(error: unknown): StandardizedErrorResponse | null {
  if (!isApiError(error)) {
    return null
  }

  const data = error.response?.data
  if (!isStandardizedErrorResponse(data)) {
    return null
  }

  return data
}

export function extractFieldErrors(error: unknown): FieldErrors {
  const fieldErrors: FieldErrors = {}
  const errorResponse = parseApiError(error)
  if (!errorResponse) {
    return fieldErrors
  }

  errorResponse.errors.forEach((err) => {
    const attrKey = err.attr
    if (attrKey) {
      if (!fieldErrors[attrKey]) {
        fieldErrors[attrKey] = []
      }
      fieldErrors[attrKey]!.push(err.detail)
    }
  })

  return fieldErrors
}
```

### Things To Notice

- Unknown errors are type-checked before field extraction logic runs.
- One helper returns field-level arrays, while other helpers can collapse them for toasts or form libraries.
- Form code can stay small because parsing logic is centralized.

## Why It Helps

- Error handling stays consistent across forms, toasts, and generic API surfaces.
