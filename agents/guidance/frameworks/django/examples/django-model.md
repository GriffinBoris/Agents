---
id: framework-django-example-model
title: Django Model Example
description: Example Django model that follows repository model conventions.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - model
applies_to:
  - django
status: active
order: 1
---

# Django Model Example

## Scenario

- Use this shape when adding a new model that should follow the repository's ordering, field, and lifecycle conventions.

## Recommended Shape

### Good Example

```python
from django.db import models
from django.utils.translation import gettext

from core.common import ProjectBaseModel


class ExampleModel(ProjectBaseModel):
    class Meta:
        ordering = ('id',)

    class Status(models.TextChoices):
        PENDING = 'pending', gettext('Pending')
        APPROVED = 'approved', gettext('Approved')

    name = models.TextField(null=False, blank=False, verbose_name=gettext('name'))
    status = models.TextField(choices=Status.choices, default=Status.PENDING, null=False, blank=False, verbose_name=gettext('status'))
    owner = models.ForeignKey('core.Member', null=True, blank=True, on_delete=models.DO_NOTHING)

    @staticmethod
    def get_status_choices():
        return ExampleModel.Status.choices

    def transition_to(self, next_status):
        self.status = next_status
        self.save()
        return self
```

### Things To Notice

- `Meta` appears before supporting inner classes and fields.
- Human-readable `TextChoices` labels use `gettext(...)`.
- This repository's model style keeps explicit `null` and `blank` values on fields instead of relying on implicit Django defaults.
- Model field declarations stay on one line so the class body is easier to scan.
- Field arguments stay in a consistent order: field-specific arguments first, then `default`, `null`, `blank`, and `verbose_name`.
- Set `default` only when the field has a real domain default. Do not use empty strings or other convenience defaults just to avoid required input.
- The relation uses `'app.Model'` plus explicit `on_delete`.
- Relation fields keep the target model first and place `on_delete` last.
- Intrinsic lifecycle logic stays on the model instead of being pushed into a generic service.

## Why It Helps

- This layout keeps models predictable to scan and makes lifecycle rules easy to find.

---

## Related Rules

### Django Models

- Extend `ProjectBaseModel` from `core/common.py` for all models.
- Prefer `models.TextField` for new string fields unless a specific length constraint is required.
- Follow this model declaration order:
  1. Class definition.
  2. `class Meta`.
  3. Supporting inner classes such as `TextChoices`.
  4. Field declarations.
  5. Optional dunder methods.
  6. Optional `save()`, `delete()`, then any remaining helpers.
- Keep field declarations single-line.
- Keep field arguments in this order:
  1. For relations, pass the target model as `'app.Model'`.
  2. Field-specific arguments.
  3. `default`.
  4. `null`.
  5. `blank`.
  6. `verbose_name` wrapped in `gettext(...)`.
  7. For relations, set `on_delete` explicitly.
- Only set `default` when the model truly has a domain-level default value.
- Do not use `default=''` or other placeholder defaults as a shortcut for optional fields, form convenience, or avoiding validation.
- Enable history logging when needed by defining `history_log_fields` or `history_log_private_fields`, and pass `log_user_id` to `save()` when tracking user changes.
- Prefer `@staticmethod` over `@classmethod` for model helper methods.

### `on_delete` Policy

- This repository currently uses `on_delete=models.DO_NOTHING` as the established convention for existing relationships.
- `DO_NOTHING` risks orphaned records and referential integrity issues, so understand that trade-off before copying it blindly into a new context.
- In greenfield work, consider `CASCADE`, `SET_NULL`, or `PROTECT` based on the actual domain relationship.
- Any change away from `DO_NOTHING` in existing models requires deliberate migration planning.

### Model Lifecycle Side Effects

- Do not hide I/O in model `save()` or `delete()`.
- Keep lifecycle methods limited to database-level concerns such as field defaults, validation, and audit logging.
- Put third-party I/O in explicit service functions or Celery tasks that views or commands call directly.
- If current code already has I/O in `save()` or `delete()`, do not add more; when touching that code, consider extracting the I/O into a service layer.
