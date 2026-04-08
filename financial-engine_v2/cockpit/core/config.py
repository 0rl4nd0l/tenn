from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_env_loaded = False


def load_env(repo_root: Path | None = None) -> None:
    """Load .env from the financial-engine_v2 root (same file the backend uses).

    Shell env vars take precedence — dotenv only fills in missing keys.
    Safe to call multiple times; only loads once.
    """
    global _env_loaded  # noqa: PLW0603
    if _env_loaded:
        return
    _env_loaded = True

    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[2]
    env_path = repo_root / ".env"
    if not env_path.is_file():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path, override=False)
    except ImportError:
        # Fallback: parse KEY=VALUE lines manually (no interpolation).
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if key and key not in os.environ:
                os.environ[key] = value


DEFAULT_BACKEND_URL = "http://localhost:8000"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_LLAMACPP_URL = "http://localhost:8001"
DEFAULT_LLAMACPP_MODEL = "model:gpt-oss-20b"


DEFAULT_CONFIG = {
    "llm": {
        "provider": "llamacpp",
        "ollama_url": "",
        "llamacpp_url": DEFAULT_LLAMACPP_URL,
        "llamacpp_api_key": "local-openai-key",
        "model": DEFAULT_LLAMACPP_MODEL,
        "router_mode_opt_in": False,
        "timeout_seconds": 120,
    },
    "paths": {
        "allow_roots": [str(Path.home())],
        "default_workspace": str(Path.cwd()),
    },
    "memory": {
        "mode": "global_persisted",
        "state_db": str(Path.home() / ".financial_engine_cockpit" / "state.db"),
    },
    "actions": {
        "confirm_required": True,
    },
    "backend": {
        "api_base_url": DEFAULT_BACKEND_URL,
    },
    "web": {
        # Default on: agent tools (fetch_url, search_web) require explicit opt-out via Ops or pre-boot.
        "enabled_default": True,
    },
    "exports": {
        "dir": "reports/analysis",
    },
    "reports": {
        "dir": "reports",
    },
}

VALID_LLM_PROVIDERS = {"llamacpp", "ollama"}

# Must match keys used in cockpit_llm.yaml and HybridRouter.
VALID_HYBRID_ROUTER_POLICIES = frozenset(
    {"local_only", "local_preferred", "api_preferred", "api_only"}
)

VALID_TOOL_DEBUG_CHOICES = frozenset({"failures", "full", "off"})

# Default authoritative Cockpit LLM block (mirrors config/cockpit_llm.yaml).
DEFAULT_COCKPIT_LLM_FILE: dict[str, Any] = {
    "allow_env_override": False,
    "hybrid_router_policy": "local_preferred",
    "llm_profile_label": "ops",
    "tool_debug": "failures",
    # Per-stack defaults: applied at startup via os.environ.setdefault (host env wins if set).
    "defaults": {
        "extraction_model": "qwen2.5-14b-instruct",
        "embedding_model": "nomic-embed-text",
        "anthropic_model": "claude-sonnet-4-20250514",
    },
    "llm": {
        "provider": "llamacpp",
        "model": DEFAULT_LLAMACPP_MODEL,
        "llamacpp_url": DEFAULT_LLAMACPP_URL,
        "ollama_url": DEFAULT_OLLAMA_URL,
        "llamacpp_api_key": "local-openai-key",
        "timeout_seconds": 300,
        "router_mode_opt_in": False,
    },
}


def cockpit_llm_stack_defaults(cm: dict[str, Any]) -> dict[str, str]:
    """Normalized defaults map from cfg['cockpit_llm']['defaults'] (may be empty strings)."""
    raw = cm.get("defaults") if isinstance(cm.get("defaults"), dict) else {}
    return {
        "extraction_model": str(raw.get("extraction_model") or "").strip(),
        "embedding_model": str(raw.get("embedding_model") or "").strip(),
        "anthropic_model": str(raw.get("anthropic_model") or "").strip(),
    }


