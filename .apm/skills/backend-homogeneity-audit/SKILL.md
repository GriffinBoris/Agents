---
name: backend-homogeneity-audit
description: Audit Django and Python backend code against established app, view, serializer, service, URL, task, and test patterns. Use when explicitly reviewing or comparing backend consistency; do not trigger for ordinary implementation that only needs Python or Django guidance.
---

# Backend Homogeneity Audit

## Scope

- Compare Django and Python backend code with the closest established repository patterns.

### Boundaries

- Use this as the backend pattern-matching audit for Django and Python code.
- Pair it with `architecture-audit` when file, folder, or code structure also needs review.
- Follow the shared review contract in [review-workflows](../review-workflows/SKILL.md); the criteria and output below are additions specific to backend consistency.

## Workflow

1. Apply the shared review workflow.
2. Load the Python and Django guidance and only the examples matching the backend concerns in scope.
3. Inspect the closest comparable backend modules and apply every relevant criterion below.

## Reference Selection

- [Python conventions](../python-conventions/SKILL.md)
- [Django patterns](../django-patterns/SKILL.md)
- relevant docs in `.apm/skills/python-conventions/references/examples/`
- relevant docs in `.apm/skills/django-patterns/references/examples/`

## Review Criteria

### Inspection Targets

- the repository's configured backend root and Django apps
- view, API, serializer, and URL modules in their established locations
- service modules and management commands
- feature tests and the repository's shared fixture builders

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

In addition to the shared review output, include:

- preferred reference files and why they are the right pattern
- reusable backend structures found in the existing repository

## Completion Checklist

- The closest comparable backend implementation was reviewed.
- Every applicable app, API, serializer, service, task, and test concern above was evaluated.
