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

Use this pattern when a Vue route, route-local store, dialog, form, or API module needs a shared frontend contract for data that crosses a boundary.

Good triggers include:

- a Django endpoint returns a persisted resource, detail payload, options bundle, or action response
- a create, update, transition, or action endpoint accepts a frontend payload
- a form needs a Zod schema, default state, and typed field errors
- a route-local store needs to type records, rows, filters, and mutations without using `any`
- a frontend API method needs to declare both the response type and request body type
- an existing form is using a returned entity interface as editable state
- a new domain needs a clear home under `frontend/src/types/<domain>/`

Do not use this pattern to create broad catch-all type files or named filter interfaces for every small query object. The goal is one obvious contract per API or form boundary, not more files than the workflow needs.

## Why This Shape Exists

The frontend has three important data boundaries:

- Django serializers return snake_case API payloads with backend-owned fields such as `id`, timestamps, status, counts, nested objects, and derived labels.
- Vue stores, components, and route views use camelCase state and should not know about Django serializer casing.
- Forms and actions submit only the fields the frontend can actually send, often a smaller or different shape than the returned resource.

The canonical API client in `frontend/src/utils/api.ts` converts request bodies and response bodies at the transport boundary. That means shared frontend interfaces should describe the post-conversion camelCase shape that route code actually consumes. If a Django serializer returns `created_ts`, the frontend type should expose `createdTs`. Components and stores should never type local state with snake_case keys just because the backend uses them.

Separating returned resource interfaces from request/input interfaces prevents a common form bug: editable state grows fake `id`, `createdTs`, `updatedTs`, nested lists, or placeholder IDs just to satisfy a persisted entity interface. Those fields are not part of the submitted contract, so they should not appear in the form DTO.

The tradeoff is a little more naming discipline. A domain folder can contain `ThingInterface.ts`, `ThingInputInterface.ts`, `ThingRequestInterface.ts`, `ThingAvailableOptionsInterface.ts`, `ThingEnums.ts`, and action-specific response files. In exchange, the API module, store, form, and tests can all point to the same explicit contract.

## Recommended Shape

### Domain Type Folder

Group shared API and domain contracts by domain under `frontend/src/types/<domain>/`.

```text
frontend/src/types/
├── api/
│   ├── EmptyResponseInterface.ts
│   └── ErrorResponseInterface.ts
├── auth/
│   ├── AppAccessInterface.ts
│   ├── AppBootstrapResponseInterface.ts
│   ├── AuthUserInterface.ts
│   ├── ForgotPasswordRequestInterface.ts
│   ├── LoginRequestInterface.ts
│   └── RegisterInputInterface.ts
├── contact/
│   ├── CreateEnrollmentFromSurveyInputInterface.ts
│   ├── CreateEnrollmentFromSurveyRequestInterface.ts
│   ├── ContactRequestInterface.ts
│   ├── ContactInterface.ts
│   └── ContactListFiltersInterface.ts
├── survey/
│   ├── InputBindingMappingAvailableBindingInterface.ts
│   ├── SurveyAIGenerateInputInterface.ts
│   ├── SurveyAIGenerateResponseInterface.ts
│   ├── SurveyFormInputInterface.ts
│   └── SurveyFormInterface.ts
├── pricing/
│   ├── RateCardRequestInterface.ts
│   ├── RateCardInterface.ts
│   └── RateCardPlanOverrideInterface.ts
└── organization/
    ├── OrganizationInputInterface.ts
    ├── OrganizationInterface.ts
    ├── OrganizationInvitationInputInterface.ts
    └── OrganizationMembershipInterface.ts
```

Use explicit filenames. A reader should know whether a file contains a returned resource, a request payload, a form input schema, an options payload, or an action response before opening it.

### Returned Resource Interface

Use `ThingInterface` for persisted resources returned by the backend. These interfaces include backend-owned fields because they describe API output, not form input.