def apply_stack_defaults_to_environ(cm: dict[str, Any]) -> None:
    """Populate process env from cockpit_llm.defaults when keys are unset (host env wins).

    Also sets COCKPIT_LLM_PROFILE=ops when unset — maps to local-first routing with Anthropic
    fallback when ``allow_env_override`` is true (see resolve_hybrid_router_policy). When
    ``allow_env_override`` is false, hybrid_router_policy in YAML remains authoritative.
    """
    d = cockpit_llm_stack_defaults(cm)
    if d["extraction_model"]:
        os.environ.setdefault("EXTRACT_MODEL", d["extraction_model"])
    if d["embedding_model"]:
        os.environ.setdefault("EMBED_MODEL", d["embedding_model"])
        os.environ.setdefault("EMBEDDING_MODEL", d["embedding_model"])
    if d["anthropic_model"]:
        os.environ.setdefault("ANTHROPIC_MODEL", d["anthropic_model"])
    os.environ.setdefault("COCKPIT_LLM_PROFILE", "ops")


def effective_extraction_model(cm: dict[str, Any]) -> str:
    return os.environ.get("EXTRACT_MODEL", "").strip() or cockpit_llm_stack_defaults(cm)["extraction_model"]


def effective_embedding_model(cm: dict[str, Any]) -> str:
    return (
        os.environ.get("EMBED_MODEL", "").strip()
        or os.environ.get("EMBEDDING_MODEL", "").strip()
        or cockpit_llm_stack_defaults(cm)["embedding_model"]
    )


def effective_anthropic_model(cm: dict[str, Any]) -> str:
    return os.environ.get("ANTHROPIC_MODEL", "").strip() or cockpit_llm_stack_defaults(cm)["anthropic_model"]


def format_cockpit_llm_readonly(repo_root: Path) -> str:
    """Human-readable snapshot of authoritative cockpit_llm settings (for pre-boot / Ops)."""
    cfg = load_config(None)
    merge_cockpit_llm_file(cfg, repo_root)
    cm = cfg.get("cockpit_llm") or {}
    llm = cfg.get("llm") or {}
    path = repo_root / "config" / "cockpit_llm.yaml"
    pol = str(cm.get("hybrid_router_policy") or "")
    td = str(cm.get("tool_debug") or "")
    d = cockpit_llm_stack_defaults(cm)
    lines = [
        f"Source: {path}",
        f"allow_env_override: {cm.get('allow_env_override')}",
        "  (false = file only for cockpit LLM; true = env may override)",
        f"hybrid_router_policy: {pol}",
        f"  → {describe_hybrid_router_policy(pol)}",
        f"llm_profile_label: {cm.get('llm_profile_label')}  (diagnostic label only)",
        f"tool_debug → COCKPIT_TOOL_DEBUG: {td}",
        f"  → {describe_tool_debug_choice(td)}",
        "defaults (EXTRACT_MODEL / EMBED_MODEL / ANTHROPIC_MODEL setdefault on startup):",
        f"  extraction_model: {d['extraction_model'] or '(none)'}",
        f"  embedding_model: {d['embedding_model'] or '(none)'}",
        f"  anthropic_model: {d['anthropic_model'] or '(none)'}",
        f"provider / model: {llm.get('provider')} / {llm.get('model')}",
        f"llamacpp_url: {llm.get('llamacpp_url')}",
        f"router_mode_opt_in: {llm.get('router_mode_opt_in')}",
        "",
        "Edit config/cockpit_llm.yaml to change these; restart Cockpit to apply.",
    ]
    return "\n".join(lines)


def describe_hybrid_router_policy(policy: str | None) -> str:
    """One-line meaning for pre-boot / Ops (current value)."""
    key = (policy or "").strip().lower()
    return {
        "local_only": "Chat/agent uses only local llama.cpp (no Anthropic), subject to clients being wired.",
        "local_preferred": "Prefer local llama.cpp; Anthropic only when policy + keys allow.",
        "api_preferred": "Prefer Anthropic when API key is set; otherwise local.",
        "api_only": "Prefer Anthropic; fall back to local if the API is missing or fails.",
    }.get(key, "Unknown or invalid policy in YAML — fix hybrid_router_policy.")


def describe_tool_debug_choice(choice: str | None) -> str:
    raw = (choice or "failures").strip().lower()
    if raw in {"off", "0", "false", "none"}:
        raw = "off"
    return {
        "failures": "Logs failed tool calls and short hints in the chat UI.",
        "full": "Verbose tool traces for every tool invocation (noisy).",
        "off": "No tool trace lines appended to chat output.",
    }.get(raw, "Maps to env COCKPIT_TOOL_DEBUG for in-chat diagnostics.")


