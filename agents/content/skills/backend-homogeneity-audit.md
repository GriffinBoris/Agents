---
kind: skill
name: backend-homogeneity-audit
description: >
  Find and compare backend patterns such as views, serializers, services, URLs,
  app layout, and tests so new work matches established Django and Python conventions.
---

# Backend Homogeneity Audit

## When to use
- Adding or reviewing Django views, serializers, URLs, services, management commands, or tasks
- Checking whether a backend change matches existing repository patterns
- Looking for reusable backend structure before creating something new

## Boundary
- Use this as the backend pattern-matching audit for Django and Python code.
- Pair it with `architecture-audit` when file, folder, or code structure also needs review.
- Use `full-review` for the final comprehensive scoped review workflow.

## Read first
- `agents/guidance/guidance.md`
- `agents/guidance/languages/python/guidance.md`
- `agents/guidance/frameworks/django/guidance.md`
- `agents/guidance/project/guidance.md`
- relevant docs in `agents/guidance/languages/python/examples/`
- relevant docs in `agents/guidance/frameworks/django/examples/`

## Where to look
- `backend/*/views/**/*.py`
- `backend/api/**/*.py`
- `backend/*/urls.py`
- `backend/*/services/`
- `backend/*/management/commands/`
- `backend/*/tests/`
- `backend/core/test_fixtures.py`

## What to compare

### App structure
- flat app files versus `models/`, `views/`, or `api/` packages
- thin project-root and app-root URL hubs
- colocated feature packages for transport code when the surface is large enough

### Views and APIs
- base view inheritance and helper usage
- queryset scoping and ownership checks
- request validation order
- response serialization through output serializers

### Serializers
- input versus output serializer split
- field ordering and completeness
- scope validation and custom persistence patterns

### Services and tasks
- third-party integrations behind small service modules or adapters
- task model and Celery wiring patterns
- class-based stateful services when multiple methods share one subject or client

### Tests
- shared fixture builder usage
- permission setup through model permission helpers
- serializer output comparisons and ownership-boundary coverage

## Output
- preferred reference files and why they are the right pattern
- deviations found and the simplest fixes
- every verifiable in-scope guidance deviation, or an explicit statement that none were found
- blind spots and unverified areas

## Living document note
- If you find a durable backend pattern missing from the modular guidance tree, update the authored docs under `agents/guidance/` or add a named example.