```typescript
// frontend/src/types/pricing/RateCardInterface.ts
import { CatalogEntryStatus } from "@/types/catalogEntry/CatalogEntryInterface";

import type { RateCardPlanOverrideInterface } from "./RateCardPlanOverrideInterface";

export enum RateCardStatus {
  ACTIVE = "ACTIVE",
  INACTIVE = "INACTIVE",
}

export interface RateCardLinkedCatalogEntryInterface {
  id: number;
  name: string;
  planCount: number;
  slug: string;
  status: CatalogEntryStatus;
}

export interface RateCardInterface {
  workspace: number;
  createdTs: string;
  description: string;
  id: number;
  linkedPlanCount: number;
  linkedCatalogEntryCount: number;
  linkedCatalogEntries?: RateCardLinkedCatalogEntryInterface[];
  name: string;
  planOverrides?: RateCardPlanOverrideInterface[];
  status: RateCardStatus;
  updatedTs: string;
}
```

The enum lives with the returned resource because status is a backend-returned value. Request files can import that enum when forms also submit it.

### Request Or Input Interface With Schema And Defaults

Use a separate request or input file for data the frontend submits. Existing code may use `ThingInputInterface`; new endpoint-specific contracts should prefer `ThingRequestInterface` when that name better communicates that the payload goes to the backend. Do not rename existing `InputInterface` files only for churn.

```typescript
// frontend/src/types/pricing/RateCardRequestInterface.ts
import { z } from "zod";

import { RateCardStatus } from "./RateCardInterface";

export const rateCardInputSchema = z.object({
  description: z.string(),
  name: z.string().min(1, "Rate card name is required"),
  status: z.nativeEnum(RateCardStatus),
});

export type RateCardRequestInterface = z.infer<typeof rateCardInputSchema>;

export function createDefaultRateCardInput(): RateCardRequestInterface {
  return {
    description: "",
    name: "",
    status: RateCardStatus.ACTIVE,
  };
}
```

This file is the editable contract. It omits `id`, `workspace`, timestamps, linked counts, linked catalogEntries, and plan overrides because the form cannot submit those values.

### API Method Uses Both Contracts

The API method should declare the response contract and the request contract explicitly. The canonical client unwraps `data`, converts the outgoing body to snake_case, and converts the response back to camelCase.

```typescript
// frontend/src/utils/api.ts
const rateCards = {
  create: (organizationId: number, workspaceId: number, payload: RateCardRequestInterface) =>
    apiClient.post<RateCardInterface, RateCardRequestInterface>(
      `api/organizations/${organizationId}/workspaces/${workspaceId}/rate-cards/create/`,
      payload
    ),
  update: (organizationId: number, workspaceId: number, rateCardId: number, payload: Partial<RateCardRequestInterface>) =>
    apiClient.put<RateCardInterface, Partial<RateCardRequestInterface>>(
      `api/organizations/${organizationId}/workspaces/${workspaceId}/rate-cards/${rateCardId}/`,
      payload
    ),
};
```

Route code calls this with camelCase payload keys. Do not manually send `linked_plan_count`, `created_ts`, or other backend field names from stores or components.

### Form State Uses The Request Contract

Forms should validate and submit the request/input shape. They should not use a returned resource interface as editable state.

```typescript
// frontend/src/views/rateCards/rateCardsStore.ts
const {
  clearErrors,
  errors: drawerFieldErrors,
  reset,
  setErrors,
  validate,
  values: drawerFormValues,
} = useSchemaValidation(rateCardInputSchema, createDefaultRateCardInput());

async function submitDrawer() {
  if (!(await validate())) {
    return false;
  }

  const activeOrganizationId = organizationId.value;
  const activeWorkspaceId = selectedWorkspaceId.value;
  if (!activeOrganizationId || !activeWorkspaceId) {
    drawerErrorMessage.value = "Select an organization and workspace before saving this rate card.";
    return false;
  }

  isDrawerSubmitting.value = true;
  drawerErrorMessage.value = "";
  clearErrors();

  try {
    await api.rateCards.create(activeOrganizationId, activeWorkspaceId, drawerFormValues);
    notification.success("Rate card created", "The rate card is ready to use.");
    drawerOpen.value = false;
    await load();
    return true;
  } catch (error) {
    setErrors(extractFirstFieldErrors(error));
    drawerErrorMessage.value = getFirstApiErrorMessage(error, "Unable to create this rate card.");
    return false;
  } finally {
    isDrawerSubmitting.value = false;
  }
}
```

The form DTO and field errors line up because both are keyed by `RateCardRequestInterface`. The API returns `RateCardInterface`, but this create flow only needs to reload the list after success.

