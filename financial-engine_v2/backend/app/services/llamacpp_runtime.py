from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

from app.core.config import settings

DEFAULT_LLM_URL = "http://127.0.0.1:8001"
# Align with scripts/run_llama_server.sh default alias (native stack). Opt-in models
# such as gpt-oss are not defaults — select them explicitly in Cockpit / env.
DEFAULT_LLM_MODEL = "model:qwen3-30b-a3b-instruct"
MANUAL_FALLBACK_LLM_ID_MARKERS: tuple[str, ...] = ("gpt-oss",)


def is_manual_fallback_llm_model(model_id: str) -> bool:
    """True for models kept for rare/manual use (e.g. gpt-oss), not the native default path."""
    norm = str(model_id or "").strip().lower()
    return any(marker in norm for marker in MANUAL_FALLBACK_LLM_ID_MARKERS)


DEFAULT_LOCAL_LLAMACPP_API_KEY = "local-openai-key"


class LlamaCppServerUnavailable(RuntimeError):
    """Raised when llama.cpp server is unreachable (connection refused, timeout on connect)."""

    pass


def _normalize_url(base_url: str) -> str:
    normalized = str(base_url or "").strip().rstrip("/")
    if normalized.endswith("/v1"):
        normalized = normalized[: -len("/v1")]
    return normalized.rstrip("/")


def resolve_llm_runtime_config(
    *,
    base_url: str | None = None,
    model: str | None = None,
) -> tuple[str, str]:
    resolved_base_url = ""
    for candidate in (
        base_url,
        os.getenv("LLM_URL"),
        os.getenv("LLAMACPP_URL"),
        DEFAULT_LLM_URL,
    ):
        normalized = _normalize_url(str(candidate or ""))
        if normalized:
            resolved_base_url = normalized
            break

    resolved_model = ""
    for candidate in (
        model,
        os.getenv("LLM_MODEL"),
        os.getenv("LLAMACPP_MODEL"),
        DEFAULT_LLM_MODEL,
    ):
        text = str(candidate or "").strip()
        if text:
            resolved_model = text
            break

    if not resolved_base_url:
        raise RuntimeError("LLM base URL is required")
    if not resolved_model:
        raise RuntimeError("LLM model is required")
    return resolved_base_url, resolved_model


def resolve_extraction_runtime_config(
    *,
    base_url: str | None = None,
    model: str | None = None,
) -> tuple[str, str]:
    """Resolve LLM config for extraction workloads.

    In router mode (single-instance), extraction uses the same 8001 server
    but requests the extraction model by name. The router loads it on demand.

    URL priority:
      1. Explicit base_url argument
      2. EXTRACTION_LLAMACPP_URL env var / settings (legacy: dedicated 8002)
      3. Falls through to resolve_llm_runtime_config (LLAMACPP_URL / 8001)

    Model priority:
      1. Explicit model argument
      2. EXTRACT_MODEL env var / settings.extract_model
      3. Default extraction model (qwen2.5-14b-instruct)
    """
    extraction_url = (
        _normalize_url(str(base_url or ""))
        or _normalize_url(os.getenv("EXTRACTION_LLAMACPP_URL", ""))
        or _normalize_url(getattr(settings, "extraction_llamacpp_url", ""))
    )
    # Resolve extraction model regardless of whether a dedicated URL is set.
    # In router mode, extraction uses the same 8001 server but requests the
    # extraction model by name.
    resolved_model = ""
    for candidate in (
        model,
        os.getenv("EXTRACT_MODEL"),
        getattr(settings, "extract_model", ""),
        "qwen2.5-14b-instruct",
    ):
        text = str(candidate or "").strip()
        if text:
            resolved_model = text
            break
    if extraction_url:
        return extraction_url, resolved_model
    # No dedicated extraction URL — use general LLM URL with extraction model.
    resolved_base_url, _ = resolve_llm_runtime_config(base_url=base_url)
    return resolved_base_url, resolved_model


