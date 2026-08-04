from dataclasses import dataclass, field as dataclass_field
from typing import Any, Optional

from agents.django_codegen.fields import Field, render_declaration
from agents.django_codegen.naming import python_tuple, title_case
from agents.django_codegen.renderer import build_environment, render_template
from agents.django_codegen.spec import ResourceSpec


@dataclass(frozen=True)
class GeneratedFile:
    path: str
    content: str
    merge: bool = False
    note: str = ''


@dataclass(frozen=True)
class Route:
    """Precomputed scope-resolution facts shared by every generated view."""

    chain: tuple[str, ...]
    kwargs: tuple[str, ...]
    resolver: str
    parent: Optional[str]
    permission_scope: Optional[str]
    queryset_base: str
    id_kwarg: str
    detail_resolver: Optional[str] = None
    extra_imports: tuple[tuple[str, str], ...] = dataclass_field(default_factory=tuple)

    @property
    def resolver_args(self) -> str:
        return ', '.join(('request', *self.kwargs))

    @property
    def detail_resolver_args(self) -> str:
        return ', '.join(('request', *self.kwargs, self.id_kwarg))

    def params(self, detail: bool = False) -> str:
        names = [*self.kwargs, self.id_kwarg] if detail else list(self.kwargs)
        typed = ', '.join(f'{name}: int' for name in names)
        return f'request, {typed}' if typed else 'request'

    def unpack(self, needed: tuple[str, ...] = (), leaf: Optional[str] = None) -> str:
        parts = [name if name in needed else '_' for name in self.chain]

        if leaf is not None:
            parts.append(leaf)

        return ', '.join(parts)


def build_route(spec: ResourceSpec) -> Route:
    profile = spec.profile
    chain = spec.scope_chain
    parent = chain[-1] if chain else None
    permission_scope = profile.permission_scope if profile.permission_scope in chain else parent
    scope_field = spec.scope_field
    extra_imports: list[tuple[str, str]] = []

    if parent and scope_field is not None:
        queryset_base = f'{parent}.{scope_field.related_name or spec.related_name}'
    else:
        queryset_base = f'{spec.model}.objects'
        extra_imports.append((spec.models_module, spec.model))

    return Route(
        chain=chain,
        kwargs=spec.scope_kwargs,
        resolver=profile.scope_resolver(parent) if parent else '',
        parent=parent,
        permission_scope=permission_scope,
        queryset_base=queryset_base,
        id_kwarg=spec.id_kwarg,
        detail_resolver=profile.scope_resolver(spec.resource) if profile.detail_lookup == 'resource_resolver' else None,
        extra_imports=tuple(extra_imports),
    )


def sample_value(spec: ResourceSpec, field: Field) -> str:
    if field.kind == 'choice':
        group = spec.choice_group(field.choices)
        member = field.default or group.first
        return f'{spec.model}.{group.class_name}.{member}'

    if field.kind == 'bool':
        return 'True'

    if field.kind in {'int', 'positive_int', 'big_int'}:
        return '1'

    if field.kind == 'float':
        return '1.0'

    if field.kind == 'decimal':
        return "'1.00'"

    if field.kind == 'email':
        return "'generated@example.com'"

    if field.kind == 'json':
        return '[]'

    if field.name == spec.str_field:
        return f"'Generated {title_case(spec.model)}'"

    return f"'generated-{field.name.replace('_', '-')}'"


def alternate_choice_value(spec: ResourceSpec, field_name: str) -> str:
    field = next((entry for entry in spec.fields if entry.name == field_name), None)

    if field is None or field.kind != 'choice':
        return "'changed'"

    group = spec.choice_group(field.choices)
    current = field.default or group.first
    alternate = next((member for member in group.members if member != current), current)
    return f'{spec.model}.{group.class_name}.{alternate}'


