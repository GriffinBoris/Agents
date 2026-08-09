---
id: framework-django-example-task-dispatch
title: Django Task Dispatch Example
description: Example model-backed task dispatch with named tasks, lifecycle state, progress reporting, failure handling, and focused tests.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - tasks
  - celery
  - lifecycle
applies_to:
  - django
status: active
order: 11
---

# Django Task Dispatch Example

## Scenario

- Use this pattern when background work should be represented by a database row with visible lifecycle state.
- Use this pattern when a task must expose progress, failure messages, or history to operators.
- Use this pattern when several named background operations share the same enqueue, run, progress, and failure contract.
- Use this pattern when the Celery function should be only a transport entrypoint and the model should own execution.
- Use a plain service or Celery task without a model only when the work has no user-visible lifecycle, retry surface, progress, or audit requirement.

## Why This Shape Exists

- Background work needs an operator-facing source of truth. The task row records what was requested, whether it is pending, running, completed, or failed, and what progress message should be shown.
- Celery workers are transport infrastructure, not the domain contract. Keeping execution on the model makes scheduled tasks, user-triggered tasks, tests, and retry screens use the same entrypoint.
- A named task registry makes task discovery reviewable. Adding a task means adding a `TaskNameChoices` value, a dispatch-map entry, implementation, enqueue wrapper, schedule when needed, and tests.
- Singleton behavior needs to be explicit. Some jobs should collapse duplicate pending/running rows, while event-specific jobs should create one row per unit of work.
- Failures should stay visible. Unknown task names and runtime exceptions mark the task failed, write a progress message, log the exception, and optionally record task history.

## Recommended Shape

### Model Fields And Named Registry

```python
import logging
from datetime import date, timedelta
from typing import Optional

from core.base_models import BaseModel
from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext
from survey.models.SurveyEvent import SurveyEvent
from survey.services.analytics_rollups import roll_up_survey_analytics
from survey.services.event_forwarding import forward_event
from task.celery import run_task

logger = logging.getLogger(__name__)


class UnmappedTaskError(Exception):
	pass


class Task(BaseModel):
	class Meta:
		ordering = ('id',)

	class TaskNameChoices(models.TextChoices):
		PURGE_OLD_TASKS = 'purge_old_tasks', gettext('Purge old tasks')
		ROLL_UP_SURVEY_ANALYTICS = 'roll_up_survey_analytics', gettext('Roll up survey analytics')
		FORWARD_SURVEY_EVENT = 'forward_survey_event', gettext('Forward survey event')

	class StatusChoices(models.TextChoices):
		PENDING = 'PENDING', gettext('Pending')
		RUNNING = 'RUNNING', gettext('Running')
		COMPLETED = 'COMPLETED', gettext('Completed')
		FAILED = 'FAILED', gettext('Failed')

	name = models.TextField(choices=TaskNameChoices.choices, null=False, blank=False, verbose_name=gettext('Name'))
	data = models.JSONField(default=dict, null=True, blank=True, verbose_name=gettext('Data'))
	status = models.TextField(choices=StatusChoices.choices, default=StatusChoices.PENDING, null=False, blank=False, verbose_name=gettext('Status'))
	started_ts = models.DateTimeField(null=True, blank=True, verbose_name=gettext('Started Timestamp'))
	completed_ts = models.DateTimeField(null=True, blank=True, verbose_name=gettext('Completed Timestamp'))
	percent_complete = models.IntegerField(null=True, blank=True, verbose_name=gettext('Percent Complete'))
	progress_message = models.TextField(null=False, blank=True, verbose_name=gettext('Progress Message'))
```

The model is the durable task contract. It stores task identity, input data, lifecycle status, timestamps, progress percent, and a displayable message.

### Creation And Singleton Entry Points

```python
class Task(BaseModel):
	# fields omitted

	@staticmethod
	def create_task(name: str, data: Optional[dict] = None) -> 'Task':
		task = Task.objects.create(name=name, data=data or {}, percent_complete=0)
		if settings.CELERY_TASKS_ENABLED and not settings.DEBUG:
			run_task.delay(task.id)
		else:
			logger.debug('Task %s created; Celery dispatch skipped in DEBUG mode', task.id)

		return task

	@staticmethod
	def create_singleton_task(name: str, data: Optional[dict] = None) -> tuple['Task', bool]:
		existing_task = Task.objects.filter(
			name=name,
			status__in=[Task.StatusChoices.PENDING, Task.StatusChoices.RUNNING],
		).first()
		if existing_task:
			return existing_task, False

		return Task.create_task(name, data=data), True
```

Use `create_task(...)` for one row per work item, such as forwarding one survey event. Use `create_singleton_task(...)` for jobs where a pending or running row already represents the current request, such as nightly analytics rollups.

### Progress Reporting

