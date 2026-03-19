#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib import error, request


TOOL_TAG_RE = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL)
MODEL_NOT_FOUND_RE = re.compile(r"model .*not found", re.IGNORECASE)
FIRST_LINE_ONLY_RE = re.compile(
    r"\b(?:reply|respond|output)\s+(?:with\s+)?(?:only|just)\s+(?:the\s+)?first\s+line\b",
    re.IGNORECASE,
)
CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
DEFAULT_PROVIDER = "openai"
DEFAULT_OLLAMA_MODEL = "qwen2.5-coder:14b"
DEFAULT_OPENAI_MODEL = "qwen2.5-coder-14b"
DEFAULT_OPENAI_BASE_URL = "http://127.0.0.1:8001/v1"
DEFAULT_LOCAL_OPENAI_API_KEY = "local-openai-key"
PREFERRED_MODEL_FALLBACKS = (
    "qwen2.5-coder-14b",
    "qwen2.5-coder:14b",
    "deepseek-coder-6.7b",
    "deepseek-coder:6.7b",
    "llama3.1-8b",
    "llama3.1:8b",
    "phi3-mini",
    "phi3:mini",
)

SYSTEM_PROMPT = """You are a local coding agent with tool access.

When you need to use a tool, respond with EXACTLY one tool call and no extra text:
<tool_call>{"tool":"read_file","path":"relative/or/absolute/path","offset":1,"limit":200}</tool_call>

Available tools:
1) list_dir
   Args: {"path": str, "max_entries": int}
2) read_file
   Args: {"path": str, "offset": int|null, "limit": int|null}
3) write_file
   Args: {"path": str, "content": str}
4) rg_search
   Args: {"pattern": str, "path": str|null, "glob": str|null, "max_results": int}
5) run_shell
   Args: {"command": str, "timeout_seconds": int}

Path policy:
- For file tools, use paths inside the workspace.
- Do not use device files like /dev/null for file tools.

After receiving tool results, continue normally. Be concise, accurate, and action-oriented.
"""


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def default_model_for_provider(provider: str) -> str:
    if provider == "ollama":
        return DEFAULT_OLLAMA_MODEL
    return DEFAULT_OPENAI_MODEL


