---
id: framework-django-example-task-dispatch
title: Django Task Dispatch Example
description: Example model-backed task dispatch map with lifecycle handling and thin Celery wrappers.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - tasks
applies_to:
  - django
status: active
order: 11
---

# Django Task Dispatch Example

## Scenario

- Use this pattern when one task model owns multiple named background operations and should standardize lifecycle handling.

## Recommended Shape

### Good Example

```python
class Task(ProjectBaseModel):
    @staticmethod
    def create_task(name: str, data: Optional[dict] = None) -> 'Task':
        task = Task.objects.create(name=name, data=data or {}, percent_complete=0)
        if not settings.DEBUG:
            run_task.delay(task.id)
        return task

    @staticmethod
    def create_singleton_task(name: str, data: Optional[dict] = None) -> tuple['Task', bool]:
        existing = Task.objects.filter(
            name=name,
            status__in=[Task.StatusChoices.PENDING, Task.StatusChoices.RUNNING],
        ).first()
        if existing:
            return existing, False
        return Task.create_task(name, data=data), True

    def set_message_and_percent(self, message: str, percent_complete: int):
        self.percent_complete = percent_complete
        self.progress_message = message
        self.save()
        self.log_history(settings.SYSTEM_USER_ID, message, ActionFlags.TASK_LOG)

    def run(self):
        task_map = {
            'purge_old_tasks': self.purge_old_tasks,
            'aggregate_daily_company_stats': self.aggregate_daily_company_stats,
            'refresh_available_options_cache': self.refresh_available_options_cache,
        }

        self.status = Task.StatusChoices.RUNNING
        self.started_ts = timezone.now()
        self.percent_complete = 0
        self.save()

        if self.name not in task_map:
            raise UnmappedTaskError(self.name)

        task_map[self.name]()

        self.status = Task.StatusChoices.COMPLETED
        self.completed_ts = timezone.now()
        self.percent_complete = 100
        self.progress_message = 'Task completed'
        self.save()


@app.task
def refresh_available_options_cache():
    from task.models import Task

    Task.create_task('refresh_available_options_cache')
```

### Things To Notice

- Named task methods are registered in one map instead of scattered through conditionals.
- `create_task(...)` and `create_singleton_task(...)` decide how jobs enter the system before `run()` dispatches them.
- Singleton gating is explicit and based on task name plus running states.
- Scheduled and user-triggered singleton jobs should use different task names when auth context differs.
- Progress reporting is part of the model contract, not scattered through callers.
- The Celery layer stays thin: it enqueues by task name, while the model owns lifecycle and execution.

## Why It Helps

- The task model becomes the single execution entrypoint for model-backed background jobs.
