---
id: framework-django-example-request-context-middleware
title: Django Request Context Middleware Example
description: Example middleware that attaches a domain-scoped request context for reuse across views and serializers.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - middleware
applies_to:
  - django
status: active
order: 13
---

# Django Request Context Middleware Example

## Scenario

- Use this pattern when authenticated views repeatedly need the same domain context, such as the current employee or member.

## Recommended Shape

### Good Example

```python
from django.utils.functional import SimpleLazyObject

from party.models import Employee


def get_employee(request):
    try:
        if request.user.is_authenticated and request.user.id:
            return Employee.objects.get(user_id=request.user.id)
    except Employee.DoesNotExist:
        return None


class EmployeeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.employee = SimpleLazyObject(lambda: get_employee(request))
        return self.get_response(request)
```

```python
class CustomerListView(ProjectBaseAPIView):
    def get(self, request):
        queryset = Customer.objects.filter(company=request.employee.company).order_by('id')
        serializer = CustomerOutputSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
```

### Things To Notice

- Middleware resolves the repeated context once and makes it part of the request contract.
- Views scope queries through that shared boundary instead of re-looking up the same employee or member in every action.
- The context stays explicit enough that ownership rules remain easy to audit.

## Why It Helps

- Reusing one request-scoped context reduces duplication and makes tenant or company scoping harder to forget.
