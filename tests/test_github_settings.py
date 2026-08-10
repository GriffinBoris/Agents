import tempfile
import unittest
from pathlib import Path
from typing import Any, Optional
from unittest.mock import patch

from agents.github_settings.cli import detect_repository, main
from agents.github_settings.config import (
    ConfigError,
    GitHubSettings,
    dump_settings,
    load_settings,
)
from agents.github_settings.service import GitHubSettingsService


class FakeGitHubClient:
    def __init__(
        self,
        repository: dict[str, Any],
        rulesets: tuple[dict[str, Any], ...] = (),
    ):
        self.repository = repository
        self.rulesets = rulesets
        self.calls: list[tuple[str, str, Optional[dict[str, Any]]]] = []

    def get(self, path: str) -> Any:
        self.calls.append(('GET', path, None))

        if '/rulesets/' in path:
            ruleset_id = int(
                path.split('/rulesets/', maxsplit=1)[1].split('?', maxsplit=1)[0]
            )
            return next(
                ruleset for ruleset in self.rulesets if ruleset['id'] == ruleset_id
            )

        if path.endswith('rulesets?includes_parents=false&per_page=100'):
            return [
                {
                    'id': ruleset['id'],
                    'name': ruleset['name'],
                    'source_type': 'Repository',
                }
                for ruleset in self.rulesets
            ]

        return self.repository

    def patch(self, path: str, payload: dict[str, Any]) -> Any:
        return self._write('PATCH', path, payload)

    def post(self, path: str, payload: dict[str, Any]) -> Any:
        return self._write('POST', path, payload)

    def put(self, path: str, payload: dict[str, Any]) -> Any:
        return self._write('PUT', path, payload)

    def _write(self, method: str, path: str, payload: dict[str, Any]) -> Any:
        self.calls.append((method, path, payload))
        return payload


