---
id: framework-django-example-shared-test-fixtures
title: Django Shared Test Fixtures Example
description: Example shared object builders that keep API tests explicit without repeating setup in each module.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - testing
applies_to:
  - django
status: active
order: 17
---

# Django Shared Test Fixtures Example

## Scenario

- Use this pattern when many Django tests need the same users, tenants, or domain objects.

## Recommended Shape

### Good Example

```python
class TestFixtures:
    @staticmethod
    def create_user():
        return User.objects.create_user(
            username=random_string(),
            email=f'{random_string()}@notreal.fake',
            password='password',
        )

    @staticmethod
    def create_company():
        return Company.objects.create(
            name=random_string(),
            address_one=random_string(),
            city=random_string(),
            state=random_string(),
            zip_code=random_string(),
            phone=random_string(),
        )

    @staticmethod
    def create_service(company):
        return Service.objects.create(
            name=random_string(),
            description=random_string(),
            price=random.uniform(1, 1000),
            company=company,
        )
```

```python
@pytest.mark.django_db
class TestServiceListView:
    def setup_method(self):
        self.user = TestFixtures.create_user()
        self.company = TestFixtures.create_company()
        self.service = TestFixtures.create_service(self.company)
        self.url = reverse('service-list')
```

### Things To Notice

- Shared builders live in one reusable module, usually `core/test_fixtures.py` or an equivalent shared helper.
- Builder signatures stay explicit instead of hiding everything behind `**kwargs`.
- Tests still keep per-case setup local, readable, and close to the assertions they support.

## Why It Helps

- Repeated setup becomes consistent without turning every feature test into its own factory island.
