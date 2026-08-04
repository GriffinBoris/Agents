from dataclasses import dataclass, field as dataclass_field
from pathlib import Path
from typing import Any, Optional

import yaml

from agents.codegen.errors import SpecError
from agents.codegen.naming import plural_kebab


PROFILE_FILENAME = '.codegen.yaml'

SUPPORTED_INDENTS = {'tab': '\t', 'space': '    ', 'space2': '  '}

CORE_DEFAULTS: dict[str, Any] = {
    'api_prefix': '/api/',
    'indent': 'tab',
    'targets': ['django'],
    'scopes': {},
    'namespaces': {},
}


@dataclass(frozen=True)
class Profile:
    """Conventions shared by every generator, plus one opaque section per target.

    Route facts live here because a URL is not owned by one language: the backend
    routes it and the frontend calls it, and both must agree. Anything a single
    target owns lives in that target's section, so adding a generator never means
    editing this file.
    """

    api_prefix: str
    indent: str
    targets: tuple[str, ...]
    scopes: dict[str, tuple[str, ...]]
    namespaces: dict[str, str]
    sections: dict[str, dict[str, Any]] = dataclass_field(default_factory=dict)
    path: Optional[Path] = None

    def section(self, target: str) -> dict[str, Any]:
        return dict(self.sections.get(target) or {})

    def indent_for(self, target: str) -> str:
        raw = self.section(target).get('indent')

        if raw is None:
            return self.indent

        if raw not in SUPPORTED_INDENTS:
            message = (
                f'Unsupported indent {raw!r} for target {target}. Use one of: {", ".join(sorted(SUPPORTED_INDENTS))}.'
            )
            raise SpecError(message)

        return SUPPORTED_INDENTS[raw]

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

    def url_segment(self, scope: str) -> str:
        return plural_kebab(scope)


def load_profile(path: Optional[Path] = None, *, start: Optional[Path] = None) -> Profile:
    resolved = path or find_profile(start or Path.cwd())
    data = dict(CORE_DEFAULTS)

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

    reserved = set(CORE_DEFAULTS)
    sections = {key: value for key, value in data.items() if key not in reserved and isinstance(value, dict)}

    return Profile(
        api_prefix=data['api_prefix'],
        indent=SUPPORTED_INDENTS[indent],
        targets=tuple(data['targets']),
        scopes={name: tuple(kwargs) for name, kwargs in (data.get('scopes') or {}).items()},
        namespaces=dict(data.get('namespaces') or {}),
        sections=sections,
        path=path,
    )