```python
class Task(BaseModel):
	# fields omitted

	def set_message_and_percent(self, message: str, percent_complete: int):
		self.percent_complete = percent_complete
		self.progress_message = message
		self.save()
		if settings.SYSTEM_USER_ID:
			self.log_history(settings.SYSTEM_USER_ID, message)

	def set_message_and_complex_percent(
		self,
		message: str,
		current_step: int,
		total_steps: int,
		current_step_percent: int,
		step_percent_total: int,
	):
		percent_complete = int((((current_step - 1) + (current_step_percent / step_percent_total)) / total_steps) * 100)
		self.set_message_and_percent(message, percent_complete)
```

Progress updates belong on the task model so every task implementation reports status the same way. Do not invent separate progress tables, ad hoc response records, or task-specific state fields unless the item needs a distinct domain record.

### Dispatch And Failure Handling

```python
class Task(BaseModel):
	# fields omitted

	def run(self):
		task_map = {
			Task.TaskNameChoices.PURGE_OLD_TASKS: self.purge_old_tasks,
			Task.TaskNameChoices.ROLL_UP_SURVEY_ANALYTICS: self.roll_up_survey_analytics,
			Task.TaskNameChoices.FORWARD_SURVEY_EVENT: self.forward_survey_event,
		}

		try:
			self.status = Task.StatusChoices.RUNNING
			self.started_ts = timezone.now()
			self.percent_complete = 0
			self.save()

			if self.name not in task_map:
				message = f'Task {self.name} not found'
				raise UnmappedTaskError(message)

			task_map[self.name]()

			self.status = Task.StatusChoices.COMPLETED
			self.completed_ts = timezone.now()
			self.percent_complete = 100
			self.progress_message = 'Task completed'
			self.save()

		except Exception as exc:
			failure_message = f'Task failed: {exc}'
			logger.exception('Task %s failed while running %s', self.id, self.name)
			self.status = Task.StatusChoices.FAILED
			self.progress_message = failure_message
			self.save()
			if settings.SYSTEM_USER_ID:
				self.log_history(settings.SYSTEM_USER_ID, failure_message)
```

The dispatch map is the registry. It keeps task names, implementation methods, lifecycle state, and failure handling in one place. Do not scatter task-name conditionals across Celery wrappers, views, management commands, or services.

### Task Implementations

```python
class Task(BaseModel):
	# fields omitted

	def purge_old_tasks(self):
		days_ago = timezone.now() - timedelta(days=7)
		old_task_ids = list(Task.objects.filter(created_ts__lt=days_ago).values_list('id', flat=True))
		content_type = ContentType.objects.get_for_model(Task)
		LogEntry.objects.filter(content_type_id=content_type.id, object_id__in=[str(task_id) for task_id in old_task_ids]).delete()
		deleted_count, _ = Task.objects.filter(id__in=old_task_ids).delete()
		self.set_message_and_percent(f'Purged {deleted_count} old task records.', 100)

	def roll_up_survey_analytics(self):
		raw_stats_date = self.data.get('stats_date')
		stats_date = date.fromisoformat(raw_stats_date) if raw_stats_date else None
		self.set_message_and_percent('Rolling up survey analytics.', 25)
		roll_up_survey_analytics(stats_date=stats_date)
		self.set_message_and_percent('Survey analytics rollup completed.', 100)

	def forward_survey_event(self):
		event_id = self.data.get('event_id')
		if not event_id:
			raise ValueError('Missing event_id for survey event forwarding task.')

		self.set_message_and_percent('Forwarding survey event.', 25)
		event = SurveyEvent.objects.select_related('workspace').get(id=event_id)
		forward_event(event)
		self.set_message_and_percent('Survey event forwarding completed.', 100)
```

Task methods may call focused service functions for domain work. Keep the task method responsible for task input, progress updates, and task-facing failure messages; keep larger external integrations or domain algorithms in service modules.

### Thin Celery Bridge

```python
@app.task
def run_task(task_id):
	from task.models import Task

	task = Task.objects.get(id=task_id)
	task.run()
```

The worker entrypoint loads the task row and calls `run()`. It should not repeat the dispatch map, status transitions, progress handling, or business logic.

### Tests For The Task Contract

