---
id: framework-django-example-domain-profile-vs-auth-user
title: Domain Profile Versus Auth User
description: Keep authentication users, organization operators, and contact domain profiles separate so ownership, history, and permissions stay auditable.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - models
  - organization-scope
  - permissions
applies_to:
  - django
status: active
order: 21
---

# Domain Profile Versus Auth User

## Scenario

- Use this pattern when modeling contacts, contacts, members, applicants, buyers, enrollments, submissions, orders, subscriptions, invoices, support cases, or other business records.
- Use this pattern when the same Django auth user can be a platform admin, organization operator, workspace staff member, and contact in different contexts.
- Use this pattern when a domain profile may exist before login exists, such as a public survey lead, imported contact, guest checkout, or staff-created contact record.
- Use this pattern when contact-facing portal endpoints need to resolve "the current contact" from the authenticated session plus organization, not from arbitrary contact IDs.

## Why This Shape Exists

Django auth users are credentials and session identity. They answer "who logged in?" and carry authentication details such as email, password, staff flags, superuser status, and session-backed request identity.

Domain profiles are business and history identity. An organization-scoped `Contact` answers "which contact or buyer does this workflow history belong to?" and carries the domain data that survives account changes: demographic fields, portal linkage, enrollments, survey submissions, orders, coupon usage, support history, and billing context.

Conflating those concepts creates security and data-history problems:

- Staff users can accidentally become "contacts" because an enrollment points at `settings.AUTH_USER_MODEL`.
- A contact who has no portal login yet cannot be represented cleanly.
- One auth user cannot safely belong to two organization contact profiles without organization-scoped uniqueness.
- Contact history becomes hard to preserve when credentials are merged, disabled, deleted, or replaced.
- Staff/operator permission checks become tangled with contact/contact ownership checks.
- Contact portal routes are tempted to accept `contact_id` from the URL even though the session plus organization already determines the contact.

The recommended standard is: use auth `User` for login and operator identity; use memberships for organization and workspace staff access; use organization-scoped `Contact` records for contact history; link `Contact.user` only when a portal login exists.

## Recommended Shape

### Auth User Is Credential Identity

```python
class OrganizationMembership(BaseModel):
	class Meta:
		constraints = (models.UniqueConstraint(fields=('organization', 'user'), name='unique_organization_membership'),)
		ordering = ('id',)

	class RoleChoices(models.TextChoices):
		ADMIN = 'ADMIN', gettext('Admin')
		MEMBER = 'MEMBER', gettext('Member')

	organization = models.ForeignKey('tenancy.Organization', related_name='memberships', null=False, blank=False, verbose_name=gettext('Organization'), on_delete=models.DO_NOTHING)
	user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='organization_memberships', null=False, blank=False, verbose_name=gettext('User'), on_delete=models.DO_NOTHING)
	role = models.TextField(choices=RoleChoices.choices, default=RoleChoices.MEMBER, null=False, blank=False, verbose_name=gettext('Role'))
	is_active = models.BooleanField(default=True, null=False, blank=False, verbose_name=gettext('Is Active'))
```

Organization and workspace staff access belongs to membership models that point at auth users. A user can log in, hold organization roles, hold workspace roles, create audit entries, and still not be a contact.

Use `request.user` for the current session and for staff/operator actions:

```python
class OrderCreateFromApprovedPlanView(ProjectEnrollmentAccessMixin):
	def post(self, request, organization_id: int, enrollment_id: int, approved_plan_id: int, workspace_id: Optional[int] = None):
		organization, workspace = self.resolve_workspace_route_scope(request, organization_id, workspace_id)
		enrollment = get_object_or_404(self._get_enrollment_queryset(request, organization, workspace), pk=enrollment_id)
		approved_plan = get_object_or_404(
			ApprovedItemPlan.objects.filter(enrollment=enrollment).select_related('item', 'item_option', 'catalog_entry_subscription_plan').order_by('id'),
			pk=approved_plan_id,
		)
		self.require_permission(request, AppPermission.permission(AppPermissionChoices.WORKSPACE_MANAGE), workspace=enrollment.catalog_entry.workspace)

		serializer = OrderCreateFromApprovedPlanInputSerializer(
			data=self.build_serializer_data(request),
			context={'request': request, 'approved_plan': approved_plan},
		)
		serializer.is_valid(raise_exception=True)

		order = ApprovedPlanOrderCreationService(
			organization=organization,
			enrollment=enrollment,
			approved_plan=approved_plan,
			shipping_address=serializer.validated_data['shipping_address'],
			created_by=request.user,
			coupon=serializer.validated_data.get('coupon'),
		).create()

		return Response(OrderDetailOutputSerializer(order).data, status=status.HTTP_201_CREATED)
```

