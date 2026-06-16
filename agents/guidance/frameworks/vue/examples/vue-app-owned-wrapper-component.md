---
id: framework-vue-example-app-owned-wrapper-component
title: Vue App-Owned Wrapper Component Example
description: Standards for app-owned Vue wrappers around unstyled PrimeVue primitives and plain HTML controls.
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

Use this pattern when a shared UI primitive should belong to the application instead of leaking PrimeVue, raw Tailwind class bundles, accessibility wiring, icon handling, or pass-through configuration into route views.

Good triggers include:

- a PrimeVue primitive such as `Button`, `InputText`, `Select`, `AutoComplete`, `Menu`, `Tabs`, `Tag`, `Checkbox`, or `Card` is repeated outside `src/components/`
- route views repeat the same button tones, focus rings, loading spinner, disabled state, `pt` map, `data-testid`, icon slot, or `aria-label` wiring
- form fields need consistent label, hint, error, required or optional labels, and input IDs across dialogs and route pages
- shell or navigation controls need a small plain HTML wrapper because native button or anchor behavior is enough
- a route-local component has become reusable across unrelated routes and no longer imports route stores, route params, or domain APIs
- an app-owned wrapper needs to hide the implementation difference between a PrimeVue unstyled primitive and a plain HTML control behind similar props such as `tone`, `size`, `loading`, `label`, `icon`, and `rootClass`

Do not use this pattern to turn every one-off visual block into a shared component. Promote shared wrappers when reuse is real, when the implementation is easy to misuse, or when centralizing the behavior makes review and refactoring easier.

## Why This Shape Exists

This pattern uses PrimeVue in unstyled mode:

```typescript
// frontend/src/main.ts

app.use(PrimeVue, { unstyled: true });
app.directive("tooltip", Tooltip);
```

Unstyled PrimeVue gives the app control over design tokens, spacing, focus treatment, dark-mode behavior, and overlay surfaces. The cost is that every raw PrimeVue primitive needs a complete `pt` map and consistent state classes. If route views import PrimeVue directly, the app quickly accumulates several button systems, several select overlays, several table actions, and several subtly different error states.

The app-owned wrapper boundary keeps those choices in one place:

- `frontend/src/components/ui/` owns low-level controls and surfaces such as `AppButton`, `AppIconButton`, `AppInputText`, `AppSelect`, `AppAutocomplete`, `AppCheckbox`, `AppMenu`, `AppTabStrip`, `AppTag`, `AppSurface`, `AppDrawer`, and feedback primitives.
- `frontend/src/components/forms/` owns labeled field wrappers such as `AppTextField`, `AppSelectField`, `AppTextareaField`, and `AppAutocompleteField` that compose `FormField` plus a low-level input primitive.
- `frontend/src/components/page/` owns reusable page composition and list/table pieces such as `PageHeader`, `PageSection`, `PageStatusCard`, `AppTable`, `AppTableCell`, and `EntityIndexTable`.
- `frontend/src/components/layout/` owns shell containers, scroll frames, guest/fullscreen shells, and main content panes.
- `frontend/src/components/navigation/` owns shared navigation primitives such as breadcrumbs, sidebars, and sidebar nav items.
- `frontend/src/core/survey/runtime/ui/` may own runtime-specific wrappers when the public survey runtime needs CSS-variable-driven behavior that is not the global workspace design system.

The tradeoff is that wrappers add a small layer between routes and PrimeVue. That layer is intentional. It gives reviewers one app-facing API to check, keeps semantic tokens consistent, makes route views read as item workflows, and lets the implementation move between PrimeVue and plain HTML without rewriting every caller.

## Recommended Shape

### PrimeVue Setup Stays Global And Thin

Keep PrimeVue registration in `main.ts`. Do not configure Axios, theme defaults, or per-component pass-through maps in route views or stores.

```typescript
// frontend/src/main.ts

import { createPinia } from "pinia";
import PrimeVue from "primevue/config";
import Tooltip from "primevue/tooltip";
import { createApp } from "vue";

import App from "./App.vue";
import "./assets/base.css";
import router from "./router";

const app = createApp(App);

app.use(createPinia());
app.use(PrimeVue, { unstyled: true });
app.directive("tooltip", Tooltip);
app.use(router);

app.mount("#app");
```

