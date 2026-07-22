import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class ToolConfig:
    name: str
    profiles: tuple[str, ...]
    check: tuple[str, ...]
    fix: Optional[tuple[str, ...]]
    cwd: Path
    required_paths: tuple[Path, ...]
    optional: bool


@dataclass(frozen=True)
class LintConfig:
    path: Path
    tools: tuple[ToolConfig, ...]


def default_config_path() -> Path:
    return Path(__file__).resolve().parents[1] / 'rules' / 'config' / 'agents-lint.toml'


def load_config(path: Path, root: Path) -> LintConfig:
    resolved_path = path.resolve()

    with resolved_path.open('rb') as config_file:
        raw_config = tomllib.load(config_file)

    version = raw_config.get('version')
    if version != 1:
        raise ValueError(f'{resolved_path}: expected version = 1, got {version!r}')

    raw_tools = raw_config.get('tools')
    if not isinstance(raw_tools, list) or not raw_tools:
        raise ValueError(f'{resolved_path}: expected at least one [[tools]] entry')

    tools = tuple(_load_tool(raw_tool, root, resolved_path) for raw_tool in raw_tools)
    names = [tool.name for tool in tools]
    duplicate_names = sorted({name for name in names if names.count(name) > 1})

    if duplicate_names:
        raise ValueError(f'{resolved_path}: duplicate tool names: {", ".join(duplicate_names)}')

    return LintConfig(path=resolved_path, tools=tools)


def _load_tool(raw_tool: object, root: Path, config_path: Path) -> ToolConfig:
    if not isinstance(raw_tool, dict):
        raise ValueError(f'{config_path}: each [[tools]] entry must be a table')

    name = _required_string(raw_tool, 'name', config_path)
    profiles = _string_tuple(raw_tool.get('profiles', ('all',)), 'profiles', name, config_path)
    check = _string_tuple(raw_tool.get('check'), 'check', name, config_path)
    raw_fix = raw_tool.get('fix')
    fix = None if raw_fix is None else _string_tuple(raw_fix, 'fix', name, config_path)
    cwd_value = _required_string(raw_tool, 'cwd', config_path, default='.')
    required_paths = _string_tuple(
        raw_tool.get('required_paths', ()),
        'required_paths',
        name,
        config_path,
        allow_empty=True,
    )
    optional = raw_tool.get('optional', False)

    if not isinstance(optional, bool):
        raise ValueError(f'{config_path}: tools.{name}.optional must be a boolean')

    return ToolConfig(
        name=name,
        profiles=profiles,
        check=check,
        fix=fix,
        cwd=root / cwd_value,
        required_paths=tuple(root / required_path for required_path in required_paths),
        optional=optional,
    )


def _required_string(
    source: dict[str, object],
    key: str,
    config_path: Path,
    *,
    default: Optional[str] = None,
) -> str:
    value = source.get(key, default)

    if not isinstance(value, str) or not value:
        raise ValueError(f'{config_path}: {key} must be a non-empty string')

    return value


def _string_tuple(
    value: object,
    key: str,
    tool_name: str,
    config_path: Path,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, list) and not isinstance(value, tuple):
        raise ValueError(f'{config_path}: tools.{tool_name}.{key} must be an array of strings')

    if not allow_empty and not value:
        raise ValueError(f'{config_path}: tools.{tool_name}.{key} cannot be empty')

    if not all(isinstance(item, str) and item for item in value):
        raise ValueError(f'{config_path}: tools.{tool_name}.{key} must contain non-empty strings')

    return tuple(value)