def _looks_like_local_endpoint(base_url: str) -> bool:
    value = str(base_url or "").strip().lower()
    return value.startswith("http://127.0.0.1") or value.startswith("http://localhost")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Local Codex-like coding agent with file/shell tools.")
    ap.add_argument(
        "--model",
        default=os.environ.get("LOCAL_CODEX_MODEL", os.environ.get("CODEX_LOCAL_MODEL", "")),
        help="Model name.",
    )
    ap.add_argument(
        "--provider",
        choices=("ollama", "openai"),
        default=os.environ.get("LOCAL_CODEX_PROVIDER", DEFAULT_PROVIDER),
        help="Inference provider.",
    )
    ap.add_argument("--base-url", default="", help="Inference server base URL.")
    ap.add_argument("--api-key", default="", help="API key for openai-compatible providers.")
    ap.add_argument("--ollama-url", default="http://127.0.0.1:11434", help=argparse.SUPPRESS)
    ap.add_argument("--workspace", default=".", help="Workspace root for tool commands.")
    ap.add_argument("--temperature", type=float, default=0.1, help="Sampling temperature.")
    ap.add_argument("--num-ctx", type=int, default=32768, help="Context window size.")
    ap.add_argument("--max-tool-steps", type=int, default=12, help="Max tool iterations per prompt.")
    ap.add_argument(
        "--request-timeout-seconds",
        type=int,
        default=max(10, _env_int("LOCAL_CODEX_REQUEST_TIMEOUT_SECONDS", 120)),
        help="Timeout for each model API request.",
    )
    ap.add_argument("--prompt", default="", help="Single-shot prompt mode.")
    ap.add_argument(
        "--all-files",
        action="store_true",
        help="Allow reading/writing files outside workspace with absolute paths.",
    )
    args = ap.parse_args()
    if not args.model.strip():
        args.model = default_model_for_provider(args.provider)
    if not args.base_url.strip():
        if args.provider == "openai":
            args.base_url = os.environ.get("LOCAL_CODEX_OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL)
        else:
            args.base_url = args.ollama_url
    if not args.api_key.strip():
        args.api_key = os.environ.get("LOCAL_CODEX_OPENAI_API_KEY", "")
    if args.provider == "openai" and not args.api_key.strip() and _looks_like_local_endpoint(args.base_url):
        args.api_key = DEFAULT_LOCAL_OPENAI_API_KEY
    if args.provider == "ollama":
        args.api_key = ""
    return args


def request_json(
    url: str,
    method: str,
    payload: dict[str, Any] | None,
    timeout_seconds: float,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    req = request.Request(
        url=url,
        method=method,
        data=None if payload is None else json.dumps(payload).encode("utf-8"),
        headers=req_headers,
    )
    try:
        with request.urlopen(req, timeout=timeout_seconds) as resp:
            body = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail[:400]}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Could not reach {url}: {exc}") from exc

    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise RuntimeError(f"Unexpected response type: {type(parsed).__name__}")
    return parsed


def post_json(url: str, payload: dict[str, Any], timeout_seconds: float, headers: dict[str, str] | None = None) -> dict[str, Any]:
    return request_json(url=url, method="POST", payload=payload, timeout_seconds=timeout_seconds, headers=headers)


def get_json(url: str, timeout_seconds: float, headers: dict[str, str] | None = None) -> dict[str, Any]:
    return request_json(url=url, method="GET", payload=None, timeout_seconds=timeout_seconds, headers=headers)


def _auth_headers(api_key: str) -> dict[str, str]:
    token = api_key.strip()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def extract_available_models(payload: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    models = payload.get("models")
    if not isinstance(models, list):
        models = payload.get("data")
    if not isinstance(models, list):
        return out
    for item in models:
        if not isinstance(item, dict):
            continue
        for key in ("name", "model", "id"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                out.add(value.strip())
    return out


def fetch_available_models(provider: str, base_url: str, api_key: str, timeout_seconds: float = 5.0) -> set[str] | None:
    url = ""
    headers: dict[str, str] | None = None
    if provider == "openai":
        url = f"{base_url.rstrip('/')}/models"
        headers = _auth_headers(api_key)
    else:
        url = f"{base_url.rstrip('/')}/api/tags"
    try:
        payload = get_json(url, timeout_seconds=timeout_seconds, headers=headers)
    except Exception:
        return None
    return extract_available_models(payload)


def select_runtime_model(requested_model: str, available_models: set[str] | None) -> tuple[str, str]:
    requested = requested_model.strip()
    if not requested:
        requested = PREFERRED_MODEL_FALLBACKS[0]

    if not available_models:
        return requested, "model catalog unavailable"
    if requested in available_models:
        return requested, "requested model available"

    for candidate in PREFERRED_MODEL_FALLBACKS:
        if candidate in available_models:
            return candidate, f"requested model missing, using installed fallback {candidate}"

    chosen = sorted(available_models)[0]
    return chosen, f"requested model missing, using first installed model {chosen}"


def is_model_not_found_error(exc: Exception) -> bool:
    return MODEL_NOT_FOUND_RE.search(str(exc)) is not None


def is_retryable_runner_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(
        marker in text
        for marker in (
            "runner process has terminated",
            "exit status 2",
            "timed out waiting for llama runner to start",
            "llm server not responding",
        )
    )


def build_runtime_model_candidates(current_model: str, available_models: set[str] | None) -> list[str]:
    out: list[str] = []

    def add(model: str) -> None:
        model = model.strip()
        if not model:
            return
        if model in out:
            return
        if available_models is not None and model not in available_models:
            return
        out.append(model)

    add(current_model)

    if available_models is None:
        for candidate in PREFERRED_MODEL_FALLBACKS:
            if candidate not in out:
                out.append(candidate)
        return out

    for candidate in PREFERRED_MODEL_FALLBACKS:
        add(candidate)
    for candidate in sorted(available_models):
        add(candidate)
    return out


def resolve_path(raw_path: str, workspace: Path, allow_outside: bool) -> Path:
    p = Path(raw_path).expanduser()
    if not p.is_absolute():
        p = (workspace / p).resolve()
    else:
        p = p.resolve()
    if allow_outside:
        return p
    try:
        p.relative_to(workspace)
    except ValueError as exc:
        raise RuntimeError(f"Path outside workspace not allowed: {p}") from exc
    return p


def tool_list_dir(args: dict[str, Any], workspace: Path, allow_outside: bool) -> dict[str, Any]:
    p = resolve_path(str(args.get("path", ".")), workspace, allow_outside)
    if not p.exists():
        return {"ok": False, "error": f"Path not found: {p}"}
    if not p.is_dir():
        return {"ok": False, "error": f"Not a directory: {p}"}
    max_entries = int(args.get("max_entries", 200))
    entries = []
    for name in sorted(os.listdir(p))[: max(1, max_entries)]:
        item = p / name
        entries.append({"name": name, "type": "dir" if item.is_dir() else "file"})
    return {"ok": True, "path": str(p), "entries": entries}


def tool_read_file(args: dict[str, Any], workspace: Path, allow_outside: bool) -> dict[str, Any]:
    p = resolve_path(str(args.get("path", "")), workspace, allow_outside)
    if not p.exists():
        return {"ok": False, "error": f"File not found: {p}"}
    if not p.is_file():
        return {"ok": False, "error": f"Not a file: {p}"}
    text = p.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    offset = args.get("offset")
    limit = args.get("limit")
    if offset is None and limit is None:
        return {"ok": True, "path": str(p), "content": text}
    start = max(1, int(offset or 1))
    lim = max(1, int(limit or 200))
    chunk = lines[start - 1 : start - 1 + lim]
    numbered = "\n".join(f"{i}|{line}" for i, line in enumerate(chunk, start=start))
    return {"ok": True, "path": str(p), "content": numbered}


def tool_write_file(args: dict[str, Any], workspace: Path, allow_outside: bool) -> dict[str, Any]:
    p = resolve_path(str(args.get("path", "")), workspace, allow_outside)
    content = str(args.get("content", ""))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"ok": True, "path": str(p), "bytes_written": len(content.encode("utf-8"))}


def tool_rg_search(args: dict[str, Any], workspace: Path, allow_outside: bool) -> dict[str, Any]:
    pattern = str(args.get("pattern", "")).strip()
    if not pattern:
        return {"ok": False, "error": "Missing pattern"}
    target = args.get("path")
    glob = args.get("glob")
    max_results = max(1, int(args.get("max_results", 200)))
    search_root = workspace if target in (None, "") else resolve_path(str(target), workspace, allow_outside)
    cmd = ["rg", "-n", "--max-count", str(max_results), pattern, str(search_root)]
    if isinstance(glob, str) and glob.strip():
        cmd.extend(["--glob", glob.strip()])
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    out = (proc.stdout or "") + (proc.stderr or "")
    return {"ok": proc.returncode in (0, 1), "returncode": proc.returncode, "output": out[:50000]}


def tool_run_shell(args: dict[str, Any], workspace: Path) -> dict[str, Any]:
    command = str(args.get("command", "")).strip()
    if not command:
        return {"ok": False, "error": "Missing command"}
    timeout = max(1, int(args.get("timeout_seconds", 60)))
    proc = subprocess.run(
        command,
        shell=True,
        cwd=str(workspace),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return {
        "ok": True,
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "")[:30000],
        "stderr": (proc.stderr or "")[:30000],
    }


def run_tool(call: dict[str, Any], workspace: Path, allow_outside: bool) -> dict[str, Any]:
    name = str(call.get("tool", "")).strip()
    args = call if isinstance(call, dict) else {}
    try:
        if name == "list_dir":
            return tool_list_dir(args, workspace, allow_outside)
        if name == "read_file":
            return tool_read_file(args, workspace, allow_outside)
        if name == "write_file":
            return tool_write_file(args, workspace, allow_outside)
        if name == "rg_search":
            return tool_rg_search(args, workspace, allow_outside)
        if name == "run_shell":
            return tool_run_shell(args, workspace)
        return {"ok": False, "error": f"Unknown tool: {name}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "tool": name}


def _strip_wrapping_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if len(lines) < 2:
        return stripped
    if not lines[0].startswith("```"):
        return stripped
    if lines[-1].strip() != "```":
        return stripped
    return "\n".join(lines[1:-1]).strip()


def _safe_ast_literal(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, float, bool, type(None))):
        return node.value
    raise ValueError("unsupported literal")


def _parse_python_style_tool_call(raw: str) -> dict[str, Any] | None:
    try:
        expr = ast.parse(raw, mode="eval")
    except SyntaxError:
        return None
    call = expr.body
    if not isinstance(call, ast.Call):
        return None
    if not isinstance(call.func, ast.Name):
        return None
    if call.keywords and any(keyword.arg is None for keyword in call.keywords):
        return None

    tool_name = call.func.id.strip()
    if not tool_name:
        return None

    payload: dict[str, Any] = {"tool": tool_name}
    if call.args:
        if len(call.args) != 1 or not isinstance(call.args[0], ast.Dict):
            return None
        dict_arg = call.args[0]
        for key_node, value_node in zip(dict_arg.keys, dict_arg.values):
            if key_node is None:
                return None
            key = _safe_ast_literal(key_node)
            if not isinstance(key, str):
                return None
            payload[key] = _safe_ast_literal(value_node)
    for keyword in call.keywords:
        assert keyword.arg is not None
        payload[keyword.arg] = _safe_ast_literal(keyword.value)
    return payload


def maybe_parse_tool_call(text: str) -> dict[str, Any] | None:
    raw_text = text or ""
    m = TOOL_TAG_RE.search(raw_text)
    if m:
        raw = m.group(1).strip()
    else:
        raw = _strip_wrapping_code_fence(raw_text)
        raw = CODE_FENCE_RE.sub("", raw).strip()

    def as_tool_payload(candidate: Any) -> dict[str, Any] | None:
        if not isinstance(candidate, dict):
            return None
        if not isinstance(candidate.get("tool"), str):
            return None
        return candidate

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = None

    direct = as_tool_payload(parsed)
    if direct is not None:
        return direct

    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            embedded = json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            embedded = None
        payload = as_tool_payload(embedded)
        if payload is not None:
            return payload

    return _parse_python_style_tool_call(raw)


def first_line(text: str) -> str:
    idx = text.find("\n")
    if idx == -1:
        return text
    return text[:idx]


def wants_first_line_only(prompt: str) -> bool:
    return FIRST_LINE_ONLY_RE.search(prompt or "") is not None


def strip_number_prefix(line: str) -> str:
    return re.sub(r"^\s*\d+\|", "", line)


def ask_model(
    provider: str,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    num_ctx: int,
    request_timeout_seconds: int,
) -> str:
    timeout_seconds = max(10, float(request_timeout_seconds))
    if provider == "openai":
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        resp = post_json(
            f"{base_url.rstrip('/')}/chat/completions",
            payload,
            timeout_seconds=timeout_seconds,
            headers=_auth_headers(api_key),
        )
        choices = resp.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        first = choices[0]
        if not isinstance(first, dict):
            return ""
        message = first.get("message")
        if not isinstance(message, dict):
            return ""
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            chunks: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        chunks.append(text)
            return "".join(chunks)
        return ""

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature, "num_ctx": num_ctx},
    }
    resp = post_json(
        f"{base_url.rstrip('/')}/api/chat",
        payload,
        timeout_seconds=timeout_seconds,
    )
    msg = resp.get("message", {})
    if not isinstance(msg, dict):
        return ""
    content = msg.get("content", "")
    return str(content or "")


