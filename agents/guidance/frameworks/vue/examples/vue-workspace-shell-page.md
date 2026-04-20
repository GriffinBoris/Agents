---
id: framework-vue-example-workspace-shell-page
title: Vue Workspace Shell And Page Example
description: Example shared workspace shell and scoped page composition using app-owned wrappers, a shell store, and route-level page sections.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - shell
  - layout
applies_to:
  - vue
status: active
order: 19
---

# Vue Workspace Shell And Page Example

## Scenario

- Use this pattern when a Vue workspace has one shared shell, scoped route pages, and a small shared set of page-composition components.

## Recommended Shape

### Example File Structure

```text
src/
├── components/
│   ├── forms/
│   │   ├── AppSelectField.vue
│   │   ├── AppTextField.vue
│   │   └── AppTextareaField.vue
│   ├── layout/
│   │   ├── AppContainer.vue
│   │   ├── AppShellFrame.vue
│   │   └── MainContentPane.vue
│   ├── navigation/
│   │   ├── AppSidebarNavItem.vue
│   │   └── SidebarNav.vue
│   ├── page/
│   │   ├── InsetCard.vue
│   │   ├── ListCardRow.vue
│   │   ├── MetricCard.vue
│   │   ├── PageHeader.vue
│   │   ├── PageSection.vue
│   │   └── PageSplitLayout.vue
│   └── ui/
│       ├── AlertBanner.vue
│       ├── AppButton.vue
│       ├── AppInputText.vue
│       ├── AppSelect.vue
│       ├── AppSurface.vue
│       ├── AppTag.vue
│       ├── AppTextarea.vue
│       └── ThemeToggleButton.vue
├── router/
│   └── index.ts
└── views/
    ├── application/
    │   ├── WorkspaceShellView.vue
    │   ├── workspaceShellStore.ts
    │   └── themeStore.ts
    ├── resources/
    │   └── ResourcesView.vue
    └── design/
        └── ComponentPreviewView.vue
```

### Shell View Example

```vue
<template>
  <AppContainer>
    <div class="h-full w-full p-3 sm:p-4 lg:p-5">
      <AppShellFrame>
        <template #sidebar>
          <SidebarNav
            :items="navItems"
            :active-key="activeNavKey"
            @select="handleSelect"
          />
        </template>

        <MainContentPane v-if="workspaceShellStore.hasInitialized">
          <RouterView />
        </MainContentPane>

        <MainContentPane v-else content-class="flex min-h-full items-center justify-center p-6">
          <PageStatusCard
            title="Loading workspace"
            description="Preparing workspace context, access, and the first route view"
            :error-message="workspaceShellStore.errorMessage"
            :show-retry="Boolean(workspaceShellStore.errorMessage)"
            @retry="void workspaceShellStore.initialize()"
          />
        </MainContentPane>
      </AppShellFrame>
    </div>
  </AppContainer>
</template>
```

### Scoped Page Example

{% raw %}
```vue
<template>
  <div class="space-y-4">
    <PageSection content-class="mt-0">
      <PageHeader
        eyebrow="Projects"
        title="Project workspace"
        description="Manage records inside the selected workspace"
      >
        <template #actions>
          <AppButton label="Refresh" tone="secondary" @click="void workspaceShellStore.refreshResources()" />
        </template>
      </PageHeader>
    </PageSection>

    <PageSplitLayout>
      <template #primary>
        <PageSection
          eyebrow="Workspace"
          title="Selected workspace"
          description="Keep workspace selection in shared shell state"
        >
          <div class="mt-5 grid gap-4 lg:grid-cols-[minmax(16rem,22rem)_minmax(0,1fr)]">
            <AppSelect
              :model-value="workspaceShellStore.selectedWorkspaceId"
              :options="workspaceShellStore.workspaces"
              option-label="name"
              option-value="id"
              @update:model-value="handleWorkspaceChange"
            />

            <InsetCard>
              <p class="text-sm font-medium text-body">{{ selectedWorkspaceName }}</p>
            </InsetCard>
          </div>
        </PageSection>

        <PageSection
          eyebrow="Resource list"
          title="Workspace resources"
          description="Use shared list rows and shared states for the first workflow page"
        >
          <AlertBanner v-if="workspaceShellStore.resourcesErrorMessage" :message="workspaceShellStore.resourcesErrorMessage" tone="warning" />

          <div v-else-if="resourceRows.length" class="mt-5 space-y-3">
            <ListCardRow
              v-for="resource in resourceRows"
              :key="resource.id"
              :title="resource.name"
              :description="resource.description"
              :tag-tone="resource.tagTone"
              :tag-value="resource.tagValue"
            />
          </div>
        </PageSection>
      </template>
    </PageSplitLayout>
  </div>
</template>
```
{% endraw %}

## Things To Notice

- The shell owns bootstrap loading, navigation, and router outlet placement.
- Shared shell state lives under `src/views/application/` and exposes the selected scope plus current user context.
- Route pages compose shared `page/` wrappers so the view reads like a page outline instead of low-level card markup.
- Shared `ui/` primitives own semantic token usage, radius, border, and interaction styling.
- Shared `forms/` wrappers layer labels, hints, and errors on top of lower-level input primitives.
- The route page uses shell state instead of re-fetching bootstrap context for itself.

## Why It Helps

- The shell stays consistent across routes.
- Page views stay readable and focused on domain workflow composition.
- Shared layout, input, and page wrappers keep spacing, theme, and panel structure homogeneous.
