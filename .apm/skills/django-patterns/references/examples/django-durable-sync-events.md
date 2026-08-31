# Django Durable Sync Event Processing

## Scenario

Use this pattern when an external provider needs one or more of the following:

- signed webhook ingestion
- asynchronous outbound mutations
- retryable provider failures
- scheduled reconciliation
- operator-visible processing history
- deduplication across repeated deliveries or task retries

Do not introduce a durable event engine for a single synchronous call whose result is returned directly and needs no retry, history, or reconciliation surface.

## Why This Shape Exists

Provider integrations fail across process and network boundaries. A webhook can be delivered twice, a worker can stop after a remote mutation, or an event can arrive before another provider resource is readable. A database event gives the application a durable record of what it accepted, what it attempted, and what should happen next.

The generic engine must stay smaller than the integrations that use it. It owns event identity and processing mechanics. It does not know provider schemas, API clients, domain models, or which system owns a business field. Keeping those decisions in provider apps prevents the shared engine from becoming a framework inside the framework.

Webhook processing and scheduled reconciliation should converge through the same provider projection service. The webhook says that something changed; the provider resource read supplies the authoritative current state.

## Recommended Shape

### Keep Configuration In Django Settings

```python
SYNC = {
	'MAX_ATTEMPTS': 5,
	'PROCESSING_TIMEOUT_SECONDS': 300,
	'RETRY_DELAY_SECONDS': 60,
}
```

Read these values directly with `settings.SYNC[...]`. Do not repeat the defaults in the sync app, add a configuration wrapper around one dictionary, or cache the values on a service instance.

### Keep The Generic Event Contract Small

```python
from django.db import models
from django.utils import timezone


class Event(models.Model):
	class Meta:
		constraints = (
			models.UniqueConstraint(
				fields=('scope_key', 'direction', 'external_system', 'event_key'),
				name='sync_unique_scope_direction_system_event_key',
			),
		)

	class DirectionChoices(models.TextChoices):
		INBOUND = 'INBOUND', 'Inbound'
		OUTBOUND = 'OUTBOUND', 'Outbound'

	class StatusChoices(models.TextChoices):
		PENDING = 'PENDING', 'Pending'
		PROCESSING = 'PROCESSING', 'Processing'
		PROCESSED = 'PROCESSED', 'Processed'
		SKIPPED = 'SKIPPED', 'Skipped'
		RETRY_SCHEDULED = 'RETRY_SCHEDULED', 'Retry scheduled'
		FAILED = 'FAILED', 'Failed'

	scope_key = models.TextField()
	direction = models.TextField(choices=DirectionChoices.choices, default=DirectionChoices.INBOUND)
	external_system = models.TextField()
	event_type = models.TextField()
	event_key = models.TextField()
	payload = models.JSONField(default=dict)
	occurred_ts = models.DateTimeField(null=True, blank=True)
	caused_by_event = models.ForeignKey('self', related_name='caused_events', null=True, blank=True, on_delete=models.SET_NULL)
	status = models.TextField(choices=StatusChoices.choices, default=StatusChoices.PENDING)
	status_changed_ts = models.DateTimeField(default=timezone.now)
	attempt_count = models.IntegerField(default=0)
	next_attempt_ts = models.DateTimeField(null=True, blank=True)
	status_message = models.TextField(blank=True)
	result_payload = models.JSONField(default=dict, blank=True)
```

The identity constraint is the concurrency-safe deduplication boundary. `scope_key` identifies the provider account or connection when the provider does not guarantee globally unique event IDs.

Keep generic payloads limited to local identifiers and safe operational metadata. Raw webhook bodies, protected health information, signed documents, and provider secrets belong in encrypted provider-owned records.

### Record Events Through One Direct Service

```python
def record_event(
	scope_key: str,
	external_system: str,
	event_type: str,
	event_key: str,
	payload: dict,
	direction: str = Event.DirectionChoices.INBOUND,
	occurred_ts=None,
	caused_by_event=None,
) -> tuple[Event, bool]:
	return Event.objects.get_or_create(
		scope_key=scope_key,
		direction=direction,
		external_system=external_system,
		event_key=event_key,
		defaults={
			'event_type': event_type,
			'payload': payload,
			'occurred_ts': occurred_ts,
			'caused_by_event': caused_by_event,
		},
	)
```

Callers must provide the full identity. Do not guess scope from a display name, use an `exists()` check as the duplicate guard, or create a second event identity concept in a provider app.

