---
id: framework-django-example-model
title: Django Model Example
description: Example Django model standards for field layout, choices, relations, lifecycle invariants, audit history, and side-effect boundaries.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - model
  - lifecycle
applies_to:
  - django
status: active
order: 1
---

# Django Model Example

## Scenario

- Use this shape when adding or refactoring a Django model.
- Use this shape when a model needs repository base-model behavior such as timestamps or admin history logging.
- Use this shape when a model has intrinsic invariants that must hold no matter which view, serializer, command, or task saves it.
- Use this shape when deciding whether a lifecycle rule belongs on the model, in a serializer, in a service, or in a Celery task.

## Why This Shape Exists

- Model files are the durable domain shape. Field order, relation declarations, choices, and lifecycle helpers should be predictable enough that reviewers can scan a model quickly.
- `BaseModel` centralizes timestamps and audit history. Models should use that shared contract instead of re-implementing it locally.
- Intrinsic invariants belong close to the model. If a child record must belong to the same version, parent, organization, or scope as its related records, the model can enforce that for every persistence path.
- Transport rules do not belong on the model. Permissions, request-owned context, route scoping, and serializer-specific validation still belong in views and serializers.
- Third-party I/O should not hide in `save()` or `delete()`. Network calls, retries, sync events, and long workflows should live in explicit services or tasks so callers and tests can see when they happen.

## Recommended Shape

### Standard Model Declaration

```python
from core.base_models import BaseModel
from django.db import models
from django.utils.translation import gettext


class Item(BaseModel):
	class Meta:
		ordering = ('sort_order', 'id')
		constraints = (
			models.UniqueConstraint(fields=('collection', 'code'), name='unique_item_code_per_collection'),
		)

	class StatusChoices(models.TextChoices):
		ACTIVE = 'ACTIVE', gettext('Active')
		INACTIVE = 'INACTIVE', gettext('Inactive')

	collection = models.ForeignKey('catalog.Collection', related_name='items', null=False, blank=False, verbose_name=gettext('Collection'), on_delete=models.DO_NOTHING)
	name = models.TextField(null=False, blank=False, verbose_name=gettext('Name'))
	code = models.TextField(null=False, blank=False, verbose_name=gettext('Code'))
	status = models.TextField(choices=StatusChoices.choices, default=StatusChoices.ACTIVE, null=False, blank=False, verbose_name=gettext('Status'))
	summary = models.TextField(null=False, blank=True, verbose_name=gettext('Summary'))
	description = models.TextField(null=False, blank=True, verbose_name=gettext('Description'))
	sort_order = models.PositiveIntegerField(default=0, null=False, blank=False, verbose_name=gettext('Sort Order'))

	def __str__(self):
		return self.name
```

Keep declaration order consistent: class attributes, `Meta`, choices, fields, dunder methods, lifecycle overrides, then remaining helpers. This order lets future readers find constraints, choices, and fields without scanning a custom layout each time.

### Base Model Behavior

```python
class BaseModel(models.Model):
	history_log_fields = ()
	history_log_private_fields = ()

	created_ts = models.DateTimeField(auto_now_add=True, verbose_name=gettext('Created Time'))
	updated_ts = models.DateTimeField(auto_now=True, verbose_name=gettext('Updated Time'))

	class Meta:
		abstract = True

	def save(self, *args, **kwargs):
		is_new = self.pk is None
		log_user_id = kwargs.pop('log_user_id', None)

		super().save(*args, **kwargs)

		if not log_user_id and settings.SYSTEM_USER_ID:
			log_user_id = settings.SYSTEM_USER_ID

		if log_user_id and (self.history_log_fields or self.history_log_private_fields):
			if is_new:
				self.log_create_history(log_user_id)
			else:
				self.log_change_history(log_user_id)
```

Use `BaseModel` for repository models so timestamps and audit hooks behave consistently. Do not copy this logic into individual models.

### Audit History Contract

```python
class Task(BaseModel):
	history_log_fields = ('status',)

	class StatusChoices(models.TextChoices):
		PENDING = 'PENDING', gettext('Pending')
		RUNNING = 'RUNNING', gettext('Running')
		COMPLETED = 'COMPLETED', gettext('Completed')
		FAILED = 'FAILED', gettext('Failed')

	status = models.TextField(choices=StatusChoices.choices, default=StatusChoices.PENDING, null=False, blank=False, verbose_name=gettext('Status'))
	progress_message = models.TextField(null=False, blank=True, verbose_name=gettext('Progress Message'))
```

Use `history_log_fields` for values that can be safely shown in admin history. Use `history_log_private_fields` for values that must record that a change happened without storing before/after values. Pass `log_user_id` to `save(...)` when a user action should be attributed.

### Intrinsic Relation Invariants

