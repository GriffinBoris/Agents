---
id: framework-vue-example-app-layout
title: Vue App Layout Example
description: Example small-app and workspace-route layout shapes for Vue repositories using src/views as the main modern frontend boundary.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - structure
applies_to:
  - vue
status: active
order: 18
---

# Vue App Layout Example

## Scenario

- Use these fake file structures when deciding whether a frontend can stay flat or should split route folders, shell-level stores, and transport utilities more aggressively.

## Recommended Shape

### Small App With A Few Routes

```text
src/
├── assets/
├── components/
│   └── ui/
├── router/
│   └── index.ts
├── types/
│   ├── api/
│   │   └── ErrorResponseInterface.ts
│   └── auth/
│       ├── ChangePasswordInterface.ts
│       ├── ForgotPasswordRequestInterface.ts
│       ├── LoginRequestInterface.ts
│       ├── SignUpRequestInterface.ts
│       └── UserInterface.ts
├── utils/
│   ├── api.ts
│   └── errorHandling.ts
└── views/
    ├── application/
    │   ├── authStore.ts
    │   └── themeStore.ts
    ├── login/
    │   └── LoginView.vue
    ├── register/
    │   └── RegisterView.vue
    └── overview/
        └── OverviewView.vue
```

### Workspace App With Shared Shell State, Domain Models, And Route Folders

```text
src/
├── assets/
├── components/
│   ├── forms/
│   ├── layout/
│   ├── navigation/
│   ├── page/
│   └── ui/
├── router/
│   └── index.ts
├── types/
│   ├── api/
│   │   └── ErrorResponseInterface.ts
│   ├── auth/
│   │   ├── ChangePasswordInterface.ts
│   │   ├── ForgotPasswordRequestInterface.ts
│   │   ├── LoginRequestInterface.ts
│   │   └── SignUpRequestInterface.ts
│   ├── project/
│   │   ├── ProjectInputInterface.ts
│   │   └── ProjectInterface.ts
│   └── workspace/
│       ├── WorkspaceInputInterface.ts
│       ├── WorkspaceInterface.ts
│       └── WorkspaceAvailableOptionsInterface.ts
├── utils/
│   ├── api.ts
│   ├── caseConversion.ts
│   └── errorHandling.ts
└── views/
    ├── application/
    │   ├── authStore.ts
    │   ├── workspaceStore.ts
    │   └── themeStore.ts
    ├── projects/
    │   ├── ProjectsView.vue
    │   └── projectsStore.ts
    ├── projectDetail/
    │   ├── ProjectDetailView.vue
    │   └── components/
    │       └── ProjectHeader.vue
    ├── login/
    │   └── LoginView.vue
    ├── onboarding/
    │   └── OnboardingView.vue
    ├── settings/
    │   └── SettingsView.vue
    └── workspaces/
        ├── WorkspacesView.vue
        └── workspacesStore.ts
```

## Things To Notice

- Use `src/views/` as the main home for modern route-based frontend code.
- Use `src/components/forms/`, `src/components/layout/`, `src/components/navigation/`, `src/components/page/`, and `src/components/ui/` for distinct shared responsibilities instead of putting all shared components into one flat folder.
- Keep route entry views and route-local helpers together in the same route folder.
- Keep shared shell-level stores under `src/views/application/` instead of introducing a top-level `src/stores/` directory.
- Keep the canonical API client in `src/utils/api.ts` instead of introducing a top-level `src/services/` directory.
- Keep shared UI primitives in `src/components/`.
- Keep frontend data models under `src/types/<domain>/` instead of a catch-all `src/types.ts` file or a generic model bucket.
- Use explicit model filenames such as `WorkspaceInterface.ts`, `WorkspaceInputInterface.ts`, `ForgotPasswordRequestInterface.ts`, and `ErrorResponseInterface.ts`.
- Keep router files thin and use them to wire route folders together rather than embedding large view logic inside router modules.

## Why It Helps

- The route tree becomes the main ownership map for frontend work.
- Shared shell state still has one obvious home without expanding a parallel global store root.
- Transport stays centralized while the rest of the app remains organized around routes instead of abstract feature buckets.
