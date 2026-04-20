---
id: framework-vue-example-type-interface-pattern
title: Vue Type Interface Pattern Example
description: Example domain-foldered interface and input-type files under src/types using explicit filenames and optional Zod schemas.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - types
applies_to:
  - vue
status: active
order: 20
---

# Vue Type Interface Pattern Example

## Scenario

- Use this pattern when a frontend route or API module needs shared entity models, request payload types, validation schemas, or enum definitions.

## Recommended Shape

### Domain Type Folder

```text
src/
└── types/
    ├── api/
    │   └── ErrorResponseInterface.ts
    ├── auth/
    │   ├── ChangePasswordInterface.ts
    │   ├── ForgotPasswordRequestInterface.ts
    │   ├── LoginRequestInterface.ts
    │   └── SignUpRequestInterface.ts
    └── tenant/
        ├── TenantAvailableOptionsInterface.ts
        ├── TenantInputInterface.ts
        └── TenantInterface.ts
```

### Entity Interface Example

```typescript
export interface TenantInterface {
  id: number
  name: string
  slug: string
  status: string
  brandName: string
  supportEmail: string
  membershipRole?: string
  createdTs: string
  updatedTs: string
}
```

### Input Interface With Schema Example

```typescript
import { z } from 'zod'

export const tenantInputSchema = z.object({
  name: z.string().min(1, 'Tenant name is required'),
  slug: z.string().min(1, 'Slug is required'),
  brandName: z.string().min(1, 'Brand name is required'),
  supportEmail: z.string().email('Support email must be valid'),
})

export type TenantInputInterface = z.infer<typeof tenantInputSchema>

export function createDefaultTenantInput(): TenantInputInterface {
  return {
    name: '',
    slug: '',
    brandName: '',
    supportEmail: '',
  }
}
```

### Shared Error Shape Example

```typescript
export interface ErrorResponseInterface {
  errors: ErrorItemInterface[]
}

export interface ErrorItemInterface {
  attr?: string
  detail: string
}
```

## Things To Notice

- Group type files by domain under `src/types/<domain>/`.
- Use explicit filenames that describe the contract instead of one generic `types.ts` file.
- Keep entity interfaces and input interfaces separate when their shapes differ.
- Colocate Zod schemas and `createDefault...()` helpers with the input interface when a form depends on that contract.
- Keep shared API error shapes in a dedicated `api/` type folder instead of redefining them in every route.

## Why It Helps

- Entity shapes stay reusable across routes, stores, and API modules.
- Input validation stays close to the form contract that uses it.
- New contributors can find domain types quickly without scanning unrelated route code.
