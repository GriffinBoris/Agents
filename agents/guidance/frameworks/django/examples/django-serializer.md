---
id: framework-django-example-serializer
title: Django Serializer Example
description: Example serializer patterns for input/output splits, related fields, and validation.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - serializer
applies_to:
  - django
status: active
order: 3
---

# Django Serializer Example

## Scenario

- Use this pattern when a model needs a write serializer and a read serializer with related labels, computed fields, or custom validation.

## Recommended Shape

### Good Example

```python
from rest_framework import serializers

from example.models import ExampleModel


class ExampleInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExampleModel
        fields = (
            'id',
            'community',
            'name',
            'status',
            'assigned_member',
        )
        read_only_fields = ('id',)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        community = attrs.get('community') or self.instance.community
        assigned_member = attrs.get('assigned_member')

        if assigned_member and assigned_member.community_id != community.id:
            raise serializers.ValidationError({'assigned_member': 'Member must belong to the selected community.'})

        return attrs


class ExampleOutputSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    community_name = serializers.CharField(source='community.name', read_only=True)
    assigned_member_name = serializers.SerializerMethodField()

    class Meta:
        model = ExampleModel
        fields = (
            'id',
            'community',
            'community_name',
            'name',
            'status',
            'status_display',
            'assigned_member',
            'assigned_member_name',
            'created_ts',
            'updated_ts',
        )
        read_only_fields = fields

    def get_assigned_member_name(self, obj):
        if obj.assigned_member and obj.assigned_member.user:
            user = obj.assigned_member.user
            return f'{user.first_name} {user.last_name}'.strip() or user.username
        return None
```

### Things To Notice

- The input serializer owns cross-field validation for related records.
- The output serializer exposes related labels through `source` and `SerializerMethodField`.
- `id` stays first in the field tuple.
- The output serializer marks every field read-only.

## Why It Helps

- Splitting read and write concerns keeps validation, persistence, and response shaping easy to reason about.
