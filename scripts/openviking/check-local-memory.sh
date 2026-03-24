#!/usr/bin/env bash
# Validate a local OpenViking config and test provider connectivity.
# Usage:  scripts/openviking/check-local-memory.sh [/path/to/ov.conf]
#
# If no path is given, resolves via OPENVIKING_CONFIG_FILE or ~/.openviking/ov.conf.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENGINE_ROOT="${REPO_ROOT}/financial-engine_v2"
PYTHON="${ENGINE_ROOT}/.venv/bin/python"

if [[ ! -x "${PYTHON}" ]]; then
  PYTHON="$(command -v python3 || true)"
fi

if [[ -z "${PYTHON}" ]]; then
  echo "ERROR: python3 not found" >&2
  exit 1
fi

OV_CONF="${1:-${OPENVIKING_CONFIG_FILE:-${HOME}/.openviking/ov.conf}}"

echo "[check-local-memory] config: ${OV_CONF}"

if [[ ! -f "${OV_CONF}" ]]; then
  echo "FAIL: config file not found: ${OV_CONF}"
  echo ""
  echo "Copy an example config and edit it:"
  echo "  cp ${ENGINE_ROOT}/config/openviking/backend.ov.conf.example ~/.openviking/backend.ov.conf"
  echo "  cp ${ENGINE_ROOT}/config/openviking/cockpit.ov.conf.example ~/.openviking/cockpit.ov.conf"
  echo "  cp ${ENGINE_ROOT}/config/openviking/claude-code.ov.conf.example ~/.openviking/claude-code.ov.conf"
  exit 1
fi

"${PYTHON}" - "${OV_CONF}" <<'PY'
import sys, json, urllib.request, urllib.error
from pathlib import Path

conf_path = sys.argv[1]
with open(conf_path) as f:
    cfg = json.load(f)

ok = True

# Storage workspace
workspace = cfg.get("storage", {}).get("workspace", "")
workspace_expanded = str(Path(workspace).expanduser()) if workspace else ""
print(f"  storage.workspace : {workspace_expanded or '(not set)'}")
if workspace_expanded:
    p = Path(workspace_expanded)
    if p.exists():
        print(f"  workspace exists  : yes")
    else:
        print(f"  workspace exists  : no (will be created on first use)")

# VLM endpoint
vlm = cfg.get("vlm", {})
vlm_base = vlm.get("api_base", "")
if vlm_base:
    health_url = vlm_base.rstrip("/").rstrip("/v1") + "/health"
    try:
        with urllib.request.urlopen(health_url, timeout=3) as r:
            print(f"  vlm ({vlm_base}) : reachable (HTTP {r.status})")
    except Exception as e:
        # Try /v1/models as a fallback probe (llama.cpp)
        try:
            models_url = vlm_base.rstrip("/") + "/models"
            with urllib.request.urlopen(models_url, timeout=3) as r:
                print(f"  vlm ({vlm_base}) : reachable (HTTP {r.status})")
        except Exception:
            print(f"  vlm ({vlm_base}) : UNREACHABLE — {e}")
            ok = False
else:
    print("  vlm              : api_base not set")
    ok = False

# Embedding endpoint
dense = cfg.get("embedding", {}).get("dense", {})
embed_base = dense.get("api_base", "")
if embed_base:
    try:
        req = urllib.request.Request(
            embed_base.rstrip("/") + "/models",
            headers={"Authorization": "Bearer ollama"},
        )
        with urllib.request.urlopen(req, timeout=3) as r:
            print(f"  embedding ({embed_base}) : reachable (HTTP {r.status})")
    except Exception as e:
        print(f"  embedding ({embed_base}) : UNREACHABLE — {e}")
        ok = False
else:
    print("  embedding        : api_base not set")
    ok = False

print()
if ok:
    print("OK: config valid and providers reachable")
    sys.exit(0)
else:
    print("WARN: one or more providers unreachable (ensure llama.cpp and Ollama are running)")
    sys.exit(1)
PY
