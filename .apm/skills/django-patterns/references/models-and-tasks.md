# Django Models, Migrations, And Tasks

## Contents

- Migrations
- Models and lifecycle side effects
- Background tasks with Celery

## Migrations

- Prefer model-driven schema changes over custom SQL or data migrations whenever Django can represent the change directly.
- When a migration both creates custom permissions and grants them to groups, create or fetch the permission rows inside the migration before assigning groups.
- For model-backed task frameworks where a field such as `name` is intentionally tied to the live task registry, it is acceptable to import the task model and use its `TextChoices` directly in the migration instead of creating a new migration every time a new task name is added. Use this pattern only when the migration is deliberately acting as a registry contract, not for ordinary domain enums that should remain historical schema snapshots.

## Models

- Extend the repository's shared base model when one exists.
- Prefer `models.TextField` for new string fields unless a real length constraint is required.
- Keep model declarations in this order:
  - class definition
  - `Meta`
  - supporting inner classes such as `TextChoices`
  - field declarations
  - optional dunder methods
  - optional `save()` and `delete()`
  - remaining helpers
- For field declarations, prefer this argument order:
  - target model for relations
  - field-specific arguments
  - `default`
  - `null`
  - `blank`
  - `verbose_name`
  - `on_delete` for relations
- Only set `default` when the field has a real domain-level default value.
- Do not use empty-string or other placeholder defaults as a shortcut for optional data, form convenience, or avoiding validation.
- For relation fields, pass the target model as `'app.Model'` and set `on_delete` explicitly.
- Keep field declarations on one line.
- Wrap human-readable `TextChoices` labels in `gettext(...)`.
- Prefer `@staticmethod` for model helpers that do not need class state. Use `@classmethod` only when the helper genuinely depends on `cls`, such as shared permission-name helpers.
- Keep intrinsic lifecycle and invariant rules on the model.
- Prefer direct attribute access over `getattr` when a field is guaranteed by the model or serializer contract.
- Choose an explicit `on_delete` strategy for every relation and follow the repository's established convention unless you are deliberately migrating away from it.
- Be aware of the trade-offs between `DO_NOTHING`, `CASCADE`, `SET_NULL`, and `PROTECT`, and match the actual domain relationship.

### Model Lifecycle Side Effects

- Do not hide third-party I/O in model `save()` or `delete()` methods.
- Keep lifecycle methods limited to database concerns such as defaults, validation, and audit logging.
- Put network I/O in explicit service functions or Celery tasks that views or commands call directly.
- If existing code already has I/O in `save()` or `delete()`, do not add more. When you touch that code, consider extracting the I/O into a service layer.

## Background Tasks (Celery)

- Use Celery for background work that does not need to complete synchronously.
- Never run cleanup, purge, or third-party I/O operations in model lifecycle methods or directly in views.
- Follow the repository's task registration pattern consistently so task discovery, scheduling, and retries stay predictable.
- If the task framework supports progress reporting, update task status through the shared progress hooks instead of inventing parallel state tracking.
- When scheduling recurring tasks, use explicit cron syntax such as `crontab(minute='*/30')`.
