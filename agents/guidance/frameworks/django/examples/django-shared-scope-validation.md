---
id: framework-django-example-shared-scope-validation
title: Shared Scope Validation
description: Validate route-owned scope and related-object links at the serializer boundary so cross-organization, cross-workspace, and cross-parent combinations cannot be saved.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - serializers
  - validation
  - organization-scope
applies_to:
  - django
status: active
order: 23
---

# Shared Scope Validation

## Scenario

- Use this pattern when a mutating Django endpoint is scoped by the route, such as `organization_id`, `workspace_id`, `project_id`, `program_id`, `catalog_entry_id`, `contact_id`, or another parent resource.
- Use this pattern when a serializer accepts related-object IDs that must belong to the same organization, workspace, project, program, catalog_entry, item, enrollment, contact, or workflow boundary.
- Use this pattern when create and update payloads can combine several valid IDs into an invalid relationship, such as a contact from organization A with an catalog_entry from organization B.
- Use this pattern when a route-owned parent should win over any client-submitted parent or scope field.

## Why This Shape Exists

- Primary keys are globally valid, but they are not automatically valid together. A real object ID can still point outside the current organization, workspace, project, or parent record.
- Route-owned identity is trusted only after the view resolves it through the repository's access helpers. Client payloads must not decide that scope.
- Serializer-level validation is the clearest boundary for rejecting invalid related-object combinations before persistence, service calls, lifecycle transitions, or downstream reporting see them.
- Field-specific `serializers.ValidationError` responses keep `drf-standardized-errors` attributes precise, so tests and frontend forms can show the correct field error.
- Update serializers need to validate the proposed final relationship graph, not only the fields included in the current partial payload.

## Recommended Shape

### Avoid: Payload-Owned Scope And Unchecked Links

```python
class ProjectEnrollmentInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectEnrollment
        fields = (
            'id',
            'organization',
            'contact',
            'catalog_entry',
            'initial_survey_submission',
            'latest_survey_submission',
        )
        read_only_fields = ('id',)
```

This shape lets the client choose protected scope and only proves that each submitted ID exists. It does not prove that the contact belongs to the route organization, that the catalog_entry belongs to the same organization or selected workspace, or that the survey submissions belong to the selected catalog_entry and contact.

### Prefer: Route Scope Resolved Before Serializer Validation

```python
class ProjectEnrollmentCreateView(ProjectEnrollmentAccessMixin):
    def post(self, request, organization_id: int, workspace_id: Optional[int] = None):
        organization, route_workspace = self.resolve_workspace_route_scope(request, organization_id, workspace_id)

        serializer = ProjectEnrollmentInputSerializer(
            data=self.build_serializer_data(request),
            context={'request': request, 'organization': organization},
        )
        serializer.is_valid(raise_exception=True)

        catalog_entry_workspace = serializer.validated_data['catalog_entry'].workspace
        if route_workspace is not None and catalog_entry_workspace.id != route_workspace.id:
            raise ValidationError({'catalog_entry': 'CatalogEntry must belong to the selected workspace.'})

        self.require_permission(
            request,
            AppPermission.permission(AppPermissionChoices.WORKSPACE_MANAGE),
            workspace=catalog_entry_workspace,
        )

        instance = serializer.save()
        return Response(ProjectEnrollmentOutputSerializer(instance).data, status=status.HTTP_201_CREATED)
```

The view owns access resolution. It resolves the route organization or workspace first, passes the resolved organization into serializer context, checks route-workspace compatibility after serializer validation exposes the catalog_entry, then saves and returns the output serializer payload.

When the URL completely determines a writable foreign key, inject that value instead of trusting the payload:

```python
class SurveyFormCreateView(AuthenticatedAccessAPIView):
    def post(self, request, organization_id: int, workspace_id: int, catalog_entry_id: int):
        _, workspace, catalog_entry = self.resolve_catalog_entry_scope(request, organization_id, workspace_id, catalog_entry_id)
        self.require_permission(request, AppPermission.permission(AppPermissionChoices.WORKSPACE_MANAGE), workspace=workspace)

        serializer = SurveyFormInputSerializer(data=self.build_serializer_data(request, catalog_entry=catalog_entry.id))
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(SurveyFormOutputSerializer(instance).data, status=status.HTTP_201_CREATED)
```