def run_turn(
    user_prompt: str,
    messages: list[dict[str, str]],
    cfg: argparse.Namespace,
    workspace: Path,
) -> str:
    require_first_line_only = wants_first_line_only(user_prompt)
    messages.append({"role": "user", "content": user_prompt})

    for _ in range(max(1, int(cfg.max_tool_steps))):
        available_models = fetch_available_models(cfg.provider, cfg.base_url, cfg.api_key, timeout_seconds=5.0)
        candidates = build_runtime_model_candidates(cfg.model, available_models)
        last_exc: Exception | None = None
        assistant_text: str | None = None

        for candidate_model in candidates:
            try:
                assistant_text = ask_model(
                    cfg.provider,
                    cfg.base_url,
                    cfg.api_key,
                    candidate_model,
                    messages,
                    cfg.temperature,
                    cfg.num_ctx,
                    cfg.request_timeout_seconds,
                )
                if candidate_model != cfg.model:
                    previous_model = cfg.model
                    cfg.model = candidate_model
                    print(
                        f"[local-codex] runtime fallback switched model {previous_model} -> {candidate_model}",
                        file=sys.stderr,
                    )
                break
            except Exception as exc:
                last_exc = exc
                if is_model_not_found_error(exc) or is_retryable_runner_error(exc):
                    continue
                raise

        if assistant_text is None:
            if last_exc is not None and is_model_not_found_error(last_exc):
                hint = f". Try: ollama pull {cfg.model}" if cfg.provider == "ollama" else ""
                raise RuntimeError(f"{last_exc}{hint}") from last_exc
            if last_exc is not None:
                raise RuntimeError(
                    f"{last_exc} (attempted models: {', '.join(candidates)})"
                ) from last_exc
            raise RuntimeError("No model response and no runtime error detail available.")
        tool_call = maybe_parse_tool_call(assistant_text)
        if not tool_call:
            reply = first_line(assistant_text) if require_first_line_only else assistant_text
            messages.append({"role": "assistant", "content": reply})
            return reply

        tool_name = str(tool_call.get("tool", "")).strip()
        if require_first_line_only and tool_name == "read_file":
            tool_call = dict(tool_call)
            tool_call.setdefault("offset", 1)
            tool_call.setdefault("limit", 1)

        result = run_tool(tool_call, workspace, cfg.all_files)
        if require_first_line_only and tool_name == "read_file" and result.get("ok"):
            content = str(result.get("content", ""))
            reply = strip_number_prefix(first_line(content))
            messages.append({"role": "assistant", "content": reply})
            return reply

        messages.append({"role": "assistant", "content": assistant_text})
        messages.append(
            {
                "role": "user",
                "content": "TOOL_RESULT:\n" + json.dumps(result, ensure_ascii=True),
            }
        )
    return "Stopped after max tool steps. Re-run with a narrower prompt or higher --max-tool-steps."