def build_chain_setup(spec: ResourceSpec, *, include_other: bool) -> list[str]:
    profile = spec.profile
    lines: list[str] = []

    for index, scope in enumerate(spec.scope_chain):
        parent = spec.scope_chain[index - 1] if index else None
        argument = f'self.{parent}' if parent else ''
        other_argument = f'self.other_{parent}' if parent else ''
        lines.append(f'self.{scope} = {profile.fixtures_name}.create_{scope}({argument})')

        if include_other:
            lines.append(f'self.other_{scope} = {profile.fixtures_name}.create_{scope}({other_argument})')

    return lines


def build_membership_setup(spec: ResourceSpec) -> list[str]:
    profile = spec.profile
    lines: list[str] = []

    for role in profile.roles:
        for membership in role.memberships:
            model_name = profile.membership_model_name(membership.scope)
            lines.append(
                f'{profile.fixtures_name}.{membership.builder}('
                f'self.{role.name}, self.{membership.target}, role={model_name}.RoleChoices.{membership.role})'
            )

    return lines


def build_payload(spec: ResourceSpec) -> list[dict[str, str]]:
    return [
        {'name': field.name, 'value': sample_value(spec, field)}
        for field in spec.fields
        if field.name != spec.scope and not field.null and field.name not in spec.blocked_fields
    ]


def build_blocked(spec: ResourceSpec) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []

    for name in spec.blocked_fields:
        action = spec.action_for_field(name)
        resource_words = spec.resource.replace('_', ' ')
        action_words = action.name.replace('_', ' ') if action else 'dedicated'
        field_words = name.replace('_', ' ')
        entries.append(
            {
                'field': name,
                'message': f'Use the {resource_words} {action_words} action to change {field_words}.',
                'other_value': alternate_choice_value(spec, name),
            }
        )

    return entries


def build_actions(spec: ResourceSpec) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []

    for action in spec.actions:
        assignments = []

        for name, raw_value in action.assignments:
            field = next((entry for entry in spec.fields if entry.name == name), None)

            if field is not None and field.kind == 'choice':
                group = spec.choice_group(field.choices)
                value = f'{spec.model}.{group.class_name}.{raw_value}'
            elif field is not None and field.kind == 'bool':
                value = 'True' if raw_value.lower() in {'true', 'yes', '1'} else 'False'
            elif field is not None and field.kind in {'int', 'positive_int', 'big_int', 'float', 'decimal'}:
                value = raw_value
            else:
                value = f"'{raw_value}'"

            assignments.append({'field': name, 'value': value})

        update_fields = ', '.join(f"'{name}'" for name in (*action.fields, 'updated_ts'))
        actions.append(
            {
                'name': action.name,
                'kebab': action.kebab,
                'class_fragment': action.class_fragment,
                'assignments': assignments,
                'update_fields': update_fields,
            }
        )

    return actions


def build_filters(spec: ResourceSpec) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []

    for entry in spec.filters:
        choices_class = ''

        if entry.kind == 'choice':
            field = next((item for item in spec.fields if item.name == entry.fields[0]), None)
            group = spec.choice_group(field.choices) if field is not None and field.kind == 'choice' else None
            choices_class = group.class_name if group else ''

        search_expression = ' | '.join(f'Q({name}__icontains={entry.variable})' for name in entry.fields)
        entries.append(
            {
                'param': entry.param,
                'kind': entry.kind,
                'variable': entry.variable,
                'fields': list(entry.fields),
                'search_expression': search_expression,
                'choices_class': choices_class,
            }
        )

    return entries


def build_queryset_suffix(spec: ResourceSpec) -> str:
    suffix = ''

    if spec.select_related:
        arguments = ', '.join(f"'{name}'" for name in spec.select_related)
        suffix += f'.select_related({arguments})'

    for name, target in spec.annotations:
        suffix += f".annotate({name}=Count('{target}', distinct=True))"

    return suffix


