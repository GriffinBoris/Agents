---
id: framework-django-example-celery-enqueue
title: Django Celery Enqueue Example
description: Example thin Celery wrappers that schedule work and delegate execution to the task model.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - celery
applies_to:
  - django
status: active
order: 12
---

# Django Celery Enqueue Example

## Scenario

- Use this pattern when Celery should only schedule or enqueue work, not hold the business logic itself.

## Recommended Shape

### Good Example

```python
@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    if settings.DEBUG:
        return

    sender.add_periodic_task(crontab(minute='*/5'), sync_strategy_transactions.s())
    sender.add_periodic_task(crontab(minute=0, hour=2), purge_old_tasks.s())


@app.task
def sync_strategy_transactions():
    from task.models import Task

    Task.create_task('sync_strategy_transactions')


@app.task
def sync_datacanvas_jobs():
    from task.models import Task

    Task.create_singleton_task('sync_datacanvas_jobs')
```

### Things To Notice

- Periodic schedule definitions live in Celery configuration.
- Task functions are intentionally thin and immediately delegate to the model-backed task entrypoint.
- Singleton and non-singleton behavior stay explicit at the enqueue boundary.
- Keep task-model lifecycle, dispatch, and progress logic in the dedicated task-dispatch example rather than duplicating it here.

## Why It Helps

- Celery wiring stays simple and business logic remains centralized.
