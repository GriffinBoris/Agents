---
id: framework-vue-example-api-client
title: Vue API Client Example
description: Example API module shape using the repository's single-client pattern.
kind: example
scope: framework
name: vue
tags:
  - example
  - vue
  - api
applies_to:
  - vue
status: active
order: 1
---

# Vue API Client Example

## Scenario

- Use this shape when adding a new frontend API segment or endpoint family that should route all traffic through the shared API client.

## Recommended Shape

### Good Example

```typescript
interface Alert {
    id: number;
    name: string;
    threshold: number;
    createdTs: string;
}

interface AlertInput {
    name: string;
    threshold: number;
}

const alertsApi = {
    list(params?: { teamId?: number; alertName?: string }): Promise<Alert[]> {
        return ApiClient.get('/api/alerts/list/', buildParamsConfig(params));
    },

    detail(alertId: number): Promise<Alert> {
        return ApiClient.get(`/api/alerts/${alertId}/`);
    },

    create(payload: AlertInput): Promise<Alert> {
        return ApiClient.post('/api/alerts/create/', payload);
    },

    update(alertId: number, payload: Partial<AlertInput>): Promise<Alert> {
        return ApiClient.put(`/api/alerts/${alertId}/`, payload);
    },
};

export const api = {
    alerts: alertsApi,
};
```

### Things To Notice

- `axios` is not imported here.
- Domain API modules are defined as top-level `const` blocks.
- Request payloads use a dedicated input type.
- Return types are unwrapped models, not `AxiosResponse` objects.
- Query params stay camelCase and go through `buildParamsConfig(...)`.
- Method names and URLs follow the shared domain API pattern.

## Why It Helps

- One API client keeps transport concerns centralized and prevents casing, CSRF, and typing drift.