def build_common_context(spec: ResourceSpec) -> dict[str, Any]:
    profile = spec.profile
    route = build_route(spec)
    payload = build_payload(spec)
    parent = route.parent
    update_field = spec.str_field or (payload[0]['name'] if payload else None)

    if update_field:
        update_payload = f"{{'{update_field}': 'Updated {title_case(spec.model)}'}}"
    else:
        update_payload = '{}'

    create_lookup_parts: list[str] = []
    if spec.scope:
        create_lookup_parts.append(f'{spec.scope}=self.{spec.scope}')
    if spec.str_field:
        create_lookup_parts.append(f"{spec.str_field}='Generated {title_case(spec.model)}'")

    unique_kwargs = ', '.join(
        f"{name}='duplicate-{name.replace('_', '-')}'" for name in spec.unique if name != spec.scope
    )

    return {
        'spec': spec,
        'route': route,
        'fixtures_name': profile.fixtures_name,
        'base_view_name': profile.base_view_name,
        'base_model_name': profile.base_model_name,
        'chain_setup': build_chain_setup(spec, include_other=False),
        'full_chain_setup': build_chain_setup(spec, include_other=True),
        'membership_setup': build_membership_setup(spec),
        'parent_argument': f'self.{parent}' if parent else '',
        'other_parent_argument': f'self.other_{parent}' if parent else '',
        'payload': payload,
        'payload_lines': [f"'{entry['name']}': {entry['value']}," for entry in payload],
        'required': [entry for entry in payload if entry['name'] == spec.str_field],
        'blocked': build_blocked(spec),
        'actions': build_actions(spec),
        'filters': build_filters(spec),
        'queryset_suffix': build_queryset_suffix(spec),
        'create_lookup': ', '.join(create_lookup_parts),
        'update_payload': update_payload,
        'unique_kwargs': unique_kwargs,
        'output_fields': list(spec.output_fields),
        'detail_lookup': profile.detail_lookup,
        'ordering': ', '.join(f"'{name}'" for name in spec.ordering),
        'write_scopes': tuple(name for name in {route.permission_scope, parent} if name),
        'action_scopes': build_action_scopes(route, profile.detail_lookup),
        'route_owned_argument': f', {spec.scope}={spec.scope}.id' if spec.scope and spec.scope_field else '',
        'permission_kwarg': f'{route.permission_scope}={route.permission_scope}' if route.permission_scope else '',
        'roles': profile.roles,
        'allowed_role': next((role for role in profile.roles if role.allowed), None),
        'denied_roles': [role for role in profile.roles if not role.allowed],
        'hidden_roles': [role for role in profile.roles if role.hidden],
        'reverse_kwargs': build_reverse_kwargs(route, detail=False),
        'detail_reverse_kwargs': build_reverse_kwargs(route, detail=True),
        'history_log_fields': python_tuple(list(spec.history_log_fields or spec.blocked_fields)),
    }


def build_action_scopes(route: Route, detail_lookup: str) -> tuple[str, ...]:
    """Action views only need the permission scope, plus the parent when they build the queryset themselves."""
    names = {route.permission_scope}

    if detail_lookup == 'scoped_queryset':
        names.add(route.parent)

    return tuple(name for name in names if name)


def build_reverse_kwargs(route: Route, *, detail: bool) -> str:
    parts = [f"'{scope}_id': self.{scope}.id" for scope in route.chain]

    if detail:
        parts.append(f"'{route.id_kwarg}': self.{route.id_kwarg[:-3]}.id")

    return '{' + ', '.join(parts) + '}'