Global setup only enables PrimeVue and shared directives. Component-specific styling belongs inside app-owned wrappers.

### PrimeVue-Backed Wrapper Owns `pt`, Variants, Icons, And Loading

Use this shape when PrimeVue supplies useful component behavior but the app should own the public API and styling.

```vue
<!-- frontend/src/components/ui/AppButton.vue -->
<script setup lang="ts">
  import type { LucideIcon } from "@lucide/vue";

  import AppIcon from "@/components/ui/AppIcon.vue";
  import type { AppIconName } from "@/components/ui/appIcons";
  import { cn } from "@/utils/className";
  import Button from "primevue/button";
  import { computed } from "vue";

  type AppButtonTone = "primary" | "secondary" | "ghost" | "link";
  type AppButtonSize = "sm" | "md";

  interface Props {
    ariaControls?: string;
    ariaLabel?: string;
    ariaHaspopup?: boolean | "menu" | "dialog" | "grid" | "listbox" | "tree";
    buttonType?: "button" | "reset" | "submit";
    disabled?: boolean;
    form?: string;
    icon?: AppIconName | LucideIcon;
    label?: string;
    loading?: boolean;
    rootClass?: string;
    size?: AppButtonSize;
    testId?: string;
    tone?: AppButtonTone;
  }

  const props = withDefaults(defineProps<Props>(), {
    ariaControls: undefined,
    ariaLabel: undefined,
    ariaHaspopup: undefined,
    buttonType: "button",
    disabled: false,
    form: undefined,
    icon: undefined,
    label: undefined,
    loading: false,
    rootClass: undefined,
    size: "md",
    testId: undefined,
    tone: "secondary",
  });

  const sizeClasses = computed(() => {
    if (props.tone === "link") {
      return "gap-1.5 px-0 py-0 text-control";
    }

    return props.size === "sm" ? "gap-1.5 px-3 text-control min-h-9" : "gap-1.5 px-3.5 text-control min-h-10";
  });

  const toneClasses = computed(() => {
    if (props.tone === "primary") {
      return "border border-primary bg-primary text-primary-contrast shadow-xs hover:bg-primary/90";
    }

    if (props.tone === "ghost") {
      return "bg-surface-muted text-body hover:bg-line";
    }

    if (props.tone === "link") {
      return "border border-transparent bg-transparent text-secondary shadow-none hover:bg-transparent hover:text-body";
    }

    return "border border-line bg-surface text-body shadow-xs hover:border-body/15 hover:bg-surface-muted";
  });

  const buttonPt = computed(() => ({
    root: cn(
      "inline-flex items-center rounded-md font-medium transition-colors duration-200 ease-out focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-focus-ring/20 focus-visible:ring-offset-2 focus-visible:ring-offset-transparent disabled:cursor-not-allowed disabled:opacity-60",
      sizeClasses.value,
      toneClasses.value,
      props.rootClass
    ),
    loadingIcon: "text-control",
    icon: "text-control",
    label: "font-medium",
  }));
</script>

<template>
  <Button
    unstyled
    :type="buttonType"
    :aria-label="ariaLabel"
    :aria-controls="ariaControls"
    :aria-haspopup="ariaHaspopup"
    :disabled="disabled"
    :form="form"
    :icon="icon"
    :label="label"
    :loading="loading"
    :pt="buttonPt"
    :data-testid="testId"
  >
    <template
      v-if="loading"
      #loadingicon
    >
      <AppIcon
        icon="refresh"
        class="text-control h-4 w-4 animate-spin"
      />
    </template>

    <template
      v-else-if="icon"
      #icon
    >
      <AppIcon
        :icon="icon"
        class="text-control h-4 w-4"
      />
    </template>

    <template
      v-if="$slots.default"
      #default
    >
      <slot />
    </template>
  </Button>
</template>
```

This wrapper owns `unstyled`, `pt`, icons, loading slot, disabled treatment, focus rings, tokenized colors, and test ID placement. Callers use item-level props and do not need to know PrimeVue's slot names.

