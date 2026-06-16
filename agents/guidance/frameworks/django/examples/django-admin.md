---
id: framework-django-example-admin
title: Django Admin Example
description: Example app-local Django admin configuration with safe ModelAdmin registration, relationship handling, and shallow custom actions.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - admin
applies_to:
  - django
status: active
order: 18
---

# Django Admin Example

## Scenario

- Use this shape when adding or refactoring a Django app's `admin.py`.
- Use this shape when registering one or more models owned by the same app.
- Use this shape when an admin screen needs searchable list views, safe relationship widgets, or operator-triggered actions such as run, retry, publish, archive, or recreate.
- Use this shape when reviewing admin configuration for consistency, operator safety, and discoverability.

## Why This Shape Exists

- Django admin is an operator surface, not a dumping ground for every model in the project. Keeping registrations in the owning app makes the screen configuration live beside the models, services, and tests that explain the domain.
- `@admin.register(Model)` puts the registration next to the `ModelAdmin` class. Reviewers can see the model, screen fields, search behavior, filters, relationship widgets, and actions in one place.
- Every `BaseModel` record carries `id`, `created_ts`, and `updated_ts`. Showing those fields in admin makes records easy to identify, compare, audit, and debug without opening the database.
- High-cardinality relations such as organization, workspace, contact, catalog_entry, item, task, user, and survey records should not render as huge dropdowns. `raw_id_fields` keeps forms fast and forces operators to choose a precise related record.
- Admin actions can cause broad changes because operators run them across selected querysets. Actions must stay shallow and obvious: iterate selected records, call existing model or service behavior, and report the result with messages.
- Centralized unrelated admin modules become hard to review. They separate model ownership from admin behavior, encourage broad imports, and make one file grow with many unrelated domains.

## Recommended Shape

### App-Local Registration

```python
# backend/workspace/admin.py

from workspace.models import Workspace, WorkspaceMembership
from django.contrib import admin


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
	list_display = (
		'id',
		'organization',
		'name',
		'slug',
		'status',
		'created_ts',
		'updated_ts',
	)
	readonly_fields = ('id', 'created_ts', 'updated_ts')
	search_fields = ('name', 'slug', 'contact_name', 'contact_email')
	list_filter = ('status', 'organization')
	raw_id_fields = ('organization', 'default_survey_theme')


@admin.register(WorkspaceMembership)
class WorkspaceMembershipAdmin(admin.ModelAdmin):
	list_display = (
		'id',
		'workspace',
		'user',
		'role',
		'is_active',
		'created_ts',
		'updated_ts',
	)
	readonly_fields = ('id', 'created_ts', 'updated_ts')
	search_fields = ('workspace__name', 'workspace__slug', 'user__email', 'user__username')
	list_filter = ('role', 'is_active')
	raw_id_fields = ('workspace', 'user')
```

Keep admin ownership inside the app that owns the models. Register each model with a dedicated `ModelAdmin` class so the screen configuration can evolve independently as the model grows.

### Relationship-Heavy Records

