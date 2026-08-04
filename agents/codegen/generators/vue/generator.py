from pathlib import Path
from typing import Any

from agents.codegen.fields import Field
from agents.codegen.generators.base import BaseGenerator, GeneratedFile
from agents.codegen.generators.vue.profile import VueProfile, build_vue_profile
from agents.codegen.naming import camel_case, class_case
from agents.codegen.profile import Profile
from agents.codegen.renderer import build_environment, render_template
from agents.codegen.resource import ResourceSpec


TEMPLATES_ROOT = Path(__file__).resolve().parent / 'templates'

# Neutral field kinds mapped to the TypeScript types the frontend contracts use.
TS_TYPES = {
    'text': 'string',
    'slug': 'string',
    'email': 'string',
    'url': 'string',
    'uuid': 'string',
    'date': 'string',
    'datetime': 'string',
    'time': 'string',
    'duration': 'string',
    'decimal': 'string',
    'file': 'string',
    'image': 'string',
    'int': 'number',
    'positive_int': 'number',
    'big_int': 'number',
    'float': 'number',
    'bool': 'boolean',
    'json': 'unknown[]',
    'fk': 'number',
    'o2o': 'number',
    'm2m': 'number[]',
}

ZOD_TYPES = {
    'text': 'z.string()',
    'slug': 'z.string()',
    'email': 'z.string().email()',
    'url': 'z.string().url()',
    'uuid': 'z.string().uuid()',
    'date': 'z.string()',
    'datetime': 'z.string()',
    'time': 'z.string()',
    'duration': 'z.string()',
    'decimal': 'z.string()',
    'file': 'z.string()',
    'image': 'z.string()',
    'int': 'z.number()',
    'positive_int': 'z.number()',
    'big_int': 'z.number()',
    'float': 'z.number()',
    'bool': 'z.boolean()',
    'json': 'z.array(z.unknown())',
    'fk': 'z.number()',
    'o2o': 'z.number()',
    'm2m': 'z.array(z.number())',
}

TS_DEFAULTS = {
    'string': '""',
    'number': '0',
    'boolean': 'false',
}


def ts_type(spec: ResourceSpec, field: Field) -> str:
    if field.kind == 'choice':
        group = spec.choice_group(field.choices)
        return f'{spec.model}{class_case(group.field_name)}' if group else 'string'

    base = TS_TYPES.get(field.kind, 'unknown')
    return f'{base} | null' if field.null else base


def zod_type(spec: ResourceSpec, field: Field) -> str:
    if field.kind == 'choice':
        group = spec.choice_group(field.choices)
        expression = f'z.nativeEnum({spec.model}{class_case(group.field_name)})' if group else 'z.string()'
    elif field.kind == 'text' and field.name == spec.str_field:
        label = field.label
        expression = f'z.string().min(1, "{label} is required")'
    else:
        expression = ZOD_TYPES.get(field.kind, 'z.unknown()')

    return f'{expression}.nullable()' if field.null else expression


def ts_default(spec: ResourceSpec, field: Field) -> str:
    if field.null:
        return 'null'

    if field.kind == 'choice':
        group = spec.choice_group(field.choices)

        if group:
            member = field.default or group.first
            return f'{spec.model}{class_case(group.field_name)}.{member}'

        return "''"

    if field.kind == 'm2m' or field.kind == 'json':
        return '[]'

    resolved = TS_TYPES.get(field.kind, 'unknown')

    if field.default is not None and resolved == 'number':
        return field.default

    if field.default is not None and resolved == 'boolean':
        return 'true' if str(field.default).lower() in {'true', 'yes', '1'} else 'false'

    if field.default is not None and resolved == 'string':
        return f'"{field.default}"'

    return TS_DEFAULTS.get(resolved, 'undefined')


def enum_name(spec: ResourceSpec, group) -> str:
    return f'{spec.model}{class_case(group.field_name)}'


