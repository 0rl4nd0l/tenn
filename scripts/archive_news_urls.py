#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ARCHIVED_IMPL = Path(__file__).resolve().parent / "archive" / "legacy_cleanup_20260309" / "archive_news_urls.py"


def main() -> int:
    payload = {
        "status": "archived",
        "message": "archive page collection has been parked",
        "archived_impl": str(ARCHIVED_IMPL),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