```python
# backend/order/admin.py

from django.contrib import admin
from order.models import CouponUsage, Order, OrderItem, OrderTimelineEntry


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
	list_display = (
		'id',
		'organization',
		'workspace',
		'contact',
		'status',
		'source',
		'resolved_price_amount',
		'created_ts',
		'updated_ts',
	)
	readonly_fields = ('id', 'created_ts', 'updated_ts')
	search_fields = (
		'contact__email',
		'shipping_full_name',
		'shipping_line_1',
		'shipping_city',
		'shipping_postal_code',
	)
	list_filter = ('status', 'source', 'organization')
	raw_id_fields = (
		'organization',
		'workspace',
		'contact',
		'enrollment',
		'approved_item_plan',
		'catalog_entry_subscription_plan',
	)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
	list_display = (
		'id',
		'order',
		'item_name',
		'quantity',
		'unit_price_amount',
		'total_price_amount',
		'created_ts',
		'updated_ts',
	)
	readonly_fields = ('id', 'created_ts', 'updated_ts')
	search_fields = ('item_name', 'catalog_entry_subscription_plan_name')
	raw_id_fields = ('order', 'item', 'item_option', 'catalog_entry_subscription_plan')


@admin.register(OrderTimelineEntry)
class OrderTimelineEntryAdmin(admin.ModelAdmin):
	list_display = ('id', 'order', 'entry_type', 'created_by', 'created_ts', 'updated_ts')
	readonly_fields = ('id', 'created_ts', 'updated_ts')
	search_fields = ('message',)
	list_filter = ('entry_type',)
	raw_id_fields = ('order', 'created_by')


@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
	list_display = ('id', 'coupon', 'order', 'contact', 'code', 'discount_amount', 'created_ts', 'updated_ts')
	readonly_fields = ('id', 'created_ts', 'updated_ts')
	search_fields = ('code',)
	raw_id_fields = ('coupon', 'order', 'contact')
```

Use `raw_id_fields` for foreign keys that point at tables operators cannot reasonably scan in a select dropdown. Use `search_fields` for identifiers operators actually have: email, slug, code, postal code, internal name, reference text, or another stable searchable field.

### Large Domain Admin File

```python
# backend/survey/admin.py

from django.contrib import admin
from survey.models.ComponentNode import ComponentNode
from survey.models.SurveyForm import SurveyForm
from survey.models.SurveyFormVersion import SurveyFormVersion
from survey.models.SurveySession import SurveySession


@admin.register(SurveyForm)
class SurveyFormAdmin(admin.ModelAdmin):
	list_display = (
		'id',
		'catalog_entry',
		'name',
		'slug',
		'status',
		'active_published_version',
		'sort_order',
		'created_ts',
		'updated_ts',
	)
	readonly_fields = ('id', 'created_ts', 'updated_ts')
	search_fields = ('name', 'slug', 'intro_title', 'description')
	list_filter = ('status', 'catalog_entry__workspace__organization')
	raw_id_fields = ('catalog_entry', 'theme_override', 'active_published_version', 'created_by')


@admin.register(SurveyFormVersion)
class SurveyFormVersionAdmin(admin.ModelAdmin):
	list_display = (
		'id',
		'survey_form',
		'version_number',
		'status',
		'published_at',
		'created_ts',
		'updated_ts',
	)
	readonly_fields = ('id', 'publish_snapshot', 'created_ts', 'updated_ts')
	search_fields = ('survey_form__name', 'internal_name')
	list_filter = ('status', 'survey_form__catalog_entry__workspace__organization')
	raw_id_fields = ('survey_form', 'created_from_version', 'published_by')


@admin.register(ComponentNode)
class ComponentNodeAdmin(admin.ModelAdmin):
	list_display = (
		'id',
		'survey_form_version',
		'page',
		'parent_node',
		'stable_key',
		'component_type',
		'sort_order',
		'is_enabled',
		'created_ts',
		'updated_ts',
	)
	readonly_fields = ('id', 'created_ts', 'updated_ts')
	search_fields = ('stable_key', 'label', 'component_type', 'slot_name')
	list_filter = ('component_type', 'is_enabled', 'survey_form_version__survey_form__catalog_entry__workspace__organization')
	raw_id_fields = ('survey_form_version', 'page', 'parent_node')


@admin.register(SurveySession)
class SurveySessionAdmin(admin.ModelAdmin):
	list_display = (
		'id',
		'survey_form',
		'survey_form_version',
		'status',
		'contact',
		'project_enrollment',
		'created_ts',
		'updated_ts',
	)
	readonly_fields = ('id', 'metadata', 'created_ts', 'updated_ts')
	search_fields = ('survey_form__name', 'current_page_key', 'last_completed_page_key')
	list_filter = ('status', 'survey_form__catalog_entry__workspace__organization')
	raw_id_fields = (
		'workspace',
		'catalog_entry',
		'survey_form',
		'survey_form_version',
		'lead',
		'contact',
		'project_enrollment',
		'selected_item',
		'selected_item_option',
		'selected_plan',
		'selected_rate_card',
	)
```

