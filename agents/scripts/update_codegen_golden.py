#!/usr/bin/env python3

"""Refresh the Django code generator's review baselines.

By default this regenerates the checked-in golden files. Run it after changing a
template, a derivation rule, or a bundled example spec, then review the diff. The
golden files are the reviewable record of what the generator emits, so an
unreviewed change here is a change to every future resource.

Pass --accept-guidance to also re-record the guidance example digests. Only do that
after actually reviewing the templates the changed example governs. Accepting a
digest is a statement that the templates still match the guidance, not a way to
silence the failure.
"""

import argparse
import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from agents.django_codegen.generator import generate  # noqa: E402
from agents.django_codegen.guidance_links import drifted_links, load_links, record_digests  # noqa: E402
from agents.django_codegen.profile import load_profile  # noqa: E402
from agents.django_codegen.spec import load_spec  # noqa: E402


EXAMPLES_ROOT = PROJECT_ROOT / 'agents' / 'django_codegen' / 'examples'
GOLDEN_ROOT = PROJECT_ROOT / 'tests' / 'golden' / 'django_codegen'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Refresh the Django code generator review baselines.')
    parser.add_argument(
        '--accept-guidance',
        action='store_true',
        help='Re-record guidance example digests. Only after reviewing the templates they govern.',
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    profile = load_profile(EXAMPLES_ROOT / '.django-codegen.yaml')

    if GOLDEN_ROOT.exists():
        shutil.rmtree(GOLDEN_ROOT)

    written = 0

    for spec_path in sorted(path for path in EXAMPLES_ROOT.glob('*.yaml') if not path.name.startswith('.')):
        spec = load_spec(spec_path, profile)

        for generated in generate(spec):
            if not generated.content.strip():
                continue

            target = GOLDEN_ROOT / spec_path.stem / generated.path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(generated.content, encoding='utf-8')
            written += 1
            print(f'wrote {target.relative_to(PROJECT_ROOT)}')

    print(f'\n{written} golden files refreshed.')

    drifted = drifted_links(load_links())

    if args.accept_guidance:
        record_digests()
        print(f'Recorded digests for {len(load_links())} linked guidance examples.')
    elif drifted:
        print('\nLinked guidance examples have changed since the templates were reviewed:')

        for link in drifted:
            print(f'  {link.example} -> {", ".join(link.templates)}')

        print('\nReview those templates, then re-run with --accept-guidance.')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