def url_template(spec: ResourceSpec) -> str:
    """The API path as a TypeScript template literal, with camelCase scope arguments."""
    prefix = spec.url_prefix(template='${{{camel}Id}}')
    return prefix.lstrip('/')


def scope_arguments(spec: ResourceSpec) -> list[str]:
    return [f'{camel_case(scope)}Id: number' for scope in spec.scope_chain]


def scope_argument_names(spec: ResourceSpec) -> list[str]:
    return [f'{camel_case(scope)}Id' for scope in spec.scope_chain]


class VueGenerator(BaseGenerator):
    """Emits the mechanical half of the frontend contract: types, schema, API methods.

    Route folders, views, and stores are deliberately not generated. Those compose
    sections and own workflow state, which is judgment rather than transcription.
    """

    name = 'vue'
    templates_root = TEMPLATES_ROOT

    def output_root(self, profile: Profile) -> str:
        return build_vue_profile(profile).frontend_root

    def describe(self, spec: ResourceSpec) -> str:
        return f'{spec.domain}/{spec.model}'

    def generate(self, spec: ResourceSpec) -> list[GeneratedFile]:
        profile = build_vue_profile(spec.profile)
        environment = build_environment(TEMPLATES_ROOT)
        common = self.build_context(spec, profile)

        files = [
            self.build_interface(spec, profile, environment, common),
            self.build_request_interface(spec, profile, environment, common),
        ]

        if spec.endpoints or spec.actions:
            files.append(self.build_api_segment(spec, profile, environment, common))

        return files

    def build_context(self, spec: ResourceSpec, profile: VueProfile) -> dict[str, Any]:
        readable = [
            {'name': camel_case(field.name), 'type': ts_type(spec, field)}
            for field in spec.fields
        ]
        writable = [
            {
                'name': camel_case(field.name),
                'type': ts_type(spec, field),
                'zod': zod_type(spec, field),
                'default': ts_default(spec, field),
            }
            for field in spec.writable_fields
        ]

        return {
            'spec': spec,
            'profile': profile,
            'enums': [
                {'name': enum_name(spec, group), 'members': list(group.members)} for group in spec.choices
            ],
            # Only enums the request schema actually references get imported into it.
            'request_enums': [
                enum_name(spec, group)
                for group in spec.choices
                if any(field.kind == 'choice' and field.choices == group.field_name for field in spec.writable_fields)
            ],
            'readable': sorted(readable, key=lambda entry: entry['name']),
            'writable': sorted(writable, key=lambda entry: entry['name']),
            'interface_name': f'{spec.model}Interface',
            'request_name': f'{spec.model}RequestInterface',
            'schema_name': f'{spec.resource_camel}InputSchema',
            'defaults_name': f'createDefault{spec.model}Input',
            'url': url_template(spec),
            'scope_arguments': scope_arguments(spec),
            'scope_argument_names': scope_argument_names(spec),
            'id_argument': f'{spec.resource_camel}Id',
            'api_client_name': profile.api_client_name,
        }

    def types_path(self, spec: ResourceSpec, profile: VueProfile, filename: str) -> str:
        return f'{profile.types_dir}/{spec.domain}/{filename}'

    def build_interface(self, spec, profile, environment, common) -> GeneratedFile:
        content = render_template(environment, 'interface.ts.jinja', common, profile.indent)
        return GeneratedFile(path=self.types_path(spec, profile, f'{spec.model}Interface.ts'), content=content)

    def build_request_interface(self, spec, profile, environment, common) -> GeneratedFile:
        content = render_template(environment, 'request_interface.ts.jinja', common, profile.indent)
        return GeneratedFile(
            path=self.types_path(spec, profile, f'{spec.model}RequestInterface.ts'),
            content=content,
        )

    def build_api_segment(self, spec, profile, environment, common) -> GeneratedFile:
        content = render_template(environment, 'api_segment.ts.jinja', common, profile.indent)
        return GeneratedFile(
            path=profile.api_client,
            content=content,
            merge=True,
            note=f'Add the {spec.plural_camel} segment to {profile.api_client}.',
        )
