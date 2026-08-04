import argparse
import sys
from pathlib import Path

from agents.django_codegen.fields import SpecError
from agents.django_codegen.generator import generate
from agents.django_codegen.guidance_links import drifted_links, load_links
from agents.django_codegen.profile import PROFILE_FILENAME, STARTER_PROFILE, load_profile
from agents.django_codegen.spec import load_spec
from agents.django_codegen.writer import DIFFERS, MATCHES, SKIPPED, apply_files


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='generate_django.py',
        description='Generate Django models, serializers, views, URLs, admin, and tests from a resource spec.',
    )
    parser.add_argument('specs', nargs='*', help='Resource spec YAML files.')
    parser.add_argument('--profile', help=f'Path to the project profile. Defaults to the nearest {PROFILE_FILENAME}.')
    parser.add_argument('--out', help='Output root. Defaults to the profile backend_root.')
    parser.add_argument(
        '--init-profile',
        nargs='?',
        const='.',
        metavar='DIRECTORY',
        help=f'Write a starter {PROFILE_FILENAME} into DIRECTORY (default: current directory) and exit.',
    )

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--check',
        dest='mode',
        action='store_const',
        const='check',
        help='Report drift without writing. Exits non-zero when generated output differs.',
    )
    mode_group.add_argument(
        '--diff',
        dest='mode',
        action='store_const',
        const='diff',
        help='Print a unified diff for every file that differs, without writing.',
    )
    mode_group.add_argument(
        '--force',
        dest='mode',
        action='store_const',
        const='force',
        help='Overwrite existing non-merge files. Merge targets are still left alone.',
    )
    parser.set_defaults(mode='write')
    return parser.parse_args(argv)


def init_profile(directory: str) -> int:
    target = Path(directory) / PROFILE_FILENAME

    if target.exists():
        print(f'{target} already exists. Edit it directly rather than regenerating it.', file=sys.stderr)
        return 1

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(STARTER_PROFILE, encoding='utf-8')
    print(f'Wrote {target}')
    print(
        '\nEvery value in it is a placeholder. Replace them with this repository\'s real\n'
        'helper names before generating, then check the file in. Reading one existing\n'
        'list view, create view, and view test is usually enough to fill it in.'
    )
    return 0


def warn_about_guidance_drift() -> None:
    try:
        drifted = drifted_links(load_links())
    except (SpecError, OSError):
        return

    if not drifted:
        return

    print('warning: generator templates may be stale. These guidance examples changed since', file=sys.stderr)
    print('         the templates were last reviewed against them:', file=sys.stderr)

    for link in drifted:
        print(f'         {link.example} -> {", ".join(link.templates)}', file=sys.stderr)

    print('', file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    if args.init_profile is not None:
        return init_profile(args.init_profile)

    if not args.specs:
        print('No resource specs given. Pass one or more spec files, or --init-profile to start.', file=sys.stderr)
        return 2

    try:
        profile = load_profile(Path(args.profile) if args.profile else None)
    except SpecError as error:
        print(f'profile error: {error}', file=sys.stderr)
        return 2

    if profile.path is None:
        print(
            f'warning: no {PROFILE_FILENAME} found, using built-in defaults. Scopes and roles will be\n'
            f'         empty, so generated views and tests will be thin. Run --init-profile first.',
            file=sys.stderr,
        )

    warn_about_guidance_drift()

    out_root = Path(args.out) if args.out else Path(profile.backend_root)
    drift = False

    for spec_path in args.specs:
        try:
            spec = load_spec(Path(spec_path), profile)
            files = generate(spec)
        except SpecError as error:
            print(f'{spec_path}: {error}', file=sys.stderr)
            return 2
        except OSError as error:
            print(f'{spec_path}: {error}', file=sys.stderr)
            return 2

        print(f'{spec_path} -> {spec.app}/{spec.feature} ({len(files)} files, mode={args.mode})')

        for result in apply_files(files, out_root, mode=args.mode):
            if result.status == MATCHES:
                continue

            marker = {DIFFERS: 'DRIFT', SKIPPED: 'EXISTS'}.get(result.status, result.status.upper())
            note = f'  # {result.file.note}' if result.file.note else ''
            print(f'  {marker:>11}  {result.file.path}{note}')

            if result.is_drift:
                drift = True

                if args.mode == 'diff':
                    print(result.diff)

    if args.mode == 'check' and drift:
        print('\nGenerated output differs from the files on disk.', file=sys.stderr)
        return 1

    return 0
