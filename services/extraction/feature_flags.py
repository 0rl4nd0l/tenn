#!/usr/bin/env python3
from __future__ import annotations

import os


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    value = str(raw).strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


ENABLE_STRICT_PERIOD_FILTER = _env_bool("ENABLE_STRICT_PERIOD_FILTER", True)
ENABLE_STRICT_SCOPE_FILTER = _env_bool("ENABLE_STRICT_SCOPE_FILTER", True)
ENABLE_STRICT_EVIDENCE = _env_bool("ENABLE_STRICT_EVIDENCE", True)
ENABLE_ANOMALY_FILTER = _env_bool("ENABLE_ANOMALY_FILTER", True)