```python
@pytest.mark.django_db
class TestTaskModel:
	def setup_method(self):
		self.user = FixtureFactory.create_user(email='task-model@example.com')
		self.task_name = Task.TaskNameChoices
		self.status = Task.StatusChoices

	def _create_task(self, name=None, data=None, status=None, percent_complete=0):
		return Task.objects.create(
			name=name or self.task_name.PURGE_OLD_TASKS,
			data=data or {},
			status=status or self.status.PENDING,
			percent_complete=percent_complete,
		)

	def test_create_singleton_task_reuses_existing_pending_or_running_task(self, monkeypatch, settings):
		queued_task_ids = []
		settings.DEBUG = False
		settings.CELERY_TASKS_ENABLED = True
		existing_task = self._create_task(data={'source': 'existing'}, status=self.status.RUNNING)
		monkeypatch.setattr(run_task, 'delay', lambda task_id: queued_task_ids.append(task_id))

		task, created = Task.create_singleton_task(self.task_name.PURGE_OLD_TASKS, data={'source': 'new'})

		assert created is False
		assert task.id == existing_task.id
		assert task.data == {'source': 'existing'}
		assert queued_task_ids == []

	def test_run_marks_task_failed_for_unknown_task(self, monkeypatch, settings):
		settings.SYSTEM_USER_ID = self.user.id
		history_messages = []
		logged_errors = []
		monkeypatch.setattr(Task, 'log_history', lambda self, user_id, message: history_messages.append((user_id, message)))
		monkeypatch.setattr('task.models.logger.exception', lambda message, *args: logged_errors.append((message, args)))
		task = self._create_task(name='missing_task')

		task.run()
		task.refresh_from_db()

		assert task.status == self.status.FAILED
		assert task.progress_message == 'Task failed: Task missing_task not found'
		assert history_messages == [(self.user.id, 'Task failed: Task missing_task not found')]
		assert logged_errors == [('Task %s failed while running %s', (task.id, 'missing_task'))]
```

Task tests should prove enqueue behavior, singleton reuse, progress updates, dispatch success, dispatch failure, task-specific required data, and Celery wrapper delegation.

## Things To Notice

- Task names are `TextChoices`; callers use `Task.TaskNameChoices.*` instead of bare strings.
- `create_task(...)` creates the row first, then queues `run_task.delay(task.id)` only when Celery tasks are enabled and the app is not running in debug mode.
- `create_singleton_task(...)` gates only pending and running tasks. Completed and failed tasks do not block new work.
- `run()` owns lifecycle transitions from pending to running to completed or failed.
- Failure handling logs the exception, marks the row failed, stores a visible progress message, and records task history when `SYSTEM_USER_ID` exists.
- Task implementation methods call service functions for domain-heavy work but keep task input and progress updates local.
- Celery wrappers stay thin and delegate into `Task.create_task(...)`, `Task.create_singleton_task(...)`, or `Task.run()`.
- Tests monkeypatch Celery dispatch and service functions so task behavior is deterministic.

## Rules To Follow

- Add a `TaskNameChoices` value for every model-backed task.
- Add each task name to the `run()` dispatch map in the same change as the implementation method.
- Use `create_task(...)` for per-object work and `create_singleton_task(...)` for jobs that should not run concurrently under the same task name.
- Store task-specific inputs in `data` and validate required keys inside the task implementation.
- Use `set_message_and_percent(...)` or `set_message_and_complex_percent(...)` for user-visible progress.
- Catch failures at the task lifecycle boundary so the task row is marked `FAILED`.
- Do not put long-running business logic, external API details, or retry loops in Celery wrappers.
- Do not dispatch by matching on display labels or non-unique names.
- Test the model-backed task behavior and the Celery wrapper delegation.

## Refactor Signals

- A Celery task contains the dispatch map, progress updates, or business workflow instead of calling the task model.
- A background operation has no row recording pending/running/completed/failed state even though operators need to see or retry it.
- Several views or commands enqueue the same task name with slightly different data contracts.
- Singleton behavior is implemented with ad hoc queries in callers instead of `create_singleton_task(...)`.
- A task implementation updates progress by setting fields directly instead of using shared progress helpers.
- Failures disappear into logs without marking a task row failed.
- Tests only assert that a Celery function was called and do not verify task lifecycle state.

## Verification

- Run the focused task model tests after changing task lifecycle, dispatch, singleton behavior, or task implementation:

```bash
pytest backend/task/tests/test_models.py::TestTaskModel
```

- Add tests for:
  - `create_task(...)` enqueue behavior when Celery is enabled and not in debug mode
  - debug-mode enqueue suppression
  - singleton reuse for pending/running rows
  - completed/failed rows allowing new singleton work
  - progress helper updates and history logging
  - successful `run()` completion
  - unknown task failure
  - required `data` validation for each task-specific implementation
  - Celery wrapper delegation

- Run `ruff check` on modified Python files. For guidance-only Markdown edits, inspect headings and code fences, and run the guidance builder.

## Why It Helps

- Operators get one reliable place to inspect background work.
- Task lifecycle and failure behavior are consistent across scheduled and user-triggered work.
- Celery remains replaceable infrastructure rather than the owner of business behavior.
- Tests can verify task behavior synchronously without needing a worker.
- Future tasks are easier to review because the required registry, lifecycle, progress, Celery, and test changes are explicit.
