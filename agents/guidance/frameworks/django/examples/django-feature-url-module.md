---
id: framework-django-example-feature-url-module
title: Django Feature URL Module Example
description: Example feature-local URL module with predictable REST-style and action routes.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - urls
applies_to:
  - django
status: active
order: 7
---

# Django Feature URL Module Example

## Scenario

- Use this pattern when one feature package owns its own views and should expose a focused `urls.py` beside those views.

## Recommended Shape

### Good Example

```python
from django.urls import path
from workflow.views.assignment import views

app_name = 'assignment'

urlpatterns = [
    path('list/', views.AssignmentListView.as_view(), name='assignment-list'),
    path('create/', views.AssignmentCreateView.as_view(), name='assignment-create'),
    path('<int:pk>/', views.AssignmentDetailView.as_view(), name='assignment-detail'),
    path('status-options/', views.AssignmentStatusOptionsListView.as_view(), name='assignment-status-options-list'),
    path('<int:pk>/history/', views.AssignmentHistoryListView.as_view(), name='assignment-history-list'),
    path('<int:pk>/transition/', views.AssignmentTransitionView.as_view(), name='assignment-transition'),
]
```

### Things To Notice

- Standard list, create, and detail routes stay easy to spot.
- Feature-specific endpoints such as `status-options/`, `<int:pk>/history/`, or `<int:pk>/transition/` live beside the CRUD routes they extend.
- Item-specific actions keep the object identifier in the path so route intent stays explicit.
- Route names stay predictable and app-local, which keeps `reverse(...)` usage clear in tests and views.

## Why It Helps

- Feature routing stays close to the views it serves.
- Larger apps can grow feature-by-feature without turning one root URL file into a giant flat list.
