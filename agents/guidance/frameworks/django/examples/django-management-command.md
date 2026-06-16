---
id: framework-django-example-management-command
title: Django Management Command Example
description: Example management command structure for first-class operational entrypoints with safe CLI contracts, cleanup, transactions, and tests.
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

- Use this pattern when repeatable operational work needs a Django-aware entrypoint, such as seeding data, importing files, exporting records, running maintenance, rebuilding derived state, or preparing an end-to-end test database.
- Use this pattern when a task needs ORM access, settings, transactions, permissions-aware domain methods, or repository fixture builders.
- Use this pattern when a command may run in production and needs explicit confirmation, a `--noinput` path, or a deliberate `--allow-production` flag.
- Use this pattern when another command, test, task, or setup flow should call the behavior programmatically through Django's command framework.
- Do not add loose repo-root scripts for work that depends on Django models, settings, or migrations. Put the entrypoint under the owning app's `management/commands/` package.

## Why This Shape Exists

- Management commands are first-class operational entrypoints. They are discoverable through `manage.py help`, run with the same settings and app registry as the rest of Django, and can be called from tests or orchestration commands with `call_command(...)`.
- CLI contracts need to be explicit. Every declared option should be honored exactly, validated early, and reflected in command behavior. A flag that parses but is ignored is a production risk.
- Production safety should be visible at the top of the flow. Destructive commands need guard clauses, `--allow-production`, and non-interactive failure paths before they delete or mutate anything.
- Commands should orchestrate rather than hide domain rules. Use the command for argument parsing, prompts, resource setup, progress output, and transaction boundaries. Keep intrinsic model lifecycle rules on the model, and keep external integrations behind focused services or tasks.
- Command output is part of the operator contract. Use `self.stdout.write(...)` and `self.style.*(...)` so tests can capture output and Django can manage verbosity, color, and streams.

## Recommended Shape

### Put The Command In The Owning App

```text
backend/partner/
	management/
		__init__.py
		commands/
			__init__.py
			import_service_networks.py
	tests/
		test_import_service_networks_command.py
```

The app that owns the data or workflow should own the command. A command that imports service networks belongs with `partner`, not in a repo-root `scripts/` directory or a generic `core` bucket unless it truly coordinates the whole project.

### Define A Clear CLI Contract

```python
import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from partner.models import PartnerStatusChoices, ServiceNetwork
from tenancy.models import Organization


class Command(BaseCommand):
	help = 'Import service networks for one organization from a CSV file.'

	def add_arguments(self, parser):
		parser.add_argument('source_path')
		parser.add_argument('--organization-id', type=int, required=True)
		parser.add_argument('--dry-run', action='store_true')
		parser.add_argument('--allow-production', action='store_true')
		parser.add_argument('--noinput', action='store_true')
		parser.add_argument('--batch-size', type=int, default=100)

	def handle(self, *args, **options):
		source_path = Path(options['source_path'])
		batch_size = options['batch_size']
		if batch_size <= 0:
			raise CommandError('--batch-size must be greater than 0.')

		if not source_path.exists():
			raise CommandError(f'Source file does not exist: {source_path}')

		if not settings.DEBUG and not options['allow_production']:
			raise CommandError('Use --allow-production to import service networks in production.')

		if not settings.DEBUG and not options['noinput']:
			self._confirm_production_import(source_path)

		organization = Organization.objects.get(id=options['organization_id'])
		imported_count = self._import_service_networks(
			organization=organization,
			source_path=source_path,
			batch_size=batch_size,
			dry_run=options['dry_run'],
		)

		if options['dry_run']:
			self.stdout.write(self.style.WARNING(f'Dry run found {imported_count} service networks.'))
			return

		self.stdout.write(self.style.SUCCESS(f'Imported {imported_count} service networks.'))
```

The `handle()` method reads as a boundary checklist: parse and validate options, enforce safety flags, resolve the route-equivalent scope, call focused work, and report the result.

### Keep Prompts And Guard Clauses Explicit

```python
class Command(BaseCommand):
	# add_arguments and handle omitted

	def _confirm_production_import(self, source_path):
		self.stdout.write(self.style.WARNING('You are importing service networks in production.'))
		self.stdout.write(f'Source file: {source_path}')
		confirmation = input('Type IMPORT to continue: ').strip()
		if confirmation != 'IMPORT':
			raise CommandError('Import cancelled.')
```

