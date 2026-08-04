from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

from agents.django_codegen.fields import SpecError
from agents.django_codegen.naming import class_case, plural_kebab, snake_case


PROFILE_FILENAME = '.django-codegen.yaml'

DEFAULT_PROFILE: dict[str, Any] = {
    'backend_root': 'backend',
    'api_prefix': '/api/',
    'base_view': 'common.access.base_views.AuthenticatedAccessAPIView',
    'base_model': 'core.base_models.BaseModel',
    'fixtures': 'tests.fixtures.FixtureFactory',
    'random_string': 'core.utility.random_string',
    'permission_module': 'common.permissions',
    'default_permission': 'WORKSPACE_MANAGE',
    'permission_scope': 'workspace',
    'on_delete': 'DO_NOTHING',
    'indent': 'tab',
    'detail_lookup': 'scoped_queryset',
    'layout': 'feature_package',
    'model_layout': 'module',
    'scopes': {},
    'namespaces': {},
    'membership_models': {},
    'roles': {},
}

SUPPORTED_INDENTS = {'tab': '\t', 'space': '    '}
STATUS_CONSTANTS = {
    200: 'HTTP_200_OK',
    201: 'HTTP_201_CREATED',
    400: 'HTTP_400_BAD_REQUEST',
    403: 'HTTP_403_FORBIDDEN',
    404: 'HTTP_404_NOT_FOUND',
}
SUPPORTED_DETAIL_LOOKUPS = frozenset({'scoped_queryset', 'resource_resolver'})
SUPPORTED_LAYOUTS = frozenset({'feature_package', 'flat'})
SUPPORTED_MODEL_LAYOUTS = frozenset({'module', 'package'})


@dataclass(frozen=True)
class Membership:
    target: str
    scope: str
    role: str

    @property
    def builder(self) -> str:
        return f'create_{self.scope}_membership'


@dataclass(frozen=True)
class Role:
    name: str
    memberships: tuple[Membership, ...]
    expect: int
    is_superuser: bool

    @property
    def email(self) -> str:
        return f'{self.name.replace("_", "-")}@example.com'

    @property
    def allowed(self) -> bool:
        return self.expect == 200

    @property
    def hidden(self) -> bool:
        return self.expect == 404

    @property
    def status_constant(self) -> str:
        return STATUS_CONSTANTS.get(self.expect, 'HTTP_200_OK')


@dataclass(frozen=True)
class Profile:
    backend_root: str
    api_prefix: str
    base_view: str
    base_model: str
    fixtures: str
    random_string: str
    permission_module: str
    default_permission: str
    permission_scope: str
    on_delete: str
    indent: str
    detail_lookup: str
    layout: str
    model_layout: str
    scopes: dict[str, tuple[str, ...]]
    namespaces: dict[str, str]
    membership_models: dict[str, str]
    roles: tuple[Role, ...]
    path: Optional[Path] = None

    @property
    def base_view_module(self) -> str:
        return self.base_view.rsplit('.', 1)[0]

    @property
    def base_view_name(self) -> str:
        return self.base_view.rsplit('.', 1)[-1]

    @property
    def base_model_module(self) -> str:
        return self.base_model.rsplit('.', 1)[0]

    @property
    def base_model_name(self) -> str:
        return self.base_model.rsplit('.', 1)[-1]

    @property
    def random_string_module(self) -> str:
        return self.random_string.rsplit('.', 1)[0]

    @property
    def random_string_name(self) -> str:
        return self.random_string.rsplit('.', 1)[-1]

    @property
    def fixtures_module(self) -> str:
        return self.fixtures.rsplit('.', 1)[0]

    @property
    def fixtures_name(self) -> str:
        return self.fixtures.rsplit('.', 1)[-1]

    def scope_kwargs(self, scope: Optional[str]) -> tuple[str, ...]:
        if not scope:
            return ()

        if scope not in self.scopes:
            known = ', '.join(sorted(self.scopes)) or 'none declared'
            message = f'Unknown scope {scope!r}. Declare it under "scopes" in {PROFILE_FILENAME}. Known scopes: {known}.'
            raise SpecError(message)

        return self.scopes[scope]

    def scope_chain(self, scope: Optional[str]) -> tuple[str, ...]:
        return tuple(kwarg[:-3] for kwarg in self.scope_kwargs(scope))

    def scope_resolver(self, scope: str) -> str:
        return f'resolve_{scope}_scope'

    def namespace_prefix(self, scope: Optional[str]) -> str:
        if not scope:
            return ''

        return self.namespaces.get(scope, '')

    def membership_model(self, scope: str) -> str:
        return self.membership_models.get(scope, f'{class_case(scope)}Membership')

    def membership_model_name(self, scope: str) -> str:
        return self.membership_model(scope).rsplit('.', 1)[-1]

    def membership_model_module(self, scope: str) -> str:
        dotted = self.membership_model(scope)
        return dotted.rsplit('.', 1)[0] if '.' in dotted else f'{scope}.models'

    def url_segment(self, scope: str) -> str:
        return plural_kebab(scope)


