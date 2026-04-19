from __future__ import annotations

import json
import os
import threading
import time
from typing import Callable

import httpx

# httpx.Client is not thread-safe. Cockpit calls health() via asyncio.to_thread while
# chat() runs on the Textual thread — one pooled client per OS thread.
_DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=600.0, write=120.0, pool=5.0)
_DEFAULT_LIMITS = httpx.Limits(max_connections=6, max_keepalive_connections=3)


class LlamaCppClient:
    """Chat client for llama.cpp servers using the OpenAI-compatible API (/v1/...)."""

    def __init__(self, base_url: str, model: str, api_key: str = "") -> None:
        self.base_url = self._normalize_base_url(base_url)
        self.model = model
        self._api_key = api_key.strip()
        self._thread_local = threading.local()

    def _http_client(self) -> httpx.Client:
        c = getattr(self._thread_local, "http_client", None)
        if c is None:
            c = httpx.Client(timeout=_DEFAULT_TIMEOUT, limits=_DEFAULT_LIMITS)
            self._thread_local.http_client = c
        return c

    def switch_model(self, new_model: str) -> None:
        """Update the active model name for subsequent requests."""
        resolved = self._resolve_model_id(new_model)
        if resolved != new_model:
            self._log_model_resolution(new_model, resolved)
        self.model = resolved

    @staticmethod
    def _extract_model_path(status_obj: dict | None) -> str:
        if not isinstance(status_obj, dict):
            return ""
        args_list = status_obj.get("args") or []
        for i, arg in enumerate(args_list):
            if arg == "--model" and i + 1 < len(args_list):
                return str(args_list[i + 1] or "").strip()

        preset_text = str(status_obj.get("preset") or "")
        for line in preset_text.splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip().lower() == "model":
                return value.strip()
        return ""

    def _fetch_model_registry(self, timeout: float = 5.0) -> dict[str, dict[str, str]]:
        url = f"{self.base_url}/v1/models"
        headers = self._build_headers()
        req_timeout = httpx.Timeout(
            connect=min(5.0, timeout),
            read=timeout,
            write=timeout,
            pool=2.0,
        )
        response = self._http_client().get(url, headers=headers, timeout=req_timeout)
        response.raise_for_status()
        payload = response.json() if response.content else {}
        result: dict[str, dict[str, str]] = {}
        for entry in payload.get("data", []):
            model_id = str(entry.get("id", "") or "").strip()
            if not model_id:
                continue
            status_obj = entry.get("status") or {}
            model_path = self._extract_model_path(status_obj)
            result[model_id] = {
                "status": str(status_obj.get("value", "unknown") or "unknown").strip(),
                "model_path": model_path,
                "path_stem": model_path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
                if model_path
                else "",
            }
        return result

    @staticmethod
    def _is_usable_registry_entry(info: dict[str, str]) -> bool:
        return bool(info.get("model_path")) or info.get("status") == "loaded"

    @staticmethod
    def _model_alias_tokens(model_id: str, info: dict[str, str]) -> set[str]:
        tokens = {str(model_id or "").strip().lower()}
        path_stem = str(info.get("path_stem") or "").strip().lower()
        if path_stem:
            tokens.add(path_stem)
        if model_id.startswith("model:"):
            tokens.add(model_id.split(":", 1)[1].strip().lower())
        return {token for token in tokens if token}

    @classmethod
    def _matches_requested_model(
        cls,
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
        for token in cls._model_alias_tokens(model_id, info):
            if any(not req or not token for req in requested_tokens):
                continue
            if any(req == token for req in requested_tokens):
                return True
            if any(
                req.startswith(token) or token.startswith(req)
                for req in requested_tokens
            ):
                return True
        return False

    def _resolve_model_id(self, requested_model: str) -> str:
        requested = str(requested_model or "").strip()
        if not requested:
            return requested
        try:
            registry = self._fetch_model_registry()
        except Exception:
            return requested
        if not registry:
            return requested

        info = registry.get(requested)
        if info and self._is_usable_registry_entry(info):
            return requested

        for model_id, model_info in registry.items():
            if self._is_usable_registry_entry(
                model_info
            ) and self._matches_requested_model(
                requested,
                model_id,
                model_info,
            ):
                return model_id

        for model_id, model_info in registry.items():
            if model_info.get("status") == "loaded":
                return model_id

        return requested

    @staticmethod
    def _log_model_resolution(requested: str, resolved: str) -> None:
        try:
            import logging

            logging.getLogger(__name__).warning(
                "Resolved stale llama.cpp model id %s -> %s",
                requested,
                resolved,
            )
        except Exception:
            pass

    def health(self, timeout: float = 5.0) -> dict:
        url = f"{self.base_url}/v1/models"
        headers = self._build_headers()
        t = httpx.Timeout(
            connect=min(5.0, timeout), read=timeout, write=timeout, pool=2.0
        )
        try:
            response = self._http_client().get(url, headers=headers, timeout=t)
            response.raise_for_status()
            payload = response.json() if response.content else {}
            names = [
                str(m.get("id", "")).strip()
                for m in payload.get("data", [])
                if m.get("id")
            ]
            return {"ok": True, "url": self.base_url, "models": names}
        except Exception as exc:
            return {"ok": False, "url": self.base_url, "error": str(exc)}

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}

        api_key = self._api_key
        if not api_key:
            for env_name in ("LLAMACPP_API_KEY", "LLM_API_KEY"):
                api_key = str(os.getenv(env_name) or "").strip()
                if api_key:
                    break
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        raw_header = str(os.getenv("LLM_AUTH_HEADER") or "").strip()
        if raw_header:
            name, sep, value = raw_header.partition(":")
            if not sep or not name.strip() or not value.strip():
                raise RuntimeError(
                    "LLM_AUTH_HEADER must be formatted as 'Header-Name: value'"
                )
            headers[name.strip()] = value.strip()

        return headers

    @staticmethod
    def _extract_choice_content(choice: dict | None) -> str:
        if not isinstance(choice, dict):
            return ""
        delta = choice.get("delta")
        if isinstance(delta, dict):
            content = delta.get("content")
            if isinstance(content, str) and content:
                return content
        message = choice.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str) and content:
                return content
            if isinstance(content, list):
                parts = [
                    str(item.get("text") or "")
                    for item in content
                    if isinstance(item, dict) and item.get("type") == "text"
                ]
                joined = "".join(parts).strip()
                if joined:
                    return joined
        content = choice.get("text")
        if isinstance(content, str) and content:
            return content
        return ""

    @staticmethod
    def _error_body_preview(response: httpx.Response | None, limit: int = 300) -> str:
        if response is None:
            return ""
        try:
            body = response.read().decode("utf-8", errors="replace")
        except Exception:
            try:
                body = response.text
            except Exception:
                body = ""
        return body[:limit]

    def chat(
        self,
        prompt: str,
        timeout: float = 120.0,
        on_chunk: Callable[[str], None] | None = None,
        prior_messages: list[dict] | None = None,
    ) -> str:
        url = f"{self.base_url}/v1/chat/completions"
        parts: list[str] = []
        headers = self._build_headers()
        resolved_model = self._resolve_model_id(self.model)
        if resolved_model != self.model:
            self._log_model_resolution(self.model, resolved_model)
            self.model = resolved_model

        if prior_messages:
            messages = prior_messages + [{"role": "user", "content": prompt}]
        else:
            messages = [{"role": "user", "content": prompt}]

        stream_timeout = httpx.Timeout(
            connect=5.0, read=timeout, write=min(120.0, timeout), pool=5.0
        )
        deadline = time.monotonic() + timeout
        try:
            with self._http_client().stream(
                "POST",
                url,
                headers=headers,
                timeout=stream_timeout,
                json={
                    "model": resolved_model,
                    "messages": messages,
                    "stream": True,
                    "chat_template_kwargs": {"enable_thinking": False},
                },
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if time.monotonic() > deadline:
                        raise TimeoutError(
                            f"llama.cpp wall-clock timeout ({timeout:.0f}s) exceeded at {url}; "
                            f"received {len(parts)} token chunks. The model is streaming too slowly "
                            "for this deadline — consider switching to the API backend or a smaller model."
                        )
                    if not line:
                        continue
                    if isinstance(line, bytes):
                        line = line.decode("utf-8", errors="ignore")
                    if line == "data: [DONE]":
                        break
                    if line.startswith("data: "):
                        line = line[6:]
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    choices = payload.get("choices") or []
                    chunk = self._extract_choice_content(
                        choices[0] if choices else None
                    )
                    if chunk:
                        parts.append(chunk)
                        if on_chunk is not None:
                            on_chunk(chunk)
        except httpx.HTTPStatusError as exc:
            body = self._error_body_preview(exc.response)
            hint = ""
            if exc.response is not None and exc.response.status_code == 401:
                hint = (
                    " Verify LLM_API_KEY / LLM_AUTH_HEADER for the llama.cpp endpoint."
                )
            raise RuntimeError(
                f"llama.cpp request failed ({exc.response.status_code}) at {url}: {body}{hint}"
            ) from exc
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise RuntimeError(
                f"llama.cpp request error at {url}: {exc}. "
                "Verify llama-server is running (curl http://localhost:8001/v1/models)."
            ) from exc

        if not parts:
            fallback = self._retry_non_stream_completion(
                url=url,
                headers=headers,
                timeout=stream_timeout,
                model=resolved_model,
                messages=messages,
            )
            if fallback:
                if on_chunk is not None:
                    on_chunk(fallback)
                return fallback
            raise RuntimeError(f"llama.cpp returned no content from {url}")
        return "".join(parts)

    def _retry_non_stream_completion(
        self,
        *,
        url: str,
        headers: dict[str, str],
        timeout: httpx.Timeout,
        model: str,
        messages: list[dict[str, str]],
    ) -> str:
        response: httpx.Response | None = None
        try:
            response = self._http_client().post(
                url,
                headers=headers,
                timeout=timeout,
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "chat_template_kwargs": {"enable_thinking": False},
                },
            )
            response.raise_for_status()
            payload = response.json() if response.content else {}
            choices = payload.get("choices") or []
            return self._extract_choice_content(choices[0] if choices else None)
        except httpx.HTTPStatusError as exc:
            body = self._error_body_preview(exc.response)
            raise RuntimeError(
                f"llama.cpp request failed ({exc.response.status_code}) at {url}: {body}"
            ) from exc
        except (httpx.ConnectError, httpx.TimeoutException):
            return ""
        except Exception:
            return ""

    @staticmethod
    def _normalize_base_url(raw: str) -> str:
        value = (raw or "").strip()
        if not value:
            value = "http://localhost:8001"
        if "://" not in value:
            value = f"http://{value}"
        value = value.rstrip("/")
        # Strip trailing /v1 if present — we append it ourselves per-call.
        if value.lower().endswith("/v1"):
            value = value[:-3]
        return value
