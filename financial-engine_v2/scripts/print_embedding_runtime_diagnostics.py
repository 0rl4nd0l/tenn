#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.embeddings import get_embedding_runtime_diagnostics  # noqa: E402


def main() -> int:
    print(json.dumps(get_embedding_runtime_diagnostics(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
