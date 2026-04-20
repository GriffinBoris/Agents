---
id: framework-django-example-transition-endpoint
title: Transition Endpoint
description: Use dedicated transition endpoints for lifecycle changes instead of generic partial updates.
kind: example
scope: framework
name: django
tags:
  - django
  - views
  - antipatterns
applies_to:
  - django
status: active
order: 22
---

# Transition Endpoint

## Avoid

```python
def put(self, request, pk: int):
    instance = self.get_object(pk)
    serializer = OrderSerializer(instance, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    instance = serializer.save()
    return Response(OrderSerializer(instance).data)
```

## Prefer

```python
def post(self, request, pk: int):
    instance = self.get_object(pk)
    serializer = OrderTransitionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    instance = transition_order(
        order=instance,
        next_status=serializer.validated_data['status'],
        notes=serializer.validated_data.get('notes', ''),
    )
    return Response(OrderSerializer(instance).data)
```

## Why

- Lifecycle changes are business rules, not ordinary field edits.
- A dedicated transition path makes allowed moves explicit.
- Validation, auditability, and automation stay easier to reason about.
