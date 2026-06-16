---
id: framework-django-example-concrete-model-meta
title: Concrete Model Meta
description: Prefer plain concrete Django model Meta classes unless inheriting abstract Meta is an intentional model-options contract.
kind: example
scope: framework
name: django
tags:
  - django
  - models
  - antipatterns
applies_to:
  - django
status: active
order: 20
---

# Concrete Model Meta

## Scenario

- Use this when a concrete Django model extends an abstract base model such as `BaseModel`.
- Use this when a concrete model needs its own `ordering`, `constraints`, `permissions`, `default_permissions`, or `default_related_name`.
- Use this when reviewing model changes that subclass an abstract base model's `Meta` only to set `abstract = False`.
- Use this when distinguishing Django model `Meta` inheritance from serializer `Meta` inheritance.

## Why This Shape Exists

- Django field inheritance and Django `Meta` inheritance are different mechanisms. Concrete models inherit fields from abstract base models without needing to subclass the base model's `Meta`.
- `BaseModel` gives repository models `created_ts`, `updated_ts`, and audit history through normal abstract model inheritance. Concrete model `Meta` classes should show only the concrete model options that actually apply to that table.
- Subclassing an abstract base `Meta` just to write `abstract = False` makes reviewers ask which options were intentionally inherited. If the base `Meta` later gains `ordering`, `permissions`, `constraints`, or `default_related_name`, every concrete child that subclasses it may silently inherit behavior it did not ask for.
- Model `Meta` options affect schema and runtime behavior. Some options produce migrations, some affect default query order, and some create permissions. Keeping the concrete model's options explicit makes those effects reviewable.
- Serializer `Meta` inheritance is a separate pattern. serializers may intentionally inherit another serializer's `Meta` to extend a `fields` tuple for detail output. Do not apply this model anti-pattern to serializers.

## Recommended Shape

### Avoid Inheriting Abstract Meta Just To Make A Concrete Model

```python
from core.base_models import BaseModel
from django.db import models
from django.utils.translation import gettext


class Item(BaseModel):
	class Meta(BaseModel.Meta):
		abstract = False
		constraints = (
			models.UniqueConstraint(fields=('collection', 'code'), name='unique_item_code_per_collection'),
		)
		ordering = ('sort_order', 'id')

	collection = models.ForeignKey('catalog.Collection', related_name='items', null=False, blank=False, verbose_name=gettext('Collection'), on_delete=models.DO_NOTHING)
	name = models.TextField(null=False, blank=False, verbose_name=gettext('Name'))
	code = models.TextField(null=False, blank=False, verbose_name=gettext('Code'))
	sort_order = models.PositiveIntegerField(default=0, null=False, blank=False, verbose_name=gettext('Sort Order'))
```

This shape adds a second inheritance story even though the model already inherits the base fields and base methods from `BaseModel`. It also makes inherited model options look accidental instead of deliberate.

### Prefer A Plain Concrete Meta

```python
from core.base_models import BaseModel
from django.db import models
from django.utils.translation import gettext


class Item(BaseModel):
	class Meta:
		constraints = (
			models.UniqueConstraint(fields=('collection', 'code'), name='unique_item_code_per_collection'),
		)
		ordering = ('sort_order', 'id')

	collection = models.ForeignKey('catalog.Collection', related_name='items', null=False, blank=False, verbose_name=gettext('Collection'), on_delete=models.DO_NOTHING)
	name = models.TextField(null=False, blank=False, verbose_name=gettext('Name'))
	code = models.TextField(null=False, blank=False, verbose_name=gettext('Code'))
	sort_order = models.PositiveIntegerField(default=0, null=False, blank=False, verbose_name=gettext('Sort Order'))
```

This is the repository-standard shape for concrete models that extend `BaseModel`. The concrete table gets the inherited fields and methods, while its `Meta` shows the concrete table's own constraints and ordering.

### Fields Still Inherit Without Meta Inheritance

```python
class BaseModel(models.Model):
	created_ts = models.DateTimeField(auto_now_add=True, verbose_name=gettext('Created Time'))
	updated_ts = models.DateTimeField(auto_now=True, verbose_name=gettext('Updated Time'))

	class Meta:
		abstract = True


class Organization(BaseModel):
	class Meta:
		ordering = ('id',)

	name = models.TextField(null=False, blank=False, verbose_name=gettext('Name'))
	code = models.TextField(null=False, blank=False, verbose_name=gettext('Code'))
```

`Organization` still has `created_ts` and `updated_ts` because those are model fields declared on the abstract base class. The plain child `Meta` does not remove inherited fields, methods, class attributes, or lifecycle behavior.

### Inherit Abstract Meta Only When The Options Are The Contract

```python
class ScopedModel(BaseModel):
	scope = models.ForeignKey('tenancy.Organization', related_name='%(app_label)s_%(class)s_records', null=False, blank=False, verbose_name=gettext('Organization'), on_delete=models.DO_NOTHING)

	class Meta:
		abstract = True
		default_related_name = '%(app_label)s_%(class)s_records'
		permissions = (
			('view_scoped_records', 'Can view scoped records'),
		)


class Report(ScopedModel):
	class Meta(ScopedModel.Meta):
		constraints = (
			models.UniqueConstraint(fields=('scope', 'code'), name='unique_report_code_per_scope'),
		)
		ordering = ('scope_id', 'code', 'id')

	name = models.TextField(null=False, blank=False, verbose_name=gettext('Name'))
	code = models.TextField(null=False, blank=False, verbose_name=gettext('Code'))
```

