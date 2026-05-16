from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "financial-engine_v2" / "scripts" / "smoke_local.sh"


FAKE_CURL = """#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


args = sys.argv[1:]
url = next((arg for arg in args if arg.startswith("http://") or arg.startswith("https://")), "")
output = args[args.index("-o") + 1]
mode = os.environ.get("FAKE_BACKFILL_MODE", "celery")
log_path = os.environ["FAKE_CURL_LOG"]

with open(log_path, "a", encoding="utf-8") as handle:
    handle.write(url + "\\n")

if url.endswith("/api/health"):
    payload = {"status": "ok"}
elif "/api/backfill/ticker/" in url:
    payload = {"mode": mode, "ticker": "BHP"}
elif "/api/docs" in url:
    payload = [{"id": "doc-1", "ticker": "BHP"}]
elif url.endswith("/rag/query"):
    payload = {"ok": True, "hits": [{"id": "hit-1"}]}
else:
    payload = {"ok": False, "url": url}

Path(output).write_text(json.dumps(payload), encoding="utf-8")
print("200", end="")
"""


def _make_fake_bin(tmp_path: Path) -> Path:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    curl = fake_bin / "curl"
    curl.write_text(FAKE_CURL, encoding="utf-8")
    curl.chmod(curl.stat().st_mode | stat.S_IXUSR)
    python = fake_bin / "python"
    python.symlink_to(sys.executable)
    return fake_bin


def _run_smoke(
    tmp_path: Path,
    *,
    require_sync_backfill: bool,
    backfill_mode: str = "celery",
) -> subprocess.CompletedProcess[str]:
    log_path = tmp_path / "curl.log"
    fake_bin = _make_fake_bin(tmp_path)
    env = os.environ.copy()
    env.update(
        {
            "BASE_URL": "http://fake-backend",
            "FAKE_CURL_LOG": str(log_path),
            "FAKE_BACKFILL_MODE": backfill_mode,
            "PATH": f"{fake_bin}:{env['PATH']}",
        }
    )
    if require_sync_backfill:
        env["SMOKE_REQUIRE_SYNC_BACKFILL"] = "1"
    else:
        env.pop("SMOKE_REQUIRE_SYNC_BACKFILL", None)
    return subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_smoke_skips_sync_backfill_by_default(tmp_path: Path) -> None:
    result = _run_smoke(tmp_path, require_sync_backfill=False)

    assert result.returncode == 0
    assert '"sync_backfill":"skipped"' in result.stdout
    assert "/api/backfill/ticker/" not in (tmp_path / "curl.log").read_text(
        encoding="utf-8"
    )


def test_smoke_requires_sync_backfill_when_opted_in(tmp_path: Path) -> None:
    result = _run_smoke(
        tmp_path,
        require_sync_backfill=True,
        backfill_mode="celery",
    )

    assert result.returncode == 1
    assert "Backend not running in sync mode." in result.stderr
    assert "/api/backfill/ticker/BHP?years=1&process_documents=true" in (
        tmp_path / "curl.log"
    ).read_text(encoding="utf-8")


def test_smoke_accepts_sync_backfill_when_opted_in(tmp_path: Path) -> None:
    result = _run_smoke(
        tmp_path,
        require_sync_backfill=True,
        backfill_mode="sync",
    )

    assert result.returncode == 0
    assert '"mode": "sync"' in result.stdout