def build_model_file(spec: ResourceSpec, environment, common: dict) -> GeneratedFile:
    profile = spec.profile
    meta_lines: list[str] = []

    if spec.ordering:
        meta_lines.append(f'ordering = {python_tuple(list(spec.ordering))}')

    if spec.unique:
        meta_lines.append('constraints = (')
        meta_lines.append(
            f"\tmodels.UniqueConstraint(fields={python_tuple(list(spec.unique))}, name='{spec.unique_name}'),"
        )
        meta_lines.append(')')

    history_fields = spec.history_log_fields or spec.blocked_fields
    context = {
        **common,
        'imports': [
            (profile.base_model_module, profile.base_model_name),
            ('django.db', 'models'),
            ('django.utils.translation', 'gettext'),
        ],
        'meta_lines': meta_lines,
        'declarations': [
            render_declaration(
                field,
                model_name=spec.model,
                default_on_delete=profile.on_delete,
                related_name=spec.related_name,
            )
            for field in spec.fields
        ],
        'history_log_fields': python_tuple(list(history_fields)) if history_fields else '',
    }

    content = render_template(environment, 'model.py.jinja', context, profile.indent)
    path = f'{spec.app}/models/{spec.model}.py' if profile.model_layout == 'package' else f'{spec.app}/models.py'
    return GeneratedFile(path=path, content=content, merge=profile.model_layout != 'package')


def build_admin_file(spec: ResourceSpec, environment, common: dict) -> GeneratedFile:
    context = {
        **common,
        'imports': [('django.contrib', 'admin'), (spec.models_module, spec.model)],
        'list_display': python_tuple(list(spec.admin_list_display)),
        'readonly_fields': python_tuple(['id', 'created_ts', 'updated_ts']),
        'search_fields': python_tuple(list(spec.search_fields)) if spec.search_fields else '',
        'list_filter': python_tuple(list(spec.list_filter)) if spec.list_filter else '',
        'raw_id_fields': python_tuple(list(spec.raw_id_fields)) if spec.raw_id_fields else '',
    }
    content = render_template(environment, 'admin.py.jinja', context, spec.profile.indent)
    return GeneratedFile(path=f'{spec.app}/admin.py', content=content, merge=True)


def build_serializers_file(spec: ResourceSpec, environment, common: dict) -> GeneratedFile:
    scope_checks = [
        {
            'field': check.field,
            'parent': check.parent,
            'message': f'{title_case(check.field)} must belong to the selected {check.parent.replace("_", " ")}.',
        }
        for check in spec.scope_checks
    ]
    context = {
        **common,
        'imports': [(spec.models_module, spec.model), ('rest_framework', 'serializers')],
        'input_fields': python_tuple(list(spec.input_fields), level=3),
        'output_fields': python_tuple(list(spec.output_fields), level=3),
        'scope_checks': scope_checks,
    }
    content = render_template(environment, 'serializers.py.jinja', context, spec.profile.indent)
    return GeneratedFile(path=f'{spec.feature_dir}/serializers.py', content=content)


def build_views_file(spec: ResourceSpec, environment, common: dict) -> GeneratedFile:
    profile = spec.profile
    route = common['route']
    imports: list[tuple[str, str]] = [
        (profile.base_view_module, profile.base_view_name),
        ('rest_framework', 'status'),
        ('rest_framework.response', 'Response'),
        (spec.serializers_module, f'{spec.model}OutputSerializer'),
        *route.extra_imports,
    ]

    if 'create' in spec.endpoints or 'detail' in spec.endpoints:
        imports.append((spec.serializers_module, f'{spec.model}InputSerializer'))

    if common['permission_kwarg'] and (spec.endpoints or spec.actions):
        imports.append((profile.permission_module, 'AppPermission'))
        imports.append((profile.permission_module, 'AppPermissionChoices'))

    if spec.actions:
        imports.append((spec.models_module, spec.model))

    if any(entry['kind'] == 'search' for entry in common['filters']):
        imports.append(('django.db.models', 'Q'))

    if any(entry['kind'] == 'choice' for entry in common['filters']):
        imports.append(('rest_framework.exceptions', 'ValidationError'))
        imports.append((spec.models_module, spec.model))

    if spec.annotations:
        imports.append(('django.db.models', 'Count'))

    needs_lookup = ('detail' in spec.endpoints or spec.actions) and profile.detail_lookup == 'scoped_queryset'
    if needs_lookup:
        imports.append(('django.shortcuts', 'get_object_or_404'))

    content = render_template(environment, 'views.py.jinja', {**common, 'imports': imports}, profile.indent)
    return GeneratedFile(path=f'{spec.feature_dir}/views.py', content=content)


