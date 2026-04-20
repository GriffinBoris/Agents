---
id: framework-django-example-management-command
title: Django Management Command Example
description: Example management command structure with focused helpers and early guard clauses.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - management-command
applies_to:
  - django
status: active
order: 9
---

# Django Management Command Example

## Scenario

- Use this pattern when a command has a few branches or prompts, but should still read as a straightforward orchestration flow.

## Recommended Shape

### Good Example

```python
class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--keep-file', action='store_true')
        parser.add_argument('--backup-scope', choices=('development', 'production'))
        parser.add_argument('--allow-production', action='store_true')
        parser.add_argument('--page-size', type=int, default=10)

    def _resolve_backup_scope(self, backup_scope, noinput):
        if not settings.IS_DEVELOPMENT:
            return 'production'

        if backup_scope:
            return backup_scope

        if noinput:
            self.stdout.write(self.style.ERROR('Backup scope is required with --noinput'))
            return None

        while True:
            self.stdout.write('Select backup scope:')
            self.stdout.write('[1] development')
            self.stdout.write('[2] production')
            selection = input('Enter 1 or 2: ').strip()

            if selection == '1':
                return 'development'

            if selection == '2':
                return 'production'

            self.stdout.write(self.style.WARNING('Invalid selection'))

    def handle(self, *args, **options):
        page_size = options['page_size']
        if page_size <= 0:
            self.stdout.write(self.style.ERROR('Page size must be greater than 0'))
            return

        backup_scope = self._resolve_backup_scope(options['backup_scope'], options['noinput'])
        if not backup_scope:
            return

        storage_config = self._get_storage_config(backup_scope)
        if not storage_config:
            return

        blob_storage = BlobStorageAdapter(
            connection_string=storage_config['OPTIONS']['connection_string'],
            container_name=self._get_container_name(storage_config['OPTIONS']),
        )

        # continue with the main command flow
```

### Things To Notice

- `handle()` stays short and mostly orchestrates helpers.
- Guard clauses exit early for invalid input or missing configuration.
- Prompting, config resolution, and setup live in named helpers instead of one long `handle()` body.

## Why It Helps

- The command remains readable as options grow.

---

## Related Rule: Model-Owned Lifecycle

### Avoid

```python
def transition_order(*, order, next_status):
    allowed = ORDER_STATUS_TRANSITIONS.get(order.status, ())
    if next_status not in allowed:
        raise ValidationError({'status': 'Invalid status change.'})

    order.status = next_status
    order.save()
    return order
```

### Prefer

```python
class Order(models.Model):
    ALLOWED_STATUS_TRANSITIONS = {
        'DRAFT': ('SUBMITTED',),
        'SUBMITTED': ('APPROVED',),
    }

    def transition_to(self, next_status):
        allowed = self.ALLOWED_STATUS_TRANSITIONS.get(self.status, ())
        if next_status not in allowed:
            raise ValidationError({'status': 'Invalid status change.'})

        self.status = next_status
        self.save()
        return self
```

### Why It Helps

- If a lifecycle rule is intrinsic to one model, the model is the clearest place to keep it.
- Generic service modules become dumping grounds when they absorb one-model lifecycle rules.
- Keep services for third-party adapters, cross-boundary orchestration, or disposable integration logic.
