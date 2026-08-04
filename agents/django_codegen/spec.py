from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Optional

import yaml

from agents.django_codegen.fields import Field, SpecError, parse_field
from agents.django_codegen.naming import (
    class_case,
    kebab_case,
    plural_kebab,
    plural_snake,
    snake_case,
    title_case,
)
from agents.django_codegen.profile import Profile


TIMESTAMP_FIELDS = ('created_ts', 'updated_ts')
SEARCH_EXCLUDED_NAMES = frozenset({'description', 'summary', 'notes', 'body', 'content', 'message', 'payload'})
SEARCHABLE_KINDS = frozenset({'text', 'slug', 'email', 'url'})
FILTERABLE_KINDS = frozenset({'choice', 'bool'})
IDENTITY_NAMES = frozenset({'name', 'slug', 'code', 'title', 'label', 'key', 'email', 'reference'})
SCANNABLE_KINDS = frozenset({'choice', 'bool', 'int', 'positive_int', 'big_int', 'decimal', 'float', 'date', 'datetime'})
DEFAULT_ENDPOINTS = ('list', 'create', 'detail')
SUPPORTED_ENDPOINTS = frozenset({'list', 'create', 'detail', 'delete'})
SUPPORTED_SPEC_KEYS = frozenset(
    {
        'app',
        'model',
        'scope',
        'choices',
        'fields',
        'unique',
        'ordering',
        'search',
        'filters',
        'actions',
        'endpoints',
        'permission',
        'feature',
        'path_segment',
        'id_kwarg',
        'namespace',
        'list_filter',
        'history_log_fields',
        'str_field',
        'validate_scope',
        'layout',
        'annotations',
        'select_related',
    }
)


@dataclass(frozen=True)
class ChoiceGroup:
    field_name: str
    members: tuple[str, ...]

    @property
    def class_name(self) -> str:
        return f'{class_case(self.field_name)}Choices'

    def label(self, member: str) -> str:
        return title_case(member)

    @property
    def first(self) -> str:
        return self.members[0]


@dataclass(frozen=True)
class Filter:
    param: str
    kind: str
    fields: tuple[str, ...]

    @property
    def variable(self) -> str:
        return 'search' if self.kind == 'search' else f'{self.param}_filter'


@dataclass(frozen=True)
class Action:
    name: str
    assignments: tuple[tuple[str, str], ...]

    @property
    def kebab(self) -> str:
        return kebab_case(self.name)

    @property
    def class_fragment(self) -> str:
        return class_case(self.name)

    @property
    def fields(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self.assignments)


@dataclass(frozen=True)
class ScopeCheck:
    field: str
    parent: str


@dataclass(frozen=True)
class ResourceSpec:
    app: str
    model: str
    scope: Optional[str]
    feature: str
    fields: tuple[Field, ...]
    choices: tuple[ChoiceGroup, ...]
    unique: tuple[str, ...]
    unique_name: Optional[str]
    ordering: tuple[str, ...]
    search_fields: tuple[str, ...]
    list_filter: tuple[str, ...]
    filters: tuple[Filter, ...]
    actions: tuple[Action, ...]
    endpoints: tuple[str, ...]
    permission: str
    path_segment: str
    id_kwarg: str
    namespace: str
    history_log_fields: tuple[str, ...]
    str_field: Optional[str]
    scope_checks: tuple[ScopeCheck, ...]
    layout: str
    annotations: tuple[tuple[str, str], ...]
    select_related: tuple[str, ...]
    profile: Profile
    path: Optional[Path] = None

    @property
    def resource(self) -> str:
        return snake_case(self.model)

    @property
    def resource_kebab(self) -> str:
        return kebab_case(self.model)

    @property
    def related_name(self) -> str:
        return plural_snake(self.model)

    @property
    def scope_chain(self) -> tuple[str, ...]:
        return self.profile.scope_chain(self.scope)

    @property
    def scope_kwargs(self) -> tuple[str, ...]:
        return self.profile.scope_kwargs(self.scope)

    @property
    def scope_field(self) -> Optional[Field]:
        if not self.scope:
            return None

        return next((field for field in self.fields if field.name == self.scope), None)

    @property
    def relation_fields(self) -> tuple[Field, ...]:
        return tuple(field for field in self.fields if field.is_relation)

    @property
    def choice_fields(self) -> tuple[Field, ...]:
        return tuple(field for field in self.fields if field.kind == 'choice')

    @property
    def input_fields(self) -> tuple[str, ...]:
        return ('id', *(field.name for field in self.fields))

    @property
    def output_fields(self) -> tuple[str, ...]:
        return ('id', *(field.name for field in self.fields), *TIMESTAMP_FIELDS)

    @property
    def admin_list_display(self) -> tuple[str, ...]:
        columns: list[str] = ['id']

        for field in self.fields:
            if field.is_relation or field.kind in SCANNABLE_KINDS:
                columns.append(field.name)
                continue

            if field.name in IDENTITY_NAMES or field.name == self.str_field:
                columns.append(field.name)

        return (*columns, *TIMESTAMP_FIELDS)

    @property
    def raw_id_fields(self) -> tuple[str, ...]:
        return tuple(field.name for field in self.relation_fields)

    @property
    def blocked_fields(self) -> tuple[str, ...]:
        blocked: list[str] = []

        for action in self.actions:
            for name in action.fields:
                if name not in blocked:
                    blocked.append(name)

        return tuple(blocked)

    def action_for_field(self, name: str) -> Optional[Action]:
        return next((action for action in self.actions if name in action.fields), None)

    def choice_group(self, name: str) -> Optional[ChoiceGroup]:
        return next((group for group in self.choices if group.field_name == name), None)

    @property
    def route_name_prefix(self) -> str:
        return self.resource_kebab

    def route_name(self, suffix: str) -> str:
        return f'{self.route_name_prefix}-{suffix}'

    def full_route_name(self, suffix: str) -> str:
        return f'{self.namespace}:{self.route_name(suffix)}'

    @property
    def views_package(self) -> str:
        """The package that owns views.py, serializers.py, and the feature urls.py."""
        if self.layout == 'flat':
            return self.app

        return f'{self.app}.views.{self.feature}'

    @property
    def serializers_module(self) -> str:
        return f'{self.views_package}.serializers'

    @property
    def models_module(self) -> str:
        return f'{self.app}.models'

    @property
    def feature_dir(self) -> str:
        if self.layout == 'flat':
            return self.app

        return f'{self.app}/views/{self.feature}'

    @property
    def url_prefix(self) -> str:
        segments = [self.profile.api_prefix.strip('/')]

        for scope in self.scope_chain:
            segments.append(self.profile.url_segment(scope))
            segments.append(f'{{self.{scope}.id}}')

        segments.append(self.path_segment)
        return '/' + '/'.join(segment for segment in segments if segment) + '/'


