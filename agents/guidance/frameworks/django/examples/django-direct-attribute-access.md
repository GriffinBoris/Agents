---
id: framework-django-example-direct-attribute-access
title: Direct Attribute Access
description: Prefer explicit branching and direct attribute access over fail-soft getattr fallbacks for required fields.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - serializers
  - antipatterns
applies_to:
  - django
status: active
order: 25
---

# Direct Attribute Access

## Scenario

- Use this standard when a Django model field, serializer field, serializer context value, validated-data key, or request attribute is required by the current contract.
- Use it when a serializer has different create and update paths and must merge submitted fields with existing instance fields before validating the proposed final state.
- Use it when middleware, authentication, or a base view guarantees a request attribute such as `request.user` or `request.access_context`.
- Use it when refactoring code that uses `getattr(..., None)`, `hasattr(...)`, chained `or` fallbacks, or broad `.get(...)` defaults to keep broken contracts alive.
- Use optional access only when the data is actually optional by domain or query shape, such as a nullable relation, an omitted PATCH field, an optional query annotation, or an optional user-submitted field.

## Why This Shape Exists

- Required fields are contracts. Direct access makes that contract visible and fails immediately when the caller, serializer, middleware, queryset, or test setup violates it.
- Defensive fallbacks hide broken data flow. `getattr(self.instance, 'owner', None)` makes a missing field look the same as a deliberately empty value, which sends reviewers to the wrong problem.
- Create and update serializers have different sources of truth. Create paths should read required submitted values directly from `attrs`; update paths should start from `self.instance` and then intentionally apply submitted overrides.
- Middleware-owned request attributes should be treated like framework attributes after middleware is installed. Views should use `request.access_context`, not branch around a missing middleware contract.
- Optional data still needs clear handling. Nullable relations, optional annotations, and optional payload fields should be represented with explicit optional branches, not broad fallback logic that also covers impossible states.
- Tests should prove the intended contract. Missing required fields, cross-scope IDs, partial updates, context-owned persistence, and optional values should each fail or succeed for a clear reason.

## Recommended Shape

### Avoid: Fail-Soft Required Instance Fields

```python
selected_owner = owner or getattr(self.instance, 'owner', None)
if selected_owner:
    queryset = Assignment.objects.filter(project=project, owner=selected_owner)
```

This shape hides whether `owner` is required, whether `self.instance` should exist, and whether a missing model field is a real programming error. It also treats an empty submitted value, a missing instance, and a broken serializer contract as the same case.

### Prefer: Explicit Create And Update Branching

```python
if self.instance:
    selected_owner = self.instance.owner
else:
    selected_owner = owner

if owner is not None:
    selected_owner = owner

if selected_owner is not None:
    queryset = Assignment.objects.filter(project=project, owner=selected_owner)
```

This is better because each branch names the source of truth. The update path starts from the saved instance. The create path starts from the submitted value. A submitted override is applied intentionally instead of being hidden inside a truthiness expression.

For required create fields, read from `attrs[...]` after DRF validation has run:

```python
def validate(self, attrs):
    attrs = super().validate(attrs)

    if self.instance:
        contact = self.instance.contact
        catalog_entry = self.instance.catalog_entry
    else:
        contact = attrs['contact']
        catalog_entry = attrs['catalog_entry']

    if 'contact' in attrs:
        contact = attrs['contact']
    if 'catalog_entry' in attrs:
        catalog_entry = attrs['catalog_entry']

    if contact.organization_id != catalog_entry.workspace.organization_id:
        raise serializers.ValidationError({'contact': 'Contact must belong to the catalog_entry organization.'})

    return attrs
```

The create branch uses `attrs['contact']` and `attrs['catalog_entry']` because those fields are required. If either field is missing, DRF should produce the required-field error before the contract is used. The update branch uses `self.instance.contact` and `self.instance.catalog_entry` directly because an existing instance must have those model fields.

### Avoid: Context Fallbacks For Route-Owned Scope

```python
def validate(self, attrs):
    attrs = super().validate(attrs)
    organization = self.context.get('organization') or attrs.get('organization') or getattr(self.instance, 'organization', None)

    if organization and attrs.get('email'):
        existing_queryset = Contact.objects.filter(organization=organization, email__iexact=attrs['email'])
        if existing_queryset.exists():
            raise serializers.ValidationError({'email': 'A contact with this email already exists.'})

    return attrs
```

This lets the payload, instance, or missing context compete for a protected scope value. It also silently skips organization-scoped uniqueness when the required context is absent.

