#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    script_path = Path(__file__).resolve().parent / "probe_news_provider_coverage.py"
    spec = importlib.util.spec_from_file_location("probe_news_provider_coverage", str(script_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load probe script: {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return int(module.main(argv))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