def interactive_loop(cfg: argparse.Namespace, workspace: Path) -> int:
    print(f"Local Codex agent started | provider={cfg.provider} | model={cfg.model} | workspace={workspace}")
    print("Commands: /exit, /help")
    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    while True:
        try:
            prompt = input("\nYou> ").strip()
        except EOFError:
            print()
            return 0
        if not prompt:
            continue
        if prompt in {"/exit", "exit", "quit"}:
            return 0
        if prompt == "/help":
            print("Ask coding tasks naturally. Agent can read/write files, search with rg, and run shell commands.")
            continue

        try:
            answer = run_turn(prompt, messages, cfg, workspace)
        except Exception as exc:
            print(f"\nAgent error> {exc}")
            continue
        print(f"\nAgent> {answer}")


def main() -> int:
    cfg = parse_args()
    workspace = Path(cfg.workspace).expanduser().resolve()
    if not workspace.exists():
        print(f"error: workspace not found: {workspace}", file=sys.stderr)
        return 2
    available_models = fetch_available_models(cfg.provider, cfg.base_url, cfg.api_key, timeout_seconds=5.0)
    selected_model, reason = select_runtime_model(cfg.model, available_models)
    if selected_model != cfg.model:
        print(
            f"[local-codex] {reason}; switched model {cfg.model} -> {selected_model}",
            file=sys.stderr,
        )
        cfg.model = selected_model

    if cfg.prompt.strip():
        messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        try:
            answer = run_turn(cfg.prompt, messages, cfg, workspace)
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(answer)
        return 0

    return interactive_loop(cfg, workspace)


if __name__ == "__main__":
    raise SystemExit(main())
