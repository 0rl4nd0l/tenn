from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_LOCAL_BACKEND = REPO_ROOT / "financial-engine_v2" / "scripts" / "run_local_backend.sh"


def test_run_local_backend_defaults_marketplace_to_direct_runtime() -> None:
    script = RUN_LOCAL_BACKEND.read_text(encoding="utf-8")

    assert 'export COCKPIT_STATE_DB="${COCKPIT_STATE_DB:-${DATA_ROOT}/cockpit/state.db}"' in script
    assert 'export MARKETPLACE_BROWSER_RUNTIME="${MARKETPLACE_BROWSER_RUNTIME:-direct}"' in script
    assert 'export MARKETPLACE_BROWSER_PROFILE_DIR="${MARKETPLACE_BROWSER_PROFILE_DIR:-${HOME}/.tenn/browser_profiles/facebook-marketplace-chrome}"' in script
    assert 'export MARKETPLACE_BROWSER_XDG_RUNTIME_DIR="${MARKETPLACE_BROWSER_XDG_RUNTIME_DIR:-/tmp/tenn-marketplace-runtime-$(id -u)}"' in script
