#!/usr/bin/env python3
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
from typing import Any


PROMPT_PATCH_RE = re.compile(
    r'function resolvePromptModeForSession\(sessionKey\)\s*\{\s*if \(!sessionKey\) return "full";\s*return isSubagentSessionKey\(sessionKey\) \? "minimal" : "full";\s*\}',
    re.DOTALL,
)
PROMPT_PATCH_REPLACEMENT = 'function resolvePromptModeForSession(sessionKey) {\n  return "minimal";\n}'
PLUGIN_STATIC_IMPORT_RE = re.compile(r'import \{ ([A-Za-z0-9_$]+) as loadOpenClawPlugins \} from "\./([^"]+\.js)";')
PLUGIN_FUNCTION_SYNC = "function ensurePluginRegistryLoaded() {"
PLUGIN_FUNCTION_ASYNC = "async function ensurePluginRegistryLoaded() {"
PLUGIN_DYNAMIC_IMPORT_TEMPLATE = 'const {{ {symbol}: loadOpenClawPlugins }} = await import("./{module}");'
DISPATCH_TEXT_TOOL_CALL_MARKER = "inferToolCallBlocksFromTextForDispatch"
DISPATCH_TRIM_FUNCTION_ANCHOR = "function trimWhitespaceFromToolCallNamesInMessage(message, allowedToolNames) {"
DISPATCH_NORMALIZE_IDS_NEEDLE = "\tnormalizeToolCallIdsInMessage(message);"
DISPATCH_HELPERS_TEMPLATE = """
function extractBalancedJsonObjectsForDispatchToolCalls(text) {
\tconst result = [];
\tlet depth = 0;
\tlet start = -1;
\tlet inString = false;
\tlet escaped = false;
\tfor (let i = 0; i < text.length; i += 1) {
\t\tconst ch = text[i];
\t\tif (inString) {
\t\t\tif (escaped) escaped = false;
\t\t\telse if (ch === "\\\\") escaped = true;
\t\t\telse if (ch === "\\"") inString = false;
\t\t\tcontinue;
\t\t}
\t\tif (ch === "\\"") {
\t\t\tinString = true;
\t\t\tcontinue;
\t\t}
\t\tif (ch === "{") {
\t\t\tif (depth === 0) start = i;
\t\t\tdepth += 1;
\t\t\tcontinue;
\t\t}
\t\tif (ch !== "}") continue;
\t\tif (depth === 0) continue;
\t\tdepth -= 1;
\t\tif (depth === 0 && start >= 0) {
\t\t\tresult.push(text.slice(start, i + 1));
\t\t\tstart = -1;
\t\t}
\t}
\treturn result;
}
function parseDispatchToolCallArguments(rawArgs) {
\tif (rawArgs == null) return {};
\tif (typeof rawArgs === "string") {
\t\tconst trimmed = rawArgs.trim();
\t\tif (!trimmed) return {};
\t\ttry {
\t\t\trawArgs = JSON.parse(trimmed);
\t\t} catch {
\t\t\treturn null;
\t\t}
\t}
\tif (!rawArgs || typeof rawArgs !== "object" || Array.isArray(rawArgs)) return {};
\treturn rawArgs;
}
function normalizeDispatchToolCallEntry(entry, allowedToolNames) {
\tif (!entry || typeof entry !== "object" || Array.isArray(entry)) return null;
\tconst rawName = typeof entry.name === "string" ? entry.name : typeof entry.function?.name === "string" ? entry.function.name : "";
\tif (!rawName || !rawName.trim()) return null;
\tconst normalizedName = normalizeToolCallNameForDispatch(rawName, allowedToolNames);
\tif (allowedToolNames && allowedToolNames.size > 0 && !allowedToolNames.has(normalizedName)) return null;
\tconst args = parseDispatchToolCallArguments(entry.arguments ?? entry.args ?? entry.params ?? entry.parameters ?? entry.function?.arguments);
\tif (args === null) return null;
\tconst rawId = typeof entry.id === "string" && entry.id.trim() ? entry.id.trim() : `text_call_${randomUUID().replace(/-/g, "").slice(0, 12)}`;
\treturn {
\t\ttype: "toolCall",
\t\tid: rawId,
\t\tname: normalizedName,
\t\targuments: args
\t};
}
function inferToolCallBlocksFromTextForDispatch(content, allowedToolNames) {
\tconst hasToolCallBlocks = content.some((block) => block && typeof block === "object" && isToolCallBlockType(block.type));
\tif (hasToolCallBlocks) return [];
\tfor (const block of content) {
\t\tif (!block || typeof block !== "object") continue;
\t\tconst text = typeof block.text === "string" ? block.text : "";
\t\tif (!text.trim()) continue;
\t\tconst trimmed = text.trim();
\t\tif (!trimmed.includes("{")) continue;
\t\tconst cleaned = trimmed.replace(/^```(?:json)?\\s*/i, "").replace(/\\s*```$/i, "").trim();
\t\tif (!cleaned) continue;
\t\tconst candidates = [cleaned, ...extractBalancedJsonObjectsForDispatchToolCalls(cleaned)];
\t\tfor (const candidate of candidates) {
\t\t\tlet parsed;
\t\t\ttry {
\t\t\t\tparsed = JSON.parse(candidate);
\t\t\t} catch {
\t\t\t\tcontinue;
\t\t\t}
\t\t\tif (Array.isArray(parsed)) {
\t\t\t\tconst calls = parsed
\t\t\t\t\t.map((entry) => normalizeDispatchToolCallEntry(entry, allowedToolNames))
\t\t\t\t\t.filter((entry) => entry !== null);
\t\t\t\tif (calls.length > 0) return calls;
\t\t\t\tcontinue;
\t\t\t}
\t\t\tif (parsed && typeof parsed === "object" && Array.isArray(parsed.tool_calls)) {
\t\t\t\tconst calls = parsed.tool_calls
\t\t\t\t\t.map((entry) => normalizeDispatchToolCallEntry(entry, allowedToolNames))
\t\t\t\t\t.filter((entry) => entry !== null);
\t\t\t\tif (calls.length > 0) return calls;
\t\t\t}
\t\t\tconst single = normalizeDispatchToolCallEntry(parsed, allowedToolNames);
\t\t\tif (single) return [single];
\t\t}
\t}
\treturn [];
}
"""
DISPATCH_TRIM_INSERT_SNIPPET = """\tconst inferredToolCalls = inferToolCallBlocksFromTextForDispatch(content, allowedToolNames);
\tif (inferredToolCalls.length > 0) {
\t\tfor (const inferredToolCall of inferredToolCalls) content.push(inferredToolCall);
\t\tif (message.stopReason !== "aborted" && message.stopReason !== "error") message.stopReason = "toolUse";
\t}
"""
TRUTHY_VALUES = {"1", "true", "yes", "on"}
OPENCLAW_AUTH_FILE_ENV = "OPENCLAW_TENN_OPENCLAW_AUTH_FILE"
DEFAULT_OPENCLAW_AUTH_FILE = Path.home() / ".openclaw" / "agents" / "main" / "agent" / "auth-profiles.json"
DEFAULT_CONTEXT_TOKENS = 65536


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in TRUTHY_VALUES


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _context_tokens_target() -> int:
    raw = os.environ.get("OPENCLAW_TENN_CONTEXT_TOKENS", "").strip()
    if not raw:
        return DEFAULT_CONTEXT_TOKENS
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_CONTEXT_TOKENS
    return max(8192, value)


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
    for item in profiles.values():
        if not isinstance(item, dict):
            continue
        provider = str(item.get("provider", "")).strip().lower()
        token = item.get("token")
        profile_type = str(item.get("type", "")).strip().lower()
        if provider != "openai":
            continue
        if not isinstance(token, str) or not token.strip():
            continue
        # Allow "manual" for backward compatibility with older files.
        if profile_type in {"", "token", "manual"}:
            return True
    return False