def build_urls_file(spec: ResourceSpec, environment, common: dict) -> GeneratedFile:
    context = {**common, 'imports': [('django.urls', 'path'), (spec.views_package, 'views')]}
    content = render_template(environment, 'urls.py.jinja', context, spec.profile.indent)
    return GeneratedFile(path=f'{spec.feature_dir}/urls.py', content=content)


def build_app_urls_file(spec: ResourceSpec, environment, common: dict) -> GeneratedFile:
    content = render_template(environment, 'app_urls.py.jinja', common, spec.profile.indent)
    return GeneratedFile(path=f'{spec.app}/urls.py', content=content, merge=True)


def build_fixture_parameter(spec: ResourceSpec, field: Field) -> dict:
    if field.is_relation and not field.null:
        return {'name': field.name, 'annotation': field.target_model, 'default': None, 'required': True}

    if field.kind == 'choice':
        group = spec.choice_group(field.choices)
        member = field.default or group.first
        return {
            'name': field.name,
            'annotation': 'str',
            'default': f'{spec.model}.{group.class_name}.{member}',
            'required': False,
        }

    if field.name == spec.str_field or field.name in spec.unique:
        return {'name': field.name, 'annotation': 'Optional[str]', 'default': 'None', 'required': False}

    if field.kind in {'int', 'positive_int', 'big_int'}:
        return {'name': field.name, 'annotation': 'int', 'default': field.default or '0', 'required': False}

    if field.kind == 'bool':
        return {'name': field.name, 'annotation': 'bool', 'default': field.default or 'False', 'required': False}

    if field.kind in {'text', 'slug', 'email', 'url'}:
        return {'name': field.name, 'annotation': 'str', 'default': "''", 'required': False}

    return {
        'name': field.name,
        'annotation': f'Optional[{field.target_model or "object"}]',
        'default': 'None',
        'required': False,
    }


def build_random_defaults(spec: ResourceSpec) -> list[dict[str, str]]:
    """Fields that must stay unique across fixture calls get a random fallback."""
    profile = spec.profile
    defaults: list[dict[str, str]] = []

    if spec.str_field:
        defaults.append(
            {
                'name': spec.str_field,
                'expression': f"f'{spec.model} {{{profile.random_string_name}()}}'",
            }
        )

    for name in spec.unique:
        field = next((entry for entry in spec.fields if entry.name == name), None)

        if field is None or field.is_relation or name == spec.str_field:
            continue

        defaults.append({'name': name, 'expression': f'{profile.random_string_name}()'})

    return defaults


def build_fixture_file(spec: ResourceSpec, environment, common: dict) -> GeneratedFile:
    profile = spec.profile
    parameters = [build_fixture_parameter(spec, field) for field in spec.fields]
    random_defaults = build_random_defaults(spec)
    imports: list[tuple[str, str]] = [(spec.models_module, spec.model)]

    if any(not entry['required'] and entry['annotation'].startswith('Optional') for entry in parameters):
        imports.append(('typing', 'Optional'))

    if random_defaults:
        imports.append((profile.random_string_module, profile.random_string_name))

    for field in spec.fields:
        if field.is_relation and field.to:
            imports.append((f'{field.to.split(".")[0]}.models', field.target_model))

    context = {
        **common,
        'imports': imports,
        'parameters': parameters,
        'random_defaults': random_defaults,
    }
    content = render_template(environment, 'fixture.py.jinja', context, profile.indent)
    return GeneratedFile(
        path=f'{profile.fixtures_module.replace(".", "/")}.py',
        content=content,
        merge=True,
        note=f'Add create_{spec.resource} to {profile.fixtures}.',
    )


