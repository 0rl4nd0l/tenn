"""Native Tenn manager runtime for OpenClaw-driven analyze/fix/verify flows."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest


RUN_ID_RE = re.compile(r"^\d{8}T\d{6}Z$")
DEFAULT_PROTECTED_PATHS = (
    ".git/",
    "financial-engine_v2/",
    "node_modules/",
    "memory/",
    "openclaw-dashboard/",
)
FIX_KEYWORDS = ("fix", "implement", "patch", "edit", "change", "optimize", "improve", "update")
VERIFY_KEYWORDS = ("verify", "retest", "re-run", "rerun", "check", "validate", "confirm")
SESSION_ENV_KEYS = (
    "OPENCLAW_SESSION_ID",
    "OPENCLAW_SESSION_KEY",
    "OPENCLAW_CHAT_SESSION",
    "SESSION_ID",
)
DEPRECATED_COMMANDS = {
    "start": "The daemon loop is retired. Use analyze/fix/verify in native OpenClaw sessions instead.",
    "stop": "The daemon loop is retired. Use native OpenClaw sessions instead.",
    "discover": "TASKS.md discovery is retired. Ask OpenClaw to analyze a scope directly.",
    "rag-index": "Repo RAG indexing is not part of the supported manager path.",
    "gates": "Gate tails are replaced by run manifests. Use report or commands.",
    "worker": "Worker tails are replaced by workers.json in the run manifest. Use report or commands.",
}
FAILURE_STATUSES = {
    "failed",
    "worker_error",
    "planner_not_ready",
    "worker_backend_not_ready",
    "backend_loading",
}
TRUTHY_VALUES = {"1", "true", "yes", "on"}
NO_PROXY_OPENER = urlrequest.build_opener(urlrequest.ProxyHandler({}))
WORKTREE_SPARSE_EXCLUDES = (".venv-docling-gpu/", "node_modules/")
WORKER_PROVIDER_VALUES = {"ollama", "llamacpp"}
OPENCLAW_AUTH_FILE_ENV = "OPENCLAW_TENN_OPENCLAW_AUTH_FILE"
DEFAULT_OPENCLAW_AUTH_FILE = Path.home() / ".openclaw" / "agents" / "main" / "agent" / "auth-profiles.json"


@dataclass(frozen=True)
class TennManagerConfig:
    repo_root: Path
    reports_root: Path
    runs_root: Path
    sessions_root: Path
    temp_root: Path
    default_branch: str
    protected_paths: tuple[str, ...]
    worker_script: Path
    worker_model: str
    worker_ollama_url: str
    worker_max_tool_steps: int
    worker_timeout_seconds: int
    planner_model: str
    python_bin: str
    worker_provider: str = "ollama"
    worker_openai_base_url: str = "http://127.0.0.1:8000/v1"
    worker_openai_api_key: str = ""
    worker_num_ctx: int = 32768


@dataclass
class WorkerExecution:
    role: str
    mode: str
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


def _read_simple_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        import yaml  # type: ignore
    except Exception:
        payload: dict[str, Any] = {}
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            key, value = line.split(":", 1)
            payload[key.strip()] = value.strip().strip('"').strip("'")
        return payload
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    return loaded if isinstance(loaded, dict) else {}


def _env_or_yaml(env_name: str, yaml_data: dict[str, Any], key: str, default: str) -> str:
    value = os.environ.get(env_name)
    if value is not None:
        return value
    raw = yaml_data.get(key, default)
    return str(raw)


def _is_truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in TRUTHY_VALUES


def _openclaw_auth_file_path() -> Path:
    override = os.environ.get(OPENCLAW_AUTH_FILE_ENV, "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return DEFAULT_OPENCLAW_AUTH_FILE


def _openclaw_openai_profile_present(auth_file: Path | None = None) -> bool:
    path = auth_file or _openclaw_auth_file_path()
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    if not isinstance(payload, dict):
        return False
    profiles = payload.get("profiles")
    if not isinstance(profiles, dict):
        return False
    for profile in profiles.values():
        if not isinstance(profile, dict):
            continue
        provider = str(profile.get("provider", "")).strip().lower()
        token = profile.get("token")
        profile_type = str(profile.get("type", "")).strip().lower()
        if provider != "openai":
            continue
        if not isinstance(token, str) or not token.strip():
            continue
        # Allow "manual" for backward compatibility with older files.
        if profile_type in {"", "token", "manual"}:
            return True
    return False


def _normalize_worker_provider(raw: str) -> str:
    value = raw.strip().lower()
    if value in WORKER_PROVIDER_VALUES:
        return value
    return "ollama"


def _split_provider_model(raw_model: str, default_provider: str) -> tuple[str, str]:
    value = raw_model.strip()
    if "/" in value:
        prefix, remainder = value.split("/", 1)
        provider = _normalize_worker_provider(prefix)
        if provider in WORKER_PROVIDER_VALUES and remainder.strip():
            return provider, remainder.strip()
    return default_provider, value


def load_config(repo_root: Path | None = None) -> TennManagerConfig:
    resolved_repo = (repo_root or Path(__file__).resolve().parents[2]).resolve()
    yaml_data = _read_simple_yaml(resolved_repo / "autodev" / "autodev.yaml")
    protected_raw = _env_or_yaml(
        "OPENCLAW_TENN_PROTECTED_PATHS",
        yaml_data,
        "protected_paths",
        ",".join(DEFAULT_PROTECTED_PATHS),
    )
    protected_paths = tuple(item.strip() for item in protected_raw.split(",") if item.strip())
    if not protected_paths:
        protected_paths = DEFAULT_PROTECTED_PATHS
    worker_provider_raw = os.environ.get("OPENCLAW_TENN_WORKER_PROVIDER", "").strip() or str(
        yaml_data.get("llm_provider_balanced", "ollama")
    )
    worker_provider = _normalize_worker_provider(worker_provider_raw)
    worker_model_env = os.environ.get("OPENCLAW_TENN_WORKER_MODEL", "").strip()
    if worker_model_env:
        worker_provider, worker_model = _split_provider_model(worker_model_env, worker_provider)
    elif worker_provider == "llamacpp":
        worker_model = str(yaml_data.get("llama_cpp_model_balanced", "qwen2.5-coder-14b"))
    else:
        worker_model = str(yaml_data.get("ollama_model_balanced", "qwen2.5-coder:7b"))

    explicit_planner_model = os.environ.get("OPENCLAW_TENN_PLANNER_MODEL", "").strip()
    explicit_local_planner_model = os.environ.get("OPENCLAW_TENN_LOCAL_PLANNER_MODEL", "").strip()
    local_planner_default = f"{worker_provider}/{worker_model}" if worker_provider in WORKER_PROVIDER_VALUES else f"ollama/{worker_model}"
    local_planner_model = explicit_local_planner_model or local_planner_default
    openai_api_key_present = bool(os.environ.get("OPENAI_API_KEY"))
    openai_auth_profile_present = _openclaw_openai_profile_present()
    force_openai_planner = _is_truthy_env("OPENCLAW_TENN_FORCE_OPENAI_PLANNER")
    if explicit_planner_model:
        planner_model = explicit_planner_model
    elif force_openai_planner:
        planner_model = "openai/gpt-4.1-mini"
    elif explicit_local_planner_model:
        planner_model = explicit_local_planner_model
    elif openai_api_key_present or openai_auth_profile_present:
        planner_model = "openai/gpt-4.1-mini"
    else:
        planner_model = local_planner_model
    worker_ollama_url = _env_or_yaml(
        "OPENCLAW_TENN_WORKER_OLLAMA_URL",
        yaml_data,
        "ollama_host",
        "http://127.0.0.1:11434",
    )
    worker_openai_base_url = _env_or_yaml(
        "OPENCLAW_TENN_WORKER_OPENAI_BASE_URL",
        yaml_data,
        "llama_cpp_base_url",
        "http://127.0.0.1:8000/v1",
    )
    worker_openai_api_key = _env_or_yaml(
        "OPENCLAW_TENN_WORKER_OPENAI_API_KEY",
        yaml_data,
        "llama_cpp_api_key",
        "",
    )
    max_steps_raw = _env_or_yaml(
        "OPENCLAW_TENN_WORKER_MAX_STEPS",
        yaml_data,
        "llm_max_generation_attempts",
        "12",
    )
    try:
        worker_max_tool_steps = max(4, int(max_steps_raw))
    except ValueError:
        worker_max_tool_steps = 12
    worker_num_ctx_raw = _env_or_yaml(
        "OPENCLAW_TENN_WORKER_NUM_CTX",
        yaml_data,
        "worker_num_ctx",
        "32768",
    )
    try:
        worker_num_ctx = max(4096, int(worker_num_ctx_raw))
    except ValueError:
        worker_num_ctx = 32768
    worker_timeout_raw = _env_or_yaml(
        "OPENCLAW_TENN_WORKER_TIMEOUT_SECONDS",
        yaml_data,
        "ollama_timeout_seconds",
        "120",
    )
    try:
        worker_timeout_seconds = max(30, int(worker_timeout_raw))
    except ValueError:
        worker_timeout_seconds = 120

    return TennManagerConfig(
        repo_root=resolved_repo,
        reports_root=resolved_repo / "autodev" / "reports",
        runs_root=resolved_repo / "autodev" / "reports" / "runs",
        sessions_root=resolved_repo / "autodev" / "reports" / "sessions",
        temp_root=Path(os.environ.get("OPENCLAW_TENN_TMP_ROOT", "/tmp/tenn-openclaw")).resolve(),
        default_branch=os.environ.get("OPENCLAW_TENN_DEFAULT_BRANCH", "main"),
        protected_paths=protected_paths,
        worker_script=(resolved_repo / "scripts" / "local_codex_agent.py").resolve(),
        worker_provider=worker_provider,
        worker_model=worker_model,
        worker_ollama_url=worker_ollama_url,
        worker_openai_base_url=worker_openai_base_url,
        worker_openai_api_key=worker_openai_api_key,
        worker_max_tool_steps=worker_max_tool_steps,
        worker_num_ctx=worker_num_ctx,
        worker_timeout_seconds=worker_timeout_seconds,
        planner_model=planner_model,
        python_bin=os.environ.get("PYTHON_BIN") or sys.executable,
    )


def _json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _make_run_dir(config: TennManagerConfig) -> Path:
    config.runs_root.mkdir(parents=True, exist_ok=True)
    base = datetime.now(timezone.utc)
    for offset_seconds in range(0, 120):
        run_id = (base + timedelta(seconds=offset_seconds)).strftime("%Y%m%dT%H%M%SZ")
        run_dir = config.runs_root / run_id
        if not run_dir.exists():
            run_dir.mkdir(parents=True, exist_ok=False)
            return run_dir
    raise RuntimeError("Could not allocate a unique run id")


def _prune_stale_temp_runs(config: TennManagerConfig, keep_run_id: str) -> None:
    ttl_raw = os.environ.get("OPENCLAW_TENN_TMP_TTL_SECONDS", "120")
    try:
        ttl_seconds = max(60, int(ttl_raw))
    except ValueError:
        ttl_seconds = 120

    root = config.temp_root
    if not root.exists():
        return
    now = time.time()
    for child in root.iterdir():
        if not child.is_dir():
            continue
        name = child.name
        if name == keep_run_id or not RUN_ID_RE.match(name):
            continue
        try:
            modified = child.stat().st_mtime
        except OSError:
            continue
        if (now - modified) < ttl_seconds:
            continue
        shutil.rmtree(child, ignore_errors=True)


def _resolve_session_id() -> str:
    for key in SESSION_ENV_KEYS:
        value = os.environ.get(key, "").strip()
        if value:
            safe = re.sub(r"[^A-Za-z0-9_.:-]+", "-", value)
            return safe[:120] or "default"
    return "default"


def _session_state_path(config: TennManagerConfig, session_id: str) -> Path:
    return config.sessions_root / f"{session_id}.json"


def _load_session_state(config: TennManagerConfig, session_id: str) -> dict[str, Any]:
    path = _session_state_path(config, session_id)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _save_session_state(config: TennManagerConfig, session_id: str, payload: dict[str, Any]) -> None:
    _json_dump(_session_state_path(config, session_id), payload)


def _read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _read_json_dict(path: Path) -> dict[str, Any]:
    raw = _read_text_if_exists(path).strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _append_command(
    records: list[dict[str, Any]],
    name: str,
    command: list[str],
    cwd: Path,
    returncode: int,
    stdout: str,
    stderr: str,
) -> None:
    records.append(
        {
            "name": name,
            "command": command,
            "cwd": str(cwd),
            "returncode": returncode,
            "stdout": stdout[-12000:],
            "stderr": stderr[-12000:],
        }
    )


def _run_command(command: list[str], cwd: Path) -> tuple[int, str, str]:
    timeout_raw = os.environ.get("OPENCLAW_TENN_COMMAND_TIMEOUT_SECONDS", "45")
    try:
        timeout_seconds = max(5, int(timeout_raw))
    except ValueError:
        timeout_seconds = 45
    try:
        proc = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        detail = f"command timed out after {timeout_seconds} seconds"
        joined_stderr = f"{stderr}\n{detail}".strip()
        return 124, stdout, joined_stderr


def _planner_mode(config: TennManagerConfig) -> str:
    return "openai" if config.planner_model.startswith("openai/") else "local_override"


def _http_get_json(url: str, timeout_seconds: float, headers: dict[str, str] | None = None) -> dict[str, Any]:
    req = urlrequest.Request(url=url, method="GET", headers=headers or {})
    try:
        with NO_PROXY_OPENER.open(req, timeout=timeout_seconds) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urlerror.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail[:400]}") from exc
    except urlerror.URLError as exc:
        raise RuntimeError(f"Could not reach {url}: {exc}") from exc
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON from {url}: {body[:200]}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError(f"Unexpected JSON payload from {url}: {type(parsed).__name__}")
    return parsed


def _extract_model_names(payload: dict[str, Any]) -> set[str]:
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


def _probe_ollama_model(ollama_url: str, model_id: str) -> tuple[str, str]:
    url = f"{ollama_url.rstrip('/')}/api/tags"
    try:
        payload = _http_get_json(url, timeout_seconds=4.0)
    except Exception as exc:
        return "unreachable", str(exc)
    model_names = _extract_model_names(payload)
    if model_names and model_id not in model_names:
        return "model_missing", f"model {model_id} is not installed in Ollama"
    return "ready", f"model {model_id} is available via Ollama"


def _probe_openai_model(base_url: str, model_id: str, api_key: str, *, backend_name: str) -> tuple[str, str]:
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    url = f"{base_url.rstrip('/')}/models"
    try:
        payload = _http_get_json(url, timeout_seconds=5.0, headers=headers)
    except Exception as exc:
        text = str(exc)
        if "Loading model" in text or "loading model" in text:
            return "backend_loading", text
        return "unreachable", text
    error_payload = payload.get("error")
    if isinstance(error_payload, dict):
        message = str(error_payload.get("message", ""))
        if "Loading model" in message or "loading model" in message:
            return "backend_loading", message
    model_names = _extract_model_names(payload)
    if model_names and model_id not in model_names:
        return "model_missing", f"model {model_id} is not present in {backend_name} endpoint"
    return "ready", f"model {model_id} is available via {backend_name}"


def _probe_gateway() -> tuple[str, str]:
    url = "http://127.0.0.1:18789/"
    req = urlrequest.Request(url=url, method="GET")
    try:
        with NO_PROXY_OPENER.open(req, timeout=3.0):
            pass
    except Exception as exc:
        return "unreachable", str(exc)
    return "ready", "gateway responded"


def _probe_planner_backend(config: TennManagerConfig) -> tuple[str, str]:
    planner_mode = _planner_mode(config)
    if planner_mode == "openai":
        if os.environ.get("OPENAI_API_KEY"):
            return "ready", f"planner model {config.planner_model}"
        if _openclaw_openai_profile_present():
            return "ready", f"planner model {config.planner_model} via OpenClaw auth profile"
        if _is_truthy_env("OPENCLAW_TENN_ALLOW_LOCAL_PLANNER"):
            return "missing_api_key", "OPENAI_API_KEY is missing; set it or set OPENCLAW_TENN_PLANNER_MODEL to a local model."
        return "missing_api_key", "OPENAI_API_KEY and OpenClaw OpenAI auth profile are missing."

    if config.planner_model.startswith("ollama/"):
        planner_local_model = config.planner_model.split("/", 1)[1].strip()
        return _probe_ollama_model(config.worker_ollama_url, planner_local_model)

    if config.planner_model.startswith("llamacpp/"):
        yaml_data = _read_simple_yaml(config.repo_root / "autodev" / "autodev.yaml")
        base_url = os.environ.get("OPENCLAW_TENN_LLAMACPP_BASE_URL", "").strip() or str(
            yaml_data.get("llama_cpp_base_url", "http://127.0.0.1:8000/v1")
        )
        api_key = os.environ.get("OPENCLAW_TENN_LLAMACPP_API_KEY", "").strip() or str(yaml_data.get("llama_cpp_api_key", ""))
        expected_id = config.planner_model.split("/", 1)[1].strip()
        return _probe_openai_model(base_url, expected_id, api_key, backend_name="llama.cpp")

    return "error", f"Unsupported planner provider in {config.planner_model}"


def _collect_backend_readiness(config: TennManagerConfig) -> dict[str, str]:
    planner_state, planner_detail = _probe_planner_backend(config)
    if config.worker_provider == "llamacpp":
        worker_backend = "llamacpp"
        worker_state, worker_detail = _probe_openai_model(
            config.worker_openai_base_url,
            config.worker_model,
            config.worker_openai_api_key,
            backend_name="llama.cpp",
        )
    else:
        worker_backend = "ollama"
        worker_state, worker_detail = _probe_ollama_model(config.worker_ollama_url, config.worker_model)
    gateway_state, gateway_detail = _probe_gateway()
    return {
        "planner_mode": _planner_mode(config),
        "planner_backend_state": planner_state,
        "planner_detail": planner_detail,
        "worker_backend": worker_backend,
        "worker_backend_state": worker_state,
        "worker_detail": worker_detail,
        "gateway_state": gateway_state,
        "gateway_detail": gateway_detail,
    }


def _git(config: TennManagerConfig, args: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    return _run_command(["git", *args], cwd or config.repo_root)


def _sparse_patterns() -> list[str]:
    patterns = ["/*"]
    for item in WORKTREE_SPARSE_EXCLUDES:
        cleaned = item.strip("/")
        if cleaned:
            patterns.append(f"!/{cleaned}/")
    return patterns


def _checkout_sparse_workspace(worktree: Path, commands: list[dict[str, Any]]) -> tuple[int, str]:
    sparse_cmd = ["git", "sparse-checkout", "set", "--no-cone", *_sparse_patterns()]
    sparse_rc, sparse_stdout, sparse_stderr = _run_command(sparse_cmd, cwd=worktree)
    _append_command(commands, "git_sparse_checkout_set", sparse_cmd, worktree, sparse_rc, sparse_stdout, sparse_stderr)
    if sparse_rc != 0:
        return sparse_rc, sparse_stderr.strip() or sparse_stdout.strip() or "git sparse-checkout set failed"

    checkout_cmd = ["git", "checkout", "--detach", "HEAD"]
    checkout_rc, checkout_stdout, checkout_stderr = _run_command(checkout_cmd, cwd=worktree)
    _append_command(commands, "git_checkout_detached", checkout_cmd, worktree, checkout_rc, checkout_stdout, checkout_stderr)
    if checkout_rc != 0:
        return checkout_rc, checkout_stderr.strip() or checkout_stdout.strip() or "git checkout --detach failed"
    return 0, ""


def _create_worktree(config: TennManagerConfig, run_id: str, commands: list[dict[str, Any]]) -> Path:
    temp_root = config.temp_root / run_id
    worktree = temp_root / "repo"
    temp_root.mkdir(parents=True, exist_ok=True)
    worktree_add_cmd = ["git", "worktree", "add", "--detach", "--no-checkout", str(worktree), "HEAD"]
    rc, stdout, stderr = _git(config, ["worktree", "add", "--detach", "--no-checkout", str(worktree), "HEAD"], cwd=config.repo_root)
    _append_command(commands, "git_worktree_add", worktree_add_cmd, config.repo_root, rc, stdout, stderr)
    if rc == 0:
        checkout_rc, checkout_error = _checkout_sparse_workspace(worktree, commands)
        if checkout_rc == 0:
            return worktree

    # `git worktree add` can leave a partially populated target directory on
    # timeout/failure; ensure fallback clone always gets a clean destination.
    if worktree.exists():
        shutil.rmtree(worktree, ignore_errors=True)
    worktree.mkdir(parents=True, exist_ok=True)

    clone_cmd = ["git", "clone", "--local", "--no-checkout", str(config.repo_root), "."]
    clone_rc, clone_stdout, clone_stderr = _run_command(clone_cmd, cwd=worktree)
    _append_command(commands, "git_clone_fallback", clone_cmd, worktree, clone_rc, clone_stdout, clone_stderr)
    if clone_rc != 0:
        raise RuntimeError(clone_stderr.strip() or clone_stdout.strip() or stderr.strip() or "isolated workspace creation failed")

    checkout_rc, checkout_error = _checkout_sparse_workspace(worktree, commands)
    if checkout_rc != 0:
        raise RuntimeError(checkout_error or "sparse checkout failed in fallback workspace")
    return worktree


def _cleanup_worktree(config: TennManagerConfig, worktree: Path | None, commands: list[dict[str, Any]]) -> None:
    if worktree is None:
        return
    rc, stdout, stderr = _git(config, ["worktree", "remove", "--force", str(worktree)], cwd=config.repo_root)
    _append_command(commands, "git_worktree_remove", ["git", "worktree", "remove", "--force", str(worktree)], config.repo_root, rc, stdout, stderr)
    parent = worktree.parent
    if parent.exists():
        shutil.rmtree(parent, ignore_errors=True)


def _changed_files(config: TennManagerConfig, worktree: Path, commands: list[dict[str, Any]]) -> list[str]:
    rc, stdout, stderr = _git(config, ["diff", "--name-only", "--relative", "HEAD", "--"], cwd=worktree)
    _append_command(commands, "git_diff_name_only", ["git", "diff", "--name-only", "--relative", "HEAD", "--"], worktree, rc, stdout, stderr)
    if rc != 0:
        raise RuntimeError(stderr.strip() or "git diff --name-only failed")
    return [line.strip() for line in stdout.splitlines() if line.strip()]


def _diff_check(config: TennManagerConfig, worktree: Path, commands: list[dict[str, Any]]) -> bool:
    rc, stdout, stderr = _git(config, ["diff", "--check"], cwd=worktree)
    _append_command(commands, "git_diff_check", ["git", "diff", "--check"], worktree, rc, stdout, stderr)
    return rc == 0


def _build_patch(config: TennManagerConfig, worktree: Path, commands: list[dict[str, Any]]) -> str:
    rc, stdout, stderr = _git(config, ["diff", "--binary", "HEAD", "--"], cwd=worktree)
    _append_command(commands, "git_diff_binary", ["git", "diff", "--binary", "HEAD", "--"], worktree, rc, stdout, stderr)
    if rc != 0:
        raise RuntimeError(stderr.strip() or "git diff --binary failed")
    return stdout


def _dirty_conflicts(config: TennManagerConfig, changed_files: list[str], commands: list[dict[str, Any]]) -> list[str]:
    if not changed_files:
        return []
    rc, stdout, stderr = _git(config, ["status", "--porcelain", "--", *changed_files], cwd=config.repo_root)
    _append_command(commands, "git_status_conflicts", ["git", "status", "--porcelain", "--", *changed_files], config.repo_root, rc, stdout, stderr)
    if rc != 0:
        raise RuntimeError(stderr.strip() or "git status failed")
    conflicts: list[str] = []
    for line in stdout.splitlines():
        if len(line) < 4:
            continue
        conflicts.append(line[3:].strip())
    return conflicts


def _status_snapshot(config: TennManagerConfig, cwd: Path, commands: list[dict[str, Any]], name: str) -> dict[str, str]:
    rc, stdout, stderr = _git(config, ["status", "--porcelain", "--untracked-files=all"], cwd=cwd)
    _append_command(commands, name, ["git", "status", "--porcelain", "--untracked-files=all"], cwd, rc, stdout, stderr)
    if rc != 0:
        raise RuntimeError(stderr.strip() or "git status snapshot failed")
    snapshot: dict[str, str] = {}
    for line in stdout.splitlines():
        if len(line) < 4:
            continue
        snapshot[line[3:].strip()] = line[:2]
    return snapshot


def _status_delta(before: dict[str, str], after: dict[str, str]) -> list[str]:
    changed: list[str] = []
    for path_text, state in after.items():
        if before.get(path_text) != state:
            changed.append(path_text)
    return sorted(changed)


def _apply_patch(config: TennManagerConfig, patch_path: Path, commands: list[dict[str, Any]]) -> None:
    rc, stdout, stderr = _git(config, ["apply", "--whitespace=nowarn", "--binary", str(patch_path)], cwd=config.repo_root)
    _append_command(commands, "git_apply_patch", ["git", "apply", "--whitespace=nowarn", "--binary", str(patch_path)], config.repo_root, rc, stdout, stderr)
    if rc != 0:
        raise RuntimeError(stderr.strip() or stdout.strip() or "git apply failed")


def _relative_matches(path_text: str, prefix: str) -> bool:
    normalized_path = path_text.replace("\\", "/")
    normalized_prefix = prefix.strip().replace("\\", "/")
    return normalized_path == normalized_prefix.rstrip("/") or normalized_path.startswith(normalized_prefix)


def _protected_path_hits(request_text: str, changed_files: list[str], protected_paths: tuple[str, ...]) -> list[str]:
    lowered_request = request_text.lower()
    hits: list[str] = []
    for changed in changed_files:
        for protected in protected_paths:
            if not _relative_matches(changed, protected):
                continue
            token = protected.rstrip("/").lower()
            if token and token not in lowered_request:
                hits.append(changed)
                break
    return sorted(set(hits))


def _build_worker_prompt(
    *,
    mode: str,
    role: str,
    request_text: str,
    previous_report: str,
    protected_paths: tuple[str, ...],
) -> str:
    def _sanitize_previous_report(text: str) -> str:
        if not text.strip():
            return ""
        marker = "\n## Worker Results"
        marker_index = text.find(marker)
        if marker_index >= 0:
            text = text[:marker_index]
        return text.strip()[-2000:]

    protected_text = ", ".join(protected_paths)
    base = [
        "You are operating on the Tenn repository inside a controlled snapshot.",
        "Do not touch protected paths unless the request explicitly scopes to them.",
        f"Protected paths: {protected_text}.",
        "Run the smallest relevant shell checks only.",
        "Return concise Markdown with sections: Summary, Findings, Commands, Files, Risks.",
    ]
    previous_context = _sanitize_previous_report(previous_report)
    if previous_context:
        base.append("Previous run context follows. Reuse it where helpful.")
        base.append(previous_context)
    if mode == "analyze":
        base.append("This is read-only analysis against the current repo snapshot. Do not modify files.")
    elif mode == "fix":
        base.append("This run is using an isolated git worktree. Implement the smallest correct fix there, then run targeted verification.")
    elif mode == "verify":
        base.append("This is read-only verification against the current repo snapshot. Prefer the same or smaller validation surface than the fix run.")
    if role == "review-local":
        base.append("Review the current diff critically. Call out regressions, weak assumptions, and missing checks.")
    return "\n".join(base + ["", f"Request: {request_text}"])


def run_worker_process(
    config: TennManagerConfig,
    *,
    role: str,
    mode: str,
    workspace: Path,
    prompt: str,
) -> WorkerExecution:
    request_timeout_override = os.environ.get("OPENCLAW_TENN_WORKER_REQUEST_TIMEOUT_SECONDS", "").strip()
    request_timeout_seconds = 0
    if request_timeout_override:
        try:
            request_timeout_seconds = int(request_timeout_override)
        except ValueError:
            request_timeout_seconds = 0
    if request_timeout_seconds <= 0:
        request_timeout_seconds = min(120, max(30, config.worker_timeout_seconds - 30))
    request_timeout_seconds = max(10, min(request_timeout_seconds, max(10, config.worker_timeout_seconds - 5)))

    command: list[str] = [
        config.python_bin,
        str(config.worker_script),
        "--workspace",
        str(workspace),
        "--model",
        config.worker_model,
        "--provider",
        "openai" if config.worker_provider == "llamacpp" else "ollama",
        "--base-url",
        config.worker_openai_base_url if config.worker_provider == "llamacpp" else config.worker_ollama_url,
        "--max-tool-steps",
        str(config.worker_max_tool_steps),
        "--num-ctx",
        str(config.worker_num_ctx),
        "--request-timeout-seconds",
        str(request_timeout_seconds),
        "--prompt",
        prompt,
    ]
    if config.worker_provider == "llamacpp" and config.worker_openai_api_key:
        command.extend(["--api-key", config.worker_openai_api_key])
    try:
        proc = subprocess.run(
            command,
            cwd=config.repo_root,
            text=True,
            capture_output=True,
            check=False,
            timeout=config.worker_timeout_seconds,
        )
        return WorkerExecution(
            role=role,
            mode=mode,
            command=command,
            returncode=proc.returncode,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
        )
    except subprocess.TimeoutExpired:
        return WorkerExecution(
            role=role,
            mode=mode,
            command=command,
            returncode=124,
            stdout="",
            stderr=f"worker timed out after {config.worker_timeout_seconds} seconds",
        )


def _write_report(
    path: Path,
    *,
    run_id: str,
    mode: str,
    request_text: str,
    session_id: str,
    previous_run_id: str | None,
    status: str,
    patch_applied: bool,
    changed_files: list[str],
    protected_hits: list[str],
    dirty_conflicts: list[str],
    workers: list[WorkerExecution],
) -> None:
    lines = [
        "# OpenClaw Tenn Run Report",
        f"- run id: `{run_id}`",
        f"- session id: `{session_id}`",
        f"- mode: `{mode}`",
        f"- status: `{status}`",
        f"- patch applied: `{str(patch_applied).lower()}`",
        f"- previous run id: `{previous_run_id or 'none'}`",
        "",
        "## Request",
        request_text.strip(),
        "",
        "## Changed Files",
    ]
    if changed_files:
        lines.extend(f"- `{item}`" for item in changed_files)
    else:
        lines.append("- none")
    lines.extend(["", "## Protected Path Blocks"])
    if protected_hits:
        lines.extend(f"- `{item}`" for item in protected_hits)
    else:
        lines.append("- none")
    lines.extend(["", "## Main Worktree Conflicts"])
    if dirty_conflicts:
        lines.extend(f"- `{item}`" for item in dirty_conflicts)
    else:
        lines.append("- none")
    lines.extend(["", "## Worker Results"])
    if not workers:
        lines.append("- none")
    for worker in workers:
        lines.extend(
            [
                f"### {worker.role}",
                f"- return code: `{worker.returncode}`",
                "",
                "```text",
                (worker.stdout or worker.stderr or "(no output)")[-6000:],
                "```",
                "",
            ]
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _build_manager_payload(
    *,
    mode: str,
    status: str,
    config: TennManagerConfig,
    patch_applied: bool,
    diff_clean: bool,
    changed_files: list[str],
    protected_hits: list[str],
    dirty_conflicts: list[str],
    error_text: str,
    cleanup_error: str,
    worktree: Path | None,
    backend: dict[str, str],
) -> dict[str, Any]:
    return {
        "mode": mode,
        "status": status,
        "planner_model": config.planner_model,
        "worker_provider": config.worker_provider,
        "worker_model": config.worker_model,
        "patch_applied": patch_applied,
        "diff_clean": diff_clean,
        "changed_files": changed_files,
        "protected_path_hits": protected_hits,
        "main_worktree_conflicts": dirty_conflicts,
        "error": error_text,
        "cleanup_error": cleanup_error,
        "worktree_path": str(worktree) if worktree else "",
        "planner_mode": backend.get("planner_mode", "unknown"),
        "planner_backend_state": backend.get("planner_backend_state", "unknown"),
        "planner_detail": backend.get("planner_detail", ""),
        "worker_backend": backend.get("worker_backend", "unknown"),
        "worker_backend_state": backend.get("worker_backend_state", "unknown"),
        "worker_detail": backend.get("worker_detail", ""),
        "gateway_state": backend.get("gateway_state", "unknown"),
        "gateway_detail": backend.get("gateway_detail", ""),
    }


def _mode_from_alias(alias: str, request_text: str) -> str:
    lowered = request_text.lower()
    if alias == "task-run":
        if any(token in lowered for token in VERIFY_KEYWORDS):
            return "verify"
        if any(token in lowered for token in FIX_KEYWORDS):
            return "fix"
        return "analyze"
    if alias == "task":
        return "analyze"
    if alias == "run":
        if request_text.strip():
            return _mode_from_alias("task-run", request_text)
        return "analyze"
    return alias


def _default_request_text(alias: str) -> str:
    if alias == "run":
        return "Analyze the Tenn workspace for the highest-priority broken OpenClaw orchestration issue and propose the next smallest safe fix."
    return ""


def execute_request(config: TennManagerConfig, mode: str, request_text: str, session_id: str | None = None) -> dict[str, Any]:
    resolved_session_id = session_id or _resolve_session_id()
    state = _load_session_state(config, resolved_session_id)
    previous_run_id = str(state.get("last_run_id", "")).strip() or None
    previous_report = ""
    if previous_run_id and RUN_ID_RE.match(previous_run_id):
        previous_report = _read_text_if_exists(config.runs_root / previous_run_id / "report.md")

    run_dir = _make_run_dir(config)
    run_id = run_dir.name
    _prune_stale_temp_runs(config, keep_run_id=run_id)
    commands: list[dict[str, Any]] = []
    workers: list[WorkerExecution] = []
    changed_files: list[str] = []
    protected_hits: list[str] = []
    dirty_conflicts: list[str] = []
    patch_applied = False
    patch_path = run_dir / "patch.diff"
    worktree: Path | None = None
    status = "completed"
    error_text = ""
    diff_clean = True
    backend = _collect_backend_readiness(config)

    request_payload = {
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "session_id": resolved_session_id,
        "mode": mode,
        "request": request_text,
        "previous_run_id": previous_run_id,
    }
    _json_dump(run_dir / "request.json", request_payload)
    _json_dump(
        run_dir / "manager.json",
        _build_manager_payload(
            mode=mode,
            status="starting",
            config=config,
            patch_applied=False,
            diff_clean=True,
            changed_files=[],
            protected_hits=[],
            dirty_conflicts=[],
            error_text="",
            cleanup_error="",
            worktree=None,
            backend=backend,
        ),
    )
    _json_dump(run_dir / "workers.json", {"workers": []})
    _json_dump(run_dir / "commands.json", {"commands": []})
    _write_report(
        run_dir / "report.md",
        run_id=run_id,
        mode=mode,
        request_text=request_text,
        session_id=resolved_session_id,
        previous_run_id=previous_run_id,
        status="starting",
        patch_applied=False,
        changed_files=[],
        protected_hits=[],
        dirty_conflicts=[],
        workers=[],
    )

    try:
        if backend["planner_backend_state"] != "ready":
            status = "backend_loading" if backend["planner_backend_state"] == "backend_loading" else "planner_not_ready"
            error_text = backend["planner_detail"]
        else:
            if backend["worker_backend_state"] != "ready":
                status = "worker_backend_not_ready"
                error_text = backend["worker_detail"]
            else:
                use_isolated_workspace = mode in {"analyze", "fix", "verify"}
                baseline_status: dict[str, str] = {}
                workspace = config.repo_root
                if use_isolated_workspace:
                    worktree = config.temp_root / run_id / "repo"
                    worktree = _create_worktree(config, run_id, commands)
                    workspace = worktree
                else:
                    baseline_status = _status_snapshot(config, config.repo_root, commands, "git_status_baseline")
                primary_role = "review-local" if mode in {"analyze", "verify"} else "coder-local"
                primary_prompt = _build_worker_prompt(
                    mode=mode,
                    role=primary_role,
                    request_text=request_text,
                    previous_report=previous_report,
                    protected_paths=config.protected_paths,
                )
                primary = run_worker_process(
                    config,
                    role=primary_role,
                    mode=mode,
                    workspace=workspace,
                    prompt=primary_prompt,
                )
                workers.append(primary)
                _append_command(commands, primary_role, primary.command, config.repo_root, primary.returncode, primary.stdout, primary.stderr)

                if mode == "fix":
                    reviewer = run_worker_process(
                        config,
                        role="review-local",
                        mode=mode,
                        workspace=workspace,
                        prompt=_build_worker_prompt(
                            mode=mode,
                            role="review-local",
                            request_text=request_text,
                            previous_report=primary.stdout,
                            protected_paths=config.protected_paths,
                        ),
                    )
                    workers.append(reviewer)
                    _append_command(commands, "review-local", reviewer.command, config.repo_root, reviewer.returncode, reviewer.stdout, reviewer.stderr)

                patch_text = ""
                if use_isolated_workspace:
                    changed_files = _changed_files(config, workspace, commands)
                    diff_clean = _diff_check(config, workspace, commands)
                    if mode == "fix":
                        patch_text = _build_patch(config, workspace, commands) if changed_files else ""
                else:
                    changed_files = _status_delta(
                        baseline_status,
                        _status_snapshot(config, config.repo_root, commands, "git_status_after"),
                    )
                    diff_clean = not changed_files
                if patch_text:
                    patch_path.write_text(patch_text, encoding="utf-8")

                protected_hits = _protected_path_hits(request_text, changed_files, config.protected_paths)
                if mode == "analyze" and changed_files:
                    status = "analysis_modified_files"
                elif any(worker.returncode != 0 for worker in workers):
                    status = "worker_error"
                elif protected_hits:
                    status = "protected_path_blocked"
                elif mode == "verify" and changed_files:
                    status = "verify_modified_files"
                elif mode == "fix" and patch_text:
                    dirty_conflicts = _dirty_conflicts(config, changed_files, commands)
                    if dirty_conflicts:
                        status = "main_worktree_conflict"
                    else:
                        _apply_patch(config, patch_path, commands)
                        patch_applied = True
                        status = "applied"
                elif mode == "fix":
                    status = "no_change"
                elif mode == "verify":
                    status = "verified" if diff_clean else "verify_diff_issue"
    except Exception as exc:
        status = "failed"
        error_text = str(exc)
    finally:
        cleanup_error = ""
        try:
            _cleanup_worktree(config, worktree, commands)
        except Exception as exc:
            cleanup_error = str(exc)
        manager_payload = _build_manager_payload(
            mode=mode,
            status=status,
            config=config,
            patch_applied=patch_applied,
            diff_clean=diff_clean,
            changed_files=changed_files,
            protected_hits=protected_hits,
            dirty_conflicts=dirty_conflicts,
            error_text=error_text,
            cleanup_error=cleanup_error,
            worktree=worktree,
            backend=backend,
        )
        _json_dump(run_dir / "manager.json", manager_payload)
        _json_dump(
            run_dir / "workers.json",
            {
                "workers": [
                    {
                        "role": worker.role,
                        "mode": worker.mode,
                        "command": worker.command,
                        "returncode": worker.returncode,
                        "stdout": worker.stdout[-12000:],
                        "stderr": worker.stderr[-12000:],
                    }
                    for worker in workers
                ]
            },
        )
        _json_dump(run_dir / "commands.json", {"commands": commands})
        _write_report(
            run_dir / "report.md",
            run_id=run_id,
            mode=mode,
            request_text=request_text,
            session_id=resolved_session_id,
            previous_run_id=previous_run_id,
            status=status,
            patch_applied=patch_applied,
            changed_files=changed_files,
            protected_hits=protected_hits,
            dirty_conflicts=dirty_conflicts,
            workers=workers,
        )
        _save_session_state(
            config,
            resolved_session_id,
            {
                "last_run_id": run_id,
                "last_mode": mode,
                "last_status": status,
                "last_request": request_text,
            },
        )

    return {
        "run_id": run_id,
        "status": status,
        "patch_applied": patch_applied,
        "changed_files": changed_files,
        "protected_path_hits": protected_hits,
        "main_worktree_conflicts": dirty_conflicts,
        "report_path": str(run_dir / "report.md"),
        "commands_path": str(run_dir / "commands.json"),
        "error": error_text,
        "planner_mode": backend["planner_mode"],
        "planner_backend_state": backend["planner_backend_state"],
        "worker_backend_state": backend["worker_backend_state"],
        "gateway_state": backend["gateway_state"],
    }


def _discover_runs(config: TennManagerConfig) -> list[Path]:
    if not config.runs_root.exists():
        return []
    return sorted(
        [
            path
            for path in config.runs_root.iterdir()
            if path.is_dir() and RUN_ID_RE.match(path.name) and (path / "request.json").exists()
        ],
        key=lambda item: item.name,
        reverse=True,
    )


def _summary_from_run(run_dir: Path) -> dict[str, Any]:
    request = _read_json_dict(run_dir / "request.json")
    manager = _read_json_dict(run_dir / "manager.json")
    manager_exists = (run_dir / "manager.json").exists()
    report_exists = (run_dir / "report.md").exists()
    commands_exists = (run_dir / "commands.json").exists()
    workers_exists = (run_dir / "workers.json").exists()
    status_value = str(manager.get("status", "")).strip()
    if not status_value:
        status_value = "manager_unreadable" if manager_exists else "incomplete"
    return {
        "run_id": run_dir.name,
        "mode": manager.get("mode", request.get("mode", "unknown")),
        "status": status_value,
        "patch_applied": bool(manager.get("patch_applied", False)),
        "changed_files": list(manager.get("changed_files", [])) if isinstance(manager.get("changed_files"), list) else [],
        "request": request.get("request", ""),
        "has_manager": manager_exists,
        "has_report": report_exists,
        "has_commands": commands_exists,
        "has_workers": workers_exists,
    }


def cmd_status(config: TennManagerConfig) -> int:
    runs = _discover_runs(config)
    backend = _collect_backend_readiness(config)
    print("manager_path=native_openclaw")
    print(f"repo_root={config.repo_root}")
    print(f"reports_root={config.reports_root}")
    print(f"planner_model={config.planner_model}")
    print(f"planner_mode={backend['planner_mode']}")
    print(f"planner_backend_state={backend['planner_backend_state']}")
    print(f"planner_detail={backend['planner_detail']}")
    print(f"worker_backend={backend['worker_backend']}")
    print(f"worker_backend_state={backend['worker_backend_state']}")
    print(f"worker_detail={backend['worker_detail']}")
    print(f"gateway_state={backend['gateway_state']}")
    print(f"gateway_detail={backend['gateway_detail']}")
    print(f"allow_local_planner={str(_is_truthy_env('OPENCLAW_TENN_ALLOW_LOCAL_PLANNER')).lower()}")
    print(f"force_openai_planner={str(_is_truthy_env('OPENCLAW_TENN_FORCE_OPENAI_PLANNER')).lower()}")
    print(f"openai_api_key_present={str(bool(os.environ.get('OPENAI_API_KEY'))).lower()}")
    print(f"openai_auth_profile_present={str(_openclaw_openai_profile_present()).lower()}")
    print(f"worker_provider={config.worker_provider}")
    print(f"worker_model={config.worker_model}")
    if config.worker_provider == "llamacpp":
        print(f"worker_base_url={config.worker_openai_base_url}")
    else:
        print(f"worker_base_url={config.worker_ollama_url}")
    print(f"worker_script={config.worker_script}")
    if not runs:
        print("last_run_id=none")
        print("last_status=none")
        return 0
    summary = _summary_from_run(runs[0])
    print(f"last_run_id={summary['run_id']}")
    print(f"last_mode={summary['mode']}")
    print(f"last_status={summary['status']}")
    print(f"last_patch_applied={str(summary['patch_applied']).lower()}")
    print(f"last_changed_files={len(summary['changed_files'])}")
    return 0


def cmd_latest(config: TennManagerConfig) -> int:
    runs = _discover_runs(config)
    if not runs:
        print("No runs found.")
        return 0
    summary = _summary_from_run(runs[0])
    print(f"run_id={summary['run_id']}")
    print(f"mode={summary['mode']}")
    print(f"status={summary['status']}")
    print(f"patch_applied={str(summary['patch_applied']).lower()}")
    print(f"changed_files={len(summary['changed_files'])}")
    request_text = str(summary["request"]).strip()
    if request_text:
        print(f"request={request_text}")
    return 0


def cmd_runs(config: TennManagerConfig, count: int) -> int:
    for run_dir in _discover_runs(config)[:count]:
        summary = _summary_from_run(run_dir)
        print(f"{summary['run_id']}  {summary['mode']}  {summary['status']}  changed={len(summary['changed_files'])}")
    return 0


def _resolve_run_dir(config: TennManagerConfig, run_id: str | None) -> Path:
    if run_id:
        if not RUN_ID_RE.match(run_id):
            raise ValueError("run_id must match YYYYMMDDTHHMMSSZ")
        run_dir = config.runs_root / run_id
        if not run_dir.exists():
            raise ValueError(f"run not found: {run_id}")
        return run_dir
    runs = _discover_runs(config)
    if not runs:
        raise ValueError("no runs available")
    return runs[0]


def cmd_report(config: TennManagerConfig, run_id: str | None) -> int:
    run_dir = _resolve_run_dir(config, run_id)
    print(_read_text_if_exists(run_dir / "report.md").rstrip())
    return 0


def cmd_commands(config: TennManagerConfig, run_id: str | None) -> int:
    run_dir = _resolve_run_dir(config, run_id)
    print(_read_text_if_exists(run_dir / "commands.json").rstrip())
    return 0


def cmd_doctor(config: TennManagerConfig) -> int:
    backend = _collect_backend_readiness(config)
    print(f"repo_root={config.repo_root}")
    print(f"runs_root={config.runs_root}")
    print(f"temp_root={config.temp_root}")
    print(f"worker_script_present={str(config.worker_script.exists()).lower()}")
    print(f"planner_model={config.planner_model}")
    print(f"planner_mode={backend['planner_mode']}")
    print(f"planner_backend_state={backend['planner_backend_state']}")
    print(f"worker_backend={backend['worker_backend']}")
    print(f"worker_backend_state={backend['worker_backend_state']}")
    print(f"gateway_state={backend['gateway_state']}")
    print(f"allow_local_planner={str(_is_truthy_env('OPENCLAW_TENN_ALLOW_LOCAL_PLANNER')).lower()}")
    print(f"force_openai_planner={str(_is_truthy_env('OPENCLAW_TENN_FORCE_OPENAI_PLANNER')).lower()}")
    print(f"openai_api_key_present={str(bool(os.environ.get('OPENAI_API_KEY'))).lower()}")
    print(f"openai_auth_profile_present={str(_openclaw_openai_profile_present()).lower()}")
    print(f"worker_provider={config.worker_provider}")
    print(f"worker_model={config.worker_model}")
    if config.worker_provider == "llamacpp":
        print(f"worker_base_url={config.worker_openai_base_url}")
    else:
        print(f"worker_base_url={config.worker_ollama_url}")
    print(f"openclaw_bin_present={str(shutil.which('openclaw') is not None).lower()}")
    print(f"protected_paths={','.join(config.protected_paths)}")
    recovery_script = config.repo_root / "scripts" / "openclaw_runtime_recover.py"
    if recovery_script.exists():
        rc, stdout, stderr = _run_command([config.python_bin, str(recovery_script)], cwd=config.repo_root)
        if rc == 0:
            try:
                payload = json.loads(stdout)
            except Exception:
                payload = {}
            if isinstance(payload, dict):
                print(f"host_config_state={payload.get('config_state', 'unknown')}")
                print(f"host_prompt_patch_state={(payload.get('prompt_patch') or {}).get('state', 'unknown')}")
                print(f"host_lazy_plugin_patch_state={(payload.get('lazy_plugin_patch') or {}).get('state', 'unknown')}")
                print(f"host_text_tool_call_patch_state={(payload.get('text_tool_call_patch') or {}).get('state', 'unknown')}")
                print(f"host_review_worker_write_enabled={str(payload.get('review_worker_write_enabled', False)).lower()}")
                print(f"host_planner_mode={payload.get('planner_mode', 'unknown')}")
        elif stderr.strip():
            print(f"host_recovery_check_error={stderr.strip()}")
    return cmd_status(config)


def _handle_request_command(config: TennManagerConfig, mode: str, text_parts: list[str]) -> int:
    request_text = " ".join(text_parts).strip()
    if not request_text:
        raise ValueError(f"{mode} requires a request")
    result = execute_request(config, mode=mode, request_text=request_text)
    print(f"run_id={result['run_id']}")
    print(f"status={result['status']}")
    print(f"patch_applied={str(result['patch_applied']).lower()}")
    print(f"report={result['report_path']}")
    if result["error"]:
        print(f"error={result['error']}")
    if result["protected_path_hits"]:
        print("protected_paths=" + ",".join(result["protected_path_hits"]))
    if result["main_worktree_conflicts"]:
        print("conflicts=" + ",".join(result["main_worktree_conflicts"]))
    print(f"planner_mode={result['planner_mode']}")
    print(f"planner_backend_state={result['planner_backend_state']}")
    print(f"worker_backend_state={result['worker_backend_state']}")
    print(f"gateway_state={result['gateway_state']}")
    return 0 if result["status"] not in FAILURE_STATUSES else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Native Tenn manager bridge for OpenClaw.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status")
    sub.add_parser("doctor")
    sub.add_parser("latest")

    runs_parser = sub.add_parser("runs")
    runs_parser.add_argument("count", nargs="?", type=int, default=10)

    report_parser = sub.add_parser("report")
    report_parser.add_argument("run_id", nargs="?")

    commands_parser = sub.add_parser("commands")
    commands_parser.add_argument("run_id", nargs="?")

    for name in ("analyze", "fix", "verify", "run", "task", "task-run"):
        request_parser = sub.add_parser(name)
        request_parser.add_argument("text", nargs=argparse.REMAINDER)

    for deprecated in sorted(DEPRECATED_COMMANDS):
        sub.add_parser(deprecated)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config()

    if args.command in DEPRECATED_COMMANDS:
        print(f"error: {DEPRECATED_COMMANDS[args.command]}", file=sys.stderr)
        return 2

    if args.command == "status":
        return cmd_status(config)
    if args.command == "doctor":
        return cmd_doctor(config)
    if args.command == "latest":
        return cmd_latest(config)
    if args.command == "runs":
        return cmd_runs(config, args.count)
    if args.command == "report":
        return cmd_report(config, args.run_id)
    if args.command == "commands":
        return cmd_commands(config, args.run_id)
    if args.command in {"analyze", "fix", "verify"}:
        return _handle_request_command(config, args.command, args.text)
    if args.command in {"run", "task", "task-run"}:
        request_text = " ".join(args.text).strip() or _default_request_text(args.command)
        if not request_text:
            raise ValueError(f"{args.command} requires a request")
        resolved_mode = _mode_from_alias(args.command, request_text)
        print(f"deprecated_alias={args.command}")
        return _handle_request_command(config, resolved_mode, [request_text])
    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
