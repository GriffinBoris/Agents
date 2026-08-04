from dataclasses import dataclass
from typing import Any

from agents.codegen.profile import Profile


VUE_DEFAULTS: dict[str, Any] = {
    'frontend_root': 'frontend',
    'types_dir': 'src/types',
    'api_client': 'src/utils/api.ts',
    'api_client_name': 'apiClient',
}


@dataclass(frozen=True)
class VueProfile:
    core: Profile
    frontend_root: str
    types_dir: str
    api_client: str
    api_client_name: str

    @property
    def indent(self) -> str:
        return self.core.indent_for('vue')

    @property
    def api_prefix(self) -> str:
        return self.core.api_prefix


def build_vue_profile(core: Profile) -> VueProfile:
    data = {**VUE_DEFAULTS, **core.section('vue')}
    return VueProfile(
        core=core,
        frontend_root=data['frontend_root'],
        types_dir=data['types_dir'],
        api_client=data['api_client'],
        api_client_name=data['api_client_name'],
    )