def preboot_service_probe_legend() -> str:
    """Short legend for the Service Health RichLog (probe icons)."""
    return (
        "Icons:  [OK] OK   [??] HTTP warning / non-200   [!!] unreachable / error   [ ] checking\n"
        "llama.cpp tags:  (router active) multi-model server  (router available) can enable  "
        "(single-model) one GGUF  (topology blocked: …) fix duplicate/ambiguous processes  "
        "(router degraded|unavailable) see llama-server logs"
    )


def cockpit_llm_yaml_glossary() -> str:
    """Long-form reference shown under the LLM panel on pre-boot."""
    return (
        "--- What each config field means (config/cockpit_llm.yaml) ---\n"
        "hybrid_router_policy — how HybridRouter picks local vs Anthropic for chat/agent:\n"
        "  local_only | local_preferred | api_preferred | api_only  (see one-line meanings above).\n"
        "llm_profile_label — Human label for diagnostics only; does not override hybrid_router_policy.\n"
        "tool_debug — failures | full | off → sets COCKPIT_TOOL_DEBUG (tool trace verbosity in chat).\n"
        "allow_env_override — false: file wins; COCKPIT_* / HYBRID_ROUTER_POLICY env ignored for cockpit LLM.\n"
        "  true: env vars may override the file (advanced / automation only).\n"
        "router_mode_opt_in — Intended llama-server router feature; actual mode depends on the running binary.\n"
        "defaults — extraction_model, embedding_model, anthropic_model; startup setdefault for EXTRACT_MODEL, "
        "EMBED_MODEL, EMBEDDING_MODEL, ANTHROPIC_MODEL (host env wins if already set).\n"
        "provider / model / llamacpp_url — Cockpit chat client (local llama.cpp).\n"
        "EXTRACT_MODEL — Backend extraction; effective = env or defaults.extraction_model.\n"
        "ollama_url — Ollama endpoint for embeddings; embedding model = env or defaults.embedding_model.\n"
        "anthropic_model — Claude when HybridRouter uses API; effective = ANTHROPIC_MODEL or defaults."
    )


def compute_effective_cockpit_config(
    repo_root: Path,
    config_path: str,
    *,
    profile: str,
    read_only: bool,
    no_web: bool,
    hybrid_router_policy: str | None = None,
) -> dict[str, Any]:
    """Same pipeline as launch: ``load_config`` → ``apply_runtime_flags``.

    Pre-boot UI must use this (not ``load_config(None)`` + merge only) so displayed
    values match ``_init_services`` / HybridRouter inputs.
    """
    base = load_config(config_path)
    return apply_runtime_flags(
        base,
        RuntimeFlags(
            config_path=config_path,
            profile=profile,
            read_only=read_only,
            no_web=no_web,
            repo_root=repo_root,
            hybrid_router_policy=hybrid_router_policy,
        ),
    )


def verify_effective_config_for_preboot(cfg: dict[str, Any]) -> list[str]:
    """Return human-readable errors; empty means safe to proceed (no silent invalid YAML)."""
    errors: list[str] = []
    cm = cfg.get("cockpit_llm") or {}
    pol = str(cm.get("hybrid_router_policy") or "").strip().lower()
    if pol and pol not in VALID_HYBRID_ROUTER_POLICIES:
        errors.append(
            f"Invalid hybrid_router_policy {pol!r} — must be one of "
            f"{sorted(VALID_HYBRID_ROUTER_POLICIES)} (fix config/cockpit_llm.yaml)."
        )
    td = str(cm.get("tool_debug") or "failures").strip().lower()
    if td in {"off", "0", "false", "none"}:
        td = "off"
    if td not in VALID_TOOL_DEBUG_CHOICES:
        errors.append(
            f"Invalid tool_debug {cm.get('tool_debug')!r} — must be failures | full | off "
            "(fix config/cockpit_llm.yaml)."
        )

    llm = cfg.get("llm") or {}
    provider = str(llm.get("provider") or "").strip().lower()
    if not provider:
        errors.append("llm.provider is empty after merge — check config/cockpit.yaml and config/cockpit_llm.yaml.")
    elif provider not in VALID_LLM_PROVIDERS:
        errors.append(
            f"Unsupported llm.provider {provider!r} — must be llamacpp or ollama."
        )

    model = str(llm.get("model") or "").strip()
    if not model:
        errors.append(
            "llm.model is empty — set an explicit model in config/cockpit_llm.yaml (no silent default)."
        )

    if provider == "llamacpp":
        url = str(llm.get("llamacpp_url") or "").strip()
        if not url:
            errors.append("llm.llamacpp_url is empty for llamacpp provider — set it in config/cockpit_llm.yaml.")
    if provider == "ollama":
        ourl = str(llm.get("ollama_url") or "").strip()
        if not ourl:
            errors.append("llm.ollama_url is empty for ollama provider — set it in config/cockpit_llm.yaml.")

    return errors