### Prefer: Direct Context And Protected Persistence

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

    def validate_email(self, value):
        return value.strip().lower()

    def validate(self, attrs):
        attrs = super().validate(attrs)
        organization = self.context['organization']
        email = attrs.get('email', self.instance.email if self.instance else None)

        existing_queryset = Contact.objects.filter(organization=organization, email__iexact=email)
        if self.instance:
            existing_queryset = existing_queryset.exclude(pk=self.instance.pk)

        if existing_queryset.exists():
            raise serializers.ValidationError({'email': 'A contact with this email already exists in the organization.'})

        return attrs

    def create(self, validated_data):
        return Contact.objects.create(organization=self.context['organization'], **validated_data)
```

`organization` is route-owned context, so the serializer reads it directly with `self.context['organization']`. The payload cannot choose it, and the serializer does not keep running if the view forgot to pass it.

### Avoid: Broad Request Attribute Guards

```python
def get_access_context(self, request):
    if hasattr(request, 'access_context'):
        return request.access_context

    return AccessContext(request)
```

This hides middleware ordering problems and creates a second path for access decisions. If the middleware is part of the request contract, a missing attribute should be fixed at the middleware stack or test setup.

### Prefer: Direct Middleware-Owned Request Attributes

```python
class AccessContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.access_context = SimpleLazyObject(lambda: AccessContext(request))
        return self.get_response(request)


class AccessContextMixin:
    def get_access_context(self, request):
        return request.access_context

    def resolve_organization_scope(self, request, organization_id: int):
        return get_organization_scope(self.get_access_context(request), organization_id)
```

The middleware owns attaching the attribute. The base view owns consuming it. Tests that instantiate requests directly should attach the required attribute or use the request path that runs middleware; production code should not create a fallback access context in every view.

### Optional Data That Is Legitimately Optional

Optional access is appropriate when the domain says the value may be absent.

```python
class OrderCreateFromApprovedPlanInputSerializer(serializers.Serializer):
    shipping_address = serializers.PrimaryKeyRelatedField(queryset=ContactAddress.objects.none())
    coupon_code = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        approved_plan = self.context['approved_plan']
        shipping_address = attrs['shipping_address']
        coupon_code = attrs.get('coupon_code', '').strip().upper()

        if shipping_address.address_type != ContactAddress.AddressTypeChoices.SHIPPING:
            raise serializers.ValidationError({'shipping_address': 'Select a shipping address before creating an order.'})

        if coupon_code:
            coupon = Coupon.objects.filter(
                workspace=approved_plan.enrollment.catalog_entry.workspace,
                code__iexact=coupon_code,
            ).order_by('id').first()
            if coupon is None:
                raise serializers.ValidationError({'coupon_code': 'Enter a valid coupon code.'})

            attrs['coupon'] = coupon
            attrs['coupon_code'] = coupon_code
        else:
            attrs['coupon'] = None

        return attrs
```

`shipping_address` is required, so the serializer reads `attrs['shipping_address']`. `coupon_code` is optional by API contract, so the serializer uses `attrs.get('coupon_code', '')` and handles the empty case explicitly.

Optional queryset annotations are another legitimate case:

```python
def get_usage_count(self, obj):
    annotated_usage_count = getattr(obj, 'coupon_usage_count', None)
    if annotated_usage_count is not None:
        return annotated_usage_count

    return obj.usage_count
```

The annotation is optional because the same output serializer may be used with both annotated and unannotated querysets. The fallback is not hiding a required model field; it is selecting between two supported queryset shapes.

Nullable relations should also be explicit:

```python
item_option = attrs['item_option'] if 'item_option' in attrs else self.instance.item_option

if item_option and item_option.item_id != item.id:
    raise serializers.ValidationError({'item_option': 'This variant does not belong to the selected item.'})
```

The key may be absent on partial update, and the relation may be `None` by domain. The code distinguishes omitted, submitted-null, and existing values without using `getattr` or truthiness to guess the contract.

### Explicit Serializer Persistence Branches

When `create()` and `update()` compute snapshots, replace child rows, or attach protected scope, keep the branches direct.

```python
def create(self, validated_data):
    catalog_entry_subscription_plan = validated_data.get('catalog_entry_subscription_plan')
    validated_data['resolved_price_amount'] = (
        catalog_entry_subscription_plan.price_amount if catalog_entry_subscription_plan else None
    )
    return super().create(validated_data)


def update(self, instance, validated_data):
    catalog_entry_subscription_plan = validated_data.get(
        'catalog_entry_subscription_plan',
        instance.catalog_entry_subscription_plan,
    )
    validated_data['resolved_price_amount'] = (
        catalog_entry_subscription_plan.price_amount if catalog_entry_subscription_plan else None
    )
    return super().update(instance, validated_data)
