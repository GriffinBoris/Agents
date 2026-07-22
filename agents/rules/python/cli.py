import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Optional

import libcst as cst

from agents.rules.python.runner import run_paths


def parse_args(arguments: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='agents-python-rules',
        description='Run repository-owned LibCST lint rules and safe refactors.',
    )
    parser.add_argument('action', choices=('check', 'fix'))
    parser.add_argument('paths', nargs='+', type=Path)
    parser.add_argument('--output', choices=('text', 'json'), default='text')
    return parser.parse_args(arguments)


def main(arguments: Optional[list[str]] = None) -> int:
    args = parse_args(arguments)

    try:
        results = run_paths(tuple(args.paths), fix=args.action == 'fix')
    except (OSError, cst.ParserSyntaxError) as error:
        print(f'agents-python-rules: {error}', file=sys.stderr)
        return 2

    diagnostics = [diagnostic for result in results for diagnostic in result.diagnostics]
    changed_paths = [result.path for result in results if result.changed]

    if args.output == 'json':
        print(
            json.dumps(
                {
                    'changed_paths': [str(path) for path in changed_paths],
                    'diagnostics': [asdict(diagnostic) for diagnostic in diagnostics],
                },
                indent=2,
                default=str,
            )
        )
    else:
        for path in changed_paths:
            print(f'FIXED {path}')

        for diagnostic in diagnostics:
            print(diagnostic.format())

    return 1 if diagnostics else 0
