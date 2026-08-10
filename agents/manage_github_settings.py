#!/usr/bin/env python3

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import agents.github_settings.cli  # noqa: E402

if __name__ == '__main__':
    raise SystemExit(agents.github_settings.cli.main())
