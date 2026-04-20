---
id: framework-django-example-view-tests
title: Django View Tests Example
description: Example permission-aware API tests using reverse and serializer-backed expectations.
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
order: 15
---

# Django View Tests Example

## Scenario

- Use this shape when testing list, create, update, or delete API views.

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
        self.permission_add = Permission.objects.get(codename=SchemaSettings.get_add_permission(ignore_app_label=True))
        self.permission_change = Permission.objects.get(codename=SchemaSettings.get_change_permission(ignore_app_label=True))
        self.permission_delete = Permission.objects.get(codename=SchemaSettings.get_delete_permission(ignore_app_label=True))

    def _grant_permissions(self, *permissions):
        if not permissions:
            permissions = (self.permission_view,)

        self.user.user_permissions.add(*permissions)

    def test_list_requires_permission(self, client):
        client.force_login(self.user)

        response = client.get(self.list_url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_returns_all_records(self, client):
        self._grant_permissions(self.permission_view)
        client.force_login(self.user)

        response = client.get(self.list_url)

        assert response.status_code == status.HTTP_200_OK
        expected = SchemaSettingsOutputSerializer(
            SchemaSettings.objects.order_by('schema_name', 'setting_name'),
            many=True,
        ).data
        assert response.json() == expected
```

### Things To Notice

- URLs come from `reverse(...)`, not hard-coded strings.
- Permission setup is explicit and reusable.
- Successful responses are compared against the same output serializer the view uses.
- Validation errors should assert the standardized payload shape.

## Why It Helps

- These tests stay aligned with the live serializer shape and permission model.