Use `self.context[...]` when the serializer needs the resolved object to validate relationships. Use `build_serializer_data(request, parent=parent.id)` when the model field itself should be written from the route-owned parent. In both cases, do not let client-submitted `organization`, `workspace`, `project`, `program`, or parent IDs override the route.

### Cross-Scope Validation In The Serializer

```python
class ProjectEnrollmentInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectEnrollment
        fields = (
            'id',
            'contact',
            'catalog_entry',
            'status',
            'initial_survey_submission',
            'latest_survey_submission',
            'submitted_ts',
            'reviewed_ts',
        )
        read_only_fields = ('id',)

    def get_validators(self):
        return []

    def validate(self, attrs):
        attrs = super().validate(attrs)
        organization = self.context['organization']
        contact = attrs.get('contact', self.instance.contact if self.instance else None)
        catalog_entry = attrs.get('catalog_entry', self.instance.catalog_entry if self.instance else None)
        initial_submission = attrs.get(
            'initial_survey_submission',
            self.instance.initial_survey_submission if self.instance else None,
        )
        latest_submission = attrs.get(
            'latest_survey_submission',
            self.instance.latest_survey_submission if self.instance else None,
        )

        if contact and contact.organization_id != organization.id:
            raise serializers.ValidationError({'contact': 'Contact must belong to the selected organization.'})

        if catalog_entry and catalog_entry.workspace.organization_id != organization.id:
            raise serializers.ValidationError({'catalog_entry': 'CatalogEntry must belong to the selected organization.'})

        if contact and catalog_entry:
            existing_enrollment_queryset = ProjectEnrollment.objects.filter(contact=contact, catalog_entry=catalog_entry)
            if self.instance:
                existing_enrollment_queryset = existing_enrollment_queryset.exclude(pk=self.instance.pk)

            if existing_enrollment_queryset.exists():
                raise serializers.ValidationError({'catalog_entry': 'An enrollment for this contact and catalog_entry already exists.'})

        for field_name, submission in (
            ('initial_survey_submission', initial_submission),
            ('latest_survey_submission', latest_submission),
        ):
            if not submission:
                continue

            if submission.survey_form.catalog_entry.workspace.organization_id != organization.id:
                raise serializers.ValidationError({field_name: 'Survey submission must belong to the selected organization.'})

            if catalog_entry and submission.survey_form.catalog_entry_id != catalog_entry.id:
                raise serializers.ValidationError({field_name: 'Survey submission must belong to the selected catalog_entry.'})

            if contact and submission.contact_id and submission.contact_id != contact.id:
                raise serializers.ValidationError({field_name: 'Survey submission already belongs to another contact.'})

        return attrs
```

Use the local domain names that match the feature. The same shape applies when the boundary is project-owned tasks and assignees, program-owned requirements and submissions, workspace-owned contacts and forms, or catalog-entry-owned items, variants, pricing plans, service networks, and vendor partners.

### Validate The Proposed Final State On Create And Update

```python
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
            raise serializers.ValidationError({'status': 'Use the approved plan transition endpoint for lifecycle changes.'})

        item = attrs.get('item') or (self.instance.item if self.instance else None)
        enrollment = attrs.get('enrollment') or (self.instance.enrollment if self.instance else None)

        if 'item_option' in attrs:
            item_option = attrs['item_option']
        else:
            item_option = self.instance.item_option if self.instance else None

        if 'catalog_entry_subscription_plan' in attrs:
            catalog_entry_subscription_plan = attrs['catalog_entry_subscription_plan']
        else:
            catalog_entry_subscription_plan = self.instance.catalog_entry_subscription_plan if self.instance else None

        if item_option and item_option.item_id != item.id:
            raise serializers.ValidationError({'item_option': 'This variant does not belong to the selected item.'})

        if item and enrollment and item.catalog_entry_id != enrollment.catalog_entry_id:
            raise serializers.ValidationError({'item': "This item does not belong to the enrollment's catalog_entry."})

        if catalog_entry_subscription_plan and enrollment and catalog_entry_subscription_plan.catalog_entry_id != enrollment.catalog_entry_id:
            raise serializers.ValidationError({'catalog_entry_subscription_plan': "This pricing plan does not belong to the enrollment's catalog_entry."})

        if catalog_entry_subscription_plan and item and catalog_entry_subscription_plan.item_id and catalog_entry_subscription_plan.item_id != item.id:
            raise serializers.ValidationError({'catalog_entry_subscription_plan': 'This pricing plan does not match the selected item.'})

        return attrs
```

