import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from agents.github_settings.api import GitHubApiError, GitHubClient, write_output
from agents.github_settings.config import (
    ConfigError,
    dump_settings,
    load_settings,
)
from agents.github_settings.service import GitHubSettingsService, SettingsPlan

DEFAULT_CONFIG_PATH = Path('.github/repository-settings.yml')


class CliError(RuntimeError):
    pass


def parse_args(arguments: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Manage GitHub repository settings from checked-in YAML.'
    )
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument(
        '--repository', help='GitHub repository in OWNER/REPOSITORY format.'
    )
    parser.add_argument(
        '--api-url', default=os.environ.get('GITHUB_API_URL', 'https://api.github.com')
    )

    subparsers = parser.add_subparsers(dest='action', required=True)
    subparsers.add_parser('validate', help='Validate YAML without contacting GitHub.')
    subparsers.add_parser('plan', help='Show differences between YAML and GitHub.')

    apply_parser = subparsers.add_parser('apply', help='Apply YAML to GitHub.')
    apply_parser.add_argument(
        '--yes', action='store_true', help='Confirm the displayed changes.'
    )

    export_parser = subparsers.add_parser(
        'export', help='Export current GitHub settings as YAML.'
    )
    export_parser.add_argument('--output', type=Path)
    export_parser.add_argument('--force', action='store_true')
    return parser.parse_args(arguments)


def main(arguments: Optional[list[str]] = None) -> int:
    args = parse_args(arguments)

    try:
        if args.action == 'validate':
            settings = load_settings(args.config)
            print(f'Valid: {args.config} ({len(settings.rulesets)} ruleset(s))')
            return 0

        service = _build_service(args.repository, args.api_url)

        if args.action == 'export':
            content = dump_settings(service.read())
            if args.output is None:
                print(content, end='')
            else:
                write_output(args.output, content, force=args.force)
                print(f'Exported: {args.output}')
            return 0

        desired = load_settings(args.config)
        plan = service.plan(desired)
        _print_plan(plan)

        if args.action == 'plan' or not plan.has_changes:
            return 0

        if not args.yes:
            raise CliError('apply requires --yes after reviewing the plan')

        service.apply(plan)
        print('Applied GitHub repository settings.')
        return 0
    except (
        CliError,
        ConfigError,
        FileExistsError,
        GitHubApiError,
        OSError,
        ValueError,
    ) as error:
        print(f'agents-github-settings: {error}', file=sys.stderr)
        return 2


def detect_repository(explicit_repository: Optional[str]) -> str:
    if explicit_repository:
        return explicit_repository

    environment_repository = os.environ.get('GITHUB_REPOSITORY')
    if environment_repository:
        return environment_repository

    completed_process = subprocess.run(
        ['git', 'remote', 'get-url', 'origin'],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed_process.returncode != 0:
        raise CliError('pass --repository or set GITHUB_REPOSITORY')

    remote_url = completed_process.stdout.strip()
    remote_url = remote_url.removesuffix('.git')

    if remote_url.startswith('git@github.com:'):
        repository = remote_url.removeprefix('git@github.com:')
    elif 'github.com/' in remote_url:
        repository = remote_url.split('github.com/', maxsplit=1)[1]
    else:
        raise CliError('origin is not a github.com repository; pass --repository')

    if repository.count('/') != 1:
        raise CliError(
            'could not determine OWNER/REPOSITORY from origin; pass --repository'
        )

    return repository


def _build_service(repository: Optional[str], api_url: str) -> GitHubSettingsService:
    token = _load_token()
    return GitHubSettingsService(
        GitHubClient(token=token, api_url=api_url),
        detect_repository(repository),
    )


def _load_token() -> str:
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if token:
        return token

    completed_process = subprocess.run(
        ['gh', 'auth', 'token'],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed_process.returncode != 0 or not completed_process.stdout.strip():
        raise CliError('set GH_TOKEN or GITHUB_TOKEN, or authenticate the gh CLI')

    return completed_process.stdout.strip()


def _print_plan(plan: SettingsPlan) -> None:
    if not plan.has_changes:
        print('No GitHub settings changes.')
        return

    for field, value in plan.repository_update.items():
        print(f'UPDATE repository.{field} -> {value!r}')

    for ruleset in plan.ruleset_creates:
        print(f'CREATE ruleset {ruleset["name"]}')

    for update in plan.ruleset_updates:
        print(f'UPDATE ruleset {update.payload["name"]}')
