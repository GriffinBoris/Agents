# Django Integrations And Idempotency

## Contents

- Services and shared helpers
- External event idempotency

## Services And Shared Helpers

- Centralize session-refresh or retry logic inside one service helper instead of repeating reconnect logic at each call site.
- Prefer small service classes when multiple operations share the same client or identity context, but do not cache plain Django settings in `__init__` just to avoid repeated `settings.<VAR>` reads.
- Extract repeated setup or teardown only after multiple call sites clearly share the same boilerplate.
- When a backend workflow naturally breaks into stages, prefer responsibility-based module names such as `adapters/`, `extractors/`, `loaders/`, or `transforms/` instead of generic `utils.py` buckets.
- Avoid near-duplicate views; if two routes need the same behavior, point them at the same view class.
- Prefer normal `.objects` manager access over `_base_manager` unless lower-level behavior is truly required.
- Avoid regex queries when exact equality or `__in` filters express the rule more clearly.
- Read configuration directly from `settings.<VAR>` unless local caching materially improves readability.

## External Event Idempotency

- Treat webhook event IDs and provider object IDs as database invariants, not application-level hints. Back each claimed identifier with a unique constraint at the provider's documented scope, using an account-qualified composite constraint when the identifier is not globally unique.
- Do not use an `exists()`-then-create check as the only duplicate guard. Concurrent deliveries can both pass the check; claim the event inside `transaction.atomic()` and treat the unique-constraint conflict as the duplicate path. Catch `IntegrityError` outside the atomic block that attempted the insert, or use an inner savepoint when a larger transaction must continue.
- For database-only handlers, keep the event claim and its domain writes in the same transaction so a failed handler does not permanently consume the event. When processing includes external I/O, avoid holding a database transaction open; persist an explicit processing state and define retry or stale-claim recovery semantics instead.
- Protect the domain effect as well as the delivery ledger. When a provider payment, refund, shipment, or similar object has its own stable external ID, enforce uniqueness at the documented provider scope on that domain record so different deliveries cannot apply the same effect twice.
- Lock mutable aggregate or lifecycle rows with `select_for_update()` before calculating and writing balances, totals, or status transitions that concurrent events can change.
- Test repeated delivery, duplicate provider-object IDs, handler failure followed by retry, and stale-instance updates. Use the production database engine for true concurrency tests when backend locking behavior is part of the contract.