### Different Form Shape And Backend Request Shape

Some workflows need a UI-specific input shape plus a narrower backend request shape. Keep both contracts explicit when the form gathers extra control state that the API should not receive.

```typescript
// frontend/src/types/contact/CreateEnrollmentFromSurveyInputInterface.ts
import { z } from "zod";

export const createEnrollmentFromSurveyInputSchema = z
  .object({
    contact: z.number().nullable(),
    dateOfBirth: z.string(),
    email: z.string(),
    firstName: z.string(),
    lastName: z.string(),
    mode: z.enum(["existing", "new"]),
    phone: z.string(),
    status: z.string().optional(),
  })
  .superRefine((values, context) => {
    if (values.mode === "existing") {
      if (!values.contact) {
        context.addIssue({ code: z.ZodIssueCode.custom, message: "Contact is required", path: ["contact"] });
      }
      return;
    }

    if (!values.email.trim()) {
      context.addIssue({ code: z.ZodIssueCode.custom, message: "Email is required", path: ["email"] });
    }
  });

export type CreateEnrollmentFromSurveyInputInterface = z.infer<typeof createEnrollmentFromSurveyInputSchema>;
```

```typescript
// frontend/src/types/contact/CreateEnrollmentFromSurveyRequestInterface.ts
export interface CreateEnrollmentFromSurveyRequestInterface {
  contact?: number;
  dateOfBirth?: string;
  email?: string;
  firstName?: string;
  surveySubmission: number;
  lastName?: string;
  phone?: string;
  status?: string;
}
```

The form's `mode` field is a UI decision. The backend request should receive either `contact` for an existing contact or new-contact fields for a new contact, plus the route-owned `surveySubmission`.

```typescript
const payload: CreateEnrollmentFromSurveyRequestInterface = {
  surveySubmission: props.submissionId,
  status: formValues.status || undefined,
};

if (formValues.mode === "existing") {
  payload.contact = formValues.contact as number;
} else {
  payload.email = formValues.email.trim();
  payload.firstName = formValues.firstName.trim() || undefined;
  payload.lastName = formValues.lastName.trim() || undefined;
  payload.phone = formValues.phone.trim() || undefined;
  payload.dateOfBirth = formValues.dateOfBirth || undefined;
}

await api.enrollments.createFromSurvey(props.organizationId, props.workspaceId, payload);
```

Use this split when the UI shape and backend shape are genuinely different. Do not create both files when one request contract already describes the form and API payload cleanly.

### Action Response Interface

Use an action-specific response interface when an endpoint returns a result object that is not a persisted resource.

```typescript
// frontend/src/types/survey/SurveyAIGenerateResponseInterface.ts
export interface SurveyAIGenerateResponseInterface {
  applied: {
    bindingsCreated: number;
    bindingsUpdated: number;
    nodesCreated: number;
    nodesUpdated: number;
    notes: string[];
    pagesCreated: number;
    pagesUpdated: number;
    themeOverrideGroupsApplied: number;
  };
  message: string;
  model: string;
}
```

```typescript
const surveyFormVersions = {
  aiGenerate: (
    organizationId: number,
    workspaceId: number,
    catalogEntryId: number,
    surveyFormId: number,
    versionId: number,
    payload: SurveyAIGenerateInputInterface
  ) =>
    apiClient.post<SurveyAIGenerateResponseInterface, SurveyAIGenerateInputInterface>(
      `api/organizations/${organizationId}/workspaces/${workspaceId}/catalog-entries/${catalogEntryId}/survey-forms/${surveyFormId}/versions/${versionId}/ai-generate/`,
      payload,
      { timeout: 300_000 }
    ),
};
```

`ResponseInterface` is useful here because the noun is an action result, not a durable model the rest of the app edits.

### Options And Available Data Interfaces

Use descriptive names for option bundles or available-values payloads. Do not force them into a generic entity name when they are read-only helper data for a workflow.

```typescript
// frontend/src/types/survey/InputBindingMappingAvailableBindingInterface.ts
import type { SurveyBuilderFieldOptionInterface } from "@/types/survey/SurveyBuilderFieldOptionInterface";

export interface InputBindingMappingAvailableBindingInterface {
  bindingKey: string;
  fieldType: string;
  id: number;
  label: string;
  options: SurveyBuilderFieldOptionInterface[];
}
```