def normalize_model_name_for_compare(name: str) -> str:
    """Compare config model id to loaded GGUF path / router id."""
    s = (name or "").strip()
    if not s:
        return ""
    if "/" in s or s.lower().endswith(".gguf"):
        return Path(s).stem
    return s


def verify_chat_model_matches_llamacpp_runtime(
    cfg: dict[str, Any],
    loaded_model_id: str,
) -> str | None:
    """If llama.cpp reports a loaded model, it must match cfg llm.model or return error text."""
    llm = cfg.get("llm") or {}
    if str(llm.get("provider") or "").strip().lower() != "llamacpp":
        return None
    want = normalize_model_name_for_compare(str(llm.get("model") or ""))
    got = normalize_model_name_for_compare(loaded_model_id)
    if not got:
        return None
    if not want:
        return "Effective llm.model is empty — cannot verify against running llama.cpp."
    if want.lower() != got.lower():
        return (
            f"Config llm.model ({want!s}) does not match loaded llama.cpp model ({got!s}). "
            "Align config/cockpit_llm.yaml with the running server or reload the matching GGUF — "
            "launch is blocked to avoid silent mismatch."
        )
    return None


def format_llm_backend_tasks_readonly(repo_root: Path) -> str:
    """Legacy: merge cockpit_llm into defaults without loading config/cockpit.yaml.

    Prefer :func:`compute_effective_cockpit_config` + :func:`format_llm_backend_tasks_from_cfg`
    so the UI matches launch.
    """
    cfg = load_config(None)
    merge_cockpit_llm_file(cfg, repo_root)
    return format_llm_backend_tasks_from_cfg(cfg, repo_root, cockpit_config_path=None)


def format_llm_backend_tasks_from_cfg(
    cfg: dict[str, Any],
    repo_root: Path,
    *,
    cockpit_config_path: str | None = None,
) -> str:
    """Task-oriented read-only text from an *effective* config (post apply_runtime_flags)."""
    llm = cfg.get("llm") or {}
    cm = cfg.get("cockpit_llm") or {}
    provider = str(llm.get("provider") or "llamacpp")
    chat_model = str(llm.get("model") or "")
    llamacpp_url = str(llm.get("llamacpp_url") or "")
    ollama_url = str(llm.get("ollama_url") or "")
    policy = str(cm.get("hybrid_router_policy") or "")
    tool_dbg = str(cm.get("tool_debug") or "failures")
    allow_env = cm.get("allow_env_override", False)
    extract_disp = effective_extraction_model(cm) or "(not set — add defaults.extraction_model in YAML)"
    embed_disp = effective_embedding_model(cm) or "(not set)"
    anthropic_disp = effective_anthropic_model(cm) or "(not set)"
    path = repo_root / "config" / "cockpit_llm.yaml"
    policy_line = describe_hybrid_router_policy(policy)
    tool_line = describe_tool_debug_choice(tool_dbg)
    allow_line = (
        "Env vars cannot override cockpit LLM settings (file is authoritative)."
        if not allow_env
        else "COCKPIT_* / HYBRID_ROUTER_POLICY may override the file when set in the environment."
    )
    parity = (
        f"Effective pipeline (matches Launch): load_config({cockpit_config_path}) → apply_runtime_flags"
        if cockpit_config_path
        else "Effective config: merged defaults + config/cockpit_llm.yaml only (no config/cockpit.yaml — legacy path)."
    )
    body = "\n".join(
        [
            parity,
            f"Authoritative YAML: {path}",
            "",
            "Task → model / endpoint",
            f"  Cockpit chat & agent:    {provider}  {chat_model}",
            f"                             {llamacpp_url}",
            f"  Backend PDF extraction:   EXTRACT_MODEL={extract_disp}",
            f"  Embeddings (Ollama):      {ollama_url}  model={embed_disp}",
            f"  Anthropic (Claude API):   ANTHROPIC_MODEL={anthropic_disp}  (when router uses cloud)",
            "",
            "Resolved routing & diagnostics",
            f"  hybrid_router_policy = {policy}",
            f"    → {policy_line}",
            f"  llm_profile_label = {cm.get('llm_profile_label')!s}  (display only)",
            f"  tool_debug = {tool_dbg}  → {tool_line}",
            f"  allow_env_override = {allow_env}  → {allow_line}",
            f"  router_mode_opt_in (YAML) = {llm.get('router_mode_opt_in')}",
            "",
            "To change: edit config/cockpit_llm.yaml; set EXTRACT_MODEL in financial-engine_v2/.env for workers. "
            "Restart Cockpit / backend to apply.",
            "",
            cockpit_llm_yaml_glossary(),
        ]
    )
    return body


