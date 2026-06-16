---
id: framework-django-example-transition-endpoint
title: Transition Endpoint
description: Use dedicated transition endpoints, transition input serializers, and domain transition functions for lifecycle changes instead of generic partial updates.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - views
  - serializers
  - services
  - testing
  - lifecycle
applies_to:
  - django
status: active
order: 22
---

# Transition Endpoint

## Scenario

- Use this shape when a model has a lifecycle field such as `status`, `is_active`, `stage`, `submitted_ts`, `approved_ts`, `reviewed_ts`, or an external-sync state.
- Use this shape when moving between lifecycle states triggers business rules, audit history, timeline entries, timestamps, notifications, task scheduling, or integration work.
- Use this shape when the URL already scopes the resource through organization, workspace, enrollment, catalog_entry, order, or another parent identity.
- Use this shape when a generic update serializer currently accepts lifecycle fields that should be changed only through explicit actions.

## Why This Shape Exists

- Lifecycle changes are commands, not ordinary representation edits. `PUT` and `PATCH` are good for changing editable resource attributes; they are a poor fit for actions such as approve, archive, activate, revoke, submit, cancel, or recover.
- A dedicated transition endpoint creates a small audit surface: the route, permission check, transition payload, allowed-state rule, persistence step, and response serializer are all visible in one flow.
- Generic update serializers often cannot express transition rules clearly. If `status` can be changed in a generic `ModelSerializer`, callers can bypass required timestamps, history entries, side effects, or allowed-state validation.
- Route-owned scope must be enforced before the transition. The client should not be able to transition an object by sending a different `organization`, `workspace`, `enrollment`, or parent id in the payload.
- The stronger end state keeps transport code thin and makes the lifecycle rule reusable from admin actions, tasks, management commands, and future endpoints.

## Recommended Shape

### Avoid Generic Field Edits For Lifecycle Changes

```python
def put(self, request, pk: int):
    instance = self.get_object(pk)
    serializer = ApprovedItemPlanInputSerializer(instance, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    instance = serializer.save()
    return Response(ApprovedItemPlanOutputSerializer(instance).data)
```

This accepts `status` as just another editable field. It hides whether `PROPOSED -> ACTIVE` is valid, whether approval timestamps were required, whether the current user had transition permission, and whether audit history was recorded.

### Prefer A Named Transition Route

```python
from django.urls import path

from contact.views.approved_plan import views

app_name = 'approved_plan'

urlpatterns = [
    path('<int:approved_plan_id>/', views.ApprovedItemPlanDetailView.as_view(), name='approved-plan-detail'),
    path(
        '<int:approved_plan_id>/transition/',
        views.ApprovedItemPlanTransitionView.as_view(),
        name='approved-plan-transition',
    ),
]
```

Use an action route when the operation is a business event. `transition/`, `approve/`, `archive/`, `activate/`, `deactivate/`, `cancel/`, and `submit/` are clearer than overloading a generic detail update.

### Block Lifecycle Fields In Generic Updates

```python
from contact.models import ApprovedItemPlan
from rest_framework import serializers

APPROVED_PLAN_TRANSITION_MESSAGE = 'Use the approved plan transition endpoint for lifecycle changes.'


class ApprovedItemPlanInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovedItemPlan
        fields = (
            'id',
            'enrollment',
            'item',
            'item_option',
            'catalog_entry_subscription_plan',
            'status',
            'notes',
            'approved_ts',
        )
        read_only_fields = ('id',)

    def validate(self, attrs):
        attrs = super().validate(attrs)

        if self.instance and 'status' in self.initial_data:
            raise serializers.ValidationError({'status': APPROVED_PLAN_TRANSITION_MESSAGE})

        if self.instance and 'approved_ts' in self.initial_data:
            raise serializers.ValidationError({'approved_ts': APPROVED_PLAN_TRANSITION_MESSAGE})

        return attrs
```

Keep create behavior separate from update behavior. Initial creation may legitimately set an initial lifecycle value when that is part of the creation contract. Updating an existing row should reject lifecycle fields and point callers to the transition endpoint.

### Use A Transition Input Serializer