If an endpoint returns a larger options bundle, use a name such as `OrganizationAvailableOptionsInterface` or `RateCardAvailableOptionsInterface` and keep it in the same domain folder as the workflow that consumes it.

```typescript
export interface RateCardAvailableOptionsInterface {
  workspaces: Array<{ label: string; value: number }>;
  statuses: Array<{ label: string; value: RateCardStatus }>;
}
```

Prefer one options interface for the backend-returned bundle. Do not define parallel option shapes in every component unless those options are purely local presentation data.

### Casing Stays CamelCase In Types

Frontend interfaces describe camelCase data after API conversion. The backend may expose `created_ts`, `linked_plan_count`, and `support_email`, but frontend code uses `createdTs`, `linkedPlanCount`, and `supportEmail`.

```typescript
// frontend/src/types/organization/OrganizationInterface.ts
export interface OrganizationInterface {
  brandName: string;
  createdTs: string;
  id: number;
  membershipRole: OrganizationMembershipRole | null;
  name: string;
  slug: string;
  status: OrganizationStatus;
  supportEmail: string;
  updatedTs: string;
}
```

```typescript
// frontend/src/types/organization/OrganizationInputInterface.ts
export const organizationInputSchema = z.object({
  brandName: z.string().min(1, "Brand name is required"),
  name: z.string().min(1, "Organization name is required"),
  status: z.nativeEnum(OrganizationStatus),
  supportEmail: z.string().email("Support email must be valid"),
});
```

The request schema also stays camelCase because `ApiClient.post(...)` and `ApiClient.put(...)` call `camelToSnake(...)` before sending JSON.

### Query Params And Filter Interfaces

Simple query params can be typed inline at the API method boundary. Extract a named filter interface only when the query shape is reused, important enough to document, or complex enough that inline typing would make the API module harder to scan.

```typescript
// Prefer inline for one-off simple filters.
const examples = {
  list: (organizationId: number, filters?: { workspaceId?: number; search?: string; status?: string }) =>
    apiClient.get<ExampleInterface[]>(
      `api/organizations/${organizationId}/examples/list/`,
      buildParamsConfig(filters)
    ),
};
```

```typescript
// Use a named interface when the shape is reused or meaningful across route state and API calls.
export interface CatalogEntryOrganizationListFiltersInterface {
  workspaceId?: number;
  search?: string;
  status?: string;
}

const catalogEntries = {
  listByOrganization: (organizationId: number, filters?: CatalogEntryOrganizationListFiltersInterface) =>
    apiClient.get<CatalogEntryInterface[]>(
      `api/organizations/${organizationId}/catalog-entries/list/`,
      buildParamsConfig(filters)
    ),
};
```

Callers still pass camelCase keys such as `workspaceId`. `buildParamsConfig(...)` converts params to snake_case at the API boundary.

### Shared API Error Shape

Keep shared transport-level shapes in `frontend/src/types/api/` so form and error helpers use one error contract.

```typescript
// frontend/src/types/api/ErrorResponseInterface.ts
export interface ErrorItemInterface {
  attr?: string;
  code?: string;
  detail: string;
}

export interface ErrorResponseInterface {
  errors?: ErrorItemInterface[];
}
```

Feature forms should use the shared error helpers rather than redefining DRF error payloads in local type files.

## Things To Notice

- `src/types/<domain>/` owns shared frontend contracts; route folders own route-local view models and local component props.
- Returned resource interfaces include backend-owned output fields. Request and input interfaces include only writable or submitted fields.
- Zod schemas and `createDefault...()` helpers live with the request/input contract they validate.
- Enums live with the returned resource when they describe backend-returned values, and request/input files import those enums when forms submit them.
- Frontend types use camelCase even when the backend serializer uses snake_case.
- `api.ts` is the boundary that combines response and request types in `apiClient.get/post/put/delete` calls.
- `InputInterface` is tolerated and common in the current codebase; prefer `RequestInterface` for new endpoint-specific backend payloads when that name is clearer.
- Available-options and action-response interfaces should be named by the thing the endpoint returns, not by a generic catch-all response suffix.
- Simple filter interfaces are not worth extracting by default. Extract them only when they are reused or materially improve readability.
- Shared error shapes belong under `src/types/api/`, not inside every route folder.

