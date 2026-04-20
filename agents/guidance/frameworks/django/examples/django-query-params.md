---
id: framework-django-example-query-params
title: Django Query Param Parsing Example
description: Example direct query param parsing with optional filters and shared validator helpers.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - query-params
applies_to:
  - django
status: active
order: 8
---

# Django Query Param Parsing Example

## Scenario

- Use this pattern when a DRF view needs a few filters or numeric query params without heavy parsing machinery.

## Recommended Shape

### Good Example

```python
page = int(request.query_params.get('page', 1))
page_size = int(request.query_params.get('page_size', 10))

account_id = request.query_params.get('account_id')
if account_id:
    queryset = queryset.filter(account_id=account_id)

schedule_ids = None
if 'schedule_ids' in request.query_params:
    schedule_ids = [int(x.strip()) for x in request.query_params['schedule_ids'].split(',') if x.strip()]

days = BlankableIntegerField().to_internal_value(request.query_params.get('days', 7))
```

### Things To Notice

- Simple direct conversion is the default for trusted internal APIs.
- Optional filters stay as short guard clauses.
- Shared DRF field converters are the escape hatch when you need a standardized validation response.
- Business query params stay snake_case, and reserved renderer keys such as `format` should not be repurposed for feature behavior.

## Why It Helps

- This keeps views easy to scan and avoids repetitive try or except wrappers.
