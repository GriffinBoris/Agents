---
id: framework-django-example-concrete-model-meta
title: Concrete Model Meta
description: Prefer a plain concrete Django Meta class over inheriting abstract Meta just to turn abstraction off.
kind: example
scope: framework
name: django
tags:
  - django
  - models
  - antipatterns
applies_to:
  - django
status: active
order: 20
---

# Concrete Model Meta

## Avoid

```python
class Report(ScopedModel):
    class Meta(ScopedModel.Meta):
        abstract = False
        constraints = (
            models.UniqueConstraint(fields=('scope', 'slug'), name='unique_report_slug_per_scope'),
        )
        ordering = ('id',)
```

## Prefer

```python
class Report(ScopedModel):
    class Meta:
        constraints = (
            models.UniqueConstraint(fields=('scope', 'slug'), name='unique_report_slug_per_scope'),
        )
        ordering = ('id',)
```

## Why

- Field inheritance still comes from the base model.
- A plain `Meta` makes the concrete model's options obvious.
- Subclassing abstract `Meta` just to set `abstract = False` adds noise.