def load_profile(path: Optional[Path] = None, *, start: Optional[Path] = None) -> Profile:
    resolved = path or find_profile(start or Path.cwd())
    data = dict(DEFAULT_PROFILE)

    if resolved is not None and resolved.exists():
        loaded = yaml.safe_load(resolved.read_text(encoding='utf-8')) or {}

        if not isinstance(loaded, dict):
            message = f'Profile {resolved} must contain a mapping.'
            raise SpecError(message)

        data.update(loaded)

    return build_profile(data, resolved)


def find_profile(start: Path) -> Optional[Path]:
    current = start.resolve()

    for candidate in (current, *current.parents):
        profile_path = candidate / PROFILE_FILENAME
        if profile_path.exists():
            return profile_path

    return None


def build_profile(data: dict[str, Any], path: Optional[Path]) -> Profile:
    indent = data.get('indent', 'tab')
    if indent not in SUPPORTED_INDENTS:
        message = f'Unsupported indent {indent!r}. Use one of: {", ".join(sorted(SUPPORTED_INDENTS))}.'
        raise SpecError(message)

    detail_lookup = data.get('detail_lookup', 'scoped_queryset')
    if detail_lookup not in SUPPORTED_DETAIL_LOOKUPS:
        message = f'Unsupported detail_lookup {detail_lookup!r}. Use one of: {", ".join(sorted(SUPPORTED_DETAIL_LOOKUPS))}.'
        raise SpecError(message)

    layout = data.get('layout', 'feature_package')
    if layout not in SUPPORTED_LAYOUTS:
        message = f'Unsupported layout {layout!r}. Use one of: {", ".join(sorted(SUPPORTED_LAYOUTS))}.'
        raise SpecError(message)

    model_layout = data.get('model_layout', 'module')
    if model_layout not in SUPPORTED_MODEL_LAYOUTS:
        message = f'Unsupported model_layout {model_layout!r}. Use one of: {", ".join(sorted(SUPPORTED_MODEL_LAYOUTS))}.'
        raise SpecError(message)

    scopes = {name: tuple(kwargs) for name, kwargs in (data.get('scopes') or {}).items()}

    return Profile(
        backend_root=data['backend_root'],
        api_prefix=data['api_prefix'],
        base_view=data['base_view'],
        base_model=data['base_model'],
        fixtures=data['fixtures'],
        random_string=data['random_string'],
        permission_module=data['permission_module'],
        default_permission=data['default_permission'],
        permission_scope=data['permission_scope'],
        on_delete=data['on_delete'],
        indent=SUPPORTED_INDENTS[indent],
        detail_lookup=detail_lookup,
        layout=layout,
        model_layout=model_layout,
        scopes=scopes,
        namespaces=dict(data.get('namespaces') or {}),
        membership_models=dict(data.get('membership_models') or {}),
        roles=build_roles(data.get('roles') or {}),
        path=path,
    )


def build_roles(raw_roles: dict[str, Any]) -> tuple[Role, ...]:
    roles: list[Role] = []

    for name, raw_role in raw_roles.items():
        role_data = raw_role if isinstance(raw_role, dict) else {'expect': raw_role}
        memberships = tuple(parse_membership(entry) for entry in role_data.get('memberships') or [])

        roles.append(
            Role(
                name=snake_case(name),
                memberships=memberships,
                expect=int(role_data.get('expect', 200)),
                is_superuser=bool(role_data.get('superuser', False)),
            )
        )

    return tuple(roles)


def parse_membership(entry: str) -> Membership:
    target, _, role = entry.partition(':')
    target = target.strip()
    role = role.strip() or 'ADMIN'
    scope = target[len('other_') :] if target.startswith('other_') else target
    return Membership(target=target, scope=scope, role=role)
