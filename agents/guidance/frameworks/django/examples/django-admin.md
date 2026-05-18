---
id: framework-django-example-admin
title: Django Admin Example
description: Example app-local admin registration with ModelAdmin configuration and nested custom actions.
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

- Use these shapes when adding or updating an app-local `admin.py` file and you want a generic example that still reflects the conventions used in this repository.

## Recommended Shape

### Standard Model Registration

```python
from django.contrib import admin

from catalog.models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'slug',
        'is_active',
        'created_ts',
        'updated_ts',
    )
    readonly_fields = ('id', 'created_ts', 'updated_ts')
    search_fields = ('name', 'slug')
    list_filter = ('is_active',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'category',
        'name',
        'sku',
        'status',
        'created_ts',
        'updated_ts',
    )
    readonly_fields = ('id', 'created_ts', 'updated_ts')
    search_fields = ('name', 'sku', 'category__name')
    list_filter = ('status', 'category')
    raw_id_fields = ('category',)
```

### Admin With Actions

```python
from django.contrib import admin, messages

from imports.models import ImportJob


@admin.register(ImportJob)
class ImportJobAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'source_name',
        'status',
        'percent_complete',
        'created_ts',
        'updated_ts',
    )
    readonly_fields = ('id', 'created_ts', 'updated_ts')
    search_fields = ('source_name', 'progress_message')
    list_filter = ('status',)
    actions = ('run_jobs', 'retry_jobs')

    @admin.action(description='Run selected jobs')
    def run_jobs(self, request, queryset):
        for instance in queryset:
            instance.run()
            instance.refresh_from_db()

            if instance.status == ImportJob.StatusChoices.COMPLETED:
                self.message_user(request, f'Import job {instance.id} completed', messages.SUCCESS)
                continue

            self.message_user(request, f'Import job {instance.id} failed', messages.ERROR)

    @admin.action(description='Retry selected jobs')
    def retry_jobs(self, request, queryset):
        for instance in queryset:
            retried_instance = instance.retry()
            self.message_user(request, f'Import job {retried_instance.id} queued', messages.SUCCESS)
```

### Admin For Relationship-Heavy Records

```python
from django.contrib import admin

from orders.models import Order, OrderLine


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'customer',
        'status',
        'submitted_ts',
        'created_ts',
        'updated_ts',
    )
    readonly_fields = ('id', 'created_ts', 'updated_ts')
    search_fields = ('customer__email', 'customer__full_name', 'reference_code')
    list_filter = ('status', 'submitted_ts')
    raw_id_fields = ('customer', 'shipping_address')


@admin.register(OrderLine)
class OrderLineAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'order',
        'product_name',
        'quantity',
        'created_ts',
        'updated_ts',
    )
    readonly_fields = ('id', 'created_ts', 'updated_ts')
    search_fields = ('order__reference_code', 'product_name')
    raw_id_fields = ('order',)
```

### Things To Notice

- Keep related registrations inside the owning app's `admin.py` rather than centralizing unrelated admin registrations in a shared module.
- Import models from the same app and register each one with `@admin.register(...)` directly above its `ModelAdmin` class.
- Keep one `ModelAdmin` class per model and group the file by app responsibility.
- Start with `list_display`, then add `readonly_fields`, `search_fields`, `list_filter`, `raw_id_fields`, and `actions` only when they help that model.
- Always include `id`, `created_ts`, and `updated_ts` in both `list_display` and `readonly_fields`.
- Use `raw_id_fields` for foreign keys that would be expensive or awkward as dropdowns.
- Use related lookups such as `category__name`, `customer__email`, or `order__reference_code` in `search_fields` and `list_filter` when operators need cross-model navigation.
- Keep custom actions in the `actions` tuple and define those action methods on the same `ModelAdmin` class that exposes them.
- Prefer `@admin.action(description='...')` over setting `short_description` separately so the action label stays beside the implementation.
- Keep action methods shallow: iterate the queryset, call the real model or service behavior, refresh when needed, and report results with `self.message_user(...)`.
- Import `messages` only when action methods need success or error feedback.
- Use multi-line tuples once a field list gets long enough that a single line is hard to scan.

## Additional Scenarios

- Use a simple registration shape when the model only needs basic list, search, and filter behavior.
- Add `raw_id_fields` when the model points at high-cardinality relations.
- Add custom actions only when operators need an explicit admin-triggered workflow such as run, retry, publish, or archive.
- Keep those workflows inside the `ModelAdmin` class unless the action logic is reused broadly enough to justify a dedicated service call.

## Why It Helps

- This keeps admin registration easy to find within each app, makes admin screens structurally consistent across models, and keeps custom actions close to the class that owns them.

---

## Related Rules

### Django Admin Configuration

- Keep each model's admin registration in the owning app's `admin.py`.
- Register models with `@admin.register(Model)` and subclass `admin.ModelAdmin`.
- Always include `id`, `created_ts`, and `updated_ts` in `list_display` and `readonly_fields`.
- Use `search_fields`, `list_filter`, and `raw_id_fields` where relevant.
- Keep custom actions in the `actions` tuple and label them with `@admin.action(description='...')`.
- Keep action methods on the same `ModelAdmin` class that exposes the action.
