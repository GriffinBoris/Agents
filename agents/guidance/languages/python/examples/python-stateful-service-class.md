---
id: language-python-example-stateful-service-class
title: Python Stateful Service Class Example
description: Example class that stores shared dependencies and workflow state instead of scattering related functions.
kind: example
scope: language
name: python
tags:
  - example
  - python
  - classes
applies_to:
  - python
status: active
order: 4
---

# Python Stateful Service Class Example

## Scenario

- Use this pattern when several methods operate on the same record and external client, and the workflow is easier to read as one stateful object than as disconnected free functions.

## Recommended Shape

### Good Example

```python
class InvoiceSyncService:
    def __init__(self, api_client: BillingApiClient, invoice: Invoice):
        self.api_client = api_client
        self.invoice = invoice

    def sync(self) -> Invoice:
        remote_invoice = self._fetch_remote_invoice()
        self._apply_remote_fields(remote_invoice)
        self.invoice.save()
        return self.invoice

    def _fetch_remote_invoice(self) -> dict:
        if not self.invoice.external_id:
            raise ValueError('Invoice must have an external_id before syncing')

        return self.api_client.get_invoice(self.invoice.external_id)

    def _apply_remote_fields(self, remote_invoice: dict):
        self.invoice.external_status = remote_invoice['status']
        self.invoice.amount = remote_invoice['amount']
        self.invoice.paid_ts = remote_invoice['paid_ts']
```

### Context Manager Variant

```python
class TempExportWriter:
    def __init__(self, export_directory: Path, filename: str):
        self.export_directory = export_directory
        self.filename = filename
        self.file_path = export_directory / filename

    def __enter__(self):
        self.export_directory.mkdir(parents=True, exist_ok=True)
        return self.file_path

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file_path.exists():
            self.file_path.unlink()
```

### Things To Notice

- The class stores shared dependencies once in `__init__`.
- The public method is a clear verb, and the private helpers split the workflow into readable steps.
- Method signatures stay small because the shared state lives on `self`.
- The context-manager variant is appropriate only because the class owns a resource that needs cleanup.

## Why It Helps

- Related behavior stays together, shared state is explicit, and the code avoids turning one workflow into a pile of loosely related helper functions.