def build_view_tests_file(spec: ResourceSpec, environment, common: dict) -> GeneratedFile:
    profile = spec.profile
    imports: list[tuple[str, str]] = [
        ('django.urls', 'reverse'),
        ('rest_framework', 'status'),
        (profile.fixtures_module, profile.fixtures_name),
        (spec.serializers_module, f'{spec.model}OutputSerializer'),
        (spec.models_module, spec.model),
    ]

    for role in profile.roles:
        for membership in role.memberships:
            imports.append(
                (profile.membership_model_module(membership.scope), profile.membership_model_name(membership.scope))
            )

    context = {**common, 'imports': imports, 'chain_setup': common['full_chain_setup']}
    content = render_template(environment, 'test_views.py.jinja', context, profile.indent)
    return GeneratedFile(path=f'{spec.feature_dir}/tests/test_views.py', content=content)


def build_serializer_tests_file(spec: ResourceSpec, environment, common: dict) -> GeneratedFile:
    profile = spec.profile
    context = {
        **common,
        'imports': [
            (profile.fixtures_module, profile.fixtures_name),
            (spec.models_module, spec.model),
            (spec.serializers_module, f'{spec.model}InputSerializer'),
            (spec.serializers_module, f'{spec.model}OutputSerializer'),
        ],
    }
    content = render_template(environment, 'test_serializers.py.jinja', context, profile.indent)
    return GeneratedFile(path=f'{spec.feature_dir}/tests/test_serializers.py', content=content)


def build_model_tests_file(spec: ResourceSpec, environment, common: dict) -> GeneratedFile:
    profile = spec.profile
    imports = [
        (profile.fixtures_module, profile.fixtures_name),
        (spec.models_module, spec.model),
    ]

    if common['unique_kwargs']:
        imports.append(('django.db', 'IntegrityError'))

    context = {**common, 'imports': imports}
    content = render_template(environment, 'test_models.py.jinja', context, profile.indent)
    return GeneratedFile(path=f'{spec.app}/tests/test_{spec.resource}_models.py', content=content)


def build_models_init(spec: ResourceSpec) -> Optional[GeneratedFile]:
    if spec.profile.model_layout != 'package':
        return None

    line = f'from {spec.app}.models.{spec.model} import {spec.model}  # noqa: F401\n'
    return GeneratedFile(path=f'{spec.app}/models/__init__.py', content=line, merge=True)


def build_package_inits(spec: ResourceSpec) -> list[GeneratedFile]:
    paths = [f'{spec.app}/tests/__init__.py']

    if spec.layout != 'flat':
        paths.extend(
            [
                f'{spec.app}/views/__init__.py',
                f'{spec.feature_dir}/__init__.py',
                f'{spec.feature_dir}/tests/__init__.py',
            ]
        )

    return [GeneratedFile(path=path, content='') for path in paths]


def generate(spec: ResourceSpec) -> list[GeneratedFile]:
    environment = build_environment()
    common = build_common_context(spec)
    files: list[GeneratedFile] = [
        build_model_file(spec, environment, common),
        build_admin_file(spec, environment, common),
        build_serializers_file(spec, environment, common),
        build_views_file(spec, environment, common),
        build_urls_file(spec, environment, common),
        build_fixture_file(spec, environment, common),
        build_view_tests_file(spec, environment, common),
        build_serializer_tests_file(spec, environment, common),
        build_model_tests_file(spec, environment, common),
    ]

    if spec.layout != 'flat':
        files.append(build_app_urls_file(spec, environment, common))

    models_init = build_models_init(spec)
    if models_init is not None:
        files.append(models_init)

    files.extend(build_package_inits(spec))
    return files