### Form Field Wrapper Composes Label, Error, And Input Primitive

Use a two-layer form pattern: low-level input wrappers under `components/ui/`, then labeled field wrappers under `components/forms/`.

```vue
<!-- frontend/src/components/forms/AppTextField.vue -->
<template>
  <FormField
    :label="label"
    :hint="hint"
    :error="error"
    :input-id="inputId"
    :optional-label="optionalLabel"
    :root-class="rootClass"
  >
    <AppInputText
      :input-id="inputId"
      :model-value="modelValue"
      :type="type"
      :placeholder="placeholder"
      :disabled="disabled"
      :autocomplete="autocomplete"
      :has-error="Boolean(error)"
      :test-id="testId"
      @update:model-value="onUpdateModelValue"
    />
  </FormField>
</template>

<script setup lang="ts">
  import AppInputText from "@/components/ui/AppInputText.vue";
  import FormField from "@/components/ui/FormField.vue";

  interface Props {
    autocomplete?: string;
    disabled?: boolean;
    error?: string;
    hint?: string;
    inputId?: string;
    label: string;
    modelValue: string;
    optionalLabel?: string;
    placeholder?: string;
    rootClass?: string;
    testId?: string;
    type?: "date" | "email" | "number" | "password" | "search" | "tel" | "text" | "url";
  }

  withDefaults(defineProps<Props>(), {
    autocomplete: undefined,
    disabled: false,
    error: undefined,
    hint: undefined,
    inputId: undefined,
    optionalLabel: undefined,
    placeholder: undefined,
    rootClass: undefined,
    testId: undefined,
    type: "text",
  });

  const emit = defineEmits<{
    "update:modelValue": [value: string];
  }>();

  function onUpdateModelValue(value: string | undefined) {
    emit("update:modelValue", value ?? "");
  }
</script>
```

`AppTextField` does not know about login, workspaces, catalogEntries, contacts, organizations, or any route-local store. It only coordinates the reusable field contract.

### Plain HTML Wrapper Uses The Same App Language

Use plain HTML when native behavior is enough and PrimeVue does not add useful state or accessibility handling. Keep the app-facing props just as small and semantic as PrimeVue-backed wrappers.

```vue
<!-- frontend/src/components/navigation/AppSidebarNavItem.vue -->
<script setup lang="ts">
  import type { LucideIcon } from "@lucide/vue";

  import AppIcon from "@/components/ui/AppIcon.vue";
  import type { AppIconName } from "@/components/ui/appIcons";
  import { cn } from "@/utils/className";
  import { computed } from "vue";

  interface Props {
    active?: boolean;
    badge?: string;
    collapsed?: boolean;
    disabled?: boolean;
    icon: AppIconName | LucideIcon;
    label: string;
    testId?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    active: false,
    badge: undefined,
    collapsed: false,
    disabled: false,
    testId: undefined,
  });

  const buttonClass = computed(() => {
    return cn(
      "group flex text-left transition-colors duration-150 ease-out",
      props.collapsed ? "mx-auto h-8 w-8 items-center justify-center rounded-lg p-0" : "h-9 w-full items-center justify-between rounded-lg px-2.5 py-0",
      props.disabled ? "cursor-not-allowed text-secondary opacity-60" : props.active ? "bg-line text-body" : "text-body/85 hover:bg-line/50 hover:text-body"
    );
  });

  const contentClass = computed(() => {
    return cn("flex min-w-0 items-center", props.collapsed ? "justify-center gap-0" : "gap-3");
  });
</script>

<template>
  <button
    type="button"
    :aria-label="collapsed ? label : undefined"
    :data-testid="testId"
    :disabled="disabled"
    :class="buttonClass"
  >
    <span :class="contentClass">
      <AppIcon
        :icon="icon"
        class="text-control h-[1.05rem] w-[1.05rem]"
      />
      <span class="text-base-body truncate overflow-hidden font-normal">
        {{ label }}
      </span>
    </span>

    <span
      v-if="badge"
      class="text-muted border-line bg-surface rounded-full border px-2 py-0.5 font-medium"
    >
      {{ badge }}
    </span>
  </button>
</template>
```