```python
from contact.models import ApprovedItemPlan
from rest_framework import serializers


class ApprovedItemPlanTransitionInputSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ApprovedItemPlan.StatusChoices.choices)
    approved_ts = serializers.DateTimeField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = self.context['instance']

        if attrs['status'] == ApprovedItemPlan.StatusChoices.APPROVED and 'approved_ts' not in attrs:
            raise serializers.ValidationError({'approved_ts': 'Approved plans need an approval timestamp.'})

        if attrs['status'] == instance.status:
            raise serializers.ValidationError({'status': 'Plan is already in this status.'})

        return attrs
```

The transition serializer validates payload shape and field-level requirements. It should not load the target object from a client-submitted id when the route already identifies the object. Pass the route-resolved `instance` through context and access it directly.

### Keep Allowed-State Rules In A Domain Boundary

```python
from django.db import transaction
from rest_framework import serializers

from contact.models import ApprovedItemPlan

APPROVED_PLAN_ALLOWED_TRANSITIONS = {
    ApprovedItemPlan.StatusChoices.PROPOSED: {
        ApprovedItemPlan.StatusChoices.APPROVED,
        ApprovedItemPlan.StatusChoices.CLOSED,
    },
    ApprovedItemPlan.StatusChoices.APPROVED: {
        ApprovedItemPlan.StatusChoices.ACTIVE,
        ApprovedItemPlan.StatusChoices.REPLACED,
        ApprovedItemPlan.StatusChoices.EXPIRED,
        ApprovedItemPlan.StatusChoices.CLOSED,
    },
    ApprovedItemPlan.StatusChoices.ACTIVE: {
        ApprovedItemPlan.StatusChoices.REPLACED,
        ApprovedItemPlan.StatusChoices.EXPIRED,
        ApprovedItemPlan.StatusChoices.CLOSED,
    },
    ApprovedItemPlan.StatusChoices.REPLACED: set(),
    ApprovedItemPlan.StatusChoices.EXPIRED: set(),
    ApprovedItemPlan.StatusChoices.CLOSED: set(),
}


@transaction.atomic
def transition_approved_item_plan(
    *,
    plan: ApprovedItemPlan,
    next_status: str,
    approved_ts=None,
    notes: str = '',
    transitioned_by,
):
    allowed_statuses = APPROVED_PLAN_ALLOWED_TRANSITIONS[plan.status]
    if next_status not in allowed_statuses:
        raise serializers.ValidationError({'status': f'Cannot transition approved plan from {plan.status} to {next_status}.'})

    update_fields = ['status', 'updated_ts']
    plan.status = next_status

    if approved_ts is not None:
        plan.approved_ts = approved_ts
        update_fields.append('approved_ts')

    if notes:
        plan.notes = notes
        update_fields.append('notes')

    plan.save(update_fields=update_fields, log_user_id=transitioned_by.id)
    return plan
```

The allowed transition graph belongs in a model method or service function, not in the view. Use a service when the transition writes multiple models, starts tasks, emits integration events, or creates timeline rows. Use a model method only when the rule is intrinsic to that model and does not need external dependencies.

### Add Audit Or Timeline Behavior Where The Item Needs History

```python
class ApprovedItemPlan(BaseModel):
    history_log_fields = ('status', 'approved_ts')

    class StatusChoices(models.TextChoices):
        PROPOSED = 'PROPOSED', gettext('Proposed')
        APPROVED = 'APPROVED', gettext('Approved')
        ACTIVE = 'ACTIVE', gettext('Active')
        REPLACED = 'REPLACED', gettext('Replaced')
        EXPIRED = 'EXPIRED', gettext('Expired')
        CLOSED = 'CLOSED', gettext('Closed')
```

Use the repository's `history_log_fields` and `save(log_user_id=...)` path when admin-style history is enough. If operators need contact support history, create a first-class timeline or sync-event record inside the transition service instead of reconstructing events later from status fields.

### Scope The Object Before Validating The Transition

