from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from agents.github_settings.api import GitHubClient
from agents.github_settings.config import (
    REPOSITORY_FIELDS,
    RULESET_FIELDS,
    GitHubSettings,
)


@dataclass(frozen=True)
class RulesetUpdate:
    ruleset_id: int
    payload: dict[str, Any]


@dataclass(frozen=True)
class SettingsPlan:
    repository_update: dict[str, Any]
    ruleset_creates: tuple[dict[str, Any], ...]
    ruleset_updates: tuple[RulesetUpdate, ...]

    @property
    def has_changes(self) -> bool:
        return bool(
            self.repository_update or self.ruleset_creates or self.ruleset_updates
        )


class GitHubSettingsService:
    def __init__(self, client: GitHubClient, repository: str):
        owner, name = _split_repository(repository)
        self.client = client
        self.repository = repository
        self.repository_path = f'/repos/{quote(owner, safe="")}/{quote(name, safe="")}'

    def read(self) -> GitHubSettings:
        repository_response = self.client.get(self.repository_path)
        repository = {
            field: repository_response[field]
            for field in REPOSITORY_FIELDS
            if field in repository_response
        }

        ruleset_summaries = self.client.get(
            f'{self.repository_path}/rulesets?includes_parents=false&per_page=100',
        )
        rulesets = tuple(
            _normalize_ruleset(
                self.client.get(
                    f'{self.repository_path}/rulesets/{summary["id"]}?includes_parents=false'
                )
            )
            for summary in ruleset_summaries
            if summary.get('source_type') == 'Repository'
        )
        return GitHubSettings(repository=repository, rulesets=rulesets)

    def plan(self, desired: GitHubSettings) -> SettingsPlan:
        current = self.read()
        repository_update = {
            field: value
            for field, value in desired.repository.items()
            if current.repository.get(field) != value
        }

        current_rulesets = {ruleset['name']: ruleset for ruleset in current.rulesets}
        desired_names = {ruleset['name'] for ruleset in desired.rulesets}
        summary_response = self.client.get(
            f'{self.repository_path}/rulesets?includes_parents=false&per_page=100',
        )
        ruleset_ids = {
            summary['name']: summary['id']
            for summary in summary_response
            if summary.get('source_type') == 'Repository'
            and summary.get('name') in desired_names
        }

        creates: list[dict[str, Any]] = []
        updates: list[RulesetUpdate] = []

        for desired_ruleset in desired.rulesets:
            current_ruleset = current_rulesets.get(desired_ruleset['name'])
            if current_ruleset is None:
                creates.append(desired_ruleset)
            elif current_ruleset != desired_ruleset:
                updates.append(
                    RulesetUpdate(
                        ruleset_id=ruleset_ids[desired_ruleset['name']],
                        payload=desired_ruleset,
                    )
                )

        return SettingsPlan(
            repository_update=repository_update,
            ruleset_creates=tuple(creates),
            ruleset_updates=tuple(updates),
        )

    def apply(self, plan: SettingsPlan) -> None:
        if plan.repository_update:
            self.client.patch(self.repository_path, plan.repository_update)

        for ruleset in plan.ruleset_creates:
            self.client.post(f'{self.repository_path}/rulesets', ruleset)

        for update in plan.ruleset_updates:
            self.client.put(
                f'{self.repository_path}/rulesets/{update.ruleset_id}',
                update.payload,
            )


def _split_repository(repository: str) -> tuple[str, str]:
    parts = repository.split('/')
    if len(parts) != 2 or not all(parts):
        raise ValueError('repository must use OWNER/REPOSITORY format')

    return parts[0], parts[1]


def _normalize_ruleset(ruleset: dict[str, Any]) -> dict[str, Any]:
    normalized = {field: ruleset[field] for field in RULESET_FIELDS if field in ruleset}
    normalized.setdefault('bypass_actors', [])
    return normalized
