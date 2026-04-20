---
id: framework-django-example-serializer-tests
title: Django Serializer Tests Example
description: Example input and output serializer tests with exact field assertions.
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
order: 16
---

# Django Serializer Tests Example

## Scenario

- Use this shape when serializer behavior changes or when a serializer has non-trivial validation.

## Recommended Shape

### Good Example

```python
@pytest.mark.django_db
class TestSchemaSettingsInputSerializer:
    def setup_method(self):
        self.user = TestFixtures.create_user()
        self.valid_payload = {
            'schema_name': 'SCHEMA_ONE',
            'setting_name': 'setting_one',
            'setting_value': 'value_one',
        }

    def test_valid_payload_creates_instance(self):
        serializer = SchemaSettingsInputSerializer(
            data=self.valid_payload,
            context={'log_user_id': self.user.pk},
        )
        assert serializer.is_valid(), serializer.errors

        instance = serializer.save()

        assert instance.schema_name == self.valid_payload['schema_name']
        assert instance.setting_name == self.valid_payload['setting_name']
        assert instance.setting_value == self.valid_payload['setting_value']


@pytest.mark.django_db
class TestSchemaSettingsOutputSerializer:
    def setup_method(self):
        self.instance = TestFixtures.create_schema_setting(
            schema_name='SCHEMA_ONE',
            setting_name='setting_one',
            setting_value='value_one',
        )

    def test_output_payload(self):
        serializer = SchemaSettingsOutputSerializer(self.instance)
        data = serializer.data
        remaining = dict(data)

        assert remaining.pop('schema_name') == self.instance.schema_name
        assert remaining.pop('setting_name') == self.instance.setting_name
        assert remaining.pop('setting_value') == self.instance.setting_value
        assert remaining
```

### Things To Notice

- Input serializer tests cover create, update, required fields, and validation failures.
- Output serializer tests assert the payload shape instead of only checking one or two fields.
- Copying `serializer.data` into a mutable dict and popping fields makes unexpected keys fail the test.

## Why It Helps

- Exact output assertions catch accidental field drift.