### Let The Provider App Own Private Delivery Data And Queueing

```python
from django.db import transaction


def record_and_queue_webhook(connection, contract, raw_payload):
	with transaction.atomic():
		event, created = record_event(
			scope_key=f'provider:{connection.id}',
			external_system='provider',
			event_type=contract.event_type,
			event_key=contract.event_id,
			payload={
				'provider_event_type': contract.event_type,
				'object_id': contract.object_id,
			},
		)
		if created:
			ProviderWebhookDelivery.objects.create(
				event=event,
				connection=connection,
				payload=raw_payload,
			)

	if not created:
		return event, None, False

	task = Task.create_task(
		Task.TaskNameChoices.PROCESS_PROVIDER_EVENT,
		data={'event_id': event.id},
	)
	return event, task, True
```

The webhook endpoint verifies the signature over the exact raw body, validates the provider envelope, calls this service, and returns promptly. It does not make provider API calls or mutate domain projections inline.

The event and encrypted delivery record commit before task creation. If the project enqueues directly to a broker rather than creating a model-backed task, register the enqueue call with `transaction.on_commit(...)`.

### Keep Provider Dispatch Explicit

```python
from functools import wraps

from sync.dispatch import SyncDispatch
from sync.exceptions import EventFailure, EventRetry, EventSkipped

dispatch = SyncDispatch()


def provider_event(event_type: str, direction=Event.DirectionChoices.INBOUND):
	def register(handler):
		@wraps(handler)
		def handle(event, task):
			try:
				return handler(event, task)
			except (EventFailure, EventRetry, EventSkipped):
				raise
			except ProviderRateLimitError as error:
				raise EventRetry(str(error)) from error
			except (ProviderAuthenticationError, ProviderValidationError) as error:
				raise EventFailure(str(error)) from error

		return dispatch.event('provider', event_type, direction=direction)(handle)

	return register


@provider_event('record.updated')
def synchronize_record(event, task):
	delivery = event.provider_webhook_delivery
	provider_record = provider_client.records.get(delivery.payload['data']['record_id'])
	projection = project_provider_record(provider_record)
	return {'projection_id': projection.id}


@provider_event('record.create', direction=Event.DirectionChoices.OUTBOUND)
def create_record(event, task):
	local_record = LocalRecord.objects.get(id=event.payload['record_id'])
	provider_record = provider_client.records.create(build_create_request(local_record))
	projection = project_provider_record(provider_record)
	return {'projection_id': projection.id, 'provider_record_id': provider_record.id}
```

The dispatch module is an ordinary imported module. It registers supported provider event types and translates provider failures into generic processing outcomes. Unknown event types should fail or skip explicitly according to product policy; they should not fall through to a guessed handler.

### Keep The Background Task Thin

```python
def process_provider_event(task):
	task.set_message_and_percent('Processing provider event.', 25)
	event = process_event(task.data['event_id'], task, dispatch)
	if event is None:
		task.set_message_and_percent('Provider event was already processed.', 100)
		return

	task.set_message_and_percent(f'Provider event finished with status {event.status}.', 100)
```

The task supplies lifecycle and operator progress. The generic sync processor claims the event and invokes one provider handler. The provider handler owns external I/O and projection logic.

### Reconcile Through The Same Projection Service

```python
def reconcile_active_records(connection):
	for local_record in get_active_provider_records(connection):
		event, created = record_event(
			scope_key=f'provider:{connection.id}',
			external_system='provider',
			event_type='record.reconcile',
			event_key=f'record:{local_record.id}:reconcile:{reconciliation_window()}',
			payload={'record_id': local_record.id},
		)
		if created:
			Task.create_task(
				Task.TaskNameChoices.PROCESS_PROVIDER_EVENT,
				data={'event_id': event.id},
			)
```

The reconciliation handler should read the authoritative provider resource and call the same `project_provider_record(...)` service used by webhook handlers. Do not implement separate webhook and reconciliation state machines.

### Test The Engine And Each Provider Boundary