def _backup_file(path: Path) -> Path:
    backup = path.with_name(f"{path.name}.bak.{_timestamp()}")
    shutil.copy2(path, backup)
    return backup


def _load_config(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, str(exc)
    return payload if isinstance(payload, dict) else None, None


def _ensure_dict(parent: dict[str, Any], key: str) -> dict[str, Any]:
    existing = parent.get(key)
    if isinstance(existing, dict):
        return existing
    replacement: dict[str, Any] = {}
    parent[key] = replacement
    return replacement


def _set_value(parent: dict[str, Any], key: str, value: Any, changes: list[str]) -> None:
    if parent.get(key) != value:
        parent[key] = value
        changes.append(key)


def _provider_has_model(config: dict[str, Any], provider: str, model_id: str) -> bool:
    providers = ((config.get("models") or {}).get("providers") or {})
    if not isinstance(providers, dict):
        return False
    provider_payload = providers.get(provider)
    if not isinstance(provider_payload, dict):
        return False
    models = provider_payload.get("models")
    if not isinstance(models, list):
        return False
    for item in models:
        if not isinstance(item, dict):
            continue
        if item.get("id") == model_id or item.get("name") == model_id:
            return True
    return False


def _resolve_local_worker_model(config: dict[str, Any]) -> str:
    if _provider_has_model(config, "llamacpp", "qwen2.5-coder-14b"):
        return "llamacpp/qwen2.5-coder-14b"
    if _provider_has_model(config, "ollama", "qwen2.5-coder:14b"):
        return "ollama/qwen2.5-coder:14b"
    defaults = ((config.get("agents") or {}).get("defaults") or {})
    model = defaults.get("model")
    if isinstance(model, dict) and isinstance(model.get("primary"), str) and model["primary"].strip():
        return str(model["primary"])
    if isinstance(model, str) and model.strip():
        return model
    return "ollama/qwen2.5-coder:14b"


def _upsert_agent(agents_list: list[dict[str, Any]], agent_id: str, desired: dict[str, Any], changes: list[str]) -> None:
    for item in agents_list:
        if isinstance(item, dict) and item.get("id") == agent_id:
            for key, value in desired.items():
                if item.get(key) != value:
                    item[key] = deepcopy(value)
                    changes.append(f"agents.list[{agent_id}].{key}")
            return
    agents_list.append(deepcopy(desired))
    changes.append(f"agents.list[{agent_id}]")


def normalize_config(
    config: dict[str, Any],
    repo_root: Path,
    *,
    openai_auth_profile_present: bool | None = None,
) -> tuple[dict[str, Any], list[str], list[str]]:
    changes: list[str] = []
    warnings: list[str] = []

    agents = _ensure_dict(config, "agents")
    defaults = _ensure_dict(agents, "defaults")
    defaults_model = _ensure_dict(defaults, "model")
    defaults_models = _ensure_dict(defaults, "models")
    defaults_subagents = _ensure_dict(defaults, "subagents")
    tools = _ensure_dict(config, "tools")
    tools_exec = _ensure_dict(tools, "exec")
    tools_sessions = _ensure_dict(tools, "sessions")

    local_worker_model = _resolve_local_worker_model(config)
    explicit_planner_model = os.environ.get("OPENCLAW_TENN_PLANNER_MODEL", "").strip()
    explicit_local_planner_model = os.environ.get("OPENCLAW_TENN_LOCAL_PLANNER_MODEL", "").strip()
    local_planner_model = explicit_local_planner_model or local_worker_model
    openai_api_key_present = bool(os.environ.get("OPENAI_API_KEY"))
    if openai_auth_profile_present is None:
        openai_auth_profile_present = _openclaw_openai_profile_present()
    force_openai_planner = _truthy_env("OPENCLAW_TENN_FORCE_OPENAI_PLANNER")
    if explicit_planner_model:
        main_primary = explicit_planner_model
    elif force_openai_planner:
        main_primary = "openai/gpt-4.1-mini"
        warnings.append("OPENCLAW_TENN_FORCE_OPENAI_PLANNER is set; OpenAI credentials are required.")
    elif explicit_local_planner_model:
        main_primary = explicit_local_planner_model
    elif openai_api_key_present or openai_auth_profile_present:
        main_primary = "openai/gpt-4.1-mini"
    else:
        main_primary = local_planner_model
        warnings.append("OPENAI_API_KEY is not set; defaulting main planner to local model.")
    main_fallbacks: list[str] = []
    if main_primary.startswith("openai/"):
        if local_planner_model and local_planner_model != main_primary:
            main_fallbacks = [local_planner_model]
    context_tokens = _context_tokens_target()

    _set_value(defaults, "workspace", str(repo_root), changes)
    _set_value(defaults, "repoRoot", str(repo_root), changes)
    _set_value(defaults, "skipBootstrap", True, changes)
    _set_value(defaults, "contextTokens", context_tokens, changes)
    _set_value(defaults, "timeoutSeconds", 900, changes)
    _set_value(defaults, "maxConcurrent", 1, changes)
    _set_value(defaults_model, "primary", local_worker_model, changes)
    _set_value(defaults_subagents, "runTimeoutSeconds", 900, changes)
    _set_value(defaults_subagents, "maxConcurrent", 2, changes)
    _set_value(defaults_subagents, "maxSpawnDepth", 1, changes)
    _set_value(defaults_subagents, "maxChildrenPerAgent", 2, changes)

    worker_model_cfg = _ensure_dict(defaults_models, local_worker_model)
    worker_model_params = _ensure_dict(worker_model_cfg, "params")
    _set_value(worker_model_params, "streaming", False, changes)

    _set_value(tools, "profile", "coding", changes)
    if "alsoAllow" in tools:
        tools.pop("alsoAllow", None)
        changes.append("tools.alsoAllow")
    _set_value(tools_exec, "host", "gateway", changes)
    _set_value(tools_exec, "security", "allowlist", changes)
    _set_value(tools_exec, "ask", "on-miss", changes)
    _set_value(tools_sessions, "visibility", "tree", changes)

    agents_list = agents.get("list")
    if not isinstance(agents_list, list):
        agents_list = []
        agents["list"] = agents_list
        changes.append("agents.list")

    main_agent = {
        "id": "main",
        "default": True,
        "workspace": str(repo_root),
        "agentDir": str(Path.home() / ".openclaw" / "agents" / "main" / "agent"),
        "model": {"primary": main_primary, "fallbacks": main_fallbacks},
        "subagents": {"allowAgents": ["coder-local", "review-local"]},
        "tools": {"profile": "coding"},
    }
    coder_agent = {
        "id": "coder-local",
        "workspace": str(repo_root),
        "agentDir": str(Path.home() / ".openclaw" / "agents" / "coder-local" / "agent"),
        "model": local_worker_model,
        "tools": {"profile": "coding"},
    }
    review_agent = {
        "id": "review-local",
        "workspace": str(repo_root),
        "agentDir": str(Path.home() / ".openclaw" / "agents" / "review-local" / "agent"),
        "model": local_worker_model,
        "tools": {"profile": "coding"},
    }
    _upsert_agent(agents_list, "main", main_agent, changes)
    _upsert_agent(agents_list, "coder-local", coder_agent, changes)
    _upsert_agent(agents_list, "review-local", review_agent, changes)
    return config, changes, warnings


def _detect_openclaw_root() -> Path | None:
    binary = shutil.which("openclaw")
    candidates: list[Path] = []
    if binary:
        resolved = Path(binary).resolve()
        candidates.append(resolved.parent.parent / "lib" / "node_modules" / "openclaw")
    home = Path.home() / ".nvm" / "versions" / "node"
    if home.exists():
        candidates.extend(sorted(home.glob("*/lib/node_modules/openclaw"), reverse=True))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def inspect_prompt_patch(openclaw_root: Path | None, apply: bool) -> tuple[dict[str, Any], list[Path]]:
    status: dict[str, Any] = {
        "openclaw_root": str(openclaw_root) if openclaw_root else "",
        "reply_file": "",
        "state": "missing",
    }
    backups: list[Path] = []
    if openclaw_root is None:
        status["state"] = "openclaw_not_found"
        return status, backups
    dist_dir = openclaw_root / "dist"
    reply_file = next(iter(sorted(dist_dir.glob("reply-*.js"))), None)
    if reply_file is None:
        status["state"] = "reply_dist_missing"
        return status, backups
    status["reply_file"] = str(reply_file)
    text = reply_file.read_text(encoding="utf-8", errors="replace")
    if 'function resolvePromptModeForSession(sessionKey) {\n  return "minimal";\n}' in text:
        status["state"] = "already_patched"
        return status, backups
    if not PROMPT_PATCH_RE.search(text):
        status["state"] = "pattern_not_found"
        return status, backups
    status["state"] = "patch_required"
    if apply:
        backups.append(_backup_file(reply_file))
        reply_file.write_text(PROMPT_PATCH_RE.sub(PROMPT_PATCH_REPLACEMENT, text, count=1), encoding="utf-8")
        status["state"] = "patched"
    return status, backups


def inspect_lazy_plugin_patch(openclaw_root: Path | None, apply: bool) -> tuple[dict[str, Any], list[Path]]:
    status: dict[str, Any] = {
        "openclaw_root": str(openclaw_root) if openclaw_root else "",
        "plugin_registry_file": "",
        "run_main_file": "",
        "program_file": "",
        "state": "missing",
    }
    backups: list[Path] = []
    if openclaw_root is None:
        status["state"] = "openclaw_not_found"
        return status, backups

    dist_dir = openclaw_root / "dist"
    plugin_file = next(iter(sorted(dist_dir.glob("plugin-registry-*.js"))), None)
    run_main_file = next(iter(sorted(dist_dir.glob("run-main-*.js"))), None)
    program_file = next(iter(sorted(dist_dir.glob("program-*.js"))), None)
    if plugin_file is None or run_main_file is None or program_file is None:
        status["state"] = "dist_files_missing"
        return status, backups
    status["plugin_registry_file"] = str(plugin_file)
    status["run_main_file"] = str(run_main_file)
    status["program_file"] = str(program_file)

    plugin_text = plugin_file.read_text(encoding="utf-8", errors="replace")
    run_main_text = run_main_file.read_text(encoding="utf-8", errors="replace")
    program_text = program_file.read_text(encoding="utf-8", errors="replace")

    static_match = PLUGIN_STATIC_IMPORT_RE.search(plugin_text)
    import_symbol = static_match.group(1) if static_match else ""
    plugin_module = static_match.group(2) if static_match else ""
    is_already_async = PLUGIN_FUNCTION_ASYNC in plugin_text
    has_static_import = static_match is not None
    run_main_awaited = "await ensurePluginRegistryLoaded();" in run_main_text
    program_awaited = "await ensurePluginRegistryLoaded();" in program_text

    if is_already_async and not has_static_import and run_main_awaited and program_awaited:
        status["state"] = "already_patched"
        return status, backups

    status["state"] = "patch_required"
    if not apply:
        return status, backups

    if plugin_module:
        plugin_text = plugin_text.replace(static_match.group(0) + "\n", "", 1)
    elif "loadOpenClawPlugins" not in plugin_text:
        status["state"] = "pattern_not_found"
        return status, backups

    if PLUGIN_FUNCTION_SYNC in plugin_text:
        plugin_text = plugin_text.replace(PLUGIN_FUNCTION_SYNC, PLUGIN_FUNCTION_ASYNC, 1)
    if plugin_module:
        dynamic_import = PLUGIN_DYNAMIC_IMPORT_TEMPLATE.format(symbol=import_symbol, module=plugin_module)
        if dynamic_import not in plugin_text:
            needle = "const config = loadConfig();\n\tloadOpenClawPlugins({"
            replacement = "const config = loadConfig();\n\t" + dynamic_import + "\n\tloadOpenClawPlugins({"
            if needle not in plugin_text:
                status["state"] = "pattern_not_found"
                return status, backups
            plugin_text = plugin_text.replace(needle, replacement, 1)

    if "ensurePluginRegistryLoaded();" in run_main_text:
        run_main_text = run_main_text.replace("ensurePluginRegistryLoaded();", "await ensurePluginRegistryLoaded();")
    if "ensurePluginRegistryLoaded();" in program_text:
        program_text = program_text.replace("ensurePluginRegistryLoaded();", "await ensurePluginRegistryLoaded();")

    backups.append(_backup_file(plugin_file))
    plugin_file.write_text(plugin_text, encoding="utf-8")
    backups.append(_backup_file(run_main_file))
    run_main_file.write_text(run_main_text, encoding="utf-8")
    backups.append(_backup_file(program_file))
    program_file.write_text(program_text, encoding="utf-8")

    status["state"] = "patched"
    return status, backups


def inspect_text_tool_call_patch(openclaw_root: Path | None, apply: bool) -> tuple[dict[str, Any], list[Path]]:
    status: dict[str, Any] = {
        "openclaw_root": str(openclaw_root) if openclaw_root else "",
        "state": "missing",
        "dispatch_files_total": 0,
        "dispatch_files_checked": 0,
        "dispatch_files_patched": 0,
        "dispatch_files_already_patched": 0,
        "dispatch_files_failed": [],
    }
    backups: list[Path] = []
    if openclaw_root is None:
        status["state"] = "openclaw_not_found"
        return status, backups

    candidate_files: list[Path] = []
    for pattern in (
        openclaw_root / "dist" / "*.js",
        openclaw_root / "dist" / "plugin-sdk" / "*.js",
    ):
        candidate_files.extend(sorted(pattern.parent.glob(pattern.name)))
    patch_targets = [
        path
        for path in candidate_files
        if path.is_file()
        and ".bak." not in path.name
        and path.suffix == ".js"
        and DISPATCH_TRIM_FUNCTION_ANCHOR in path.read_text(encoding="utf-8", errors="replace")
    ]
    status["dispatch_files_total"] = len(patch_targets)
    if not patch_targets:
        status["state"] = "dispatch_dist_missing"
        return status, backups

    patchable = 0
    for dispatch_file in patch_targets:
        text = dispatch_file.read_text(encoding="utf-8", errors="replace")
        if DISPATCH_TEXT_TOOL_CALL_MARKER in text:
            status["dispatch_files_checked"] = int(status["dispatch_files_checked"]) + 1
            status["dispatch_files_already_patched"] = int(status["dispatch_files_already_patched"]) + 1
            continue
        if DISPATCH_TRIM_FUNCTION_ANCHOR not in text or DISPATCH_NORMALIZE_IDS_NEEDLE not in text:
            status["dispatch_files_failed"].append(str(dispatch_file))
            continue
        patchable += 1
        if not apply:
            status["dispatch_files_checked"] = int(status["dispatch_files_checked"]) + 1
            continue

        updated = text.replace(DISPATCH_TRIM_FUNCTION_ANCHOR, DISPATCH_HELPERS_TEMPLATE.strip() + "\n" + DISPATCH_TRIM_FUNCTION_ANCHOR, 1)
        updated = updated.replace(DISPATCH_NORMALIZE_IDS_NEEDLE, DISPATCH_TRIM_INSERT_SNIPPET + DISPATCH_NORMALIZE_IDS_NEEDLE, 1)
        if updated == text:
            status["dispatch_files_failed"].append(str(dispatch_file))
            continue
        backups.append(_backup_file(dispatch_file))
        dispatch_file.write_text(updated, encoding="utf-8")
        status["dispatch_files_checked"] = int(status["dispatch_files_checked"]) + 1
        status["dispatch_files_patched"] = int(status["dispatch_files_patched"]) + 1

    failed_files = status["dispatch_files_failed"]
    if isinstance(failed_files, list) and failed_files:
        if int(status["dispatch_files_patched"]) > 0:
            status["state"] = "partial_patched_with_failures"
        elif int(status["dispatch_files_already_patched"]) > 0:
            status["state"] = "already_patched_with_failures"
        else:
            status["state"] = "pattern_not_found"
        return status, backups

    if apply and int(status["dispatch_files_patched"]) > 0:
        status["state"] = "patched"
        return status, backups
    if patchable > 0:
        status["state"] = "patch_required"
        return status, backups
    status["state"] = "already_patched"
    return status, backups


def _review_worker_write_enabled(config: dict[str, Any]) -> bool:
    agents_list = ((config.get("agents") or {}).get("list") or [])
    if not isinstance(agents_list, list):
        return False
    for item in agents_list:
        if not isinstance(item, dict) or item.get("id") != "review-local":
            continue
        tools = item.get("tools")
        if not isinstance(tools, dict):
            return True
        deny = tools.get("deny")
        if isinstance(deny, list):
            denied = {str(entry).strip().lower() for entry in deny}
            if "write" in denied or "edit" in denied:
                return False
        return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Normalize OpenClaw host config and runtime patches for Tenn.")
    parser.add_argument("--config", default=str(Path.home() / ".openclaw" / "openclaw.json"))
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    config_path = Path(args.config).expanduser().resolve()
    repo_root = Path(args.repo_root).expanduser().resolve()
    auth_file_path = _openclaw_auth_file_path()
    openai_auth_profile_present = _openclaw_openai_profile_present(auth_file_path)
    payload: dict[str, Any] = {
        "config_path": str(config_path),
        "repo_root": str(repo_root),
        "apply": bool(args.apply),
        "openai_api_key_present": bool(os.environ.get("OPENAI_API_KEY")),
        "openai_auth_profile_present": openai_auth_profile_present,
        "openclaw_auth_file": str(auth_file_path),
        "allow_local_planner": _truthy_env("OPENCLAW_TENN_ALLOW_LOCAL_PLANNER"),
        "force_openai_planner": _truthy_env("OPENCLAW_TENN_FORCE_OPENAI_PLANNER"),
        "planner_mode": "unknown",
        "planner_model_target": "",
        "review_worker_write_enabled": False,
        "config_state": "missing",
        "config_backups": [],
        "config_changes": [],
        "warnings": [],
        "prompt_patch": {},
        "prompt_patch_backups": [],
        "lazy_plugin_patch": {},
        "lazy_plugin_patch_backups": [],
        "text_tool_call_patch": {},
        "text_tool_call_patch_backups": [],
    }

    if not config_path.exists():
        payload["warnings"].append("OpenClaw config file was not found.")
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1

    config, error_text = _load_config(config_path)
    if error_text or config is None:
        payload["warnings"].append(f"Could not parse config: {error_text}")
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1

    normalized, changes, warnings = normalize_config(
        config,
        repo_root,
        openai_auth_profile_present=openai_auth_profile_present,
    )
    payload["warnings"].extend(warnings)
    payload["config_changes"] = changes
    payload["config_state"] = "already_normalized" if not changes else "changes_required"
    if args.apply and changes:
        backup = _backup_file(config_path)
        payload["config_backups"].append(str(backup))
        config_path.write_text(json.dumps(normalized, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        payload["config_state"] = "patched"
    effective = normalized
    main_planner = ""
    agents_list = ((effective.get("agents") or {}).get("list") or [])
    if isinstance(agents_list, list):
        for item in agents_list:
            if not isinstance(item, dict) or item.get("id") != "main":
                continue
            model_payload = item.get("model")
            if isinstance(model_payload, dict):
                candidate = model_payload.get("primary")
                if isinstance(candidate, str):
                    main_planner = candidate.strip()
            elif isinstance(model_payload, str):
                main_planner = model_payload.strip()
            break
    payload["planner_model_target"] = main_planner
    payload["planner_mode"] = "openai" if main_planner.startswith("openai/") else "local_override"
    payload["review_worker_write_enabled"] = _review_worker_write_enabled(effective)

    openclaw_root = _detect_openclaw_root()
    prompt_status, prompt_backups = inspect_prompt_patch(openclaw_root, apply=args.apply)
    payload["prompt_patch"] = prompt_status
    payload["prompt_patch_backups"] = [str(path) for path in prompt_backups]
    lazy_status, lazy_backups = inspect_lazy_plugin_patch(openclaw_root, apply=args.apply)
    payload["lazy_plugin_patch"] = lazy_status
    payload["lazy_plugin_patch_backups"] = [str(path) for path in lazy_backups]
    text_tool_call_status, text_tool_call_backups = inspect_text_tool_call_patch(openclaw_root, apply=args.apply)
    payload["text_tool_call_patch"] = text_tool_call_status
    payload["text_tool_call_patch_backups"] = [str(path) for path in text_tool_call_backups]

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
