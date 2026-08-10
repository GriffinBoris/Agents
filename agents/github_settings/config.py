from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPOSITORY_BOOLEAN_FIELDS = frozenset(
    {
        'allow_auto_merge',
        'allow_merge_commit',
        'allow_rebase_merge',
        'allow_squash_merge',
        'allow_update_branch',
        'delete_branch_on_merge',
        'has_discussions',
        'has_issues',
        'has_projects',
        'has_wiki',
        'web_commit_signoff_required',
    }
)
REPOSITORY_ENUM_FIELDS = {
    'merge_commit_message': frozenset({'BLANK', 'PR_BODY', 'PR_TITLE'}),
    'merge_commit_title': frozenset({'MERGE_MESSAGE', 'PR_TITLE'}),
    'squash_merge_commit_message': frozenset({'BLANK', 'COMMIT_MESSAGES', 'PR_BODY'}),
    'squash_merge_commit_title': frozenset({'COMMIT_OR_PR_TITLE', 'PR_TITLE'}),
}
REPOSITORY_FIELDS = REPOSITORY_BOOLEAN_FIELDS.union(REPOSITORY_ENUM_FIELDS)
RULESET_FIELDS = frozenset(
    {'bypass_actors', 'conditions', 'enforcement', 'name', 'rules', 'target'}
)


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class GitHubSettings:
    repository: dict[str, Any]
    rulesets: tuple[dict[str, Any], ...]


def load_settings(path: Path) -> GitHubSettings:
    resolved_path = path.resolve()
    document = _load_yaml_mapping(resolved_path)

    if document.get('version') != 1:
        raise ConfigError(f'{resolved_path}: version must be 1')

    repository = document.get('repository')
    if not isinstance(repository, dict):
        raise ConfigError(f'{resolved_path}: repository must be a mapping')

    _validate_repository(repository, resolved_path)
    rulesets = _load_rulesets(document.get('rulesets', []), resolved_path)
    return GitHubSettings(repository=dict(repository), rulesets=rulesets)


def dump_settings(settings: GitHubSettings) -> str:
    document = {
        'version': 1,
        'repository': settings.repository,
        'rulesets': list(settings.rulesets),
    }
    return yaml.safe_dump(document, sort_keys=False, width=120)


def _load_rulesets(
    raw_rulesets: object, config_path: Path
) -> tuple[dict[str, Any], ...]:
    if not isinstance(raw_rulesets, list):
        raise ConfigError(f'{config_path}: rulesets must be a list')

    rulesets: list[dict[str, Any]] = []

    for index, raw_ruleset in enumerate(raw_rulesets):
        if isinstance(raw_ruleset, str):
            ruleset_path = _resolve_ruleset_path(config_path, raw_ruleset)
            ruleset = _load_yaml_mapping(ruleset_path)
            source = ruleset_path
        elif isinstance(raw_ruleset, dict):
            ruleset = dict(raw_ruleset)
            source = config_path
        else:
            raise ConfigError(
                f'{config_path}: rulesets[{index}] must be a YAML path or mapping'
            )

        _validate_ruleset(ruleset, source)
        rulesets.append(ruleset)

    names = [ruleset['name'] for ruleset in rulesets]
    duplicate_names = sorted({name for name in names if names.count(name) > 1})
    if duplicate_names:
        raise ConfigError(
            f'{config_path}: duplicate ruleset names: {", ".join(duplicate_names)}'
        )

    return tuple(rulesets)


def _resolve_ruleset_path(config_path: Path, raw_path: str) -> Path:
    ruleset_path = (config_path.parent / raw_path).resolve()

    if not ruleset_path.is_relative_to(config_path.parent):
        raise ConfigError(
            f'{config_path}: ruleset path must stay within {config_path.parent}'
        )

    if ruleset_path.suffix not in {'.yaml', '.yml'}:
        raise ConfigError(
            f'{config_path}: ruleset path must end in .yml or .yaml: {raw_path}'
        )

    return ruleset_path


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding='utf-8') as yaml_file:
            document = yaml.safe_load(yaml_file)
    except OSError as error:
        raise ConfigError(f'{path}: {error}') from error
    except yaml.YAMLError as error:
        raise ConfigError(f'{path}: invalid YAML: {error}') from error

    if not isinstance(document, dict):
        raise ConfigError(f'{path}: expected a YAML mapping')

    return document


def _validate_repository(repository: dict[str, Any], source: Path) -> None:
    unknown_fields = sorted(set(repository).difference(REPOSITORY_FIELDS))
    if unknown_fields:
        raise ConfigError(
            f'{source}: unsupported repository settings: {", ".join(unknown_fields)}'
        )

    for field in REPOSITORY_BOOLEAN_FIELDS.intersection(repository):
        if not isinstance(repository[field], bool):
            raise ConfigError(f'{source}: repository.{field} must be a boolean')

    for field, choices in REPOSITORY_ENUM_FIELDS.items():
        if field in repository and repository[field] not in choices:
            choice_list = ', '.join(sorted(choices))
            raise ConfigError(
                f'{source}: repository.{field} must be one of: {choice_list}'
            )


def _validate_ruleset(ruleset: dict[str, Any], source: Path) -> None:
    unknown_fields = sorted(set(ruleset).difference(RULESET_FIELDS))
    if unknown_fields:
        raise ConfigError(
            f'{source}: unsupported ruleset fields: {", ".join(unknown_fields)}'
        )

    name = ruleset.get('name')
    if not isinstance(name, str) or not name:
        raise ConfigError(f'{source}: ruleset.name must be a non-empty string')

    if ruleset.get('target') not in {'branch', 'push', 'tag'}:
        raise ConfigError(f'{source}: ruleset.target must be branch, push, or tag')

    if ruleset.get('enforcement') not in {'active', 'disabled', 'evaluate'}:
        raise ConfigError(
            f'{source}: ruleset.enforcement must be active, disabled, or evaluate'
        )

    conditions = ruleset.get('conditions')
    if not isinstance(conditions, dict):
        raise ConfigError(f'{source}: ruleset.conditions must be a mapping')

    ref_name = conditions.get('ref_name')
    if ruleset['target'] in {'branch', 'tag'}:
        if not isinstance(ref_name, dict):
            raise ConfigError(
                f'{source}: branch and tag rulesets require conditions.ref_name'
            )
        _validate_string_list(
            ref_name.get('include'), 'conditions.ref_name.include', source
        )
        _validate_string_list(
            ref_name.get('exclude'), 'conditions.ref_name.exclude', source
        )

    rules = ruleset.get('rules')
    if not isinstance(rules, list) or not rules:
        raise ConfigError(f'{source}: ruleset.rules must be a non-empty list')

    for index, rule in enumerate(rules):
        if not isinstance(rule, dict) or not isinstance(rule.get('type'), str):
            raise ConfigError(
                f'{source}: ruleset.rules[{index}] must have a string type'
            )

    bypass_actors = ruleset.get('bypass_actors', [])
    if not isinstance(bypass_actors, list):
        raise ConfigError(f'{source}: ruleset.bypass_actors must be a list')


def _validate_string_list(value: object, field: str, source: Path) -> None:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ConfigError(f'{source}: {field} must be a list of non-empty strings')
