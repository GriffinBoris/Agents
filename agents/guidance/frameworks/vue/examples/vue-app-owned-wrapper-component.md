---
id: framework-vue-example-app-owned-wrapper-component
title: Vue App-Owned Wrapper Component Example
description: Example shared UI wrappers around unstyled PrimeVue primitives and plain HTML controls with similar app-facing APIs.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - components
  - primevue
applies_to:
  - vue
status: active
order: 18
---

# Vue App-Owned Wrapper Component Example

## Scenario

- Use this pattern when either a PrimeVue primitive such as `Button`, `Tag`, `Message`, or `Card`, or a plain HTML control such as `<button>` or `<a>`, should become a reusable app-owned component with shared styling and a small prop API.
- The app-facing wrapper API does not need to diverge just because one implementation uses PrimeVue and another uses plain HTML.

## Recommended Shape

### PrimeVue Wrapper Example

```vue
<script setup lang="ts">
import { cn } from '@/utils/className'
import Button from 'primevue/button'
import { computed } from 'vue'

type AppButtonTone = 'primary' | 'secondary' | 'ghost'
type AppButtonSize = 'sm' | 'md'

interface Props {
  buttonType?: 'button' | 'reset' | 'submit'
  disabled?: boolean
  icon?: string
  label?: string
  rootClass?: string
  size?: AppButtonSize
  tone?: AppButtonTone
}

const props = withDefaults(defineProps<Props>(), {
  buttonType: 'button',
  disabled: false,
  icon: undefined,
  label: undefined,
  rootClass: undefined,
  size: 'md',
  tone: 'secondary',
})

const sizeClasses = computed(() => {
  return props.size === 'sm' ? 'gap-1.5 px-3 py-1.5 text-[13px]' : 'gap-1.5 px-3.5 py-2 text-[13px]'
})

const toneClasses = computed(() => {
  if (props.tone === 'primary') {
    return 'border border-primary bg-primary text-primary-contrast shadow-sm hover:bg-primary/90'
  }

  if (props.tone === 'ghost') {
    return 'border border-transparent bg-transparent text-secondary hover:bg-line/50 hover:text-primary'
  }

  return 'border border-line bg-surface text-body shadow-sm hover:bg-line/30'
})

const buttonPt = computed(() => ({
  root: cn(
    'inline-flex items-center rounded-md font-medium transition-colors duration-200 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring/20 focus-visible:ring-offset-2 focus-visible:ring-offset-transparent disabled:cursor-not-allowed disabled:opacity-60',
    sizeClasses.value,
    toneClasses.value,
    props.rootClass,
  ),
  icon: 'text-[13px]',
  label: 'font-medium',
}))
</script>

<template>
  <Button
    unstyled
    :type="buttonType"
    :disabled="disabled"
    :icon="icon"
    :label="label"
    :pt="buttonPt"
  >
    <template
      v-if="$slots.default"
      #default
    >
      <slot />
    </template>
  </Button>
</template>
```

### Plain HTML Wrapper Example

```vue
<script setup lang="ts">
import { cn } from '@/utils/className'
import { type VariantProps, cva } from 'class-variance-authority'
import type { HTMLAttributes } from 'vue'

const button = cva('shadow-xs focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 hover:cursor-pointer', {
  variants: {
    size: {
      sm: 'rounded-md px-2 py-1 text-sm font-normal',
      md: 'rounded-md px-2.5 py-1.5 text-sm font-normal',
      lg: 'rounded-md px-3 py-2 text-sm font-normal',
    },
    tone: {
      primary: 'border border-primary bg-primary text-primary-contrast hover:bg-primary/90 focus-visible:outline-primary',
      secondary: 'border border-line bg-surface text-body hover:bg-background focus-visible:outline-primary',
      ghost: 'border border-transparent bg-transparent text-body hover:bg-background focus-visible:outline-primary',
    },
    disabled: {
      true: 'disabled:cursor-not-allowed disabled:opacity-60',
      false: '',
    },
  },
  defaultVariants: {
    size: 'md',
    tone: 'primary',
    disabled: false,
  },
})

type ButtonProps = VariantProps<typeof button>

interface Props {
  class?: HTMLAttributes['class']
  disabled?: boolean
  iconPosition?: 'leading' | 'trailing'
  loading?: boolean
  size?: ButtonProps['size']
  tone?: ButtonProps['tone']
  type?: 'button' | 'reset' | 'submit'
}

const props = withDefaults(defineProps<Props>(), {
  class: undefined,
  disabled: false,
  iconPosition: 'leading',
  loading: false,
  size: 'md',
  tone: 'primary',
  type: 'button',
})
</script>

<template>
  <button
    :type="type"
    :disabled="disabled || loading"
    :class="cn(button({ size, tone, disabled: disabled || loading }), props.class)"
  >
    <span class="flex items-center justify-center gap-2">
      <span
        v-if="loading"
        class="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
      />

      <template v-else>
        <slot
          v-if="iconPosition === 'leading'"
          name="icon"
        />
        <slot />
        <slot
          v-if="iconPosition === 'trailing'"
          name="icon"
        />
      </template>
    </span>
  </button>
</template>
```

### Things To Notice

- Choose the base primitive by responsibility.
- Use a PrimeVue-backed wrapper when the component needs accessibility-heavy behavior, overlays, keyboard support, or richer internal state that PrimeVue already handles well.
- Use a plain HTML wrapper when the component is mostly a visual primitive and native browser behavior is already sufficient.
- Keep the app-facing prop API as similar as practical across PrimeVue-backed and plain HTML wrappers when they solve the same product problem.
- In both cases, keep the prop API small and use product language such as `tone`, `size`, `loading`, or `iconPosition` instead of leaking raw styling internals into every caller.
- Centralize variant classes in one place so spacing, focus treatment, color usage, radius, and disabled states stay consistent.
- Let the wrapper own low-level implementation details such as `unstyled`, `pt`, `cva(...)`, spinner markup, slot ordering, and semantic token usage.
- Do not mirror the entire third-party component API unless multiple real call sites need that surface.

## Why It Helps

- Shared wrappers let the application own the design system whether the implementation is backed by PrimeVue or plain HTML.
- Screens stay focused on page logic instead of accumulating repeated Tailwind classes, pass-through configuration, and one-off loading or icon patterns.
