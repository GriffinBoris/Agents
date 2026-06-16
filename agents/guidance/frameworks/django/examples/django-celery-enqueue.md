---
id: framework-django-example-celery-enqueue
title: Django Celery Enqueue Example
description: Example Celery configuration and task wrappers that schedule work, delegate to model-backed tasks, and keep business logic out of worker functions.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - celery
  - tasks
applies_to:
  - django
status: active
order: 12
---

# Django Celery Enqueue Example

## Scenario

- Use this pattern when adding a Celery wrapper for a model-backed task.
- Use this pattern when scheduling recurring work with `crontab(...)`.
- Use this pattern when the task app already owns task lifecycle through a `Task` model.
- Use this pattern when a Celery function should queue or run a task row and nothing more.

## Why This Shape Exists

- Celery functions are worker entrypoints. If they also own business logic, lifecycle state, progress, and retry behavior, the same operation becomes hard to trigger from views, commands, tests, or operator screens.
- The database task row is the durable contract. Celery should enqueue that row or run that row; the model should decide how lifecycle and failure state are recorded.
- Schedules should be visible and explicit. `crontab(minute=30, hour=2)` communicates operational timing better than hidden runtime conditionals.
- Local development should not accidentally start recurring production-style work. Schedule registration returns early in `DEBUG`.

## Recommended Shape

### Celery App Configuration

```python
import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev_local')

app = Celery('example_app')
app.config_from_object('django.conf:settings', namespace='CELERY')
```

The Celery module configures the worker and imports only worker-level dependencies at module load. Django models are imported inside task functions to avoid app-loading surprises.

### Periodic Schedule Registration

```python
@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
	from django.conf import settings

	if settings.DEBUG:
		return

	sender.add_periodic_task(crontab(minute=0, hour=2), purge_old_tasks.s())
	sender.add_periodic_task(crontab(minute=30, hour=2), roll_up_survey_analytics.s())
```

Keep schedules grouped in the Celery configuration boundary. Use explicit cron values and return early in debug mode so local development does not register recurring jobs.

### Autodiscovery Boundary

```python
app.autodiscover_tasks()
```

Call autodiscovery after schedule setup and before task function definitions. Do not hide schedule registration inside model imports or feature services.

### Enqueue Wrappers

```python
@app.task
def purge_old_tasks():
	from task.models import Task

	Task.create_task(Task.TaskNameChoices.PURGE_OLD_TASKS)


@app.task
def roll_up_survey_analytics():
	from task.models import Task

	Task.create_singleton_task(Task.TaskNameChoices.ROLL_UP_SURVEY_ANALYTICS)
```

Enqueue wrappers choose whether the operation is normal or singleton work. They do not parse task-specific payloads, mutate domain objects, call external APIs, or update progress.

### Runner Wrapper

```python
@app.task
def run_task(task_id):
	from task.models import Task

	task = Task.objects.get(id=task_id)
	task.run()
```

`run_task(...)` is the worker bridge. It loads the task row and delegates to `Task.run()`, where lifecycle transitions, dispatch, completion, and failure handling live.

### Tests For Celery Wiring

```python
@pytest.mark.django_db
class TestTaskModel:
	def setup_method(self):
		self.task_name = Task.TaskNameChoices

	def test_purge_old_tasks_celery_task_delegates_to_model_create_task(self, monkeypatch):
		created_tasks = []
		monkeypatch.setattr(Task, 'create_task', lambda name, data=None: created_tasks.append((name, data)))

		task_celery.purge_old_tasks()

		assert created_tasks == [(self.task_name.PURGE_OLD_TASKS, None)]

	def test_roll_up_survey_analytics_celery_task_delegates_to_model_singleton_task(self, monkeypatch):
		created_tasks = []
		monkeypatch.setattr(Task, 'create_singleton_task', lambda name, data=None: created_tasks.append((name, data)))

		task_celery.roll_up_survey_analytics()

		assert created_tasks == [(self.task_name.ROLL_UP_SURVEY_ANALYTICS, None)]

	def test_setup_periodic_tasks_registers_schedule_when_not_debug(self, settings):
		registered_tasks = []
		settings.DEBUG = False

		class Sender:
			@staticmethod
			def add_periodic_task(schedule, signature):
				registered_tasks.append((schedule, signature))

		task_celery.setup_periodic_tasks(Sender())

		assert len(registered_tasks) == 2
		schedule, signature = registered_tasks[0]
		assert schedule.minute == {0}
		assert schedule.hour == {2}
		assert signature.task == 'task.celery.purge_old_tasks'
```

Celery tests should prove delegation and schedule registration. They should not need a live worker.

## Things To Notice

- Celery imports Django settings inside `setup_periodic_tasks(...)`, where the value is needed.
- Schedule registration returns immediately in debug mode.
- Wrapper functions import `Task` inside the function body to avoid circular import and app-loading issues.
- Wrapper functions use `Task.TaskNameChoices.*` instead of bare task-name strings.
- Normal wrappers call `Task.create_task(...)`; singleton wrappers call `Task.create_singleton_task(...)`.
- `run_task(...)` calls `task.run()` and does not duplicate lifecycle or dispatch logic.
- Tests monkeypatch `Task.create_task(...)`, `Task.create_singleton_task(...)`, and `Task.run(...)` to verify delegation.

## Rules To Follow

- Keep Celery task functions thin. They should schedule, enqueue, or run a task row.
- Put task lifecycle, dispatch maps, progress updates, and failure handling on the model-backed task contract.
- Use explicit `crontab(...)` schedules for recurring work.
- Gate periodic schedule registration in debug mode unless the project deliberately supports local recurring jobs.
- Use `TaskNameChoices` constants in Celery wrappers.
- Choose singleton behavior at the enqueue boundary when duplicate pending/running rows should collapse.
- Do not perform third-party I/O directly inside the Celery wrapper when a model-backed task or service layer owns the workflow.
- Add tests for every wrapper and schedule.

## Refactor Signals

- A Celery function contains loops, external API calls, queryset-heavy domain logic, progress updates, or status transitions.
- The same background operation can be triggered from a view, schedule, and command but each path implements a different code path.
- A wrapper passes a display label or free-form string instead of a `TaskNameChoices` value.
- Scheduled jobs are registered through hidden imports or runtime side effects instead of the Celery configuration boundary.
- Local development starts periodic jobs because schedule setup is not gated.
- Tests require a real Celery worker to prove wrapper behavior.

## Verification

- Run the focused task app tests after changing Celery wrappers or schedules:

```bash
pytest backend/task/tests/test_models.py::TestTaskModel
```

- Add or update tests for:
  - wrapper delegation to `Task.create_task(...)`
  - wrapper delegation to `Task.create_singleton_task(...)`
  - `run_task(...)` loading the row and calling `run()`
  - schedule registration when `DEBUG = False`
  - schedule suppression when `DEBUG = True`

- Run `ruff check` on modified Python files. For guidance-only Markdown edits, inspect headings and code fences, and run the guidance builder.

## Why It Helps

- Celery stays a small, predictable transport layer.
- Background jobs remain testable without a worker.
- Operators and frontend screens read task status from one model-backed contract.
- New recurring jobs are easy to review because schedule, task name, enqueue behavior, implementation, and tests are separate and explicit.