class GitHubSettingsConfigTest(unittest.TestCase):
    def test_loads_repository_settings_and_referenced_ruleset(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            ruleset_directory = root / 'rulesets'
            ruleset_directory.mkdir()
            (ruleset_directory / 'main.yml').write_text(
                'name: Main\ntarget: branch\nenforcement: active\n'
                'conditions:\n  ref_name:\n    include: [~DEFAULT_BRANCH]\n    exclude: []\n'
                'rules:\n  - type: deletion\n',
                encoding='utf-8',
            )
            config_path = root / 'repository-settings.yml'
            config_path.write_text(
                'version: 1\nrepository:\n  delete_branch_on_merge: true\n'
                'rulesets:\n  - rulesets/main.yml\n',
                encoding='utf-8',
            )

            settings = load_settings(config_path)

            self.assertEqual({'delete_branch_on_merge': True}, settings.repository)
            self.assertEqual('Main', settings.rulesets[0]['name'])

    def test_rejects_unsupported_repository_setting(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            config_path = Path(temporary_directory) / 'settings.yml'
            config_path.write_text(
                'version: 1\nrepository:\n  unknown_setting: true\n',
                encoding='utf-8',
            )

            with self.assertRaisesRegex(ConfigError, 'unsupported repository settings'):
                load_settings(config_path)

    def test_rejects_ruleset_path_outside_config_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config_directory = root / '.github'
            config_directory.mkdir()
            config_path = config_directory / 'settings.yml'
            config_path.write_text(
                'version: 1\nrepository: {}\nrulesets:\n  - ../outside.yml\n',
                encoding='utf-8',
            )

            with self.assertRaisesRegex(ConfigError, 'must stay within'):
                load_settings(config_path)


class GitHubSettingsServiceTest(unittest.TestCase):
    def test_plan_and_apply_update_repository_and_upsert_rulesets(self) -> None:
        existing_ruleset = {
            'id': 42,
            'name': 'Existing',
            'target': 'branch',
            'enforcement': 'disabled',
            'bypass_actors': [],
            'conditions': {'ref_name': {'include': ['~DEFAULT_BRANCH'], 'exclude': []}},
            'rules': [{'type': 'deletion'}],
        }
        client = FakeGitHubClient(
            repository={'delete_branch_on_merge': False, 'allow_update_branch': True},
            rulesets=(existing_ruleset,),
        )
        service = GitHubSettingsService(client, 'owner/repository')
        desired = GitHubSettings(
            repository={'delete_branch_on_merge': True, 'allow_update_branch': True},
            rulesets=(
                {
                    'name': 'Existing',
                    'target': 'branch',
                    'enforcement': 'active',
                    'bypass_actors': [],
                    'conditions': {
                        'ref_name': {'include': ['~DEFAULT_BRANCH'], 'exclude': []}
                    },
                    'rules': [{'type': 'deletion'}],
                },
                {
                    'name': 'New',
                    'target': 'branch',
                    'enforcement': 'active',
                    'bypass_actors': [],
                    'conditions': {
                        'ref_name': {'include': ['refs/heads/release'], 'exclude': []}
                    },
                    'rules': [{'type': 'non_fast_forward'}],
                },
            ),
        )

        plan = service.plan(desired)
        service.apply(plan)

        self.assertEqual({'delete_branch_on_merge': True}, plan.repository_update)
        self.assertEqual(['New'], [ruleset['name'] for ruleset in plan.ruleset_creates])
        self.assertEqual(
            ['Existing'], [update.payload['name'] for update in plan.ruleset_updates]
        )
        self.assertIn(
            ('PATCH', '/repos/owner/repository', {'delete_branch_on_merge': True}),
            client.calls,
        )
        self.assertTrue(
            any(
                method == 'POST' and path.endswith('/rulesets')
                for method, path, _ in client.calls
            )
        )
        self.assertTrue(
            any(
                method == 'PUT' and path.endswith('/rulesets/42')
                for method, path, _ in client.calls
            )
        )

    def test_read_exports_only_managed_api_fields(self) -> None:
        client = FakeGitHubClient(
            repository={
                'name': 'repository',
                'private': False,
                'allow_update_branch': True,
                'delete_branch_on_merge': True,
            },
            rulesets=(
                {
                    'id': 7,
                    'node_id': 'RRS_123',
                    'name': 'Main',
                    'target': 'branch',
                    'enforcement': 'active',
                    'bypass_actors': [],
                    'conditions': {
                        'ref_name': {'include': ['~DEFAULT_BRANCH'], 'exclude': []}
                    },
                    'rules': [{'type': 'deletion'}],
                },
            ),
        )

        settings = GitHubSettingsService(client, 'owner/repository').read()
        exported = dump_settings(settings)

        self.assertNotIn('private:', exported)
        self.assertNotIn('node_id:', exported)
        self.assertIn('allow_update_branch: true', exported)
        self.assertIn('name: Main', exported)


class GitHubSettingsCliTest(unittest.TestCase):
    def test_detect_repository_supports_https_origin(self) -> None:
        completed_process = type(
            'CompletedProcess',
            (),
            {'returncode': 0, 'stdout': 'https://github.com/owner/repository.git\n'},
        )()

        with (
            patch.dict(
                'agents.github_settings.cli.os.environ',
                {'GITHUB_REPOSITORY': ''},
            ),
            patch(
                'agents.github_settings.cli.subprocess.run',
                return_value=completed_process,
            ),
        ):
            self.assertEqual('owner/repository', detect_repository(None))

    def test_validate_does_not_require_github_authentication(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            config_path = Path(temporary_directory) / 'settings.yml'
            config_path.write_text(
                'version: 1\nrepository:\n  allow_update_branch: true\n',
                encoding='utf-8',
            )

            exit_code = main(['--config', str(config_path), 'validate'])

            self.assertEqual(0, exit_code)


if __name__ == '__main__':
    unittest.main()