```python
from django.core.exceptions import ValidationError


class ComponentNode(BaseModel):
	class Meta:
		constraints = (
			models.UniqueConstraint(fields=('survey_form_version', 'stable_key'), name='unique_component_node_stable_key_per_version'),
		)
		ordering = ('page_id', 'parent_node_id', 'slot_name', 'sort_order', 'id')

	survey_form_version = models.ForeignKey('survey.SurveyFormVersion', related_name='component_nodes', null=False, blank=False, verbose_name=gettext('Survey Form Version'), on_delete=models.DO_NOTHING)
	page = models.ForeignKey('survey.SurveyPage', related_name='component_nodes', null=False, blank=False, verbose_name=gettext('Page'), on_delete=models.DO_NOTHING)
	parent_node = models.ForeignKey('survey.ComponentNode', related_name='child_nodes', null=True, blank=True, verbose_name=gettext('Parent Node'), on_delete=models.DO_NOTHING)
	stable_key = models.SlugField(null=False, blank=False, verbose_name=gettext('Stable Key'))
	label = models.TextField(null=False, blank=True, verbose_name=gettext('Label'))
	sort_order = models.PositiveIntegerField(default=0, null=False, blank=False, verbose_name=gettext('Sort Order'))

	def save(self, *args, **kwargs):
		self._validate_relations()
		super().save(*args, **kwargs)

	def _validate_relations(self):
		errors = {}

		if self.page_id and self.page.survey_form_version_id != self.survey_form_version_id:
			errors['page'] = gettext('Page must belong to the same survey form version.')

		if self.parent_node_id and self.parent_node.page_id != self.page_id:
			errors['parent_node'] = gettext('Parent node must belong to the same page.')

		if errors:
			raise ValidationError(errors)
```

Use model-level validation for invariants that should hold for every save path. Keep request-specific rules, permission checks, route ownership, and cross-scope serializer input validation in views and serializers.

### Lifecycle Helpers Without Hidden I/O

```python
class OperatorInvitation(BaseModel):
	class StatusChoices(models.TextChoices):
		PENDING = 'PENDING', gettext('Pending')
		ACCEPTED = 'ACCEPTED', gettext('Accepted')
		REVOKED = 'REVOKED', gettext('Revoked')
		EXPIRED = 'EXPIRED', gettext('Expired')

	status = models.TextField(choices=StatusChoices.choices, default=StatusChoices.PENDING, null=False, blank=False, verbose_name=gettext('Status'))
	expires_ts = models.DateTimeField(null=False, blank=False, verbose_name=gettext('Expires Time'))

	def get_effective_status(self):
		if self.status == self.StatusChoices.PENDING and self.expires_ts <= timezone.now():
			return self.StatusChoices.EXPIRED

		return self.status

	def can_be_accepted(self):
		return self.get_effective_status() == self.StatusChoices.PENDING
```

Intrinsic state helpers are fine on the model. Sending invitation emails, accepting invitations, creating memberships, and recording external sync attempts should live in explicit services or tasks.

## Things To Notice

- Models extend `BaseModel` unless there is a deliberate reason not to.
- `Meta` appears before choices and field declarations.
- `TextChoices` labels use `gettext(...)`.
- Field declarations stay on one line and keep argument order consistent.
- New string fields use `models.TextField` unless a real length constraint exists.
- Defaults represent real domain defaults, not convenience values to avoid validation.
- Relations use string model references such as `'workspace.Workspace'` and set `on_delete` explicitly.
- Existing relationships commonly use `models.DO_NOTHING`; use another `on_delete` strategy only with a deliberate data-integrity plan.
- Model-level `save()` overrides are limited to intrinsic database invariants and then call `super().save(...)`.
- Third-party I/O, long workflows, and retries stay out of `save()` and `delete()`.

## Rules To Follow

- Use `BaseModel` for repository domain models.
- Keep model declaration order stable: class attributes, `Meta`, choices, fields, dunder methods, lifecycle overrides, helpers.
- Always include explicit `null`, `blank`, and `verbose_name` on fields following local style.
- Use `gettext(...)` for human-readable labels.
- Do not add `default=''` or placeholder defaults for optional fields.
- Use `models.TextField` for unconstrained strings.
- Put intrinsic invariants on the model only when every save path must enforce them.
- Put request-specific scoping, permissions, and serializer input validation outside the model.
- Keep network I/O and background work in services or Celery tasks.
- Add or update model tests when changing audit history, constraints, state helpers, or model-level validation.

## Refactor Signals

- A model has fields, choices, and helpers in a custom order that makes the class hard to scan.
- Multiple models copy timestamp or audit-history behavior instead of using `BaseModel`.
- A model uses empty-string defaults to avoid required input.
- A `save()` method sends email, calls an API, schedules a task, or performs retry behavior.
- A serializer and a model enforce the same intrinsic invariant in different ways.
- A model helper depends on request state, route parameters, permissions, or the current user.
- Related records can be saved with mismatched parent/version/organization scope through non-serializer code.
- A model change lacks tests for history logging, lifecycle helper, or validation behavior.

## Verification

- Run targeted model tests for the model or base behavior you changed:

```bash
pytest backend/core/tests/test_base_models.py::TestBaseModel
pytest backend/tenancy/tests/test_models.py
pytest backend/survey/tests/test_component_models.py
```

- Add or update tests for:
  - audit create/change/private-field history
	  - `TextChoices` lifecycle helpers such as `get_effective_status()`
	  - model-level relation validation
	  - custom `save()` behavior and `refresh_from_db()` after state changes

- Run `ruff check` on modified Python files. For guidance-only Markdown edits, inspect headings and code fences, and run the guidance builder.

## Why It Helps

- Models stay predictable to scan and review.
- Shared base behavior prevents copy-pasted timestamps and audit logging.
- Intrinsic invariants are enforced consistently across views, serializers, tasks, commands, and shell usage.
- Side effects stay visible at explicit service or task boundaries.
- Model tests become a reliable safety net for domain behavior that should not depend on the HTTP layer.