Partial updates are still relationship updates. Merge submitted fields with `self.instance` values before validating so changing only `item_option`, `pricing_plan`, `assignee`, or `submission` cannot quietly create an invalid final graph.

### Persist Route-Owned Scope Directly

```python
class ContactInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = (
            'id',
            'email',
            'first_name',
            'last_name',
            'phone',
        )
        read_only_fields = ('id',)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        organization = self.context['organization']
        email = attrs.get('email', self.instance.email if self.instance else None)

        contact_queryset = Contact.objects.filter(organization=organization, email__iexact=email)
        if self.instance:
            contact_queryset = contact_queryset.exclude(pk=self.instance.pk)

        if contact_queryset.exists():
            raise serializers.ValidationError({'email': 'A contact with this email already exists in the selected organization.'})

        return attrs

    def create(self, validated_data):
        return Contact.objects.create(organization=self.context['organization'], **validated_data)
```

Custom `create()` or `update()` methods should be boring: attach route-owned context, snapshot derived values, or update a related link intentionally, then return the saved instance. Do not add fallback scope selection such as `validated_data.get('organization') or self.context['organization']`; the payload should not contain protected scope in the first place.

### Serializer Tests For Cross-Scope Failures

```python
@pytest.mark.django_db
class TestProjectEnrollmentInputSerializer:
    def setup_method(self):
        self.organization = FixtureFactory.create_organization(name='Organization One', slug='organization-one')
        self.other_organization = FixtureFactory.create_organization(name='Organization Two', slug='organization-two')
        self.workspace = FixtureFactory.create_workspace(self.organization, name='Primary Workspace', slug='primary-workspace')
        self.other_organization_workspace = FixtureFactory.create_workspace(self.other_organization, name='Other Workspace', slug='other-workspace')
        self.catalog_entry = FixtureFactory.create_catalog_entry(self.workspace, name='Operations Project', slug='weight-management')
        self.other_catalog_entry = FixtureFactory.create_catalog_entry(self.other_organization_workspace, name='Other CatalogEntry', slug='other-catalog_entry')
        self.contact = FixtureFactory.create_contact(self.organization, email='contact@example.com')
        self.other_contact = FixtureFactory.create_contact(self.other_organization, email='other@example.com')
        self.context = {'organization': self.organization}

    def test_rejects_cross_organization_contact(self):
        serializer = ProjectEnrollmentInputSerializer(
            data={'contact': self.other_contact.id, 'catalog_entry': self.catalog_entry.id},
            context=self.context,
        )

        assert not serializer.is_valid()
        assert serializer.errors == {'contact': ['Contact must belong to the selected organization.']}

    def test_rejects_cross_organization_catalog_entry(self):
        serializer = ProjectEnrollmentInputSerializer(
            data={'contact': self.contact.id, 'catalog_entry': self.other_catalog_entry.id},
            context=self.context,
        )

        assert not serializer.is_valid()
        assert serializer.errors == {'catalog_entry': ['CatalogEntry must belong to the selected organization.']}
```

Serializer tests should assert the exact error dictionary. That verifies the field key, message, and validation boundary without going through routing or permissions.

### View Tests For Standardized Scope Errors

```python
def test_workspace_route_rejects_create_for_catalog_entry_outside_route_workspace(self, client):
    client.force_login(self.organization_admin)

    response = client.post(
        self.workspace_create_url,
        {
            'contact': self.contact.id,
            'catalog_entry': self.other_catalog_entry.id,
            'status': ProjectEnrollment.StatusChoices.UNDER_REVIEW,
        },
        content_type='application/json',
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert_standardized_validation_error(
        response,
        attr='catalog_entry',
        detail='CatalogEntry must belong to the selected workspace.',
    )
```