Do not prompt when `--noinput` is set. Non-interactive runs should either have all required flags or fail before doing work. Keep prompts small and use exact confirmation text for destructive or production operations.

### Use Transactions And Resource Cleanup Around The Work

```python
class Command(BaseCommand):
	# add_arguments, handle, and prompt omitted

	def _import_service_networks(self, organization, source_path, batch_size, dry_run):
		imported_count = 0

		with source_path.open(newline='') as source_file:
			rows = csv.DictReader(source_file)

			with transaction.atomic():
				for row in rows:
					imported_count += 1

					ServiceNetwork.objects.update_or_create(
						organization=organization,
						name=row['name'],
						defaults={
							'description': row['description'],
							'status': PartnerStatusChoices.ACTIVE,
						},
					)

					if imported_count % batch_size == 0:
						self.stdout.write(f'Processed {imported_count} service networks.')

				if dry_run:
					transaction.set_rollback(True)

		return imported_count
```

Use context managers for files, database cursors, temporary directories, API sessions, and other disposable resources. Use `transaction.atomic()` when the command is easier to reason about as an all-or-nothing unit, or when a dry run should exercise the write path and roll back.

### Compose Commands With `call_command`

```python
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
	help = 'Prepare the local e2e database and run the Django server.'

	def add_arguments(self, parser):
		parser.add_argument('--addrport', default='127.0.0.1:8000')

	def handle(self, *args, **options):
		call_command('migrate', interactive=False)
		call_command('seed_e2e_workspace')
		call_command('runserver', options['addrport'], use_reloader=False)
```

Use `call_command(...)` when one Django command needs another command's behavior. Do not shell out to `python manage.py ...` from Python code, and do not import another command class to call `handle()` directly.

### Keep Model Lifecycle Rules Out Of Generic Commands

```python
class OperatorInvitation(models.Model):
	class StatusChoices(models.TextChoices):
		PENDING = 'PENDING', gettext('Pending')
		ACCEPTED = 'ACCEPTED', gettext('Accepted')
		REVOKED = 'REVOKED', gettext('Revoked')
		EXPIRED = 'EXPIRED', gettext('Expired')

	status = models.TextField(choices=StatusChoices.choices, default=StatusChoices.PENDING, null=False, blank=False)
	expires_ts = models.DateTimeField(null=False, blank=False)

	def get_effective_status(self):
		if self.status == self.StatusChoices.PENDING and self.expires_ts <= timezone.now():
			return self.StatusChoices.EXPIRED

		return self.status

	def can_be_accepted(self):
		return self.get_effective_status() == self.StatusChoices.PENDING
```

If the rule is intrinsic to one model's lifecycle, put it on the model so views, serializers, admin actions, tasks, commands, and shell usage all share it. A command that expires invitations should call model behavior or a focused lifecycle service; it should not define its own status graph or duplicate model invariants in a one-off loop.

### Test The Command Contract

```python
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from partner.models import ServiceNetwork


@pytest.mark.django_db
class TestImportServiceNetworksCommand:
	def test_import_creates_service_networks(self, organization, tmp_path):
		source_path = tmp_path / 'service_networks.csv'
		source_path.write_text('name,description\nPrimary Network,Main service network\n')
		stdout = StringIO()

		call_command(
			'import_service_networks',
			str(source_path),
			organization_id=organization.id,
			stdout=stdout,
		)

		service_network = ServiceNetwork.objects.get(organization=organization, name='Primary Network')
		assert service_network.description == 'Main service network'
		assert 'Imported 1 service networks.' in stdout.getvalue()

	def test_dry_run_does_not_persist_rows(self, organization, tmp_path):
		source_path = tmp_path / 'service_networks.csv'
		source_path.write_text('name,description\nPrimary Network,Main service network\n')

		call_command(
			'import_service_networks',
			str(source_path),
			organization_id=organization.id,
			dry_run=True,
		)

		assert ServiceNetwork.objects.filter(organization=organization).count() == 0

	def test_production_requires_explicit_flag(self, settings, organization, tmp_path):
		settings.DEBUG = False
		source_path = tmp_path / 'service_networks.csv'
		source_path.write_text('name,description\nPrimary Network,Main service network\n')

		with pytest.raises(CommandError, match='--allow-production'):
			call_command(
				'import_service_networks',
				str(source_path),
				organization_id=organization.id,
				noinput=True,
			)
```

