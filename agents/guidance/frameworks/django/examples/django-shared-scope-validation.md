---
id: framework-django-example-shared-scope-validation
title: Shared Scope Validation
description: Validate related-object links at the serializer boundary so cross-scope combinations cannot be saved.
kind: example
scope: framework
name: django
tags:
  - django
  - serializers
  - antipatterns
applies_to:
  - django
status: active
order: 23
---

# Shared Scope Validation

## Avoid

```python
class AssignmentInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = ('project', 'task', 'owner')
```

## Prefer

```python
class AssignmentInputSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        attrs = super().validate(attrs)
        project = self.instance.project if self.instance else self.context['project']
        task = attrs.get('task')
        owner = attrs.get('owner')

        if task and task.project_id != project.id:
            raise serializers.ValidationError({'task': 'Task must belong to the selected project.'})

        if owner and owner.organization_id != project.organization_id:
            raise serializers.ValidationError({'owner': 'Owner must belong to the same organization as the project.'})

        return attrs
```

## Why

- Related records usually share a tenant, project, organization, or workflow boundary.
- Rejecting bad combinations early prevents mismatched links from leaking into downstream behavior.
- The serializer boundary is a clear place to enforce the relationship contract.
