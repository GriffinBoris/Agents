---
id: framework-vue-example-form-validation
title: Vue Dual Validation Example
description: Example form flow combining schema validation with server-side error mapping.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - forms
applies_to:
  - vue
status: active
order: 7
---

# Vue Dual Validation Example

## Scenario

- Use this pattern when a form needs client-side validation and server-side field errors in one flow.

## Recommended Shape

### Good Example

{% raw %}
```vue
<template>
  <form @submit.prevent="void submitLogin()">
    <AppTextField v-model="values.email" label="Email" type="email" :error="errors.email" />
    <AppTextField v-model="values.password" label="Password" type="password" :error="errors.password" />

    <AlertBanner v-if="errorMessage" :message="errorMessage" tone="warning" />

    <AppButton button-type="submit" :disabled="isSubmitting" label="Sign in" />
  </form>
</template>

<script setup lang="ts">
import { useSchemaValidation } from '@/composables/useSchemaValidation'
import { createDefaultLoginRequest, loginRequestSchema, type LoginRequestInterface } from '@/types/auth/LoginRequestInterface'
import { extractFieldErrors, getFirstApiErrorMessage } from '@/utils/errorHandling'
import { api } from '@/utils/api'
import { ref } from 'vue'

const { values, errors, setErrors, validate } = useSchemaValidation<LoginRequestInterface>(
  loginRequestSchema,
  createDefaultLoginRequest(),
)

const isSubmitting = ref(false)
const errorMessage = ref('')

async function submitLogin() {
  const isValid = await validate()
  if (!isValid) {
    return
  }

  isSubmitting.value = true
  errorMessage.value = ''

  try {
    await api.auth.login(values)
  } catch (error) {
    const apiFieldErrors = extractFieldErrors(error)
    setErrors({
      email: apiFieldErrors.email?.[0],
      password: apiFieldErrors.password?.[0],
    })
    errorMessage.value = getFirstApiErrorMessage(error, 'Unable to sign in.')
  } finally {
    isSubmitting.value = false
  }
}
</script>
```
{% endraw %}

```typescript
const { values, errors, reset, validate } = useSchemaValidation<FormInputInterface>(
  formInputSchema,
  createDefaultFormInput(),
)

const isSubmitting = ref(false)
const errorMessage = ref('')

const submitForm = async () => {
  const isValid = await validate()
  if (!isValid) return

  isSubmitting.value = true
  errorMessage.value = ''

  try {
    await api.domain.create(values as FormInputInterface)
    reset(createDefaultFormInput())
  } catch (error) {
    errorMessage.value = getFirstApiErrorMessage(error, 'Unable to submit the form.')
  } finally {
    isSubmitting.value = false
  }
}
```

### Things To Notice

- The Zod schema and `createDefault...()` helper live in the same type file as the input contract.
- `useSchemaValidation(...)` exposes one reactive `values` object plus field-level `errors`.
- Client-side field validation stays separate from server-side field mapping and the API-level error banner.
- Forms validate before submission and only hit the API when the schema is valid.
- Resetting with `reset(createDefault...())` keeps form state aligned with the shared default contract.

## Why It Helps

- Users see immediate field-level validation while still getting a clear server error when submission fails.
- Validation rules, defaults, and request types stay aligned because they are defined together.
