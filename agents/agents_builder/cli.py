import argparse
from pathlib import Path

from .build_runner import build
from .constants import ALL_TARGETS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Build installable agent guidance packages.')

    parser.add_argument(
        '--target',
        choices=(*ALL_TARGETS, 'all'),
        default='all',
        help='Target package to build.',
    )
    parser.add_argument(
        '--out',
        default='dist',
        help='Output directory root. Defaults to dist.',
    )
    parser.add_argument(
        '--layout',
        choices=('packaged', 'in-place'),
        default='packaged',
        help='Use packaged dist/<target> output or write the selected target directly into --out.',
    )
    parser.add_argument(
        '--clean',
        action='store_true',
        help='Remove each target output directory before rebuilding it.',
    )

    include_group = parser.add_mutually_exclusive_group()

    include_group.add_argument(
        '--include-examples',
        dest='include_examples',
        action='store_true',
        default=False,
        help='Embed full example bodies in generated instruction files.',
    )
    include_group.add_argument(
        '--metadata-only',
        dest='include_examples',
        action='store_false',
        help='List example metadata instead of full bodies.',
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_root = Path(args.out)

    if not out_root.is_absolute():
        out_root = Path.cwd() / out_root

    build(
        args.target,
        out_root,
        clean=args.clean,
        include_examples=args.include_examples,
        layout=args.layout,
    )
    return 0
