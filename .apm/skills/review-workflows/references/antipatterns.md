---
id: reference-antipatterns-overview
title: Antipatterns Overview
description: Cross-stack catalog of patterns that should not be reintroduced.
kind: reference
scope: global
name: antipatterns
tags:
  - reference
  - antipatterns
applies_to: []
status: active
order: 4
---

# Antipatterns Overview

## Purpose

- Capture recurring shapes that are intentionally discouraged.
- Pair each anti-pattern with a clearer replacement, not just a warning label.
- Keep framework-specific concrete examples in the relevant guidance skill's `references/examples/` directory.

## How To Use This Reference

- Use it as a checklist during refactors, code review, and guidance migration work.
- When you find a recurring anti-pattern in real code, add or update an example in the matching language or framework package.
- Prefer examples that show both the discouraged shape and the recommended replacement.

## Current Mapped Examples

- Django model metadata: `.apm/skills/django-patterns/references/examples/django-concrete-model-meta.md`
- Django domain profile separation: `.apm/skills/django-patterns/references/examples/django-domain-profile-vs-auth-user.md`
- Django lifecycle transitions: `.apm/skills/django-patterns/references/examples/django-transition-endpoint.md`
- Django shared-scope validation: `.apm/skills/django-patterns/references/examples/django-shared-scope-validation.md`
- Django model-owned lifecycle rules: `.apm/skills/django-patterns/references/examples/django-model.md`
- Django direct attribute access: `.apm/skills/django-patterns/references/examples/django-direct-attribute-access.md`

## Maintenance Rule

- Do not let this reference become a dumping ground for duplicate inline guidance.
- When a pattern becomes active day-to-day guidance, capture the rule in the relevant guidance file and keep this reference focused on the before-and-after catalog.