View tests should prove the HTTP boundary preserves the same scope rules and exposes the standardized error `attr` that frontend forms use.

## Things To Notice

- The route resolves organization, workspace, project, program, catalog_entry, or parent scope before serializer validation.
- The serializer reads required route-owned scope with `self.context[...]` and fails fast if the view forgot to provide it.
- Payload fields do not include route-owned `organization`, `workspace`, `project`, `program`, or parent IDs unless the model field must be injected by the view through `build_serializer_data(...)`.
- Related-object checks compare stable foreign-key IDs such as `contact.organization_id`, `catalog_entry.workspace.organization_id`, `item.catalog_entry_id`, and `variant.item_id`.
- Validation errors are keyed to the submitted field that caused the invalid relationship.
- Create validation and update validation both check the complete proposed relationship graph.
- Custom persistence attaches route-owned scope directly and returns the saved instance.
- Serializer tests assert exact `serializer.errors`; view tests assert exact standardized validation attributes and messages.

## Rules To Follow

- Resolve route-owned scope in the view with the repository's `resolve_*_scope(...)` helpers before creating the serializer.
- Do not accept client-submitted scope when the URL already determines that scope.
- Pass required route-owned objects into serializer context or inject route-owned IDs with `build_serializer_data(...)`; do not patch request data by hand in several places.
- Validate every submitted related object against the same organization, workspace, project, program, catalog_entry, contact, enrollment, or parent boundary before saving.
- For nested relationships, validate every link in the chain. For example, pricing plan to catalog_entry, item to catalog_entry, variant to item, and submission to catalog_entry and contact.
- On partial updates, combine `attrs` with `self.instance` values before validating relationship rules.
- Raise `serializers.ValidationError` from serializers and `rest_framework.exceptions.ValidationError` from views.
- Key validation errors by the exact field the client can correct.
- Add serializer tests for each cross-scope failure and each create/update path that computes or preserves related state.
- Add view tests for route-owned scope, spoofed payload scope, permission boundaries, and standardized validation errors.

## Refactor Signals

- A serializer field list includes `organization`, `workspace`, `project`, `program`, or another route-owned parent even though the URL already determines it.
- A view trusts `request.data['organization']`, `request.data['workspace']`, `request.data['project']`, or `request.data['program']` for an authenticated nested route.
- A view mutates request data manually in multiple branches because the serializer has no clear route-context contract.
- A serializer validates that IDs exist but never validates that those IDs belong together.
- A partial update validator only checks submitted fields and ignores existing instance relationships.
- Validation uses display names, slugs, or other non-unique fields to guess scope instead of comparing concrete foreign-key IDs.
- Cross-scope tests only assert `400` and do not assert the exact field and message.
- Tests create only in-scope related objects, so they cannot prove that out-of-scope relationships are rejected.
- Duplicate relationship checks live in services, tasks, and views instead of one serializer boundary.

## Verification

- Run the focused serializer test class when changing serializer relationship rules, for example `pytest backend/contact/tests/test_serializers.py::TestProjectEnrollmentInputSerializer`.
- Run the focused view test class or method when route-owned scope or standardized errors change, for example `pytest backend/contact/tests/test_views.py::TestProjectEnrollmentViews::test_workspace_route_rejects_create_for_catalog_entry_outside_route_workspace`.
- Run `ruff check` on modified Python files when implementation code changes.
- For guidance-only edits, inspect frontmatter, headings, and fenced code blocks, and run the guidance builder when practical:

```bash
python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean
```

## Why It Helps

- Cross-organization, cross-workspace, and cross-parent data leaks are rejected before invalid records can be saved.
- Views stay thin because they resolve scope and permissions while serializers own input relationship validation.
- Error responses stay predictable for frontend forms and tests.
- Partial updates remain safe because validators check the final relationship state, not only the current payload.
- Future endpoints have a repeatable review standard for route-owned context, related-object validation, and cross-scope test coverage.