The component is plain HTML, but it still follows the same wrapper rules: typed semantic props, `AppIcon`, `cn(...)`, token classes, disabled behavior, accessibility labels, and a small event surface.

### Route Callers Use App Props, Not Implementation Details

{% raw %}
```vue
<!-- frontend/src/views/workspaces/WorkspacesView.vue -->
<template>
  <PageHeader
    title="Workspaces"
    description="View and manage workspaces for the selected organization"
  >
    <template #actions>
      <AppButton
        label="New workspace"
        tone="primary"
        icon="plus"
        :disabled="!appShellStore.selectedOrganization || !workspacesStore.canCreate"
        test-id="workspaces-create-button"
        @click="handleCreateWorkspace"
      />
      <AppButton
        label="Refresh"
        tone="ghost"
        icon="refresh"
        :disabled="!appShellStore.selectedOrganization || appShellStore.isWorkspacesLoading"
        @click="void appShellStore.refreshWorkspaces()"
      />
    </template>
  </PageHeader>

  <div class="relative max-w-[17.5rem] flex-1">
    <AppIcon
      icon="search"
      class="text-secondary text-control pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2"
    />
    <AppInputText
      v-model="workspacesStore.searchTerm"
      type="search"
      placeholder="Search workspaces..."
      test-id="workspaces-search-input"
      input-class="pl-9"
    />
  </div>
</template>
```
{% endraw %}

Callers still pass route-owned state, disabled conditions, handlers, and IDs. They do not pass PrimeVue `pt` objects, raw icon slots, spinner markup, focus-ring classes, or duplicated button color classes.

### Keep Wrapper Families Split By Responsibility

```text
frontend/src/components/
├── forms/
│   ├── AppAutocompleteField.vue
│   ├── AppCheckboxField.vue
│   ├── AppSelectField.vue
│   ├── AppTextField.vue
│   └── AppTextareaField.vue
├── layout/
│   ├── AppContainer.vue
│   ├── AppMobileShellBar.vue
│   ├── AppShellFrame.vue
│   ├── FullscreenPageShell.vue
│   ├── GuestPageShell.vue
│   └── MainContentPane.vue
├── navigation/
│   ├── AppBreadcrumbs.vue
│   ├── AppSidebarNavItem.vue
│   └── SidebarNav.vue
├── page/
│   ├── AppTable.vue
│   ├── AppTableCell.vue
│   ├── EntityIndexTable.vue
│   ├── PageHeader.vue
│   ├── PageSection.vue
│   └── PageStatusCard.vue
└── ui/
    ├── AlertBanner.vue
    ├── AppButton.vue
    ├── AppCheckbox.vue
    ├── AppDrawer.vue
    ├── AppIcon.vue
    ├── AppIconButton.vue
    ├── AppInputText.vue
    ├── AppMenu.vue
    ├── AppSelect.vue
    ├── AppSurface.vue
    ├── AppTabStrip.vue
    └── AppTag.vue
```

Do not create a generic `components/common/` or `components/shared/` bucket when the component has a clearer responsibility. Folder placement should tell reviewers whether the wrapper is a primitive control, a labeled form field, page composition, layout shell, or navigation piece.

### Keep Specialized Runtime Wrappers In Their Runtime Boundary

The public survey runtime uses CSS-variable-driven wrappers under `frontend/src/core/survey/runtime/ui/`. That is a valid separate family because the runtime has a different theming contract.

```vue
<!-- frontend/src/core/survey/runtime/ui/SurveyRuntimeButton.vue -->
<script setup lang="ts">
  import AppIcon from "@/components/ui/AppIcon.vue";
  import { cn } from "@/utils/className";
  import Button from "primevue/button";
  import { computed } from "vue";

  const buttonPt = computed(() => ({
    root: cn(
      "inline-flex items-center rounded-md font-medium transition-all duration-200 ease-out focus-visible:ring-2 focus-visible:ring-focus-ring/20",
      "rounded-[var(--ti-button-radius)] [font-weight:var(--ti-button-font-weight)] [text-transform:var(--ti-button-text-transform)]",
      sizeClasses.value,
      toneClasses.value,
      props.rootClass
    ),
    icon: "text-control",
    label: "font-medium",
  }));
</script>
```

