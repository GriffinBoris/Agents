---
id: framework-django-example-serializer
title: Django Serializer Example
description: Example input/output serializer split with context-owned scope, related-object validation, lifecycle-action protection, and exact output shape.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - serializer
  - validation
  - organization-scope
applies_to:
  - django
status: active
order: 3
---

# Django Serializer Example

## Scenario

- Use this pattern when a Django model needs separate write and read contracts.
- Use this pattern when serializer behavior depends on a route-scoped object such as an organization, workspace, catalog_entry, contact, or order.
- Use this pattern when incoming identifiers must be validated against the same organization or workspace boundary before saving.
- Use this pattern when some changes must go through dedicated action endpoints instead of generic updates.

## Why This Shape Exists

- Input serializers validate what the client may submit. Output serializers describe what the API returns.
- Route-owned scope must come from the view context, not from client-submitted payload fields.
- Related records often share organization, workspace, contact, catalog_entry, or order boundaries. Those cross-links should be rejected before persistence.
- Lifecycle fields such as `status`, `is_active`, or state-machine transitions often need dedicated action views so the business rule, audit behavior, and permission check stay explicit.
- Output serializers should be deterministic contracts that frontend types and tests can trust.

## Recommended Shape

### Input Serializer With Context-Owned Scope

```python
from workspace.models import WorkspaceMembership
from core.user_lookup import get_single_user_by_case_insensitive_email
from rest_framework import serializers
from tenancy.models import OrganizationMembership


class WorkspaceMembershipInputSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True, required=False)

    class Meta:
        model = WorkspaceMembership
        fields = (
            'id',
            'email',
            'role',
            'is_active',
        )
        read_only_fields = ('id',)

    def validate_email(self, value):
        user = get_single_user_by_case_insensitive_email(
            value,
            'Multiple users already use this email address. Resolve the duplicate accounts before managing workspace memberships.',
        )
        if user is None:
            raise serializers.ValidationError('User does not exist.')

        workspace = self.context['workspace']
        if not OrganizationMembership.objects.filter(user=user, organization=workspace.organization, is_active=True).exists():
            raise serializers.ValidationError('User must belong to the organization before joining a workspace.')

        if self.instance is None and WorkspaceMembership.objects.filter(user=user, workspace=workspace).exists():
            raise serializers.ValidationError('A membership for this user already exists in the workspace.')

        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)

        if self.instance and 'is_active' in attrs:
            raise serializers.ValidationError({'is_active': 'Use the membership activate or deactivate action to change membership state.'})

        if self.instance is None and 'email' not in attrs:
            raise serializers.ValidationError({'email': 'This field is required.'})

        return attrs

    def create(self, validated_data):
        email = validated_data.pop('email')
        user = get_single_user_by_case_insensitive_email(
            email,
            'Multiple users already use this email address. Resolve the duplicate accounts before managing workspace memberships.',
        )
        return WorkspaceMembership.objects.create(
            workspace=self.context['workspace'],
            user=user,
            **validated_data,
        )
```

The view passes `workspace` through serializer context after resolving the route scope. The client submits an email and role, but never gets to choose the workspace or organization through the payload. The serializer validates the target user against the route-owned workspace's organization before creating the membership.

### Thin View Passing Enforced Context

```python
class WorkspaceMembershipCreateView(AuthenticatedAccessAPIView):
    def post(self, request, organization_id: int, workspace_id: int):
        organization, workspace = self.resolve_workspace_scope(request, organization_id, workspace_id)
        self.require_permission(request, AppPermission.permission(AppPermissionChoices.WORKSPACE_MANAGE), workspace=workspace)

        serializer = WorkspaceMembershipInputSerializer(
            data=request.data,
            context={'request': request, 'workspace': workspace},
        )
        serializer.is_valid(raise_exception=True)
        membership = serializer.save()
        return Response(WorkspaceMembershipOutputSerializer(membership).data, status=status.HTTP_201_CREATED)
```

Views should resolve scope and permissions first, then pass the resolved object into serializer context. Avoid trusting a payload field such as `workspace`, `organization`, or `contact` when the route already owns that identity.

### Output Serializer With Exact Read Contract

```python
class WorkspaceMembershipOutputSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)

    class Meta:
        model = WorkspaceMembership
        fields = (
            'id',
            'workspace',
            'email',
            'first_name',
            'last_name',
            'role',
            'is_active',
            'created_ts',
            'updated_ts',
        )
        read_only_fields = fields
```

Output serializers should normally mark every field read-only. They may expose related labels or user-facing related data through `source`, nested serializers, or `SerializerMethodField`, but they should still keep the output shape explicit.

### Output Serializer With Context-Derived Data

```python
class WorkspaceOutputSerializer(serializers.ModelSerializer):
    membership_role = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = (
            'id',
            'organization',
            'name',
            'slug',
            'status',
            'contact_name',
            'contact_email',
            'support_phone',
            'membership_role',
            'created_ts',
            'updated_ts',
        )
        read_only_fields = fields

    def get_membership_role(self, obj):
        membership_by_workspace_id = self.context.get('membership_by_workspace_id', {})
        membership = membership_by_workspace_id.get(obj.id)
        if membership:
            return membership.role

        return None
```

