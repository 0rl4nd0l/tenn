#!/usr/bin/env python3
from __future__ import annotations

import json


def main() -> int:
    payload = {
        "status": "archived_placeholder",
        "message": "legacy archived-page collector has been retired from active pipeline",
        "location": str(__file__),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