```python
from common.permissions import AppPermission, AppPermissionChoices
from contact.models import ApprovedItemPlan
from contact.views.approved_plan.serializers import (
    ApprovedItemPlanOutputSerializer,
    ApprovedItemPlanTransitionInputSerializer,
)
from contact.services.approved_plan_lifecycle import transition_approved_item_plan
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response


class ApprovedItemPlanTransitionView(ApprovedItemPlanAccessMixin):
    def post(self, request, organization_id: int, enrollment_id: int, approved_plan_id: int, workspace_id: Optional[int] = None):
        enrollment, plan = self._get_plan(request, organization_id, enrollment_id, approved_plan_id, workspace_id)
        workspace = enrollment.catalog_entry.workspace
        self.require_permission(request, AppPermission.permission(AppPermissionChoices.WORKSPACE_MANAGE), workspace=workspace)

        serializer = ApprovedItemPlanTransitionInputSerializer(
            data=self.build_serializer_data(request),
            context={'request': request, 'instance': plan},
        )
        serializer.is_valid(raise_exception=True)

        plan = transition_approved_item_plan(
            plan=plan,
            next_status=serializer.validated_data['status'],
            approved_ts=serializer.validated_data.get('approved_ts'),
            notes=serializer.validated_data.get('notes', ''),
            transitioned_by=request.user,
        )

        return Response(ApprovedItemPlanOutputSerializer(plan).data, status=status.HTTP_200_OK)
```

The view should read as a boundary checklist: resolve route scope, check permission, validate transition input, call the lifecycle function, return the output serializer.

### Keep The Scoped Lookup Explicit

```python
class ApprovedItemPlanAccessMixin(ProjectEnrollmentAccessMixin):
    def _get_plan(self, request, organization_id: int, enrollment_id: int, approved_plan_id: int, workspace_id: Optional[int] = None):
        organization, workspace = self.resolve_workspace_route_scope(request, organization_id, workspace_id)
        enrollment = get_object_or_404(self._get_enrollment_queryset(request, organization, workspace), pk=enrollment_id)
        plan = get_object_or_404(
            ApprovedItemPlan.objects.filter(enrollment=enrollment).select_related(
                'item',
                'item_option',
                'catalog_entry_subscription_plan',
            ),
            pk=approved_plan_id,
        )
        return enrollment, plan
```

Do not fetch `ApprovedItemPlan.objects.get(pk=approved_plan_id)` and then compare organization ids in later code. Build the scoped queryset first so out-of-scope resources naturally return `404`.

### Test The Transition Contract

```python
import pytest
from contact.models import ApprovedItemPlan
from contact.views.approved_plan.serializers import ApprovedItemPlanOutputSerializer
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestApprovedItemPlanTransitionView:
    def test_workspace_admin_can_transition_plan_status(self, client):
        client.force_login(self.workspace_admin)

        response = client.post(
            self.transition_url,
            {
                'status': ApprovedItemPlan.StatusChoices.APPROVED,
                'approved_ts': '2026-01-01T00:00:00Z',
            },
            content_type='application/json',
        )

        self.approved_plan.refresh_from_db()
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == ApprovedItemPlanOutputSerializer(self.approved_plan).data
        assert self.approved_plan.status == ApprovedItemPlan.StatusChoices.APPROVED
        assert self.approved_plan.approved_ts is not None

    def test_transition_rejects_disallowed_status_move(self, client):
        self.approved_plan.status = ApprovedItemPlan.StatusChoices.CLOSED
        self.approved_plan.save(update_fields=['status', 'updated_ts'])
        client.force_login(self.workspace_admin)

        response = client.post(
            self.transition_url,
            {'status': ApprovedItemPlan.StatusChoices.ACTIVE},
            content_type='application/json',
        )

        self.approved_plan.refresh_from_db()
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert self.approved_plan.status == ApprovedItemPlan.StatusChoices.CLOSED

    def test_workspace_operator_cannot_transition_plan(self, client):
        client.force_login(self.workspace_operator)

        response = client.post(
            self.transition_url,
            {'status': ApprovedItemPlan.StatusChoices.APPROVED},
            content_type='application/json',
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_other_enrollment_plan_returns_404(self, client):
        client.force_login(self.workspace_admin)
        url = reverse(
            'contact:approved-plan-transition',
            kwargs={
                'organization_id': self.organization.id,
                'enrollment_id': self.enrollment.id,
                'approved_plan_id': self.other_approved_plan.id,
            },
        )

        response = client.post(
            url,
            {'status': ApprovedItemPlan.StatusChoices.APPROVED},
            content_type='application/json',
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_detail_update_rejects_transition_fields(self, client):
        client.force_login(self.workspace_admin)

        response = client.put(
            self.detail_url,
            {'status': ApprovedItemPlan.StatusChoices.APPROVED},
            content_type='application/json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
```

