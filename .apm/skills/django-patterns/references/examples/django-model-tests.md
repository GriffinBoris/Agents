---
id: framework-django-example-model-tests
title: Django Model Tests Example
description: Example model tests for base-model behavior, lifecycle helpers, relation invariants, persisted state, and model-owned task behavior.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - testing
  - models
applies_to:
  - django
status: active
order: 14
---

# Django Model Tests Example

## Scenario

- Use this shape when model behavior changes independently of a serializer or view.
- Use this shape when testing `BaseModel` behavior such as audit history or tracked-field logging.
- Use this shape when a model method changes state, computes lifecycle status, enforces relation invariants, or coordinates model-backed task execution.
- Use serializer tests for input/output contracts and view tests for permission or route scoping; keep model tests focused on model-owned behavior.

## Why This Shape Exists

- Model tests should prove domain behavior at the persistence boundary. If a model method saves state, writes history, or rejects an invalid relationship, the test should verify the database result.
- Model methods can be called by views, serializers, services, tasks, commands, and shell sessions. Testing only through HTTP leaves important persistence paths uncovered.
- `refresh_from_db()` prevents stale in-memory assertions after `save()`, service calls, or task methods.
- Focused helpers keep object wiring readable without turning setup into a hidden factory framework.
- Monkeypatching lets tests isolate model-owned behavior from Celery, external services, clocks, or logging without making the model code defensive.

## Recommended Shape

### Shared Setup And Small Helpers

```python
import pytest
from tests.fixtures import FixtureFactory
from django.utils import timezone
from task.models import Task


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
```

Use `setup_method` for common domain objects and enum aliases. Use small helpers for repeated object wiring when they make test bodies clearer.

### Base Model History Tests

```python
@pytest.mark.django_db
class TestBaseModel:
	def setup_method(self):
		self.user = FixtureFactory.create_user(email='base-model@example.com')
		self.content_type = ContentType.objects.get_for_model(Task, for_concrete_model=False)

	def test_save_logs_create_history_with_direct_log_entry_creation(self, monkeypatch):
		monkeypatch.setattr(Task, 'history_log_fields', ('status',))

		task = Task(name=Task.TaskNameChoices.PURGE_OLD_TASKS, data={}, percent_complete=0)
		task.save(log_user_id=self.user.id)
		task.refresh_from_db()

		log_entry = LogEntry.objects.get()
		assert log_entry.user_id == self.user.id
		assert log_entry.content_type_id == self.content_type.id
		assert log_entry.object_id == str(task.id)
		assert log_entry.action_flag == ADDITION
		assert log_entry.change_message == f'User: {self.user.id} created Task'

	def test_save_logs_tracked_field_changes(self, monkeypatch):
		monkeypatch.setattr(Task, 'history_log_fields', ('status',))
		task = Task.objects.create(name=Task.TaskNameChoices.PURGE_OLD_TASKS, data={}, percent_complete=0)

		task.status = Task.StatusChoices.RUNNING
		task.save(log_user_id=self.user.id)
		task.refresh_from_db()

		log_entry = LogEntry.objects.get()
		assert log_entry.action_flag == CHANGE
		assert log_entry.change_message == f'User: {self.user.id} changed Task status from "PENDING" to "RUNNING"'
```

When testing base model behavior, assert the durable record that proves the behavior happened. For history logging, assert the `LogEntry` fields, not only that `save()` returned.

### Lifecycle Helper Tests

```python
@pytest.mark.django_db
class TestOperatorInvitation:
	def setup_method(self):
		self.invitation = FixtureFactory.create_operator_invitation(
			status=OperatorInvitation.StatusChoices.PENDING,
			expires_ts=timezone.now() + timedelta(days=1),
		)

	def test_get_effective_status_returns_pending_before_expiration(self):
		assert self.invitation.get_effective_status() == OperatorInvitation.StatusChoices.PENDING

	def test_get_effective_status_returns_expired_after_expiration(self):
		self.invitation.expires_ts = timezone.now() - timedelta(days=1)

		assert self.invitation.get_effective_status() == OperatorInvitation.StatusChoices.EXPIRED

	@pytest.mark.parametrize('status', (OperatorInvitation.StatusChoices.REVOKED, OperatorInvitation.StatusChoices.ACCEPTED))
	def test_get_effective_status_preserves_terminal_statuses(self, status):
		self.invitation.status = status
		self.invitation.expires_ts = timezone.now() - timedelta(days=1)

		assert self.invitation.get_effective_status() == status
```

Lifecycle helper tests should cover active, expired, terminal, and boundary states. If time matters, set timestamps directly or call `timezone.now()` once inside a helper to avoid drift.

### Relation Invariant Tests

