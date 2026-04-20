#!/usr/bin/env python3

import sys
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent

if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))


import agents_builder.cli  # noqa: E402


if __name__ == '__main__':
    raise SystemExit(agents_builder.cli.main())
