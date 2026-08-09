import argparse
import sys
from pathlib import Path
from typing import Optional

from agents.agents_linter.config import default_config_path, load_config
from agents.agents_linter.runner import exit_code_for, print_results, run_tools


def parse_args(arguments: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='agents-lint',
        description='Run repository lint, custom-rule, type-check, and formatting tools through one command.',
    )
    parser.add_argument('action', choices=('check', 'fix'))
    parser.add_argument(
        '--root',
        type=Path,
        default=Path.cwd(),
        help='Project root. Defaults to the current directory.',
    )
    parser.add_argument(
        '--config',
        type=Path,
        help='TOML command manifest. Defaults to .agents-lint.toml or the bundled starter config.',
    )
    parser.add_argument(
        '--profile',
        action='append',
        choices=('backend', 'frontend', 'custom'),
        default=[],
        help='Limit execution to one or more profiles. By default all profiles run.',
    )
    parser.add_argument(
        '--fail-fast',
        action='store_true',
        help='Stop after the first failed or missing required tool.',
    )
    parser.add_argument('--output', choices=('text', 'json'), default='text')
    return parser.parse_args(arguments)


def main(arguments: Optional[list[str]] = None) -> int:
    args = parse_args(arguments)
    root = args.root.resolve()
    config_path = _resolve_config_path(args.config, root)

    try:
        config = load_config(config_path, root)
        results = run_tools(
            config,
            args.action,
            set(args.profile),
            keep_going=not args.fail_fast,
        )
    except (OSError, ValueError) as error:
        print(f'agents-lint: {error}', file=sys.stderr)
        return 2

    print_results(results, args.output)
    return exit_code_for(results)


def _resolve_config_path(config_path: Optional[Path], root: Path) -> Path:
    if config_path is not None:
        return config_path if config_path.is_absolute() else root / config_path

    project_config = root / '.agents-lint.toml'
    return project_config if project_config.is_file() else default_config_path()