```

The update path has a real fallback: an omitted PATCH field keeps the instance's current pricing plan. The create path has no instance fallback because there is no existing saved state.

## Things To Notice

- Required serializer context is read with `self.context['organization']`, `self.context['workspace']`, `self.context['approved_plan']`, or the equivalent direct key.
- Required submitted fields are read with `attrs['field_name']` or `validated_data['field_name']` after serializer validation has established they must exist.
- Update validation starts from `self.instance.field_name` and then applies submitted overrides with `if 'field_name' in attrs`.
- Optional submitted fields use `.get(...)` only because `required=False`, `allow_blank=True`, `allow_null=True`, or PATCH omission makes absence valid.
- Optional model relations are checked explicitly with `is None` or truthiness after the source of truth is known.
- Optional queryset annotations may use `getattr(obj, 'annotation_name', None)` when both annotated and unannotated querysets are supported.
- Middleware-guaranteed request attributes are consumed directly. Missing middleware is a configuration or test setup problem, not a runtime branch inside every view.
- Protected route scope does not fall back to payload scope. If the URL or access context owns `organization`, `workspace`, `catalog_entry`, `contact`, or `order`, the serializer should receive that object through context or injected serializer data.

## Rules To Follow

- Do not use `getattr(..., None)` for required model fields, serializer instances, serializer context values, request attributes, or validated-data keys.
- Do not use `hasattr(...)` to branch around request attributes that middleware or authentication guarantees.
- Do not use `.context.get(...)` for context keys that the view must provide.
- Do not let payload fields act as fallback scope for route-owned or middleware-owned identity.
- Do not chain required values with `or` when valid falsey values, missing contracts, and optional values need different meanings.
- For serializer update validation, start from direct `self.instance.<field>` values and override with submitted values only when the field is present in `attrs`.
- For serializer create validation, read required submitted values directly from `attrs[...]`.
- Use `.get(...)` for optional payload fields, omitted PATCH fields, nullable relations, and optional annotations only after the optional contract is visible in the serializer field, model field, or queryset shape.
- Custom `create()` and `update()` methods must return the saved instance and must keep route-owned scope direct.
- Tests must cover required-field errors, context-owned persistence, partial update behavior, optional values, and any create/update branch that computes or snapshots data.

## Refactor Signals

- `getattr(self.instance, 'field', None)` appears in a serializer for a real model field.
- `self.context.get('organization')`, `self.context.get('workspace')`, or similar context access appears in code where the view is required to pass that value.
- A serializer picks scope with `attrs.get('organization') or self.context.get('organization')` or `validated_data.get('workspace') or self.context['workspace']`.
- A view uses `hasattr(request, 'access_context')`, `getattr(request, 'user', None)`, or a local `AccessContext(request)` fallback.
- A validation method cannot clearly say which values come from create payload, existing instance state, route context, or optional user input.
- A partial-update serializer uses `attrs.get('field') or self.instance.field`, which treats submitted `None`, empty strings, false booleans, and omitted fields as the same case.
- A serializer catches broad exceptions or skips validation when a required value is missing instead of letting the required-field, context, or attribute error expose the broken contract.
- Tests only cover happy-path creation and do not cover missing required fields, partial updates, context-owned scope, or optional-null relationships.

## Verification

- Run `ruff check` on any modified Python files that implement this standard.
- Run targeted serializer tests when changing serializer contracts, such as `pytest backend/contact/tests/test_serializers.py::TestContactInputSerializer`.
- Add or update tests for create and update paths when validation merges `attrs` with `self.instance`.
- Add tests proving route-owned context is used for persistence, for example that a created contact, coupon, mapping target, or membership belongs to the context organization or workspace.
- Add tests for optional fields that are allowed to be missing, blank, or null so reviewers can distinguish legitimate optional branches from defensive fallbacks.
- Add view or middleware tests when changing request-owned context, especially when `request.access_context`, `request.user`, organization membership, or workspace membership is part of the contract.
- For guidance-only edits, check that Markdown frontmatter remains valid and code fences are balanced.

## Why It Helps

- `getattr(..., None)` hides whether the field is actually part of the contract.
- Direct access expresses that the attribute should exist and fails loudly when the assumption is wrong.
- Explicit branching keeps create and update paths readable.
- Route-owned and middleware-owned scope stays auditable.
- Optional data stays intentional instead of becoming a blanket excuse for best-effort behavior.
- Tests become more meaningful because they prove contracts rather than preserving defensive branches.
