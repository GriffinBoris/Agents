---
id: framework-django-example-app-layout
title: Django App Layout Example
description: Example small-app and larger-api layout shapes for Django repositories.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - structure
applies_to:
  - django
status: active
order: 5
---

# Django App Layout Example

## Scenario

- Use these fake file structures when deciding whether an app can stay flat or should split models, transport code, and feature packages more aggressively.

## Recommended Shape

### App With One Main Model And Feature Views

```text
thing/
├── __init__.py
├── admin.py
├── apps.py
├── migrations/
│   └── ...
├── models.py
├── urls.py
├── views/
│   └── some_specific_view_set/
│       ├── __init__.py
│       ├── serializers.py
│       ├── urls.py
│       ├── views.py
│       └── tests/
│           ├── test_serializers.py
│           └── test_views.py
└── tests/
    └── test_models.py
```

### App With Multiple Models

```text
thing/
├── __init__.py
├── admin.py
├── apps.py
├── migrations/
│   └── ...
├── models/
│   ├── __init__.py
│   ├── thing_model.py
│   └── other_model.py
├── urls.py
├── views/
│   ├── some_specific_view_set/
│   │   ├── __init__.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── tests/
│   │       ├── test_serializers.py
│   │       └── test_views.py
│   └── another_feature/
│       ├── __init__.py
│       ├── serializers.py
│       ├── urls.py
│       ├── views.py
│       └── tests/
│           ├── test_serializers.py
│           └── test_views.py
└── tests/
    └── test_models.py
```

### Things To Notice

- Start with `models.py` when the app only has one or a few closely related models.
- Move to a `models/` package when model count or model size makes one file harder to scan.
- Keep app-root `urls.py` thin and use it as the include hub for feature-local URL modules under `views/`.
- Keep feature-specific transport code together with `views.py`, `serializers.py`, `urls.py`, and feature-local tests.
- Keep view classes and view functions in `views.py`, not in package `__init__.py` files.
- Keep feature-package `__init__.py` files minimal or empty unless they are needed for explicit exports.
- Keep app-wide model tests in the app-level `tests/` folder so model behavior stays easy to find.
- Each layout keeps related concerns together and avoids a single flat module that mixes unrelated view, serializer, and model responsibilities.

## Why It Helps

- Teams can scale an app from a simple `models.py` layout to feature-foldered views and a `models/` package without changing the core app boundary.