It is acceptable for a domain with many models to have a longer app-local `admin.py` while the app remains the ownership boundary. Keep each registration self-contained, group related registrations together, and use direct imports from the model modules when the app uses a model package.

### Operator-Safe Custom Actions

```python
# backend/task/admin.py

from django.contrib import admin, messages
from task.models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
	list_display = ('id', 'name', 'status', 'percent_complete', 'created_ts', 'updated_ts')
	readonly_fields = ('id', 'created_ts', 'updated_ts')
	search_fields = ('name', 'progress_message')
	list_filter = ('status',)
	actions = ('run_tasks', 'recreate_tasks')

	@admin.action(description='Run Task(s)')
	def run_tasks(self, request, queryset):
		for task in queryset:
			task.run()
			task.refresh_from_db()

			if task.status == Task.StatusChoices.COMPLETED:
				self.message_user(request, f'Task: {task.id} - {task.name} completed.', messages.SUCCESS)
				continue

			self.message_user(request, f'Task: {task.id} - {task.name} failed.', messages.ERROR)

	@admin.action(description='Re-Create Task(s)')
	def recreate_tasks(self, request, queryset):
		for old_task in queryset:
			new_task = Task.create_task(old_task.name, old_task.data)
			self.message_user(request, f'Task: {new_task.id} - {new_task.name} created.', messages.SUCCESS)
```

The action is the admin boundary, not the business logic boundary. It loops over the selected queryset, calls model-owned behavior, refreshes state when the called behavior mutates the database, and uses `self.message_user(...)` so the operator sees what happened.

### Avoid Centralized Unrelated Admin Modules

```python
# backend/core/admin.py

from django.contrib import admin
from workspace.models import Workspace
from order.models import Order
from item.models import Item
from tenancy.models import Organization


admin.site.register(Organization)
admin.site.register(Workspace)
admin.site.register(Item)
admin.site.register(Order)
```

Do not collect unrelated registrations in a shared or project-level admin file. This hides the configuration from the owning app, makes review scope unclear, and usually leaves models with default admin behavior instead of searchable, filterable, auditable screens.

## Things To Notice

- The file path is app-local: `backend/workspace/admin.py`, `backend/order/admin.py`, `backend/survey/admin.py`, or the equivalent owning app.
- Imports are explicit and top-level. Model imports come from the owning app, and `messages` is imported only when actions need operator feedback.
- Each model uses `@admin.register(Model)` directly above one `ModelAdmin` class.
- Each `ModelAdmin` class owns exactly one model's admin behavior.
- `list_display` always includes `id`, `created_ts`, and `updated_ts`.
- `readonly_fields` always includes `id`, `created_ts`, and `updated_ts`; add JSON snapshots, payloads, metadata, or generated audit fields when operators should inspect but not edit them.
- `search_fields` uses values operators can identify from support context, such as email, slug, code, name, key, message text, or external-facing address fields.
- `list_filter` uses fields with useful buckets, such as status, role, source, enabled flags, type choices, organization, workspace, or date-like state.
- `raw_id_fields` is the default for high-cardinality relations and nested domain records.
- Custom admin actions are listed in `actions`, labeled with `@admin.action(description='...')`, and implemented on the same `ModelAdmin` class.
- Admin actions call existing model or service behavior instead of re-implementing workflow logic inside the admin class.
- `self.message_user(...)` reports per-object success or failure when an action can produce mixed outcomes.
- Multi-line tuples are used once a field list is long enough that one line becomes hard to scan.

## Rules To Follow

