from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


def _load_sync_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "openclaw_sync_openai_auth_from_1password.py"
    spec = importlib.util.spec_from_file_location("openclaw_sync_openai_auth_from_1password", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load openclaw_sync_openai_auth_from_1password module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_main_writes_token_profile_type(monkeypatch, tmp_path: Path) -> None:
    sync = _load_sync_module()
    auth_file = tmp_path / "auth-profiles.json"

    args = argparse.Namespace(
        secret_ref="op://Personal/API Credentials/credential",
        auth_file=str(auth_file),
        profile_id="openai:manual",
        provider="openai",
        op_bin="op",
        dry_run=False,
    )
    monkeypatch.setattr(sync, "parse_args", lambda: args)
    monkeypatch.setattr(sync, "_read_secret_from_op", lambda _op_bin, _secret_ref: "sk-test")

    exit_code = sync.main()
    assert exit_code == 0
    payload = json.loads(auth_file.read_text(encoding="utf-8"))
    assert payload["profiles"]["openai:manual"]["provider"] == "openai"
    assert payload["profiles"]["openai:manual"]["token"] == "sk-test"
    assert payload["profiles"]["openai:manual"]["type"] == "token"