Do not pull runtime-only CSS variable behavior into global workspace wrappers unless the main app design system has adopted the same contract. Do not import runtime wrappers into workspace route views just to get a different visual variant.

### Avoid Raw PrimeVue And Duplicated Tailwind In Route Views

```vue
<!-- Avoid in frontend/src/views/<route>/... -->
<template>
  <Button
    unstyled
    label="Refresh"
    :pt="{
      root: 'rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm hover:bg-slate-50',
      label: 'font-medium',
    }"
  />

  <button class="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm hover:bg-slate-50">
    Refresh
  </button>
</template>
```

```vue
<!-- Prefer in frontend/src/views/<route>/... -->
<template>
  <AppButton
    label="Refresh"
    tone="ghost"
    icon="refresh"
    :disabled="isLoading"
    @click="emit('refresh')"
  />
</template>
```

Raw primitives and copied class bundles are allowed only inside the app-owned wrapper, a route-local component that is deliberately not reusable yet, or a specialized runtime boundary. Once the pattern is repeated across routes, promote it to the right shared component family.

## Things To Notice

- The wrapper API uses application language. Props such as `tone`, `size`, `loading`, `label`, `icon`, `testId`, `rootClass`, `inputId`, and `hasError` are easier to review than PrimeVue-specific slot and `pt` details at every call site.
- PrimeVue `pt` maps stay inside wrappers. Route views should not construct `pt` objects for standard controls.
- Wrappers use semantic Tailwind tokens such as `bg-surface`, `text-body`, `text-secondary`, `border-line`, `bg-primary`, `text-primary-contrast`, `text-error`, `text-warning`, and `ring-focus-ring`.
- `cn(...)` from `frontend/src/utils/className.ts` is the local class combiner. Use it when variants or caller classes need to merge cleanly.
- `AppIcon` and `appIcons.ts` are the icon boundary. Repeated icon buttons should use app icon names or typed Lucide icon props instead of inline SVG.
- Accessibility labels belong in the wrapper contract. Icon-only buttons require a real `label` or `ariaLabel`, drawers need `role="dialog"` and a label, and collapsed navigation should still expose text to assistive technology.
- Shared wrappers under `src/components/` stay store-agnostic. They should not import `useAppShellStore`, route-local stores, `api`, `router`, `route`, domain DTOs, or permission helpers.
- Wrappers can accept `rootClass`, `contentClass`, `inputClass`, or similar escape hatches, but those props are for layout integration and small spacing changes, not a second variant system.
- A form field wrapper composes label, hint, error, and the input primitive. It does not own validation, submit state, API calls, or server error parsing.
- A page wrapper composes common page structure. It does not own route query params, data loading, organization selection, or business mutations.

## Rules To Follow

- Keep raw PrimeVue imports out of route views and route-local stores. Route views should import app wrappers such as `AppButton`, `AppInputText`, `AppSelect`, `AppTable`, `PageHeader`, or route-local components that compose them.
- Keep PrimeVue `unstyled` and `pt` configuration inside app-owned wrappers or specialized runtime wrappers.
- Create shared wrappers under the narrowest correct folder: `ui/` for primitives, `forms/` for labeled inputs, `page/` for page composition, `layout/` for shell frames, and `navigation/` for navigation primitives.
- Keep wrapper props small, typed, and semantic. Do not mirror every PrimeVue prop unless multiple real call sites need that surface.
- Prefer app-level variant props over raw palette classes at call sites. Add a `tone`, `size`, `variant`, `align`, or `layout` prop only when the distinction is repeated and item-meaningful.
- Use semantic tokens and existing utility classes. Do not introduce ad hoc hex colors, raw slate/blue palettes, bespoke shadows, or one-off radii for standard controls.
- Use `AppIcon` and `AppIconName` for shared wrapper icons. Do not paste inline SVG into wrappers when a Lucide/app icon exists.
- Keep wrappers prop-driven and store/domain agnostic. Shared components must not call the API, read route params, import route-local stores, or branch on organization, workspace, catalogEntry, contact, or permission domain rules.
- Keep route-specific composition under `src/views/<route>/components/` until reuse crosses route boundaries.
- Promote a route-local component to `src/components/` only after removing route imports, domain-store imports, API calls, route-param assumptions, and domain-specific copy that would make the shared API misleading.
- Use `data-testid` or `testId` consistently at the wrapper boundary when the component is a common test target.
- For icon-only interactive controls, require accessible label text and wire it to `aria-label` and tooltip behavior through the wrapper.
- Prefer native HTML wrappers when the browser already supplies the correct behavior. Use PrimeVue wrappers for overlays, menus, tabs, autocomplete, dropdowns, dialogs, or controls where PrimeVue handles state and accessibility better.
- Keep specialized runtime wrappers, such as survey runtime wrappers, inside their runtime boundary unless the same visual and behavior contract becomes global.

