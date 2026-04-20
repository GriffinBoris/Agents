---
id: framework-vue-example-multi-step-form
title: Vue Multi-Step Form Example
description: Example parent-owned multi-step form state with step-local validation and submit logic.
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
order: 18
---

# Vue Multi-Step Form Example

## Scenario

- Use this pattern when a workflow spans multiple screens but should still build one shared request object.

## Recommended Shape

### Parent View

```vue
<script setup lang="ts">
import { ref } from 'vue'

const step = ref(0)
const signUpRequest = ref<SignUpInput>({
  firstName: '',
  lastName: '',
  email: '',
  passwordOne: '',
  passwordTwo: '',
  companyName: '',
  addressOne: '',
  addressTwo: '',
  city: '',
  state: '',
  zipCode: '',
  phone: '',
})

function nextStep() {
  step.value += 1
}

function previousStep() {
  step.value -= 1
}
</script>

<template>
  <SignUpStepOne
    v-if="step === 0"
    :sign-up-request="signUpRequest"
    @next-step="nextStep"
  />

  <SignUpStepTwo
    v-else
    :sign-up-request="signUpRequest"
    @previous-step="previousStep"
  />
</template>
```

### Step Component

```vue
<script setup lang="ts">
import { useField, useForm } from 'vee-validate'
import { watch } from 'vue'

const emit = defineEmits<{
  nextStep: []
}>()

const props = defineProps<{
  signUpRequest: SignUpInput
}>()

const { values, meta } = useForm({
  validationSchema,
  initialValues: props.signUpRequest,
})

const { value: firstName } = useField('firstName')
const { value: email } = useField('email')

watch(
  values,
  (newValues) => {
    Object.assign(props.signUpRequest, newValues)
  },
  { deep: true },
)

async function continueToNextStep() {
  if (!meta.value.valid) {
    return
  }

  await api.auth.validateUser(props.signUpRequest)
  emit('nextStep')
}
</script>
```

### Things To Notice

- The parent owns the shared DTO and current step.
- Each step validates only the fields it owns.
- Step components can call validation or preflight APIs without owning the whole workflow container.
- Shared state survives moving forward and backward because the DTO stays in the parent.

## Why It Helps

- Multi-step forms stay organized without splitting one workflow into unrelated local states.
