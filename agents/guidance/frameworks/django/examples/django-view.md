---
id: framework-django-example-crud-view
title: Django CRUD View Example
description: Example DRF list, create, and detail/update views with scoped querysets and serializer-driven responses.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - view
applies_to:
  - django
status: active
order: 2
---

# Django CRUD View Example

## Scenario

- Use these shapes when building standard DRF list, create, and detail/update views in an app that already has shared base API views and membership checks.

## Recommended Shape

### Scoped List Pattern

```python
class AlertListView(ProjectBaseAPIView):
    def get(self, request):
        queryset = Alert.objects.filter(user=request.user).order_by('id')
        serializer = AlertOutputSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
```

### Filtered List Pattern

```python
class ExampleListView(ProjectMemberAuthenticatedAPIView):
    def get(self, request, community_id: int):
        self.check_has_permission(ExampleModel.get_view_permission(include_app_name=True))
        request.member.check_has_community(community_id, raise_permission_error=True)

        queryset = ExampleModel.objects.filter(community_id=community_id)

        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)

        if not request.member.check_is_community_staff():
            queryset = queryset.filter(owner=request.member)

        queryset = queryset.order_by('id').distinct()
        serializer = ExampleOutputSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
```

### Create And Detail Pattern

```python
class ExampleCreateView(ProjectMemberAuthenticatedAPIView):
    def post(self, request, community_id: int):
        self.check_has_permission(ExampleModel.get_add_permission(include_app_name=True))
        request.member.check_has_community(community_id, raise_permission_error=True)
        request.member.check_is_community_staff(raise_permission_error=True)

        edited_data = {'community': community_id}
        edited_data.update(request.data)

        serializer = ExampleInputSerializer(data=edited_data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(community_id=community_id)
        return Response(ExampleOutputSerializer(instance).data, status=status.HTTP_201_CREATED)


class ExampleDetailView(ProjectMemberAuthenticatedAPIView):
    def put(self, request, community_id: int, pk: int):
        self.check_has_permission(ExampleModel.get_change_permission(include_app_name=True))
        request.member.check_has_community(community_id, raise_permission_error=True)
        request.member.check_is_community_staff(raise_permission_error=True)

        instance = get_object_or_404(ExampleModel, pk=pk, community_id=community_id)
        serializer = ExampleInputSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(ExampleOutputSerializer(instance).data, status=status.HTTP_200_OK)
```

### Things To Notice

- Authenticated list views scope data at the queryset level.
- Context and permission checks happen before business logic.
- `edited_data` protects server-controlled fields during create flows.
- Mutating endpoints return the serialized resource instead of an empty success payload.
- Keep these view classes in a `views.py` module inside the feature package instead of placing them in the package `__init__.py`.

## Why It Helps

- These patterns keep views deterministic, scoped, and structurally consistent across apps.
