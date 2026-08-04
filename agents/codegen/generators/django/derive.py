"""Django-only derivations over a framework-neutral ResourceSpec.

These used to be properties on the spec. They live here because a TypeScript target
has no opinion about `raw_id_fields` or where `serializers.py` goes, and the shared
spec should not carry one framework's vocabulary.
"""

from agents.codegen.generators.django.profile import build_django_profile
from agents.codegen.resource import TIMESTAMP_FIELDS, ResourceSpec


IDENTITY_NAMES = frozenset({'name', 'slug', 'code', 'title', 'label', 'key', 'email', 'reference'})
SCANNABLE_KINDS = frozenset(
    {'choice', 'bool', 'int', 'positive_int', 'big_int', 'decimal', 'float', 'date', 'datetime'}
)
FILTERABLE_KINDS = frozenset({'choice', 'bool'})


def layout(spec: ResourceSpec) -> str:
    return spec.options('django').get('layout') or build_django_profile(spec.profile).layout


def model_layout(spec: ResourceSpec) -> str:
    return spec.options('django').get('model_layout') or build_django_profile(spec.profile).model_layout


def views_package(spec: ResourceSpec) -> str:
    """The package that owns views.py, serializers.py, and the feature urls.py."""
    if layout(spec) == 'flat':
        return spec.app

    return f'{spec.app}.views.{spec.feature}'


def serializers_module(spec: ResourceSpec) -> str:
    return f'{views_package(spec)}.serializers'


def models_module(spec: ResourceSpec) -> str:
    return f'{spec.app}.models'


def feature_dir(spec: ResourceSpec) -> str:
    if layout(spec) == 'flat':
        return spec.app

    return f'{spec.app}/views/{spec.feature}'


def admin_list_display(spec: ResourceSpec) -> tuple[str, ...]:
    """Identity, state, and ordering columns. Long-form text stays off the grid."""
    override = spec.options('django').get('list_display')

    if override:
        return tuple(override)

    columns: list[str] = ['id']

    for field in spec.fields:
        if field.is_relation or field.kind in SCANNABLE_KINDS:
            columns.append(field.name)
            continue

        if field.name in IDENTITY_NAMES or field.name == spec.str_field:
            columns.append(field.name)

    return (*columns, *TIMESTAMP_FIELDS)


def raw_id_fields(spec: ResourceSpec) -> tuple[str, ...]:
    override = spec.options('django').get('raw_id_fields')

    if override:
        return tuple(override)

    return tuple(field.name for field in spec.relation_fields)


def list_filter(spec: ResourceSpec) -> tuple[str, ...]:
    override = spec.options('django').get('list_filter')

    if override:
        return tuple(override)

    names = [field.name for field in spec.fields if field.kind in FILTERABLE_KINDS]

    if spec.scope and spec.scope_field is not None and spec.scope_field.is_relation:
        names.append(spec.scope)

    return tuple(names)


def history_log_fields(spec: ResourceSpec) -> tuple[str, ...]:
    override = spec.options('django').get('history_log_fields')

    if override:
        return tuple(override)

    return spec.blocked_fields