Command tests should call `call_command(...)`, pass options by their Python keyword names, capture `stdout` when output matters, and assert database state after the command runs.

## Things To Notice

- The command lives under `<app>/management/commands/` and uses `BaseCommand`; it is not a loose script.
- `add_arguments()` is the only CLI contract. Every option declared there is used deliberately in `handle()` or a helper.
- Required identity is explicit. The command requires `--organization-id`; it does not guess by organization name or display label.
- Guard clauses run before mutation: invalid batch size, missing files, and production safety checks fail early.
- `--noinput` is honored by failing instead of prompting when required confirmation is missing.
- Output goes through `self.stdout.write(...)` and `self.style.SUCCESS`, `WARNING`, or `ERROR` instead of `print()`.
- File access uses a context manager, and database writes sit inside a transaction.
- `dry_run` exercises the same import path and rolls back instead of using a separate best-effort parser-only branch.
- `call_command(...)` composes commands and is also the test entrypoint.
- Model lifecycle rules stay on the model when they are intrinsic to that model; commands orchestrate those rules instead of redefining them.

## Rules To Follow

- Put Django-aware operational work in a management command, dedicated CLI tool, or equivalent first-class entrypoint; do not add ad hoc root scripts for ORM-backed work.
- Place a command in the app that owns the data or workflow.
- Define all options in `add_arguments()` and honor every declared option.
- Use `CommandError` for operator-facing command failures.
- Validate arguments and environment safety before opening external resources or mutating the database.
- Require explicit identity such as ids or slugs that are unique in the command's scope; do not guess from non-unique display names.
- Add `--allow-production` to destructive or broad mutating commands that can run against production data.
- Add and honor `--noinput` for commands that may prompt.
- Use `self.stdout.write(...)` and Django styles for command output.
- Use context managers for files, temporary directories, sessions, cursors, and other resources.
- Use `transaction.atomic()` when a command's changes should commit or roll back together.
- Use `call_command(...)` for programmatic execution from tests, setup commands, and orchestration commands.
- Keep intrinsic model lifecycle rules on the model; use services or tasks for cross-model orchestration, external I/O, retries, and long-running work.
- Add targeted tests for option validation, safety guards, output, idempotency or dry-run behavior, and database side effects.

## Refactor Signals

- A repo-root script imports Django models or sets `DJANGO_SETTINGS_MODULE` manually for ordinary app work.
- A command declares options that are not used or whose behavior differs from the help text.
- Destructive code runs before environment, confirmation, organization, workspace, or source-file validation.
- A production-capable command relies only on an interactive prompt and has no `--noinput` failure path.
- The command uses `print()` or writes directly to `sys.stdout`.
- File handles, database cursors, API sessions, or temporary directories are opened without scoped cleanup.
- Multiple commands shell out to `python manage.py ...` instead of using `call_command(...)`.
- A command duplicates a model's status transition graph, acceptance rule, expiration rule, or invariant instead of calling the model or lifecycle service.
- A command imports another command class and calls `handle()` directly.
- A command mutates many related rows without a clear transaction decision.
- Command behavior is only tested indirectly through a view, task, or manual runbook.

## Verification

- Run targeted command tests for behavior changes:

```bash
pytest backend/core/tests/test_seed_e2e_workspace.py
pytest backend/partner/tests/test_import_service_networks_command.py
```

- Run `ruff check` on modified Python command and test files:

```bash
ruff check backend/partner/management/commands/import_service_networks.py backend/partner/tests/test_import_service_networks_command.py
```

- For guidance-only edits, inspect headings and code fences, then run the guidance builder:

```bash
python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean
```

- Verify command-specific cases:
  - invalid options raise `CommandError`
  - `--allow-production` and `--noinput` behavior is covered
  - dry runs do not persist rows
  - resource cleanup uses context managers
  - transactional behavior is intentional
  - output is captured through `stdout`
  - repeated runs are idempotent when the command claims to be idempotent

## Why It Helps

- Operational workflows become discoverable, testable, and reusable.
- Production-impacting commands fail before they can mutate data accidentally.
- CLI behavior stays reviewable because argument parsing, guard clauses, prompts, and output are visible in one flow.
- Transactions and scoped cleanup make partial failures easier to reason about.
- Tests can exercise commands through the same `call_command(...)` path used by orchestration code.
- Domain invariants remain consistent across commands, views, serializers, admin actions, tasks, and shell usage.
