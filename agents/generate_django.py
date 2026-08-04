#!/usr/bin/env python3

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


try:
    import agents.django_codegen.cli
except ModuleNotFoundError as error:  # pragma: no cover - depends on the host environment
    if error.name not in {'jinja2', 'yaml'}:
        raise

    package = {'jinja2': 'jinja2', 'yaml': 'pyyaml'}[error.name]
    print(
        f'The Django code generator needs {package}, which is not installed.\n\n'
        f'    python3 -m pip install jinja2 pyyaml\n',
        file=sys.stderr,
    )
    raise SystemExit(2) from error


if __name__ == '__main__':
    raise SystemExit(agents.django_codegen.cli.main())
