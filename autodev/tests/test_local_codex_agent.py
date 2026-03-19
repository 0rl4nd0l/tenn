from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "local_codex_agent.py"
    spec = importlib.util.spec_from_file_location("local_codex_agent", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load local_codex_agent module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_tool_call_from_tool_tag_json() -> None:
    mod = _load_module()
    parsed = mod.maybe_parse_tool_call('<tool_call>{"tool":"read_file","path":"README.md"}</tool_call>')
    assert parsed == {"tool": "read_file", "path": "README.md"}


def test_parse_tool_call_from_fenced_json() -> None:
    mod = _load_module()
    raw = """```json
{"tool":"rg_search","pattern":"native_manager","path":"autodev"}
```"""
    parsed = mod.maybe_parse_tool_call(raw)
    assert parsed == {"tool": "rg_search", "pattern": "native_manager", "path": "autodev"}


def test_parse_tool_call_from_function_style() -> None:
    mod = _load_module()
    raw = """```sh
run_shell(command="git status --short", timeout_seconds=45)
```"""
    parsed = mod.maybe_parse_tool_call(raw)
    assert parsed == {"tool": "run_shell", "command": "git status --short", "timeout_seconds": 45}


def test_parse_tool_call_from_function_style_with_dict_arg() -> None:
    mod = _load_module()
    parsed = mod.maybe_parse_tool_call('read_file({"path":"README.md","offset":1,"limit":20})')
    assert parsed == {"tool": "read_file", "path": "README.md", "offset": 1, "limit": 20}


def test_parse_tool_call_ignores_non_call_text() -> None:
    mod = _load_module()
    assert mod.maybe_parse_tool_call('Use run_shell(command="ls") only when needed.') is None
