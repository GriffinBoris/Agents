---
id: language-python-example-pytest-class-setup
title: Python Pytest Class Setup Example
description: Example shared setup and helper methods for readable pytest test classes.
kind: example
scope: language
name: python
tags:
  - example
  - python
  - pytest
applies_to:
  - python
status: active
order: 1
---

# Python Pytest Class Setup Example

## Scenario

- Use this pattern when a test class shares users, URLs, permissions, or payload builders across multiple tests.

## Recommended Shape

### Good Example

```python
@pytest.mark.django_db
class TestSchemaSettingsViews:
    def setup_method(self):
        self.user = TestFixtures.create_user()
        self.list_url = reverse('metadata:schemasettings:schemasettings-list')
        self.create_url = reverse('metadata:schemasettings:schemasettings-create')
        self.permission_view = Permission.objects.get(codename=SchemaSettings.get_view_permission(ignore_app_label=True))

    def _grant_permissions(self, *permissions):
        if not permissions:
            permissions = (self.permission_view,)

        self.user.user_permissions.add(*permissions)

    def _payload(self, schema_name='SCHEMA_ONE', setting_name='setting_one', setting_value='value_one'):
        return {
            'schema_name': schema_name,
            'setting_name': setting_name,
            'setting_value': setting_value,
        }
```

### Things To Notice

- `setup_method` collects shared state once instead of rebuilding it in every test.
- Small helper methods keep permission setup and payload creation explicit.
- Test bodies can stay focused on the behavior under test.

## Why It Helps

- Repeated setup becomes consistent without hiding intent behind a fixture maze.