This is intentional inheritance: the child wants the abstract base's model options and adds its own concrete table options. The inherited options should be part of the base model's documented contract, not an accident caused by copying `class Meta(Base.Meta): abstract = False`.

When an abstract base defines `default_related_name`, `related_name`, constraint names, or index names that may be reused by many concrete children, include Django's substitution tokens such as `%(app_label)s` and `%(class)s` where needed so generated names stay unique.

### Keep Serializer Meta Inheritance Separate

```python
class ContactOutputSerializer(serializers.ModelSerializer):
	class Meta:
		model = Contact
		fields = (
			'id',
			'organization',
			'email',
			'created_ts',
			'updated_ts',
		)
		read_only_fields = fields


class ContactDetailOutputSerializer(ContactOutputSerializer):
	addresses = ContactAddressOutputSerializer(many=True, read_only=True)

	class Meta(ContactOutputSerializer.Meta):
		fields = (
			*ContactOutputSerializer.Meta.fields,
			'addresses',
		)
		read_only_fields = fields
```

Serializer `Meta` inheritance is acceptable when a derived serializer intentionally extends another serializer's `fields` or read-only contract. Serializer `Meta` does not create database tables, migrations, indexes, constraints, default query ordering, or Django permissions.

## Things To Notice

- The concrete model extends `BaseModel` but uses a plain `class Meta:` for its own options.
- Inherited fields and methods come from the abstract model class body, not from inheriting `BaseModel.Meta`.
- `abstract = False` is not needed on concrete children. A concrete child becomes concrete by not declaring `abstract = True` in its own effective model options.
- `constraints`, `ordering`, `permissions`, `default_permissions`, and `default_related_name` are model options. Treat them as part of the concrete model contract.
- Abstract `Meta` inheritance is fine when the child deliberately keeps base model options. Make the inherited options obvious in the abstract base and keep child additions explicit.
- Serializer `Meta` inheritance is a different review question from model `Meta` inheritance.

## Rules To Follow

- Do not write `class Meta(AbstractBase.Meta): abstract = False` on concrete Django models just to turn an abstract base into a concrete table.
- Use a plain `class Meta:` on concrete models when the model only needs its own `ordering`, `constraints`, permissions, or other table options.
- Inherit an abstract base model's `Meta` only when the inherited options are an intentional contract for every child using that pattern.
- If an abstract base model defines reusable constraints, indexes, relation names, or default related names, ensure generated names are unique per concrete child.
- Keep concrete model options explicit enough that a reviewer can predict migrations, permissions, default ordering, and reverse relation names from the child model.
- Do not use this example to reject serializer `Meta` inheritance that intentionally extends serializer fields or read-only behavior.
- Add or update model tests and migrations when changing model `Meta` options that affect constraints, permissions, ordering, indexes, or reverse relation names.

## Refactor Signals

- A concrete model subclasses `BaseModel.Meta` and sets only `abstract = False`.
- A concrete model inherits `Meta` from an abstract base whose options are not documented or not relevant to that child table.
- A future edit to an abstract base `Meta` would unexpectedly alter migrations, permissions, query ordering, or reverse relations for many concrete models.
- A model's constraints, permissions, or ordering are hard to identify because some are inherited and some are declared locally without explanation.
- A migration appears after a harmless-looking base `Meta` change and affects multiple concrete models that did not deliberately opt in.
- Tests rely on implicit queryset ordering from an inherited abstract `Meta` instead of the concrete model declaring the order it needs.
- Review discussion confuses serializer `Meta` inheritance with Django model `Meta` inheritance.

## Verification

- For a guidance-only edit, check that Markdown frontmatter remains valid and code fences are balanced.
- When changing real model code, run `python manage.py makemigrations --check --dry-run` or the project's equivalent task to confirm whether `Meta` option changes create migrations.
- Run targeted model tests for changed constraints, ordering, permissions, or reverse relation behavior.
- For constraint changes, add tests that prove duplicate records fail at the intended scope.
- For ordering changes, assert the returned order in model, serializer, or view tests that depend on it.
- For permission changes, verify the generated permission codename and any group or access tests that grant it.
- For `default_related_name` changes, verify reverse relation names from the related model and check migrations if relation metadata changed.
- Run `ruff check` on modified Python files. For Markdown-only guidance changes, run the guidance builder when practical.

## Why It Helps

- Concrete model options stay visible at the table that owns them.
- Abstract base models can still provide shared fields and behavior without making every child inherit hidden table options.
- Intentional abstract `Meta` inheritance remains available for real model-option contracts.
- Migrations become easier to review because constraints, ordering, permissions, and relation naming changes are tied to explicit model declarations.
- Tests can target the behavior that changed instead of reverse-engineering inherited options.
- Reviewers can distinguish the Django model rule from the separate serializer `Meta` extension pattern.