def resolve_embedding_runtime_config(
    *,
    base_url: str | None = None,
    model: str | None = None,
) -> tuple[str, str]:
    resolved_base_url = ""
    for candidate in (
        base_url,
        os.getenv("EMBEDDING_URL"),
        os.getenv("OLLAMA_URL"),
        getattr(settings, "ollama_url", ""),
        os.getenv("LLM_URL"),
        os.getenv("LLAMACPP_URL"),
        getattr(settings, "llamacpp_url", ""),
        DEFAULT_LLM_URL,
    ):
        normalized = _normalize_url(str(candidate or ""))
        if normalized:
            resolved_base_url = normalized
            break

    resolved_model = ""
    for candidate in (
        model,
        os.getenv("EMBEDDING_MODEL"),
        os.getenv("EMBED_MODEL"),
        getattr(settings, "embed_model", ""),
        os.getenv("LLM_MODEL"),
        os.getenv("LLAMACPP_MODEL"),
        DEFAULT_LLM_MODEL,
    ):
        text = str(candidate or "").strip()
        if text:
            resolved_model = text
            break

    if not resolved_base_url:
        raise RuntimeError("Embedding base URL is required")
    if not resolved_model:
        raise RuntimeError("Embedding model is required")
    return resolved_base_url, resolved_model


def _is_local_runtime_url(base_url: str | None) -> bool:
    normalized = _normalize_url(str(base_url or ""))
    if not normalized:
        return False
    try:
        hostname = str(urlparse(normalized).hostname or "").strip().lower()
    except Exception:
        return False
    return hostname in {"127.0.0.1", "localhost"}


def _discover_local_llamacpp_api_key() -> str:
    try:
        proc = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return ""

    for line in proc.stdout.splitlines():
        if "llama-server" not in line or "--api-key" not in line:
            continue
        _, _, tail = line.partition("--api-key")
        candidate = tail.strip().split(maxsplit=1)[0]
        if candidate:
            return candidate
    return ""


def _build_runtime_headers(
    *,
    api_key_env_names: tuple[str, ...],
    runtime_base_url: str | None = None,
    legacy_api_key_env_names: tuple[str, ...] = ("OLLAMA_API_KEY", "OPENAI_API_KEY"),
) -> dict[str, str]:
    headers: dict[str, str] = {}
    is_local_runtime = _is_local_runtime_url(runtime_base_url)

    for env_name in api_key_env_names:
        api_key = str(os.getenv(env_name) or "").strip()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            break

    if "Authorization" not in headers and is_local_runtime:
        detected = _discover_local_llamacpp_api_key()
        headers["Authorization"] = (
            f"Bearer {detected or DEFAULT_LOCAL_LLAMACPP_API_KEY}"
        )

    if "Authorization" not in headers:
        for legacy_env_name in legacy_api_key_env_names:
            api_key = str(os.getenv(legacy_env_name) or "").strip()
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
                break

    raw_header = str(os.getenv("LLM_AUTH_HEADER") or "").strip()
    if raw_header:
        name, sep, value = raw_header.partition(":")
        if not sep or not name.strip() or not value.strip():
            raise RuntimeError(
                "LLM_AUTH_HEADER must be formatted as 'Header-Name: value'"
            )
        headers[name.strip()] = value.strip()

    return headers


def build_llm_headers(*, base_url: str | None = None) -> dict[str, str]:
    runtime_base_url = base_url
    if not runtime_base_url:
        try:
            runtime_base_url, _ = resolve_llm_runtime_config()
        except Exception:
            runtime_base_url = None
    return _build_runtime_headers(
        api_key_env_names=("LLM_API_KEY",),
        runtime_base_url=runtime_base_url,
    )


def build_embedding_headers(*, base_url: str | None = None) -> dict[str, str]:
    runtime_base_url = base_url
    if not runtime_base_url:
        try:
            runtime_base_url, _ = resolve_embedding_runtime_config()
        except Exception:
            runtime_base_url = None
    headers = _build_runtime_headers(
        api_key_env_names=("LLM_API_KEY",),
        runtime_base_url=runtime_base_url,
        legacy_api_key_env_names=(
            "EMBEDDING_API_KEY",
            "OLLAMA_API_KEY",
            "OPENAI_API_KEY",
        ),
    )
    headers["Content-Type"] = "application/json"
    return headers


