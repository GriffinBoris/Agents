#!/usr/bin/env python3

"""Regenerate the checked-in golden files for the Django code generator.

Run this after changing a template, a derivation rule, or the bundled example spec,
then review the diff. The golden files are the reviewable record of what the
generator emits, so an unreviewed change here is a change to every future resource.
"""

import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from agents.django_codegen.generator import generate  # noqa: E402
from agents.django_codegen.profile import load_profile  # noqa: E402
from agents.django_codegen.spec import load_spec  # noqa: E402


EXAMPLES_ROOT = PROJECT_ROOT / 'agents' / 'django_codegen' / 'examples'
GOLDEN_ROOT = PROJECT_ROOT / 'tests' / 'golden' / 'django_codegen'


def main() -> int:
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
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