- Keep each model's admin registration in the owning app's `admin.py`.
- Do not create centralized admin modules for unrelated apps.
- Register models with `@admin.register(Model)` instead of bare `admin.site.register(Model)`.
- Use one `ModelAdmin` class per model.
- Name admin classes after the model, such as `WorkspaceAdmin`, `OrderAdmin`, or `TaskAdmin`.
- Include `id`, `created_ts`, and `updated_ts` in every `list_display` for models that extend `BaseModel`.
- Include `id`, `created_ts`, and `updated_ts` in every `readonly_fields` for models that extend `BaseModel`.
- Add `search_fields` when an operator needs to locate records by human-facing or support-facing identifiers.
- Add `list_filter` when a field gives meaningful buckets and will not produce an unusable filter list.
- Use `raw_id_fields` for foreign keys to high-cardinality models or records that are awkward or unsafe to choose from dropdowns.
- Keep admin actions shallow: iterate `queryset`, call model or service behavior, refresh changed instances when needed, and show messages.
- Do not put organization scoping, permission policy, external integration details, or long business workflows directly in `ModelAdmin` methods.
- Do not perform broad destructive actions without an explicit, reviewable operator workflow and clear messages.
- Keep admin configuration readable before clever. Prefer explicit field tuples over generated lists or shared constants.
- Add tests for model or service behavior called by admin actions; do not rely on the admin action as the only tested path for important workflow logic.

## Refactor Signals

- An app's models are registered from `core/admin.py`, project `urls.py`, settings code, or another unrelated module.
- A model is registered with `admin.site.register(Model)` and has no `ModelAdmin` configuration.
- One `ModelAdmin` class tries to configure multiple models or uses dynamic model-specific branches.
- `list_display` omits `id`, `created_ts`, or `updated_ts` for a `BaseModel` subclass.
- `readonly_fields` allows operators to edit generated identity, timestamp, snapshot, payload, or audit fields that should be inspect-only.
- A foreign key to a large table renders as a dropdown instead of using `raw_id_fields`.
- Operators cannot find records because `search_fields` lacks email, slug, name, key, code, or other real lookup fields.
- `list_filter` is missing for status, role, enabled flags, source, or type fields that operators use to triage records.
- An admin action contains workflow rules, permission policy, external API calls, retry loops, or complex branching instead of calling a model method, service, or task.
- An admin action mutates many records without reporting per-object outcomes through `self.message_user(...)`.
- Admin configuration uses generated field lists, reflection, dynamic `getattr`, or shared constants that make the actual screen shape hard to review.
- A long admin file mixes unrelated app domains instead of only the models owned by that app.
- A new admin action has no tests covering the model or service method it invokes.

## Verification

- Run Django's system checks after changing admin configuration:

```bash
python manage.py check
```

- Run the app's focused tests when admin configuration exposes new model behavior, new readonly data, or new actions:

```bash
pytest backend/task/tests
pytest backend/workspace/tests
pytest backend/order/tests
```

- Run targeted model or service tests for any behavior called by an admin action. The action should be a thin operator entrypoint; the behavior should be provable without clicking through admin.
- For relationship-heavy admin screens, manually review that every high-cardinality foreign key appears in `raw_id_fields`.
- For timestamped models, scan the changed `admin.py` for `list_display` and `readonly_fields` entries that include `id`, `created_ts`, and `updated_ts`.
- For guidance-only edits, run the guidance builder and a focused Markdown/fence check when practical:

```bash
python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean
```

## Why It Helps

- Operators get predictable, searchable admin screens with stable identifiers and audit timestamps.
- Large relationship fields stay usable and precise instead of loading slow dropdowns.
- Admin actions remain easy to review because they delegate business behavior to model or service code.
- App-local ownership keeps admin behavior close to the domain that owns it.
- Reviewers can quickly spot missing audit fields, unsafe bulk actions, unsearchable records, and admin files that are becoming centralized catch-alls.
