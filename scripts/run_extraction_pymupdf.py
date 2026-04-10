#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from _run_extraction_method_cli import run_for_method


if __name__ == "__main__":
    raise SystemExit(run_for_method("pymupdf"))
