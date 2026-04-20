---
id: framework-vue-example-dialog-form
title: Vue Dialog Form Example
description: Example self-contained dialog pattern for form submission and success handling.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - dialog
  - form
applies_to:
  - vue
status: active
order: 2
---

# Vue Dialog Form Example

## Scenario

- Use this shape when a creation flow should live inside a focused dialog while the parent page keeps list and navigation context.

## Recommended Shape

### Good Example

```vue
<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
    success: [number]
}>()

const isSaving = ref(false)
const errorMessage = ref('')

async function submit(formValues: ClinicInput) {
    isSaving.value = true
    errorMessage.value = ''

    try {
        const clinic = await api.clinics.create(formValues)
        toast.add({ severity: 'success', summary: 'Clinic created' })
        emit('success', clinic.id)
    } catch (error) {
        errorMessage.value = getFirstApiErrorMessage(error)
    } finally {
        isSaving.value = false
    }
}
</script>
```

### Things To Notice

- The dialog owns submit state, API calls, toast feedback, and error parsing.
- The parent only receives a minimal success signal.
- Error handling is centralized through a shared helper.

## Why It Helps

- This keeps parent pages simple and prevents form logic from leaking across the workspace.