`request.user` is the operator creating the order. The order's contact comes from the approved plan and enrollment chain, not from the staff user.

### Contact Is Organization-Scoped Business Identity

```python
class Contact(BaseModel):
	class Meta:
		constraints = (
			models.UniqueConstraint(Lower('email'), 'organization', name='unique_contact_email_per_organization_ci'),
			models.UniqueConstraint(fields=('organization', 'user'), condition=models.Q(user__isnull=False), name='unique_contact_user_per_organization'),
		)
		ordering = ('id',)

	class StatusChoices(models.TextChoices):
		ACTIVE = 'ACTIVE', gettext('Active')
		INACTIVE = 'INACTIVE', gettext('Inactive')

	organization = models.ForeignKey('tenancy.Organization', related_name='contacts', null=False, blank=False, verbose_name=gettext('Organization'), on_delete=models.DO_NOTHING)
	user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='contact_profiles', null=True, blank=True, verbose_name=gettext('User'), on_delete=models.DO_NOTHING)
	email = models.EmailField(null=False, blank=False, verbose_name=gettext('Email'))
	first_name = models.TextField(null=False, blank=True, verbose_name=gettext('First Name'))
	last_name = models.TextField(null=False, blank=True, verbose_name=gettext('Last Name'))
	phone = models.TextField(null=False, blank=True, verbose_name=gettext('Phone'))
	status = models.TextField(choices=StatusChoices.choices, default=StatusChoices.ACTIVE, null=False, blank=False, verbose_name=gettext('Status'))
```

The `user` link is nullable because the business profile can exist without credentials. A public survey submission, imported contact, staff-created contact, or pre-portal order can still attach to a durable `Contact`. When the contact later creates portal credentials, link the matching auth user to the organization-scoped contact profile.

Keep the link organization-scoped. The same auth user must not map to two contact profiles inside the same organization, but a user may legitimately have separate contact profiles across organizations in a white-label application.

### Workflow History Points At Contact Records

```python
class ProjectEnrollment(BaseModel):
	class Meta:
		constraints = (models.UniqueConstraint(fields=('contact', 'catalog_entry'), name='unique_contact_project_enrollment'),)
		ordering = ('id',)

	contact = models.ForeignKey('contact.Contact', related_name='enrollments', null=False, blank=False, verbose_name=gettext('Contact'), on_delete=models.DO_NOTHING)
	catalog_entry = models.ForeignKey('catalog_entry.CatalogEntry', related_name='project_enrollments', null=False, blank=False, verbose_name=gettext('CatalogEntry'), on_delete=models.DO_NOTHING)
	status = models.TextField(choices=StatusChoices.choices, default=StatusChoices.SURVEY_SUBMITTED, null=False, blank=False, verbose_name=gettext('Status'))
	initial_survey_submission = models.ForeignKey('survey.SurveySubmission', related_name='initial_project_enrollments', null=True, blank=True, verbose_name=gettext('Initial Survey Submission'), on_delete=models.DO_NOTHING)
	latest_survey_submission = models.ForeignKey('survey.SurveySubmission', related_name='latest_project_enrollments', null=True, blank=True, verbose_name=gettext('Latest Survey Submission'), on_delete=models.DO_NOTHING)
```

Enrollments belong to the contact profile. They should never point at the staff user who reviewed the enrollment, the organization admin who created the record, or the auth user that happens to share the contact's email.

```python
class SurveySubmission(BaseModel):
	class Meta:
		ordering = ('id',)

	survey_form = models.ForeignKey('survey.SurveyForm', related_name='submissions', null=False, blank=False, verbose_name=gettext('Survey Form'), on_delete=models.DO_NOTHING)
	contact = models.ForeignKey('contact.Contact', related_name='survey_submissions', null=True, blank=True, verbose_name=gettext('Contact'), on_delete=models.DO_NOTHING)
	project_enrollment = models.ForeignKey('contact.ProjectEnrollment', related_name='survey_submissions', null=True, blank=True, verbose_name=gettext('CatalogEntry Enrollment'), on_delete=models.DO_NOTHING)
	status = models.TextField(choices=StatusChoices.choices, default=StatusChoices.SUBMITTED, null=False, blank=False, verbose_name=gettext('Status'))
	public_draft_token = models.UUIDField(unique=True, editable=False, null=True, blank=True, verbose_name=gettext('Public Draft Token'))
	answers = models.JSONField(null=False, blank=False, verbose_name=gettext('Answers'))
```

