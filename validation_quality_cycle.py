#!/usr/bin/env python3
"""Root shim for scripts/validation_quality_cycle.py."""

from __future__ import annotations

import runpy
from pathlib import Path


if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "scripts" / "validation_quality_cycle.py"
    runpy.run_path(str(target), run_name="__main__")