## Refactor Signals

- A route view imports from `primevue/*` for a standard button, input, select, tag, card, menu, tabs, autocomplete, or checkbox.
- A route view or route-local component defines a `pt` object for a standard control already represented by an app wrapper.
- Several views repeat the same long button, input, table, drawer, tag, or surface class strings.
- Callers pass raw Tailwind color classes such as `bg-blue-*`, `text-slate-*`, `border-gray-*`, or ad hoc hex values for a standard control.
- A shared component imports `api`, `useRoute`, `useRouter`, `useAppShellStore`, a route-local store, or domain-specific DTOs.
- A component under `src/components/ui/` contains item copy, route names, organization/workspace/catalogEntry/contact branching, or permission rules.
- One component exposes both PrimeVue implementation details and app variant props, forcing callers to understand both APIs.
- Icon-only buttons render without accessible labels or have a tooltip that is not backed by the same label text.
- Form views repeat label, hint, and error markup instead of using `FormField` or a field wrapper.
- A wrapper has many rarely used props copied from PrimeVue. Shrink the public API to the variants and behavior the app actually uses.
- A runtime-specific wrapper is imported into workspace routes for visual convenience.

## Verification

Run structural checks when adding or refactoring app-owned wrappers:

```bash
rg -n "from \"primevue/|from 'primevue/" frontend/src/views frontend/src/components --glob "*.vue" --glob "*.ts"
rg -n ":pt=|\\bpt=|const .*Pt|computed\\(\\(\\) => \\(\\{" frontend/src/views --glob "*.vue"
rg -n "bg-(blue|slate|gray|zinc|neutral)-|text-(blue|slate|gray|zinc|neutral)-|#[0-9A-Fa-f]{3,6}" frontend/src/views frontend/src/components --glob "*.vue" --glob "*.ts"
rg -n "use[A-Z].*Store|@/utils/api|useRoute|useRouter" frontend/src/components --glob "*.vue" --glob "*.ts"
```

Run frontend verification when code changes:

```bash
cd frontend
npm run type-check
npm run lint
```

For guidance-only edits, verify the authored guidance builds into generated agent output:

```bash
rg -c '^```' agents/guidance/frameworks/vue/examples/vue-app-owned-wrapper-component.md
git diff --check -- agents/guidance/frameworks/vue/examples/vue-app-owned-wrapper-component.md
python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean
```

When reviewing a wrapper migration, also spot check representative callers. A good migration should make route views shorter and more semantic without moving route workflow state into shared components.

## Why It Helps

- The application owns its design system even when the implementation is backed by PrimeVue.
- Route views stay focused on page composition, route params, stores, API calls, and user workflow instead of low-level component styling.
- `pt` changes, token changes, focus-state fixes, dark-mode fixes, and accessibility fixes happen once in a wrapper instead of across many routes.
- Shared wrapper APIs make reviews more deterministic: reviewers can check `tone`, `size`, `loading`, `label`, `icon`, and `hasError` instead of parsing long class strings.
- Store-agnostic wrappers are easier to reuse and safer to refactor because they do not drag organization, workspace, auth, or route assumptions into unrelated screens.
- Plain HTML and PrimeVue-backed wrappers can coexist while still presenting a consistent app-facing contract.