```python
@pytest.mark.django_db
class TestComponentNode:
	def setup_method(self):
		self.organization = FixtureFactory.create_organization(name='Node Organization', slug='node-organization')
		self.workspace = FixtureFactory.create_workspace(self.organization, name='Node Workspace', slug='node-workspace')
		self.catalog_entry = FixtureFactory.create_catalog_entry(self.workspace, name='Node CatalogEntry', slug='node-catalog_entry')
		self.survey_form = FixtureFactory.create_survey_form(self.catalog_entry, name='Node Survey', slug='node-survey')
		self.version = FixtureFactory.create_survey_form_version(self.survey_form, version_number=1)
		self.page = FixtureFactory.create_survey_page(self.version, stable_key='first-page')

	def test_component_node_rejects_page_from_different_version(self):
		other_version = FixtureFactory.create_survey_form_version(self.survey_form, version_number=2)
		other_page = FixtureFactory.create_survey_page(other_version, stable_key='other-page')
		node = ComponentNode(
			survey_form_version=self.version,
			page=other_page,
			stable_key='first-name',
			component_type='text_input',
		)

		with pytest.raises(ValidationError) as error:
			node.save()

		assert error.value.message_dict == {'page': ['Page must belong to the same survey form version.']}
```

Model invariant tests should save the model or call the model method that enforces the rule. If the invariant is only tested through a serializer, another save path can still bypass it.

### State-Changing Task Model Tests

```python
@pytest.mark.django_db
class TestTaskModel:
	def test_run_marks_task_completed_for_known_task(self, monkeypatch):
		def fake_purge_old_tasks(self):
			self.progress_message = 'Ran purge'

		monkeypatch.setattr(Task, 'purge_old_tasks', fake_purge_old_tasks)
		task = self._create_task()

		task.run()
		task.refresh_from_db()

		assert task.status == self.status.COMPLETED
		assert task.started_ts is not None
		assert task.completed_ts is not None
		assert task.percent_complete == 100
		assert task.progress_message == 'Task completed'

	def test_forward_survey_event_requires_event_id(self):
		task = self._create_task(name=self.task_name.FORWARD_SURVEY_EVENT)

		with pytest.raises(ValueError) as error:
			task.forward_survey_event()

		assert str(error.value) == 'Missing event_id for survey event forwarding task.'
```

For state-changing model methods, call the method, refresh the instance, and assert the persisted fields. Monkeypatch external service calls so the test focuses on the model contract.

### What Belongs Elsewhere

```python
# Serializer test: request payload and output field contract.
serializer = ItemInputSerializer(data={'name': 'Scoped Item'}, context={'catalog_entry': catalog_entry})
assert serializer.is_valid(), serializer.errors

# View test: permission, route scope, HTTP status, response body.
response = client.post(create_url, {'name': 'Scoped Item'}, content_type='application/json')
assert response.status_code == status.HTTP_201_CREATED

# Model test: intrinsic persistence behavior independent of HTTP.
item.sort_order = 2
item.save()
item.refresh_from_db()
assert item.sort_order == 2
```

Do not force every behavior through model tests. Put the test at the boundary that owns the rule.

## Things To Notice

- Test classes are grouped by model or base-model concern.
- `setup_method` creates shared users, organizations, workspaces, or model instances once per test.
- Helpers build only repeated object wiring; they do not hide assertions or permission setup.
- State-changing tests call `refresh_from_db()` before asserting persisted fields.
- Tests assert concrete records such as `LogEntry`, task rows, persisted fields, or validation errors.
- Monkeypatching is used to isolate external services, Celery dispatch, logging, and time-sensitive collaborators.
- Parametrization is used when the same behavior should hold across several models.
- Serializer and view concerns remain in serializer and view tests.

## Rules To Follow

- Add model tests when changing model fields with generated behavior, model methods, constraints, `save()` overrides, or history logging.
- Assert the persisted database state after model methods that save.
- Use `refresh_from_db()` after saves, services, task methods, or Celery wrapper calls that mutate records.
- Test both normal and boundary states for lifecycle helpers.
- Test invalid relation combinations when the model enforces cross-record invariants.
- Monkeypatch external service calls instead of letting model tests perform network I/O or long workflows.
- Keep shared helper methods explicit and local to the test class unless many modules need the same builder.
- Do not rely on serializer or view tests as the only coverage for model-owned invariants.

## Refactor Signals

- A model method changes data but there is no test that refreshes the instance and asserts persisted fields.
- A `save()` override exists without tests for both valid and invalid paths.
- A lifecycle helper only has a happy-path test.
- A model test depends on a real Celery worker, email send, API call, or clock-sensitive timing.
- Test setup hides ownership, memberships, or required relationships behind broad catch-all helper arguments.
- Serializer tests are asserting model-level history behavior.
- View tests are the only place a model invariant is exercised.

## Verification

- Run the focused model test target for the changed behavior:

```bash
pytest backend/core/tests/test_base_models.py::TestBaseModel
pytest backend/task/tests/test_models.py::TestTaskModel
pytest backend/tenancy/tests/test_models.py
pytest backend/survey/tests/test_component_models.py
```

- Add or update tests for:
  - successful model helper behavior
  - invalid state or invalid relation behavior
  - persisted state after save
	  - history logging when those base-model hooks are involved
  - task progress, dispatch, and failure state for model-backed tasks

- Run `ruff check` on modified Python files. For guidance-only Markdown edits, inspect headings and code fences, and run the guidance builder.

## Why It Helps

- Domain invariants are protected even when code bypasses serializers or views.
- Tests fail at the boundary that owns the rule, which makes failures easier to diagnose.
- Persisted-state assertions catch bugs that in-memory assertions miss.
- Model tests stay small enough to run during focused backend work.
- Future refactors can move views or serializers without losing confidence in the underlying model behavior.
