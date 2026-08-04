from dataclasses import dataclass
from typing import Any

from agents.codegen.errors import SpecError
from agents.codegen.naming import class_case, snake_case
from agents.codegen.profile import Profile


DJANGO_DEFAULTS: dict[str, Any] = {
    'backend_root': 'backend',
    'base_view': 'common.access.base_views.AuthenticatedAccessAPIView',
    'base_model': 'core.base_models.BaseModel',
    'fixtures': 'tests.fixtures.FixtureFactory',
    'random_string': 'core.utility.random_string',
    'permission_module': 'common.permissions',
    'default_permission': 'WORKSPACE_MANAGE',
    'permission_scope': 'workspace',
    'on_delete': 'DO_NOTHING',
    'detail_lookup': 'scoped_queryset',
    'layout': 'feature_package',
    'model_layout': 'module',
    'membership_models': {},
    'roles': {},
}

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
class DjangoProfile:
    """The django section of the project profile, plus the shared core it sits on."""

    core: Profile
    backend_root: str
    base_view: str
    base_model: str
    fixtures: str
    random_string: str
    permission_module: str
    default_permission: str
    permission_scope: str
    on_delete: str
    detail_lookup: str
    layout: str
    model_layout: str
    membership_models: dict[str, str]
    roles: tuple[Role, ...]

    @property
    def indent(self) -> str:
        return self.core.indent_for('django')

    @property
    def api_prefix(self) -> str:
        return self.core.api_prefix

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

    def scope_resolver(self, scope: str) -> str:
        return self.core.scope_resolver(scope)

    def membership_model(self, scope: str) -> str:
        return self.membership_models.get(scope, f'{class_case(scope)}Membership')

    def membership_model_name(self, scope: str) -> str:
        return self.membership_model(scope).rsplit('.', 1)[-1]

    def membership_model_module(self, scope: str) -> str:
        dotted = self.membership_model(scope)
        return dotted.rsplit('.', 1)[0] if '.' in dotted else f'{scope}.models'


def build_django_profile(core: Profile) -> DjangoProfile:
    data = {**DJANGO_DEFAULTS, **core.section('django')}

    for key, allowed in (
        ('detail_lookup', SUPPORTED_DETAIL_LOOKUPS),
        ('layout', SUPPORTED_LAYOUTS),
        ('model_layout', SUPPORTED_MODEL_LAYOUTS),
    ):
        if data[key] not in allowed:
            message = f'Unsupported {key} {data[key]!r}. Use one of: {", ".join(sorted(allowed))}.'
            raise SpecError(message)

    return DjangoProfile(
        core=core,
        backend_root=data['backend_root'],
        base_view=data['base_view'],
        base_model=data['base_model'],
        fixtures=data['fixtures'],
        random_string=data['random_string'],
        permission_module=data['permission_module'],
        default_permission=data['default_permission'],
        permission_scope=data['permission_scope'],
        on_delete=data['on_delete'],
        detail_lookup=data['detail_lookup'],
        layout=data['layout'],
        model_layout=data['model_layout'],
        membership_models=dict(data['membership_models']),
        roles=build_roles(data['roles']),
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