Survey submissions may be anonymous or draft-like at first, so their `contact` link can be nullable. Once staff converts the submission into an enrollment or the portal identifies the contact, link it to `Contact` and `ProjectEnrollment` so the submitted answers become part of the contact timeline.

```python
class Order(BaseModel):
	class Meta:
		ordering = ('id',)
		constraints = (models.UniqueConstraint(fields=('approved_item_plan',), name='unique_order_approved_item_plan'),)

	organization = models.ForeignKey('tenancy.Organization', related_name='orders', null=False, blank=False, verbose_name=gettext('Organization'), on_delete=models.DO_NOTHING)
	workspace = models.ForeignKey('workspace.Workspace', related_name='orders', null=False, blank=False, verbose_name=gettext('Workspace'), on_delete=models.DO_NOTHING)
	contact = models.ForeignKey('contact.Contact', related_name='orders', null=False, blank=False, verbose_name=gettext('Contact'), on_delete=models.DO_NOTHING)
	enrollment = models.ForeignKey('contact.ProjectEnrollment', related_name='orders', null=False, blank=False, verbose_name=gettext('Enrollment'), on_delete=models.DO_NOTHING)
	approved_item_plan = models.ForeignKey('contact.ApprovedItemPlan', related_name='orders', null=False, blank=False, verbose_name=gettext('Approved Item Plan'), on_delete=models.DO_NOTHING)
	status = models.TextField(choices=StatusChoices.choices, default=StatusChoices.PENDING, null=False, blank=False, verbose_name=gettext('Status'))
```

Orders carry organization, workspace, contact, enrollment, and approved-plan identity directly. This makes list scoping and support history straightforward and prevents a staff user's auth account from becoming the order owner.

### Audit Fields May Point At Auth Users

```python
class OrderTimelineEntry(BaseModel):
	class Meta:
		ordering = ('id',)

	order = models.ForeignKey('order.Order', related_name='timeline_entries', null=False, blank=False, verbose_name=gettext('Order'), on_delete=models.DO_NOTHING)
	entry_type = models.TextField(choices=EntryTypeChoices.choices, default=EntryTypeChoices.CREATED, null=False, blank=False, verbose_name=gettext('Entry Type'))
	message = models.TextField(null=False, blank=False, verbose_name=gettext('Message'))
	created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='order_timeline_entries', null=True, blank=True, verbose_name=gettext('Created By'), on_delete=models.DO_NOTHING)
```

Auth-user foreign keys are appropriate for audit, invitations, publication, and staff action attribution. They answer "which logged-in operator did this?" They should not replace contact ownership on domain workflow rows.

### Serializer Validation Enforces Organization Identity

```python
class ContactInputSerializer(serializers.ModelSerializer):
	class Meta:
		model = Contact
		fields = (
			'id',
			'organization',
			'user',
			'email',
			'first_name',
			'last_name',
			'phone',
			'status',
		)
		read_only_fields = ('id', 'organization')

	def validate(self, attrs):
		attrs = super().validate(attrs)
		organization = self.context['organization']
		user = attrs.get('user', self.instance.user if self.instance else None)
		email = attrs.get('email', self.instance.email if self.instance else None)

		existing_email_queryset = Contact.objects.filter(organization=organization, email__iexact=email)
		if self.instance:
			existing_email_queryset = existing_email_queryset.exclude(pk=self.instance.pk)

		if existing_email_queryset.first():
			raise serializers.ValidationError({'email': 'A contact with this email already exists in the organization.'})

		if user is not None:
			existing_user_queryset = Contact.objects.filter(organization=organization, user=user)
			if self.instance:
				existing_user_queryset = existing_user_queryset.exclude(pk=self.instance.pk)

			if existing_user_queryset.first():
				raise serializers.ValidationError({'user': 'A contact for this user already exists in the organization.'})

		return attrs

	def create(self, validated_data):
		return Contact.objects.create(organization=self.context['organization'], **validated_data)
```