def load_spec(path: Path, profile: Profile) -> ResourceSpec:
    raw = yaml.safe_load(path.read_text(encoding='utf-8')) or {}

    if not isinstance(raw, dict):
        message = f'Spec {path} must contain a mapping.'
        raise SpecError(message)

    return build_spec(raw, profile, path)


def build_spec(raw: dict[str, Any], profile: Profile, path: Optional[Path] = None) -> ResourceSpec:
    unknown_keys = set(raw) - SUPPORTED_SPEC_KEYS
    if unknown_keys:
        message = f'Unsupported spec keys: {", ".join(sorted(unknown_keys))}.'
        raise SpecError(message)

    for required in ('app', 'model', 'fields'):
        if not raw.get(required):
            message = f'Spec is missing required key {required!r}.'
            raise SpecError(message)

    model = raw['model']
    app = raw['app']
    scope = raw.get('scope')
    feature = raw.get('feature') or snake_case(model)
    fields = tuple(parse_field(name, value) for name, value in raw['fields'].items())
    choices = build_choices(raw.get('choices') or {})

    validate_field_choices(fields, choices)
    fields = apply_choice_defaults(fields, choices)

    unique = tuple(raw.get('unique') or ())
    layout = raw.get('layout') or profile.layout

    return ResourceSpec(
        app=app,
        model=model,
        scope=scope,
        feature=feature,
        fields=fields,
        choices=choices,
        unique=unique,
        unique_name=derive_unique_name(model, unique) if unique else None,
        ordering=tuple(raw.get('ordering') or derive_ordering(fields)),
        search_fields=tuple(raw.get('search') or derive_search_fields(fields)),
        list_filter=tuple(raw.get('list_filter') or derive_list_filter(fields, scope)),
        filters=build_filters(raw.get('filters') or ()),
        actions=build_actions(raw.get('actions') or {}),
        endpoints=build_endpoints(raw.get('endpoints') or DEFAULT_ENDPOINTS),
        permission=raw.get('permission') or profile.default_permission,
        path_segment=raw.get('path_segment') or plural_kebab(model),
        id_kwarg=raw.get('id_kwarg') or f'{snake_case(model)}_id',
        namespace=raw.get('namespace') or derive_namespace(profile, scope, app),
        history_log_fields=tuple(raw.get('history_log_fields') or ()),
        str_field=raw.get('str_field') or derive_str_field(fields),
        scope_checks=tuple(ScopeCheck(field=key, parent=value) for key, value in (raw.get('validate_scope') or {}).items()),
        layout=layout,
        annotations=tuple((entry['name'], entry['count']) for entry in raw.get('annotations') or ()),
        select_related=tuple(raw.get('select_related') or ()),
        profile=profile,
        path=path,
    )