def llm_task_summary_lines_from_cfg(cfg: dict[str, Any]) -> list[str]:
    """Capability RichLog lines — must use the same effective cfg as Launch."""
    llm = cfg.get("llm") or {}
    cm = cfg.get("cockpit_llm") or {}
    policy = str(cm.get("hybrid_router_policy") or "")
    extract = effective_extraction_model(cm) or "(unset)"
    embed_m = effective_embedding_model(cm) or "(unset)"
    anthropic_m = effective_anthropic_model(cm) or "(unset)"
    return [
        "",
        "  LLM tasks (effective config = Launch)",
        f"    Chat:        {llm.get('provider')} / {llm.get('model')}",
        f"    Extraction:  EXTRACT_MODEL={extract}",
        f"    Embeddings:  {llm.get('ollama_url', '')}  model={embed_m}",
        f"    Anthropic:   ANTHROPIC_MODEL={anthropic_m}",
        f"    Routing:     {policy} — {describe_hybrid_router_policy(policy)}",
        f"    Tool traces: {cm.get('tool_debug')} — {describe_tool_debug_choice(str(cm.get('tool_debug')))}",
    ]


def llm_task_summary_lines(repo_root: Path) -> list[str]:
    """Legacy: without cockpit.yaml; prefer llm_task_summary_lines_from_cfg + compute_effective."""
    cfg = load_config(None)
    merge_cockpit_llm_file(cfg, repo_root)
    return llm_task_summary_lines_from_cfg(cfg)