The view owns `organization` and passes it through serializer context. The serializer allows an optional `user` link, but validates that the linked auth user is unique inside that organization. It does not use global user identity as the contact boundary.

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

	def validate(self, attrs):
		attrs = super().validate(attrs)
		organization = self.context['organization']
		contact = attrs.get('contact', self.instance.contact if self.instance else None)
		catalog_entry = attrs.get('catalog_entry', self.instance.catalog_entry if self.instance else None)
		initial_submission = attrs.get('initial_survey_submission', self.instance.initial_survey_submission if self.instance else None)

		if contact and contact.organization_id != organization.id:
			raise serializers.ValidationError({'contact': 'Contact must belong to the selected organization.'})

		if catalog_entry and catalog_entry.workspace.organization_id != organization.id:
			raise serializers.ValidationError({'catalog_entry': 'CatalogEntry must belong to the selected organization.'})

		if initial_submission and initial_submission.survey_form.catalog_entry.workspace.organization_id != organization.id:
			raise serializers.ValidationError({'initial_survey_submission': 'Survey submission must belong to the selected organization.'})

		if contact and initial_submission and initial_submission.contact_id and initial_submission.contact_id != contact.id:
			raise serializers.ValidationError({'initial_survey_submission': 'Survey submission already belongs to another contact.'})

		return attrs
```

Validate domain relationships against organization, workspace, and contact boundaries before saving. Do not attach a submission from one contact, organization, or catalog_entry to another contact's enrollment.

### Views Scope Contacts Through Organization And Staff Access

```python
class ContactAccessMixin(AuthenticatedAccessAPIView):
	def get_contact_queryset(self, request, organization):
		queryset = Contact.objects.filter(organization=organization).order_by('id')
		if self.user_has_platform_access(request):
			return queryset

		organization_membership = self.get_organization_membership(request, organization)
		if organization_membership.role == organization_membership.RoleChoices.ADMIN:
			return queryset

		accessible_workspaces = self.get_accessible_workspace_queryset(request, organization)
		return queryset.filter(enrollments__catalog_entry__workspace__in=accessible_workspaces).distinct().order_by('id')


class ContactListView(ContactAccessMixin):
	def get(self, request, organization_id: int, workspace_id: Optional[int] = None):
		organization, workspace = self.resolve_workspace_route_scope(request, organization_id, workspace_id)
		queryset = self.get_contact_queryset(request, organization)
		if workspace is None:
			workspace = self.resolve_optional_workspace_filter(request, organization)

		if workspace is not None:
			queryset = queryset.filter(enrollments__catalog_entry__workspace=workspace).distinct().order_by('id')

		return Response(ContactOutputSerializer(queryset, many=True).data, status=status.HTTP_200_OK)
```

Staff access is resolved through organization and workspace memberships attached to `request.user`. Contact rows are scoped by organization and workspace relationships. A workspace operator does not become the contact owner; the operator only receives the subset of contact profiles reachable through accessible enrollments.

### Contact Portal Resolves Current Contact From Session Plus Organization

```python
class ContactPortalOrderListView(AuthenticatedAccessAPIView):
	def get(self, request, organization):
		contact = get_object_or_404(
			Contact.objects.filter(organization=organization, user=request.user, status=Contact.StatusChoices.ACTIVE),
		)
		queryset = contact.orders.filter(organization=organization).select_related('workspace', 'enrollment').order_by('id')
		return Response(OrderListOutputSerializer(queryset, many=True).data, status=status.HTTP_200_OK)