def build_choices(raw_choices: dict[str, Any]) -> tuple[ChoiceGroup, ...]:
    groups: list[ChoiceGroup] = []

    for field_name, members in raw_choices.items():
        if not members:
            message = f'Choice group {field_name} needs at least one member.'
            raise SpecError(message)

        groups.append(ChoiceGroup(field_name=field_name, members=tuple(members)))

    return tuple(groups)


def apply_choice_defaults(fields: tuple[Field, ...], choices: tuple[ChoiceGroup, ...]) -> tuple[Field, ...]:
    by_name = {group.field_name: group for group in choices}
    resolved: list[Field] = []

    for field in fields:
        if field.kind == 'choice' and field.default is None and not field.no_default:
            resolved.append(replace(field, default=by_name[field.choices].first))
            continue

        resolved.append(field)

    return tuple(resolved)


def validate_field_choices(fields: tuple[Field, ...], choices: tuple[ChoiceGroup, ...]) -> None:
    declared = {group.field_name for group in choices}

    for field in fields:
        if field.kind == 'choice' and field.choices not in declared:
            known = ', '.join(sorted(declared)) or 'none declared'
            message = f'Field {field.name} references choice group {field.choices!r} which is not declared. Known groups: {known}.'
            raise SpecError(message)


def derive_unique_name(model: str, unique: tuple[str, ...]) -> str:
    if len(unique) == 1:
        return f'unique_{snake_case(model)}_{unique[0]}'

    return f'unique_{snake_case(model)}_{unique[-1]}_per_{unique[0]}'


def derive_ordering(fields: tuple[Field, ...]) -> tuple[str, ...]:
    names = {field.name for field in fields}

    if 'sort_order' in names:
        return ('sort_order', 'id')

    return ('id',)


def derive_search_fields(fields: tuple[Field, ...]) -> tuple[str, ...]:
    return tuple(
        field.name
        for field in fields
        if field.kind in SEARCHABLE_KINDS and field.name not in SEARCH_EXCLUDED_NAMES
    )


def derive_list_filter(fields: tuple[Field, ...], scope: Optional[str]) -> tuple[str, ...]:
    names = [field.name for field in fields if field.kind in FILTERABLE_KINDS]

    if scope and any(field.name == scope and field.is_relation for field in fields):
        names.append(scope)

    return tuple(names)


def derive_str_field(fields: tuple[Field, ...]) -> Optional[str]:
    names = {field.name for field in fields}

    for candidate in ('name', 'title', 'label', 'code', 'slug', 'email'):
        if candidate in names:
            return candidate

    return None


def derive_namespace(profile: Profile, scope: Optional[str], app: str) -> str:
    prefix = profile.namespace_prefix(scope)
    return f'{prefix}:{app}' if prefix else app


def build_filters(raw_filters: Any) -> tuple[Filter, ...]:
    filters: list[Filter] = []

    for entry in raw_filters:
        if not isinstance(entry, str):
            message = f'Filter entries must be strings, got {type(entry).__name__}.'
            raise SpecError(message)

        param, _, targets = entry.partition('=')
        param = param.strip()

        if param == 'search':
            fields = tuple(target.strip() for target in targets.split(',') if target.strip())

            if not fields:
                message = 'The search filter needs at least one field, such as "search=name".'
                raise SpecError(message)

            filters.append(Filter(param=param, kind='search', fields=fields))
            continue

        target = targets.strip() or param
        filters.append(Filter(param=param, kind='choice', fields=(target,)))

    return tuple(filters)


def build_actions(raw_actions: dict[str, Any]) -> tuple[Action, ...]:
    actions: list[Action] = []

    for name, raw_assignments in raw_actions.items():
        if not raw_assignments:
            message = (
                f'Action {name} needs at least one assignment such as "status=INACTIVE". '
                'Actions with real business rules should be written by hand.'
            )
            raise SpecError(message)

        assignments: list[tuple[str, str]] = []

        for chunk in str(raw_assignments).split(','):
            key, separator, value = chunk.partition('=')

            if not separator:
                message = f'Action {name} assignment {chunk.strip()!r} must use field=VALUE form.'
                raise SpecError(message)

            assignments.append((key.strip(), value.strip()))

        actions.append(Action(name=snake_case(name), assignments=tuple(assignments)))

    return tuple(actions)


def build_endpoints(raw_endpoints: Any) -> tuple[str, ...]:
    endpoints = tuple(raw_endpoints)
    unsupported = set(endpoints) - SUPPORTED_ENDPOINTS

    if unsupported:
        message = f'Unsupported endpoints: {", ".join(sorted(unsupported))}. Supported: {", ".join(sorted(SUPPORTED_ENDPOINTS))}.'
        raise SpecError(message)

    return endpoints