Tests should prove the happy path, disallowed state movement, lower-permission access, ownership isolation, and generic-update rejection. Add audit or timeline assertions when the transition service writes history.

## Things To Notice

- The transition route is named for the lifecycle command instead of hiding it inside a generic detail update.
- The generic input serializer rejects lifecycle fields on existing instances.
- The transition input serializer accepts only command fields, not route-owned identity.
- The object lookup is scoped through organization, workspace, enrollment, or the relevant parent before the permission check and transition.
- Allowed-state validation is enforced in the domain transition function so non-HTTP callers cannot bypass it.
- The view returns the normal output serializer for the updated resource.
- `save(log_user_id=request.user.id)` is used when model history should capture who made the change.
- Timeline, sync-event, notification, and task side effects belong in the transition service, not hidden in `save()` or scattered across views.
- Tests assert both response shape and persisted database state after the transition.

## Rules To Follow

- Do not allow generic update endpoints to change lifecycle fields on existing records.
- Use a dedicated `POST` action endpoint for lifecycle commands.
- Resolve route-owned scope before validating or applying the transition.
- Do not accept organization, workspace, enrollment, order, contact, or parent identity from the transition payload when the URL already determines it.
- Use a transition input serializer for command payload validation.
- Keep allowed-state validation in a service function or model method that can be reused outside the view.
- Raise DRF `serializers.ValidationError` or `rest_framework.exceptions.ValidationError` from the correct layer so standardized error responses keep field-specific attributes.
- Persist transition-related timestamps, notes, history, timeline rows, sync events, and tasks in the same domain boundary as the status change.
- Return the updated resource through its output serializer after a successful transition.
- Cover transition endpoints with tests for allowed transitions, disallowed transitions, lower-permission users, out-of-scope objects, generic-update rejection, and any audit or timeline writes.

## Refactor Signals

- A `put()` or `patch()` endpoint accepts `status`, `is_active`, `stage`, `approved_ts`, `submitted_ts`, `reviewed_ts`, or similar lifecycle fields on an existing instance.
- A serializer contains several `if status == ...` branches because it is trying to be both a generic update serializer and a workflow command serializer.
- A view directly assigns `instance.status = ...` in more than one place or repeats the same transition validation across endpoints.
- A transition route fetches by primary key first and checks organization, workspace, enrollment, or contact ownership afterward.
- Tests only prove that a status can change and do not prove that invalid state moves are rejected.
- A lifecycle change has timestamps or side effects in some callers but not others.
- Audit history is reconstructed from current model fields because the transition did not write a timeline, sync-event, or history entry when it happened.
- A client can spoof route-owned scope by including a different parent id in the transition payload.
- The frontend must know internal lifecycle graph rules because the backend accepts any choice value and relies on the UI to hide invalid moves.

## Verification

- Run serializer tests for the generic input serializer and transition input serializer.
- Run view tests for the transition endpoint, including allowed transition, disallowed transition, permission-negative, ownership-negative, and generic-update-rejection cases.
- Run service or model tests for the transition graph when lifecycle rules live outside the view.
- For guidance-only edits, inspect the Markdown frontmatter, heading order, and code fences, and build generated guidance when practical:

```bash
python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean
rg -n '^## |^### |^`{3}' agents/guidance/frameworks/django/examples/django-transition-endpoint.md
```

## Why It Helps

- Lifecycle rules become visible and reviewable instead of being hidden among ordinary field edits.
- Organization and workspace boundaries are enforced before a state-changing command can run.
- Status graphs, audit history, and side effects stay consistent across views, tasks, admin actions, and commands.
- Output serializer responses keep frontend contracts stable after mutations.
- Tests can prove security and workflow behavior at the HTTP boundary without duplicating the entire domain implementation.
