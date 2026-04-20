---
id: framework-django-example-action-view
title: Django Action View Example
description: Example non-CRUD action view with required input validation and one focused operation.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - drf
applies_to:
  - django
status: active
order: 10
---

# Django Action View Example

## Scenario

- Use this pattern when a view is not plain CRUD, but still needs a clear permission check, required input validation, and one focused operation.

## Recommended Shape

### Good Example

```python
class LoadCompareView(ProjectBaseAPIView):
    def _get_object(self, pk: int) -> Load:
        return get_object_or_404(Load, pk=pk)

    def get(self, request):
        self.check_has_permission(Load.get_view_permission())
        self.require_fields('load_one_id', 'load_two_id', allow_empty=False, source='query_params')

        load_one_id = self.request.query_params.get('load_one_id')
        load_two_id = self.request.query_params.get('load_two_id')

        load_one = self._get_object(load_one_id)
        load_two = self._get_object(load_two_id)

        data = LoadApproval.compare_loads(load_one, load_two)

        return Response(data=data, status=status.HTTP_200_OK)
```

### Things To Notice

- The view checks permission first, then validates required query params before doing any work.
- `require_fields(...)` keeps missing-input handling standardized instead of re-implementing ad hoc checks.
- The actual operation stays easy to scan: read ids, load objects, call domain logic, return response.

## Why It Helps

- This keeps transport concerns thin while leaving the core operation in the model or service layer.
