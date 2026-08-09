---
name: backend-homogeneity-audit
description: Use when adding or reviewing Django backend code and comparing views, serializers, services, URLs, app layout, or tests to established patterns.
---

# Backend Homogeneity Audit

## Scope

- Adding or reviewing Django views, serializers, URLs, services, management commands, or tasks
- Checking whether a backend change matches existing repository patterns
- Looking for reusable backend structure before creating something new

### Boundaries

- Use this as the backend pattern-matching audit for Django and Python code.
- Pair it with `architecture-audit` when file, folder, or code structure also needs review.
- Use `full-review` for the final comprehensive scoped review workflow.

## Workflow

1. State the exact backend scope and any blind spots.
2. Load the applicable baseline, Python, Django, project, and example guidance.
3. Inspect the closest comparable backend modules before judging the change.
4. Compare every relevant concern below and record each verifiable deviation.
5. Report the preferred patterns, simplest fixes, or explicitly state that no deviations were found.

## Reference Selection

- [Engineering baseline](../../instructions/engineering-baseline.instructions.md)
- [Python conventions](../python-conventions/SKILL.md)
- [Django patterns](../django-patterns/SKILL.md)
- the consumer-owned `project-architecture` skill
- relevant docs in `.apm/skills/python-conventions/references/examples/`
- relevant docs in `.apm/skills/django-patterns/references/examples/`

## Review Criteria

### Inspection Targets

- `backend/*/views/**/*.py`
- `backend/api/**/*.py`
- `backend/*/urls.py`
- `backend/*/services/`
- `backend/*/management/commands/`
- `backend/*/tests/`
- `backend/core/test_fixtures.py`

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

## Completion Checklist

- If you find a durable backend pattern missing from the guidance skills, update the relevant `.apm/skills/` source or add a named example under its `references/examples/` directory.