def merge_cockpit_llm_file(cfg: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    """Load config/cockpit_llm.yaml (or COCKPIT_LLM_CONFIG_PATH) and merge into cfg.

    Sets cfg[\"cockpit_llm\"] (metadata) and deep-merges cfg[\"llm\"] with the file's llm block.
    """
    path = repo_root / "config" / "cockpit_llm.yaml"
    alt = os.getenv("COCKPIT_LLM_CONFIG_PATH")
    if alt:
        path = Path(alt)
    blob: dict[str, Any]
    if path.is_file():
        blob = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(blob, dict):
            raise ValueError("cockpit_llm config must be a mapping")
    else:
        blob = {}
    merged = _deep_merge(dict(DEFAULT_COCKPIT_LLM_FILE), blob)
    llm_part = merged.pop("llm", None)
    if not isinstance(llm_part, dict):
        llm_part = {}
    cfg.setdefault("llm", {})
    cfg["llm"] = _deep_merge(cfg["llm"], llm_part)
    cfg["cockpit_llm"] = merged
    return cfg


def _apply_llm_env_overrides(cfg: dict[str, Any]) -> None:
    """Apply COCKPIT_* / EXTRACT_MODEL env vars into cfg[\"llm\"] (legacy stack alignment)."""
    cfg.setdefault("llm", {})
    provider = str(os.getenv("COCKPIT_LLM_PROVIDER", cfg["llm"].get("provider", "llamacpp")) or "").strip().lower()
    if provider not in VALID_LLM_PROVIDERS:
        raise ValueError(f"Unsupported Cockpit LLM provider: {provider}")
    cfg["llm"]["provider"] = provider
    cfg["llm"]["ollama_url"] = os.getenv(
        "COCKPIT_OLLAMA_URL",
        os.getenv("OLLAMA_URL", cfg["llm"].get("ollama_url", DEFAULT_OLLAMA_URL)),
    )
    cfg["llm"]["llamacpp_url"] = os.getenv(
        "COCKPIT_LLAMACPP_URL",
        os.getenv("LLAMACPP_URL", cfg["llm"].get("llamacpp_url", DEFAULT_LLAMACPP_URL)),
    )
    cfg["llm"]["model"] = os.getenv(
        "COCKPIT_LLM_MODEL",
        os.getenv("EXTRACT_MODEL", cfg["llm"].get("model", DEFAULT_LLAMACPP_MODEL)),
    )
    cfg["llm"]["llamacpp_api_key"] = os.getenv("LLAMACPP_API_KEY") or os.getenv("LLM_API_KEY") or cfg["llm"].get(
        "llamacpp_api_key", ""
    )
    router_mode_value = os.getenv(
        "COCKPIT_ROUTER_MODE",
        str(cfg["llm"].get("router_mode_opt_in", False)),
    )
    cfg["llm"]["router_mode_opt_in"] = str(router_mode_value).strip().lower() in {"1", "true", "yes", "on"}


def _sync_tool_debug_env(cfg: dict[str, Any]) -> None:
    """Set COCKPIT_TOOL_DEBUG from cfg[\"cockpit_llm\"][\"tool_debug\"]."""
    cm = cfg.get("cockpit_llm") or {}
    raw = str(cm.get("tool_debug", "failures") or "failures").strip().lower()
    if raw in {"off", "0", "false", "none"}:
        os.environ["COCKPIT_TOOL_DEBUG"] = "off"
    elif raw in {"full", "all", "verbose"}:
        os.environ["COCKPIT_TOOL_DEBUG"] = "full"
    else:
        os.environ["COCKPIT_TOOL_DEBUG"] = "failures"


@dataclass
class RuntimeFlags:
    config_path: str
    profile: str
    read_only: bool
    no_web: bool
    repo_root: Path | None = None
    hybrid_router_policy: str | None = None


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config(config_path: str | None) -> dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    if not config_path:
        return cfg

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("cockpit config must be a mapping")
    return _deep_merge(cfg, payload)


def apply_runtime_flags(config: dict[str, Any], flags: RuntimeFlags) -> dict[str, Any]:
    cfg = dict(config)
    cfg["runtime"] = {
        "profile": flags.profile,
        "read_only": flags.read_only,
        "no_web": flags.no_web,
    }
    if flags.no_web:
        cfg.setdefault("web", {})
        cfg["web"]["enabled_default"] = False

    repo_root = flags.repo_root or Path(__file__).resolve().parents[2]
    merge_cockpit_llm_file(cfg, repo_root)

    # Apply explicit session-level routing policy override from flags (e.g. pre-boot)
    if flags.hybrid_router_policy:
        cfg.setdefault("cockpit_llm", {})
        cfg["cockpit_llm"]["hybrid_router_policy"] = flags.hybrid_router_policy

    cm = cfg.get("cockpit_llm") or {}
    apply_stack_defaults_to_environ(cm)

    allow_env = bool(cm.get("allow_env_override", False))

    if allow_env:
        _apply_llm_env_overrides(cfg)
        # Explicit env for tool traces (optional when allow_env_override is true).
        if os.getenv("COCKPIT_TOOL_DEBUG"):
            pass  # already in environ
        else:
            _sync_tool_debug_env(cfg)
    else:
        cfg.setdefault("llm", {})
        provider = str(cfg["llm"].get("provider", "llamacpp") or "").strip().lower()
        if provider not in VALID_LLM_PROVIDERS:
            raise ValueError(f"Unsupported Cockpit LLM provider: {provider}")
        cfg["llm"]["provider"] = provider
        _sync_tool_debug_env(cfg)

    cfg.setdefault("backend", {})
    cfg["backend"]["api_base_url"] = os.getenv(
        "COCKPIT_BACKEND_URL",
        cfg["backend"].get("api_base_url", DEFAULT_BACKEND_URL),
    )
    cfg.setdefault("db", {})
    cfg["db"]["database_url"] = os.getenv("DATABASE_URL", "sqlite:///./data/fe_local.db")

    cm = cfg.get("cockpit_llm") or {}
    llm = cfg.get("llm") or {}
    logger.info(
        "cockpit_llm: allow_env_override=%s hybrid_router_policy=%s profile_label=%s "
        "tool_debug=%s provider=%s model=%s llamacpp_url=%s router_mode_opt_in=%s (source=%s)",
        allow_env,
        cm.get("hybrid_router_policy"),
        cm.get("llm_profile_label"),
        os.environ.get("COCKPIT_TOOL_DEBUG"),
        llm.get("provider"),
        llm.get("model"),
        llm.get("llamacpp_url"),
        llm.get("router_mode_opt_in"),
        repo_root / "config" / "cockpit_llm.yaml",
    )
    return cfg
