from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

import httpx

from app.core.config import settings

DEFAULT_LLM_URL = "http://127.0.0.1:8001"
DEFAULT_LLM_MODEL = "qwen2.5-coder-14b"


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
        os.getenv("EXTRACT_MODEL"),
        os.getenv("LLM_MODEL"),
        os.getenv("LLAMACPP_MODEL"),
        getattr(settings, "extract_model", ""),
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


def resolve_embedding_runtime_config(
    *,
    base_url: str | None = None,
    model: str | None = None,
) -> tuple[str, str]:
    resolved_base_url = ""
    for candidate in (
        base_url,
        os.getenv("EMBEDDING_URL"),
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
        os.getenv("EMBEDDING_MODEL"),
        os.getenv("EMBED_MODEL"),
        os.getenv("LLM_MODEL"),
        os.getenv("LLAMACPP_MODEL"),
        getattr(settings, "embed_model", ""),
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


def _build_runtime_headers(
    *,
    api_key_env_names: tuple[str, ...],
    legacy_api_key_env_names: tuple[str, ...] = ("OLLAMA_API_KEY", "OPENAI_API_KEY"),
) -> dict[str, str]:
    headers: dict[str, str] = {}

    for env_name in api_key_env_names:
        api_key = str(os.getenv(env_name) or "").strip()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            break

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
            raise RuntimeError("LLM_AUTH_HEADER must be formatted as 'Header-Name: value'")
        headers[name.strip()] = value.strip()

    return headers


def build_llm_headers() -> dict[str, str]:
    return _build_runtime_headers(api_key_env_names=("LLM_API_KEY",))


def build_embedding_headers() -> dict[str, str]:
    headers = _build_runtime_headers(
        api_key_env_names=("LLM_API_KEY",),
        legacy_api_key_env_names=("EMBEDDING_API_KEY", "OLLAMA_API_KEY", "OPENAI_API_KEY"),
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
    stripped = _re.sub(r'//[^\n]*', '', stripped)
    # Also try with thousands separators removed (e.g. 1,969,907 → 1969907).
    # The regex strips commas that sit between digits without touching JSON's
    # structural commas (which are always followed by whitespace or a quote).
    cleaned = _re.sub(r'(?<=\d),(?=\d)', '', stripped)
    # Also try with accounting parentheses converted to negatives: (5,590) → -5,590.
    # Then apply thousands-separator removal to get valid JSON numbers.
    acc = _re.sub(r'\((\d[\d,.]*)\)', lambda m: '-' + m.group(1), stripped)
    acc_cleaned = _re.sub(r'(?<=\d),(?=\d)', '', acc)
    candidates = [raw, stripped, _extract_first_json_value(stripped), cleaned, _extract_first_json_value(cleaned), acc, acc_cleaned, _extract_first_json_value(acc_cleaned)]
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


def _resolve_model_id(models_payload: dict[str, Any], requested_model: str) -> str:
    data = models_payload.get("data")
    available_models: list[str] = []
    if isinstance(data, list):
        for row in data:
            if not isinstance(row, dict):
                continue
            model_id = str(row.get("id") or "").strip()
            if model_id:
                available_models.append(model_id)
    if not available_models:
        raise RuntimeError("llama.cpp /v1/models returned no model ids")

    requested = str(requested_model or "").strip()
    if requested and requested in available_models:
        return requested
    return available_models[0]


def generate_json_llamacpp(
    base_url: str,
    model: str,
    prompt: str,
    timeout: float = 30.0,
    client: Optional[httpx.Client] = None,
    include_metadata: bool = False,
) -> Any:
    normalized_base_url, requested_model = resolve_llm_runtime_config(
        base_url=base_url,
        model=model,
    )
    headers = build_llm_headers()
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
            raise RuntimeError(
                f"llama.cpp server unavailable at {normalized_base_url}/v1/models: {exc}"
            ) from exc

        chat_url = f"{normalized_base_url}/v1/chat/completions"
        payload = {
            "model": resolved_model,
            "messages": [
                {"role": "system", "content": "Extract structured JSON only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "max_tokens": 2048,
            "response_format": {"type": "json_object"},
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
        except Exception as exc:
            raise RuntimeError(f"llama.cpp JSON generation failed at {chat_url}: {exc}") from exc
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
