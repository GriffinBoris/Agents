---
id: framework-django-example-direct-attribute-access
title: Direct Attribute Access
description: Prefer explicit branching and direct attribute access over fail-soft getattr fallbacks for required fields.
kind: example
scope: framework
name: django
tags:
  - django
  - serializers
  - antipatterns
applies_to:
  - django
status: active
order: 25
---

# Direct Attribute Access

## Avoid

```python
selected_owner = owner or getattr(self.instance, 'owner', None)
if selected_owner:
    queryset = Assignment.objects.filter(project=project, owner=selected_owner)
```

## Prefer

```python
if self.instance:
    selected_owner = self.instance.owner
else:
    selected_owner = owner

if owner is not None:
    selected_owner = owner

if selected_owner is not None:
    queryset = Assignment.objects.filter(project=project, owner=selected_owner)
```

## Why

- `getattr(..., None)` hides whether the field is actually part of the contract.
- Direct access expresses that the attribute should exist and fails loudly when the assumption is wrong.
- Explicit branching keeps create and update paths readable.