def verify_llm_models(
    base_url: str,
    headers: dict[str, str] | None = None,
    *,
    timeout: float = 30.0,
    client: Optional[httpx.Client] = None,
) -> dict[str, Any]:
    resolved_base_url, _ = resolve_llm_runtime_config(base_url=base_url)
    own_client = client is None

    def _do_verify(http_client: httpx.Client) -> dict[str, Any]:
        response = http_client.get(
            f"{resolved_base_url}/v1/models",
            headers=dict(headers or {}),
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError(f"Bad llama.cpp /v1/models response: {payload}")
        return payload

    if own_client:
        with httpx.Client(timeout=timeout) as http_client:
            return _do_verify(http_client)
    return _do_verify(client)


def _strip_code_fences(text: str) -> str:
    cleaned = str(text or "").strip()
    cleaned = re.sub(r"^\s*```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    return cleaned.strip()


def _extract_first_json_value(text: str) -> str:
    raw = str(text or "")
    object_start = raw.find("{")
    array_start = raw.find("[")
    starts = [pos for pos in (object_start, array_start) if pos >= 0]
    if not starts:
        return raw

    start = min(starts)
    opening = raw[start]
    closing = "}" if opening == "{" else "]"
    depth = 0
    in_string = False
    escaped = False

    for idx in range(start, len(raw)):
        char = raw[idx]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char == opening:
            depth += 1
            continue
        if char == closing:
            depth -= 1
            if depth == 0:
                return raw[start : idx + 1]
    return raw[start:]


def _message_content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(str(item.get("text") or ""))
        return "".join(text_parts)
    return str(content or "")


def _parse_json_text(text: str) -> Any:
    import re as _re

    raw = _message_content_to_text(text).strip()
    if not raw:
        raise ValueError("Empty response from llama.cpp")

    stripped = _strip_code_fences(raw)
    # Strip JS-style line comments (// ...) that code-oriented models emit.
    stripped = _re.sub(r"//[^\n]*", "", stripped)
    # Also try with thousands separators removed (e.g. 1,969,907 → 1969907).
    # The regex strips commas that sit between digits without touching JSON's
    # structural commas (which are always followed by whitespace or a quote).
    cleaned = _re.sub(r"(?<=\d),(?=\d)", "", stripped)
    # Also try with accounting parentheses converted to negatives: (5,590) → -5,590.
    # Then apply thousands-separator removal to get valid JSON numbers.
    acc = _re.sub(r"\((\d[\d,.]*)\)", lambda m: "-" + m.group(1), stripped)
    acc_cleaned = _re.sub(r"(?<=\d),(?=\d)", "", acc)

    # Fix garbled PDF artifacts in LLM output:
    # 1. Strip control chars (0x00-0x1F except \t \n \r) that break JSON strings
    # 2. Fix invalid JSON escape sequences (e.g. \P, \S from garbled font CMap)
    def _sanitize(s: str) -> str:
        s = _re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)
        return _re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", s)

    sanitized = _sanitize(acc_cleaned)
    candidates = [
        raw,
        stripped,
        _extract_first_json_value(stripped),
        cleaned,
        _extract_first_json_value(cleaned),
        acc,
        acc_cleaned,
        _extract_first_json_value(acc_cleaned),
        sanitized,
        _extract_first_json_value(sanitized),
    ]
    seen = set()
    for candidate in candidates:
        value = str(candidate or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            continue
    raise ValueError(f"No valid JSON found in llama.cpp response: {raw[:400]}")


def _extract_model_path(status_obj: dict[str, Any] | None) -> str:
    if not isinstance(status_obj, dict):
        return ""
    args_list = status_obj.get("args") or []
    for index, arg in enumerate(args_list):
        if arg == "--model" and index + 1 < len(args_list):
            return str(args_list[index + 1] or "").strip()

    preset_text = str(status_obj.get("preset") or "")
    for line in preset_text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip().lower() == "model":
            return value.strip()
    return ""


def _is_usable_registry_entry(info: dict[str, str]) -> bool:
    return bool(info.get("model_path")) or info.get("status") == "loaded"


def _model_alias_tokens(model_id: str, info: dict[str, str]) -> set[str]:
    tokens = {str(model_id or "").strip().lower()}
    path_stem = str(info.get("path_stem") or "").strip().lower()
    if path_stem:
        tokens.add(path_stem)
    if model_id.startswith("model:"):
        tokens.add(model_id.split(":", 1)[1].strip().lower())
    return {token for token in tokens if token}


def _matches_requested_model(
    requested: str,
    model_id: str,
    info: dict[str, str],
) -> bool:
    requested_norm = str(requested or "").strip().lower()
    if not requested_norm:
        return False

    requested_tokens = {requested_norm}
    if requested_norm.startswith("model:"):
        requested_tokens.add(requested_norm.split(":", 1)[1].strip())

    for token in _model_alias_tokens(model_id, info):
        if any(req == token for req in requested_tokens):
            return True
        if any(
            req.startswith(token) or token.startswith(req) for req in requested_tokens
        ):
            return True
    return False


def _resolve_model_id(models_payload: dict[str, Any], requested_model: str) -> str:
    data = models_payload.get("data")
    registry: dict[str, dict[str, str]] = {}
    if isinstance(data, list):
        for row in data:
            if not isinstance(row, dict):
                continue
            model_id = str(row.get("id") or "").strip()
            if not model_id:
                continue
            status_obj = row.get("status") or {}
            model_path = _extract_model_path(status_obj)
            registry[model_id] = {
                "status": str(status_obj.get("value", "unknown") or "unknown").strip(),
                "model_path": model_path,
                "path_stem": Path(model_path).stem if model_path else "",
            }
    if not registry:
        raise RuntimeError("llama.cpp /v1/models returned no model ids")

    requested = str(requested_model or "").strip()
    exact = registry.get(requested)
    if exact and _is_usable_registry_entry(exact):
        return requested

    for model_id, model_info in registry.items():
        if _is_usable_registry_entry(model_info) and _matches_requested_model(
            requested,
            model_id,
            model_info,
        ):
            return model_id

    return requested


def generate_json_llamacpp(
    base_url: str,
    model: str,
    prompt: str,
    timeout: float = 60.0,
    client: Optional[httpx.Client] = None,
    include_metadata: bool = False,
) -> Any:
    normalized_base_url, requested_model = resolve_llm_runtime_config(
        base_url=base_url,
        model=model,
    )
    headers = build_llm_headers(base_url=normalized_base_url)
    own_client = client is None

    def _do_generate(http_client: httpx.Client) -> Any:
        try:
            models_payload = verify_llm_models(
                normalized_base_url,
                headers=headers,
                timeout=timeout,
                client=http_client,
            )
            resolved_model = _resolve_model_id(models_payload, requested_model)
        except Exception as exc:
            raise LlamaCppServerUnavailable(
                f"llama.cpp server unavailable at {normalized_base_url}/v1/models: {exc}"
            ) from exc

        chat_url = f"{normalized_base_url}/v1/chat/completions"
        # Extract the opening role sentence from the user prompt (e.g.
        # "You are a financial metric extractor.") and use it as the system
        # message, so the model's persona is set correctly.  Remove the
        # duplicate sentence from the user turn to avoid wasting tokens.
        system_msg = "Output ONLY valid JSON."
        user_content = prompt
        _first_period = prompt.find(".")
        if _first_period > 0 and prompt[:_first_period].startswith("You are"):
            system_msg = prompt[: _first_period + 1].strip()
            user_content = prompt[_first_period + 1 :].strip()
        payload = {
            "model": resolved_model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0,
            "max_tokens": 2048,
            "response_format": {"type": "json_object"},
            "chat_template_kwargs": {"enable_thinking": False},
        }
        try:
            response = http_client.post(
                chat_url,
                json=payload,
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.ConnectError as exc:
            raise LlamaCppServerUnavailable(
                f"llama.cpp server unreachable at {chat_url}: {exc}"
            ) from exc
        except Exception as exc:
            raise RuntimeError(
                f"llama.cpp JSON generation failed at {chat_url}: {exc}"
            ) from exc
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError(f"Bad llama.cpp response: {data}")
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise RuntimeError(f"Bad llama.cpp choice payload: {data}")
        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise RuntimeError(f"Bad llama.cpp message payload: {data}")
        parsed = _parse_json_text(message.get("content", ""))
        if not include_metadata:
            return parsed

        usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        completion_tokens = usage.get("completion_tokens")
        return {
            "payload": parsed,
            "metrics": {
                "model_name": resolved_model,
                "prompt_tokens": int(usage.get("prompt_tokens") or 0),
                "completion_tokens": int(completion_tokens or 0),
                "total_tokens": int(usage.get("total_tokens") or 0),
                "tokens_generated": int(completion_tokens or 0),
            },
        }

    if own_client:
        with httpx.Client(timeout=timeout) as http_client:
            return _do_generate(http_client)
    return _do_generate(client)
