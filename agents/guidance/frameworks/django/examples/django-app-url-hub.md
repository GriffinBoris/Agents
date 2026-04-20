---
id: framework-django-example-app-url-hub
title: Django App URL Hub Example
description: Example app-root URL module that stays thin and delegates to feature URL packages.
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
order: 6
---

# Django App URL Hub Example

## Scenario

- Use this pattern when a Django app has enough API surface that each feature should own its own `urls.py` while the app root stays as a routing hub.

## Recommended Shape

### Good Example

```python
from django.urls import path
from django.urls.conf import include

app_name = 'inventory'

urlpatterns = [
    path('product/', include('inventory.views.product.urls')),
    path('warehouse/', include('inventory.views.warehouse.urls')),
    path('supplier/', include('inventory.views.supplier.urls')),
    path('purchase-order/', include('inventory.views.purchase_order.urls')),
    path('stock-adjustment/', include('inventory.views.stock_adjustment.urls')),
]
```

### Things To Notice

- The app-root URL file stays thin and mostly delegates prefixes to feature URL modules.
- Feature packages keep ownership of their detailed route lists.
- Prefixes remain stable entry points for API clients and `reverse(...)` namespacing.

## Why It Helps

- Routing stays organized by feature instead of becoming one long ungrouped file.
