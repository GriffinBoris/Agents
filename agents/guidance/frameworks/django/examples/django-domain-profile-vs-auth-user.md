---
id: framework-django-example-domain-profile-vs-auth-user
title: Domain Profile Versus Auth User
description: Keep domain profiles separate from authentication users.
kind: example
scope: framework
name: django
tags:
  - django
  - models
  - antipatterns
applies_to:
  - django
status: active
order: 21
---

# Domain Profile Versus Auth User

## Avoid

```python
class Enrollment(models.Model):
    workflow = models.ForeignKey('Workflow', on_delete=models.DO_NOTHING)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING)
```

## Prefer

```python
class CustomerProfile(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.DO_NOTHING)
    email = models.EmailField()
    first_name = models.TextField()
    last_name = models.TextField()


class Enrollment(models.Model):
    workflow = models.ForeignKey('Workflow', on_delete=models.DO_NOTHING)
    customer = models.ForeignKey('CustomerProfile', on_delete=models.DO_NOTHING)
```

## Why

- Auth users represent credentials and sessions.
- Domain profiles represent business entities and their history.
- Separating them avoids conflating operators, staff, and customers.