```python
@pytest.mark.django_db
class TestProviderEventProcessing:
	def test_duplicate_delivery_reuses_the_event_and_does_not_queue_twice(self, connection, contract):
		first_event, first_task, first_created = record_and_queue_webhook(connection, contract, {'data': {}})
		second_event, second_task, second_created = record_and_queue_webhook(connection, contract, {'data': {}})

		assert first_created is True
		assert second_created is False
		assert second_event == first_event
		assert first_task is not None
		assert second_task is None

	def test_retryable_provider_error_schedules_retry(self, event, monkeypatch):
		def raise_rate_limit(record_id):
			raise ProviderRateLimitError('Try again later')

		monkeypatch.setattr(
			'provider.sync_dispatch.provider_client.records.get',
			raise_rate_limit,
		)

		process_event(event.id, None, dispatch)

		event.refresh_from_db()
		assert event.status == Event.StatusChoices.RETRY_SCHEDULED
		assert event.attempt_count == 1
		assert event.next_attempt_ts is not None

	def test_webhook_and_reconciliation_use_the_same_projection(self, event, monkeypatch):
		project_record = MagicMock()
		monkeypatch.setattr('provider.sync_dispatch.project_provider_record', project_record)

		process_event(event.id, None, dispatch)

		project_record.assert_called_once()
```

## Things To Notice

- The generic event identity includes provider scope, direction, system, and external event key.
- The provider app stores the private webhook body and relation context.
- The webhook path persists first and performs no provider reads inline.
- The dispatch module translates provider exceptions and registers only supported event families.
- The processor owns claiming, attempts, retry timing, and terminal status.
- Provider handlers fetch authoritative resources and call provider-owned projection services.
- Reconciliation reuses the same projection services as webhooks.
- The task layer reports progress without duplicating event processing.
- Settings are defined once in Django settings and read directly.
- Importable application packages contain production behavior, not tutorial modules.

## Rules To Follow

- Require the complete event identity at the recording boundary and enforce it with a database constraint.
- Record events and private delivery records in one transaction.
- Enqueue only after the recording transaction commits.
- Keep raw sensitive payloads out of the generic event and its normal serializers.
- Keep provider SDK imports and exception mapping out of the generic sync app.
- Register handlers explicitly in a provider dispatch module.
- Fetch authoritative provider resources before applying provider-owned clinical, financial, or fulfillment state.
- Reuse one projection service from webhook and reconciliation paths.
- Retry only failures that are actually transient or mutations with a safe idempotency contract.
- Mark unsupported and unknown events explicitly instead of silently ignoring them.
- Keep `__init__.py` files empty unless they provide a deliberate public import surface.
- Keep executable examples in tests and authored guidance, not production app modules.

## Refactor Signals

- A generic sync model imports a provider SDK or a provider domain model.
- A provider app defines another attempt counter or event status lifecycle beside the shared event.
- A webhook view calls the provider API or updates domain records before returning.
- Generic event payloads contain raw webhook bodies, secrets, protected health information, or signed documents.
- Deduplication uses `exists()` without a matching database constraint.
- Event IDs are treated as globally unique even though the provider scopes them per account or connection.
- Webhook handlers and reconciliation jobs apply the same resource through different mapping code.
- A dispatch module guesses a handler for unknown event types.
- A worker retries every exception, including authentication and validation failures.
- Retry configuration is duplicated in settings and a local defaults dictionary.
- A production package includes an `example.py`, demo handler, or tutorial registration side effect.

## Verification

Run focused tests for the generic engine and every provider dispatch boundary:

```bash
pytest backend/sync/tests
pytest backend/provider/tests/test_webhooks.py
pytest backend/provider/tests/test_sync_dispatch.py
pytest backend/provider/tests/test_reconciliation.py
ruff check backend/sync backend/provider
python manage.py makemigrations --check --dry-run
```

Cover at least:

- repeated delivery and concurrent identity claims
- inbound and outbound events sharing the same provider key
- successful, skipped, retryable, and terminal outcomes
- maximum attempts and stale processing recovery
- unknown event policy
- private payload separation
- task creation only for newly recorded events
- webhook and scheduled reconciliation convergence
- retry after ambiguous provider mutation results
- safe lower-privilege event serialization

For guidance changes, run the guidance builder and confirm the example appears in generated metadata.

## Why It Helps

- Every provider operation has one durable, operator-visible lifecycle.
- Duplicate deliveries and task retries do not duplicate domain effects.
- Provider integrations stay understandable because ownership and exception policy are explicit.
- Reconciliation repairs missed or out-of-order webhooks through the same code path.
- Sensitive provider data stays out of generic history surfaces.
- The generic engine remains small enough to reuse without dictating provider business logic.