Use context-derived lookup maps when output depends on the current user's relationship to each object. Build those maps once in the view or shared access context rather than querying inside `get_<field>()` for every row.

### Related Scope Validation

```python
class ApprovedPlanInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovedItemPlan
        fields = (
            'id',
            'contact',
            'catalog_entry',
            'item',
            'variant',
            'pricing_plan',
        )
        read_only_fields = ('id',)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        workspace = self.context['workspace']

        if self.instance:
            contact = self.instance.contact
            catalog_entry = self.instance.catalog_entry
            item = self.instance.item
            variant = self.instance.variant
            pricing_plan = self.instance.pricing_plan
        else:
            contact = attrs['contact']
            catalog_entry = attrs['catalog_entry']
            item = attrs['item']
            variant = attrs.get('variant')
            pricing_plan = attrs.get('pricing_plan')

        if 'contact' in attrs:
            contact = attrs['contact']
        if 'catalog_entry' in attrs:
            catalog_entry = attrs['catalog_entry']
        if 'item' in attrs:
            item = attrs['item']
        if 'variant' in attrs:
            variant = attrs['variant']
        if 'pricing_plan' in attrs:
            pricing_plan = attrs['pricing_plan']

        if contact.workspace_id != workspace.id:
            raise serializers.ValidationError({'contact': 'Contact must belong to the selected workspace.'})

        if catalog_entry.workspace_id != workspace.id:
            raise serializers.ValidationError({'catalog_entry': 'CatalogEntry must belong to the selected workspace.'})

        if item.catalog_entry_id != catalog_entry.id:
            raise serializers.ValidationError({'item': 'Item must belong to the selected catalog_entry.'})

        if variant and variant.item_id != item.id:
            raise serializers.ValidationError({'variant': 'Variant must belong to the selected item.'})

        if pricing_plan and pricing_plan.catalog_entry_id != catalog_entry.id:
            raise serializers.ValidationError({'pricing_plan': 'Pricing plan must belong to the selected catalog_entry.'})

        return attrs
```

Validate cross-links where the submitted relationship is accepted. Do not let mismatched IDs persist and rely on later views or services to discover the problem.

## Things To Notice

- Input and output serializers have different jobs and different names.
- `id` stays first in every field tuple.
- Route-owned context comes from `self.context[...]` and is accessed directly when it is required.
- Client payloads do not get to choose protected fields already determined by the URL.
- Serializer validation rejects cross-organization, cross-workspace, and cross-parent links before saving.
- Dedicated action fields such as `is_active` transitions are blocked in generic update serializers.
- Custom `create()` and `update()` methods return the saved instance.
- Output serializers set `read_only_fields = fields` when every returned field is read-only.
- Serializer method fields should use context maps or already-selected related data instead of triggering repeated database lookups.

## Rules To Follow

- Prefer `ModelInputSerializer` for writes and `ModelOutputSerializer` for reads.
- Use a single serializer only when input and output shapes are truly identical.
- Keep serializer `Meta` classes explicit with `model` and `fields`.
- Include `id` first in field tuples.
- Use route-resolved objects in serializer context for protected scope.
- Do not accept organization, workspace, contact, catalog_entry, or order identity from payload when the URL already determines it.
- Validate submitted related objects against the route-owned scope.
- Put field-specific validation in `validate_<field>()` and cross-field or cross-object validation in `validate()`.
- Raise `serializers.ValidationError` from serializers so standardized DRF errors keep the correct field path.
- Implement custom persistence only when serializer defaults are not enough.
- Always return the saved instance from custom `create()` and `update()`.
- Keep lifecycle transitions behind action serializers and action views when the transition has business rules.

## Refactor Signals

- A serializer accepts `organization`, `workspace`, `contact`, `catalog_entry`, or another route-owned identifier directly from `request.data` even though the URL already determines that scope.
- A view patches request data in several places because the serializer has no clear context contract.
- A single serializer has many conditional branches because it is trying to serve both write validation and read-only response shaping.
- Output serializers omit backend-owned fields the frontend relies on, such as `id`, timestamps, status displays, or related labels.
- Serializer method fields query the database per row instead of reading a context map or selected related data.
- Validation allows cross-organization, cross-workspace, or cross-parent identifiers and relies on later code to notice the mismatch.
- Generic update serializers allow status or active-state changes that should go through dedicated action endpoints.
- Tests have to assert ad hoc response dictionaries because there is no stable output serializer contract to compare against.

## Why It Helps

- Views stay thin because serializers own input validation and response shape.
- Organization and workspace boundaries are enforced before bad relationships can be saved.
- Frontend API types remain stable because output serializers are exact contracts.
- Lifecycle workflows remain auditable because generic update serializers cannot quietly change state-machine fields.
