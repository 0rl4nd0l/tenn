from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_recover_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "openclaw_runtime_recover.py"
    spec = importlib.util.spec_from_file_location("openclaw_runtime_recover", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load openclaw_runtime_recover module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _find_agent(payload: dict, agent_id: str) -> dict:
    agents_list = ((payload.get("agents") or {}).get("list") or [])
    for item in agents_list:
        if isinstance(item, dict) and item.get("id") == agent_id:
            return item
    raise AssertionError(f"agent not found: {agent_id}")


def test_normalize_config_defaults_to_local_without_key(monkeypatch, tmp_path: Path) -> None:
    recover = _load_recover_module()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENCLAW_TENN_PLANNER_MODEL", raising=False)
    monkeypatch.delenv("OPENCLAW_TENN_LOCAL_PLANNER_MODEL", raising=False)
    monkeypatch.delenv("OPENCLAW_TENN_FORCE_OPENAI_PLANNER", raising=False)

    payload, _changes, warnings = recover.normalize_config({}, tmp_path, openai_auth_profile_present=False)
    defaults = ((payload.get("agents") or {}).get("defaults") or {})
    assert defaults.get("contextTokens") == 65536
    main_agent = _find_agent(payload, "main")
    model_payload = main_agent.get("model")
    assert isinstance(model_payload, dict)
    assert model_payload.get("primary") == "ollama/qwen2.5-coder:14b"
    assert any("defaulting main planner to local model" in warning for warning in warnings)


def test_normalize_config_honors_local_override(monkeypatch, tmp_path: Path) -> None:
    recover = _load_recover_module()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENCLAW_TENN_PLANNER_MODEL", raising=False)
    monkeypatch.delenv("OPENCLAW_TENN_FORCE_OPENAI_PLANNER", raising=False)
    monkeypatch.setenv("OPENCLAW_TENN_LOCAL_PLANNER_MODEL", "ollama/qwen2.5-coder:7b")

    payload, _changes, _warnings = recover.normalize_config({}, tmp_path, openai_auth_profile_present=False)
    main_agent = _find_agent(payload, "main")
    model_payload = main_agent.get("model")
    assert isinstance(model_payload, dict)
    assert model_payload.get("primary") == "ollama/qwen2.5-coder:7b"


def test_normalize_config_force_openai_without_key(monkeypatch, tmp_path: Path) -> None:
    recover = _load_recover_module()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENCLAW_TENN_PLANNER_MODEL", raising=False)
    monkeypatch.setenv("OPENCLAW_TENN_FORCE_OPENAI_PLANNER", "1")

    payload, _changes, warnings = recover.normalize_config({}, tmp_path, openai_auth_profile_present=False)
    main_agent = _find_agent(payload, "main")
    model_payload = main_agent.get("model")
    assert isinstance(model_payload, dict)
    assert model_payload.get("primary") == "openai/gpt-4.1-mini"
    assert any("credentials are required" in warning for warning in warnings)


def test_review_agent_is_write_capable(monkeypatch, tmp_path: Path) -> None:
    recover = _load_recover_module()
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("OPENCLAW_TENN_PLANNER_MODEL", raising=False)
    monkeypatch.delenv("OPENCLAW_TENN_LOCAL_PLANNER_MODEL", raising=False)
    monkeypatch.delenv("OPENCLAW_TENN_FORCE_OPENAI_PLANNER", raising=False)

    payload, _changes, _warnings = recover.normalize_config({}, tmp_path, openai_auth_profile_present=False)
    review_agent = _find_agent(payload, "review-local")
    tools = review_agent.get("tools")
    assert isinstance(tools, dict)
    deny = tools.get("deny")
    assert not isinstance(deny, list)


def test_normalize_config_uses_openclaw_auth_profile_for_openai(monkeypatch, tmp_path: Path) -> None:
    recover = _load_recover_module()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENCLAW_TENN_PLANNER_MODEL", raising=False)
    monkeypatch.delenv("OPENCLAW_TENN_LOCAL_PLANNER_MODEL", raising=False)
    monkeypatch.delenv("OPENCLAW_TENN_FORCE_OPENAI_PLANNER", raising=False)

    payload, _changes, warnings = recover.normalize_config({}, tmp_path, openai_auth_profile_present=True)
    main_agent = _find_agent(payload, "main")
    model_payload = main_agent.get("model")
    assert isinstance(model_payload, dict)
    assert model_payload.get("primary") == "openai/gpt-4.1-mini"
    assert not any("defaulting main planner to local model" in warning for warning in warnings)


def test_normalize_config_local_override_beats_openclaw_auth_profile(monkeypatch, tmp_path: Path) -> None:
    recover = _load_recover_module()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENCLAW_TENN_PLANNER_MODEL", raising=False)
    monkeypatch.delenv("OPENCLAW_TENN_FORCE_OPENAI_PLANNER", raising=False)
    monkeypatch.setenv("OPENCLAW_TENN_LOCAL_PLANNER_MODEL", "llamacpp/qwen2.5-coder-14b")

    payload, _changes, warnings = recover.normalize_config({}, tmp_path, openai_auth_profile_present=True)
    main_agent = _find_agent(payload, "main")
    model_payload = main_agent.get("model")
    assert isinstance(model_payload, dict)
    assert model_payload.get("primary") == "llamacpp/qwen2.5-coder-14b"
    assert not any("defaulting main planner to local model" in warning for warning in warnings)


def test_normalize_config_honors_context_tokens_override(monkeypatch, tmp_path: Path) -> None:
    recover = _load_recover_module()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENCLAW_TENN_PLANNER_MODEL", raising=False)
    monkeypatch.delenv("OPENCLAW_TENN_LOCAL_PLANNER_MODEL", raising=False)
    monkeypatch.delenv("OPENCLAW_TENN_FORCE_OPENAI_PLANNER", raising=False)
    monkeypatch.setenv("OPENCLAW_TENN_CONTEXT_TOKENS", "98304")

    payload, _changes, _warnings = recover.normalize_config({}, tmp_path, openai_auth_profile_present=False)
    defaults = ((payload.get("agents") or {}).get("defaults") or {})
    assert defaults.get("contextTokens") == 98304


def _write_dispatch_fixture(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "function normalizeToolCallNameForDispatch(rawName, allowedToolNames) {",
                "\treturn rawName.trim();",
                "}",
                "function isToolCallBlockType(type) {",
                '\treturn type === "toolCall" || type === "toolUse" || type === "functionCall";',
                "}",
                "function normalizeToolCallIdsInMessage(message) {",
                "\treturn message;",
                "}",
                "function trimWhitespaceFromToolCallNamesInMessage(message, allowedToolNames) {",
                '\tif (!message || typeof message !== "object") return;',
                "\tconst content = message.content;",
                "\tif (!Array.isArray(content)) return;",
                "\tnormalizeToolCallIdsInMessage(message);",
                "}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_inspect_text_tool_call_patch_marks_patch_required(tmp_path: Path) -> None:
    recover = _load_recover_module()
    openclaw_root = tmp_path / "openclaw"
    dispatch_path = openclaw_root / "dist" / "plugin-sdk" / "dispatch-test.js"
    _write_dispatch_fixture(dispatch_path)

    status, backups = recover.inspect_text_tool_call_patch(openclaw_root, apply=False)
    assert status["state"] == "patch_required"
    assert backups == []
    assert status["dispatch_files_total"] == 1
    assert status["dispatch_files_checked"] == 1


def test_inspect_text_tool_call_patch_applies_and_is_idempotent(tmp_path: Path) -> None:
    recover = _load_recover_module()
    openclaw_root = tmp_path / "openclaw"
    dispatch_path = openclaw_root / "dist" / "plugin-sdk" / "dispatch-test.js"
    _write_dispatch_fixture(dispatch_path)

    status_apply, backups_apply = recover.inspect_text_tool_call_patch(openclaw_root, apply=True)
    assert status_apply["state"] == "patched"
    assert status_apply["dispatch_files_patched"] == 1
    assert len(backups_apply) == 1
    patched_text = dispatch_path.read_text(encoding="utf-8")
    assert "inferToolCallBlocksFromTextForDispatch" in patched_text
    assert "const inferredToolCalls = inferToolCallBlocksFromTextForDispatch(content, allowedToolNames);" in patched_text

    status_again, backups_again = recover.inspect_text_tool_call_patch(openclaw_root, apply=False)
    assert status_again["state"] == "already_patched"
    assert status_again["dispatch_files_already_patched"] == 1
    assert backups_again == []