```

Contact portal routes should not accept arbitrary `contact_id` when the session already determines the auth user. Resolve the organization at the portal boundary, preferably from the request host for white-label portals, then resolve `Contact` through `(organization, request.user)`. If no linked contact exists, the user is authenticated but has no contact profile in that organization.

## Things To Notice

- `settings.AUTH_USER_MODEL` appears on membership and audit models because those rows describe login identity or operator action.
- `Contact.user` is nullable because a contact profile can exist before credentials exist.
- `Contact` is organization-scoped. Email and auth-user linkage are unique inside an organization, not treated as global business identity.
- Contact-facing workflow models point at `Contact`, not auth `User`.
- `SurveySubmission.contact` can be nullable while the submission is anonymous or unlinked, but once linked it points at `Contact`.
- `ProjectEnrollment.contact`, `Order.contact`, coupon usage, support cases, subscriptions, invoices, and similar history rows should be non-null contact links unless the domain genuinely supports anonymous history.
- Operator/staff identity is captured separately through `created_by`, `published_by`, `invited_by`, or timeline note authors.
- View access flows from `request.user` to memberships and permissions, then to scoped contact/domain querysets.
- Portal access flows from `request.user` plus organization to a single contact profile. It does not trust a user-submitted contact identity.
- Serializer validation rejects cross-organization, cross-workspace, and cross-contact links before persistence.

## Rules To Follow

- Use auth `User` for credentials, sessions, staff flags, superuser checks, login state, membership rows, and audit attribution.
- Use organization-scoped domain profiles such as `Contact` for contact, buyer, applicant, member, or portal history.
- Do not point enrollments, survey submissions, orders, subscriptions, invoices, support cases, coupon usage, or contact timeline rows at `settings.AUTH_USER_MODEL` as the owner.
- Keep contact profile auth links nullable when the business record can exist before portal login, after account deactivation, or from imports and staff-created records.
- Add organization-scoped uniqueness for contact email and non-null contact user linkage when those values identify a contact inside one organization.
- Use `OrganizationMembership` and workspace membership models for staff/operator authorization. Do not infer organization access from `Contact.user`.
- Use `request.user` for the acting operator in services and audit fields, not as the contact being acted on.
- Resolve route organization and workspace scope before looking up contact records, enrollments, submissions, orders, or contact-owned child rows.
- Validate every submitted domain relationship against the same organization or workspace boundary before saving.
- For contact portal endpoints, resolve the current contact from organization plus `request.user`; do not expose arbitrary contact IDs when the session identity already determines the contact.
- Add ownership-boundary tests for other organizations, other workspaces, other contacts, lower-permission operators, and unlinked or nullable contact-profile states.
- Use shared fixture builders for auth users, organization memberships, workspace memberships, contacts, enrollments, submissions, and orders instead of local one-off setup helpers.

## Refactor Signals

- A model named `Enrollment`, `Submission`, `Order`, `Subscription`, `Invoice`, `SupportCase`, or `CouponUsage` has `user = ForeignKey(settings.AUTH_USER_MODEL)` and the row represents contact history.
- A serializer accepts `user` as the contact owner when the route or current organization should identify a `Contact`.
- A contact portal route includes `<int:contact_id>` even though the session plus organization determines the contact.
- A view filters contact history with `user=request.user` outside a portal resolver instead of joining through organization-scoped `Contact`.
- A staff or operator view uses `Contact.user` to decide organization or workspace permissions.
- A workflow row can accidentally point at the organization admin or workspace operator who created it.
- A nullable contact profile state is handled with fake auth users, placeholder emails, or special staff accounts instead of a nullable `Contact.user` link.
- An organization-scoped contact uniqueness rule is enforced only in UI code, not in model constraints and serializer validation.
- Tests create only auth users and never create explicit contact profiles for contact-owned flows.
- Tests prove successful staff access but do not create another organization's contact, another workspace's enrollment, or another contact's submission/order.
- Deleting or deactivating an auth user would orphan business history because the history is keyed only to `User`.

## Verification

- For model changes, run `python manage.py makemigrations --check` or the task equivalent to confirm the intended schema is represented.
- For serializer changes, run the focused serializer tests covering contact uniqueness and cross-link validation, such as `pytest backend/contact/tests/test_serializers.py`.
- For contact view changes, run `pytest backend/contact/tests/test_views.py::TestContactViews` and `pytest backend/contact/tests/test_views.py::TestProjectEnrollmentViews`.
- For survey submission changes, run `pytest backend/survey/views/survey_submission/tests/test_views.py` and serializer tests when output or linking rules change.
- For order changes, run `pytest backend/order/tests/test_order_views.py` and `pytest backend/order/tests/test_serializers.py`.
- Run `ruff check` on modified Python files when code changes accompany the guidance.
- For guidance-only edits, inspect this Markdown file for valid frontmatter, balanced code fences, and stale model names. Run the guidance build when practical:

```bash
python3 agents/build_agents.py --target all --out /tmp/guidance-examples-build --clean
```

## Why It Helps

- Contact history remains stable even when login credentials are created, merged, disabled, or changed.
- Staff/operator permissions stay auditable because they flow through memberships and explicit permission checks.
- Organization isolation is easier to review because contact profiles carry organization identity directly.
- Portal endpoints are safer because the current contact is resolved from session plus organization rather than a client-supplied contact ID.
- Enrollments, submissions, orders, and support records can be queried as one contact timeline without guessing which auth user owns them.
- Tests can prove the real security boundary: staff access, contact ownership, organization isolation, workspace filtering, and nullable portal linkage.