## Rules To Follow

- Put shared domain contracts under `frontend/src/types/<domain>/`.
- Use explicit filenames such as `ThingInterface.ts`, `ThingInputInterface.ts`, `ThingRequestInterface.ts`, `ThingAvailableOptionsInterface.ts`, `ActionResponseInterface.ts`, and `ThingEnums.ts`.
- Keep returned resources separate from submitted payloads whenever their fields differ.
- Do not use `ThingInterface` as form state if the form cannot submit every required field on that returned resource.
- Do not add placeholder values such as `id: 0`, `createdTs: ""`, or empty nested arrays to a form DTO just to satisfy a returned resource interface.
- Keep frontend type fields camelCase. Do not add snake_case keys to frontend interfaces, form DTOs, stores, or component props.
- Do not manually call `camelToSnake(...)` or `snakeToCamel(...)` in components or stores.
- Type every API response and request body. Do not use `any` or `unknown` at the API boundary.
- Do not return `AxiosResponse` from domain API methods. Return the unwrapped typed payload.
- Prefer Zod-inferred request/input types when a form validates the same shape it submits.
- Keep schemas and default helpers close to the request/input type instead of duplicating defaults in each dialog.
- Use `Partial<ThingInputInterface>` or `Partial<ThingRequestInterface>` for ordinary partial update endpoints; create a separate update request interface only when the update payload has a different real contract.
- Use a UI input interface plus a backend request interface when the form owns UI-only control state, such as a mode toggle.
- Do not create a named filter interface for a one-off two-field query unless it is reused by route state or multiple API methods.
- Keep view-only table rows and presentation-only component prop types in the route folder unless they are reused across domains.

## Refactor Signals

- A form initializes `id`, `createdTs`, `updatedTs`, counts, nested output arrays, or read-only labels.
- A component or store imports a returned `ThingInterface` only to submit create or update payloads.
- API methods use `any`, `unknown`, untyped objects, or `AxiosResponse` as their public contract.
- A route view constructs snake_case payload or query-param keys.
- Several components duplicate the same default form object instead of using a `createDefault...()` helper.
- A Zod schema lives in a component while the request/input type lives elsewhere.
- A generic `types.ts`, `models.ts`, or `interfaces.ts` file mixes unrelated domains or several API boundaries.
- A domain folder contains both `ThingInputInterface` and `ThingRequestInterface` for the same identical payload.
- A new `FilterInterface` file only wraps one or two one-off query params used by a single method.
- A route-local table row type is promoted to `src/types/<domain>/` even though no other route uses it.
- Field errors are typed against a returned resource interface instead of the request/input interface that the form actually edits.

## Verification

Use targeted checks that prove the type boundary is consistent with the API client and the generated guidance.

```bash
# The authored guidance must build into all generated agent outputs.
python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean
```

```bash
# Type files should stay grouped under domain folders.
rg --files frontend/src/types | sort
```

```bash
# API methods should use typed response and payload contracts.
rg -n "apiClient\\.(get|post|put|delete)<" frontend/src/utils/api.ts
```

```bash
# Components and stores should not send snake_case keys to the API client.
rg -n "[a-z]+_[a-z]+" frontend/src/views frontend/src/types frontend/src/utils/api.ts
```

```bash
# Simple filters should not multiply without a reason.
rg -n "FilterInterface|FiltersInterface" frontend/src/types frontend/src/utils/api.ts frontend/src/views
```

When code changes accompany this guidance, also run the frontend verification that matches the touched area:

```bash
cd frontend
npm run type-check
npm run lint
```

For guidance-only edits, run the Markdown fence check, `git diff --check` on the authored file, and the generated-agent build.

## Why It Helps

This pattern makes frontend data ownership visible. Returned resources, submitted payloads, options bundles, action responses, and shared error contracts each have a clear name and home. Forms stop pretending to edit backend-owned fields, API methods become easier to audit, and the camelCase frontend contract stays clean even while Django continues serving snake_case serializers.

It also makes refactors safer. A reviewer can follow one domain from `src/types/<domain>/` to `src/utils/api.ts` to a route-local store or form and confirm that each boundary has the right shape. That gives future agents a concrete north star for both new work and cleanup passes.
