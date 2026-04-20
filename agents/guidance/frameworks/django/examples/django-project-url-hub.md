---
id: framework-django-example-project-url-hub
title: Django Project URL Hub Example
description: Example project-root URL module that keeps only top-level site, admin, docs, and include hubs.
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
order: 4
---

# Django Project URL Hub Example

## Scenario

- Use this pattern when the project root should expose only a few top-level routes and delegate real API surface area to app or API hubs.

## Recommended Shape

### Good Example

```python
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from core import views

user_urlpatterns = [
    path('login/', views.LoginView.as_view(), name='user-login'),
    path('logout/', views.LogoutView.as_view(), name='user-logout'),
]

urlpatterns = [
    path('', views.index),
    path('admin/dev/', include('dev.urls')),
    path('admin/', admin.site.urls),
    path('api/user/', include(user_urlpatterns)),
    path('api/billing/', include('billing.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
```

### Things To Notice

- The project root keeps only index, admin, docs, and a few include boundaries.
- Larger route families are delegated immediately instead of being flattened into one long root file.
- Small related auth routes can be grouped locally when they do not justify a separate module yet.

## Why It Helps

- The top-level router stays easy to scan, and feature routing can grow without turning `core/urls.py` into a dumping ground.
