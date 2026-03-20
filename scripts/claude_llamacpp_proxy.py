#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Iterable
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest
import uuid


DEFAULT_BIND_HOST = "127.0.0.1"
DEFAULT_BIND_PORT = 8745
DEFAULT_UPSTREAM_BASE_URL = "http://127.0.0.1:8001/v1"
DEFAULT_UPSTREAM_API_KEY = "local-openai-key"
DEFAULT_UPSTREAM_MODEL = "qwen2.5-coder-14b"
DEFAULT_TIMEOUT_SECONDS = 120.0
TEXT_BLOCK_TYPE = "text"
TOOL_USE_BLOCK_TYPE = "tool_use"
TOOL_RESULT_BLOCK_TYPE = "tool_result"


@dataclass(frozen=True)
class ProxyConfig:
    bind_host: str
    bind_port: int
    upstream_base_url: str
    upstream_api_key: str
    upstream_model: str
    timeout_seconds: float


@dataclass
class ToolUseStreamState:
    index: int
    tool_id: str
    name: str
    input_parts: list[str]
    started: bool = False
    stopped: bool = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Anthropic Messages API shim for Claude Code -> llama.cpp.")
    parser.add_argument("--host", default=os.environ.get("CLAUDE_LLAMA_PROXY_HOST", DEFAULT_BIND_HOST))
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("CLAUDE_LLAMA_PROXY_PORT", str(DEFAULT_BIND_PORT))),
    )
    parser.add_argument(
        "--upstream-base-url",
        default=os.environ.get("CLAUDE_LLAMA_UPSTREAM_BASE_URL", DEFAULT_UPSTREAM_BASE_URL),
    )
    parser.add_argument(
        "--upstream-api-key",
        default=os.environ.get("CLAUDE_LLAMA_UPSTREAM_API_KEY", DEFAULT_UPSTREAM_API_KEY),
    )
    parser.add_argument(
        "--upstream-model",
        default=os.environ.get("CLAUDE_LLAMA_UPSTREAM_MODEL", DEFAULT_UPSTREAM_MODEL),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=float(os.environ.get("CLAUDE_LLAMA_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))),
    )
    return parser.parse_args()


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))


def _json_loads(raw: str) -> Any:
    return json.loads(raw)


def _count_tokens_approx(text: str) -> int:
    compact = " ".join(str(text or "").split())
    if not compact:
        return 0
    return max(1, len(compact) // 4)


def _flatten_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        chunks: list[str] = []
        for item in value:
            if isinstance(item, dict):
                item_type = str(item.get("type") or "").strip().lower()
                if item_type == TEXT_BLOCK_TYPE:
                    chunks.append(str(item.get("text") or ""))
                elif item_type == TOOL_RESULT_BLOCK_TYPE:
                    chunks.append(_flatten_text(item.get("content")))
                else:
                    text = item.get("text")
                    if isinstance(text, str):
                        chunks.append(text)
            elif item is not None:
                chunks.append(str(item))
        return "\n".join(chunk for chunk in chunks if chunk)
    if isinstance(value, dict):
        return _json_dumps(value)
    return str(value)


def _flatten_system_text(system_value: Any) -> str:
    if isinstance(system_value, str):
        return system_value
    if isinstance(system_value, list):
        return "\n".join(
            str(item.get("text") or "")
            for item in system_value
            if isinstance(item, dict) and str(item.get("type") or "").strip().lower() == TEXT_BLOCK_TYPE
        )
    return ""


def _parse_json_object(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()
    if not text:
        return {}
    try:
        parsed = _json_loads(text)
    except Exception:
        return {"_raw_arguments": text}
    if isinstance(parsed, dict):
        return parsed
    return {"_value": parsed}


def _normalize_anthropic_messages(messages: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "").strip().lower()
        content = message.get("content")
        if isinstance(content, str):
            if content.strip():
                out.append({"role": role or "user", "content": content})
            continue
        if not isinstance(content, list):
            continue
        if role == "assistant":
            assistant_content_parts: list[str] = []
            tool_calls: list[dict[str, Any]] = []
            for block in content:
                if not isinstance(block, dict):
                    continue
                block_type = str(block.get("type") or "").strip().lower()
                if block_type == TEXT_BLOCK_TYPE:
                    text = str(block.get("text") or "")
                    if text:
                        assistant_content_parts.append(text)
                    continue
                if block_type == TOOL_USE_BLOCK_TYPE:
                    tool_name = str(block.get("name") or "").strip()
                    if not tool_name:
                        continue
                    tool_calls.append(
                        {
                            "id": str(block.get("id") or f"toolu_{uuid.uuid4().hex[:24]}"),
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": _json_dumps(block.get("input") or {}),
                            },
                        }
                    )
            if assistant_content_parts or tool_calls:
                out.append(
                    {
                        "role": "assistant",
                        "content": "\n".join(part for part in assistant_content_parts if part),
                        **({"tool_calls": tool_calls} if tool_calls else {}),
                    }
                )
            continue
        user_text_parts: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            block_type = str(block.get("type") or "").strip().lower()
            if block_type == TEXT_BLOCK_TYPE:
                text = str(block.get("text") or "")
                if text:
                    user_text_parts.append(text)
                continue
            if block_type == TOOL_RESULT_BLOCK_TYPE:
                if user_text_parts:
                    out.append({"role": "user", "content": "\n".join(user_text_parts)})
                    user_text_parts = []
                out.append(
                    {
                        "role": "tool",
                        "tool_call_id": str(block.get("tool_use_id") or ""),
                        "content": _flatten_text(block.get("content")),
                    }
                )
        if user_text_parts:
            out.append({"role": role or "user", "content": "\n".join(user_text_parts)})
    return out


def _normalize_tools(tools: Any) -> list[dict[str, Any]]:
    if not isinstance(tools, list):
        return []
    out: list[dict[str, Any]] = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        name = str(tool.get("name") or "").strip()
        if not name:
            continue
        out.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": str(tool.get("description") or ""),
                    "parameters": tool.get("input_schema") if isinstance(tool.get("input_schema"), dict) else {},
                },
            }
        )
    return out


def _normalize_tool_choice(tool_choice: Any) -> Any:
    if isinstance(tool_choice, str):
        normalized = tool_choice.strip().lower()
        if normalized in {"none", "auto", "required"}:
            return normalized
        if normalized == "any":
            return "required"
        return "auto"
    if not isinstance(tool_choice, dict):
        return "auto"
    choice_type = str(tool_choice.get("type") or "").strip().lower()
    if choice_type in {"auto", "none"}:
        return choice_type
    if choice_type == "any":
        return "required"
    if choice_type == "tool":
        name = str(tool_choice.get("name") or "").strip()
        if name:
            return {"type": "function", "function": {"name": name}}
    return "auto"


def build_openai_payload(request_body: dict[str, Any], config: ProxyConfig) -> dict[str, Any]:
    messages_raw = request_body.get("messages")
    messages = messages_raw if isinstance(messages_raw, list) else []
    payload_messages = _normalize_anthropic_messages(messages)
    system_text = _flatten_system_text(request_body.get("system"))
    if system_text:
        payload_messages.insert(0, {"role": "system", "content": system_text})

    openai_payload: dict[str, Any] = {
        "model": config.upstream_model,
        "messages": payload_messages,
        "max_tokens": int(request_body.get("max_tokens") or 4096),
        "stream": bool(request_body.get("stream")),
    }
    if "temperature" in request_body:
        openai_payload["temperature"] = request_body["temperature"]
    tools = _normalize_tools(request_body.get("tools"))
    if tools:
        openai_payload["tools"] = tools
        openai_payload["tool_choice"] = _normalize_tool_choice(request_body.get("tool_choice"))
    return openai_payload


def _usage_from_request_response(request_body: dict[str, Any], openai_response: dict[str, Any]) -> dict[str, int]:
    usage = openai_response.get("usage")
    if isinstance(usage, dict):
        input_tokens = int(usage.get("prompt_tokens") or 0)
        output_tokens = int(usage.get("completion_tokens") or 0)
        if input_tokens or output_tokens:
            return {"input_tokens": input_tokens, "output_tokens": output_tokens}
    request_text = _flatten_system_text(request_body.get("system")) + "\n" + _flatten_text(request_body.get("messages"))
    choice = ((openai_response.get("choices") or [{}])[0] or {})
    message = choice.get("message") if isinstance(choice, dict) else {}
    output_text = ""
    if isinstance(message, dict):
        output_text = _flatten_text(message.get("content"))
        tool_calls = message.get("tool_calls")
        if isinstance(tool_calls, list):
            output_text += "\n" + _flatten_text(tool_calls)
    return {
        "input_tokens": _count_tokens_approx(request_text),
        "output_tokens": _count_tokens_approx(output_text),
    }


def build_anthropic_message_response(
    request_body: dict[str, Any],
    openai_response: dict[str, Any],
    *,
    fallback_model: str,
) -> dict[str, Any]:
    choices = openai_response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("Upstream response did not include choices.")
    choice = choices[0]
    if not isinstance(choice, dict):
        raise ValueError("Upstream choice payload is invalid.")
    message = choice.get("message")
    if not isinstance(message, dict):
        raise ValueError("Upstream response did not include a message payload.")

    content_blocks: list[dict[str, Any]] = []
    content_text = _flatten_text(message.get("content"))
    if content_text:
        content_blocks.append({"type": TEXT_BLOCK_TYPE, "text": content_text})

    tool_calls = message.get("tool_calls")
    if isinstance(tool_calls, list):
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue
            function_payload = tool_call.get("function")
            if not isinstance(function_payload, dict):
                continue
            name = str(function_payload.get("name") or "").strip()
            if not name:
                continue
            content_blocks.append(
                {
                    "type": TOOL_USE_BLOCK_TYPE,
                    "id": str(tool_call.get("id") or f"toolu_{uuid.uuid4().hex[:24]}"),
                    "name": name,
                    "input": _parse_json_object(str(function_payload.get("arguments") or "")),
                }
            )

    stop_reason = _stop_reason_from_finish_reason(
        choice.get("finish_reason"),
        saw_tool_use=any(block["type"] == TOOL_USE_BLOCK_TYPE for block in content_blocks),
    )

    usage = _usage_from_request_response(request_body, openai_response)
    return {
        "id": str(openai_response.get("id") or f"msg_{uuid.uuid4().hex}"),
        "type": "message",
        "role": "assistant",
        "model": fallback_model,
        "content": content_blocks,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": usage,
    }


def build_count_tokens_response(request_body: dict[str, Any]) -> dict[str, int]:
    total_text = _flatten_system_text(request_body.get("system")) + "\n"
    total_text += _flatten_text(request_body.get("messages")) + "\n"
    total_text += _flatten_text(request_body.get("tools"))
    return {"input_tokens": _count_tokens_approx(total_text)}


def _stop_reason_from_finish_reason(finish_reason: Any, *, saw_tool_use: bool) -> str:
    normalized = str(finish_reason or "").strip().lower()
    if saw_tool_use:
        return "tool_use"
    if normalized in {"length", "max_tokens"}:
        return "max_tokens"
    return "end_turn"


def iter_sse_events(message_payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    content = message_payload.get("content")
    content_blocks = content if isinstance(content, list) else []
    usage = message_payload.get("usage") if isinstance(message_payload.get("usage"), dict) else {}
    events: list[tuple[str, dict[str, Any]]] = [
        (
            "message_start",
            {
                "type": "message_start",
                "message": {
                    "id": message_payload.get("id"),
                    "type": "message",
                    "role": "assistant",
                    "model": message_payload.get("model"),
                    "content": [],
                    "stop_reason": None,
                    "stop_sequence": None,
                    "usage": {
                        "input_tokens": int(usage.get("input_tokens") or 0),
                        "output_tokens": 0,
                    },
                },
            },
        )
    ]

    for index, block in enumerate(content_blocks):
        block_type = str(block.get("type") or "").strip().lower()
        if block_type == TEXT_BLOCK_TYPE:
            events.append(
                (
                    "content_block_start",
                    {
                        "type": "content_block_start",
                        "index": index,
                        "content_block": {"type": TEXT_BLOCK_TYPE, "text": ""},
                    },
                )
            )
            events.append(
                (
                    "content_block_delta",
                    {
                        "type": "content_block_delta",
                        "index": index,
                        "delta": {"type": "text_delta", "text": str(block.get("text") or "")},
                    },
                )
            )
            events.append(("content_block_stop", {"type": "content_block_stop", "index": index}))
            continue
        if block_type == TOOL_USE_BLOCK_TYPE:
            tool_input = block.get("input") if isinstance(block.get("input"), dict) else {}
            events.append(
                (
                    "content_block_start",
                    {
                        "type": "content_block_start",
                        "index": index,
                        "content_block": {
                            "type": TOOL_USE_BLOCK_TYPE,
                            "id": block.get("id"),
                            "name": block.get("name"),
                            "input": {},
                        },
                    },
                )
            )
            events.append(
                (
                    "content_block_delta",
                    {
                        "type": "content_block_delta",
                        "index": index,
                        "delta": {"type": "input_json_delta", "partial_json": _json_dumps(tool_input)},
                    },
                )
            )
            events.append(("content_block_stop", {"type": "content_block_stop", "index": index}))

    events.append(
        (
            "message_delta",
            {
                "type": "message_delta",
                "delta": {
                    "stop_reason": message_payload.get("stop_reason"),
                    "stop_sequence": None,
                },
                "usage": {
                    "output_tokens": int(usage.get("output_tokens") or 0),
                },
            },
        )
    )
    events.append(("message_stop", {"type": "message_stop"}))
    return events


def _iter_sse_payloads(stream: Any) -> Iterable[str]:
    event_lines: list[str] = []
    while True:
        raw_line = stream.readline()
        if not raw_line:
            break
        line = raw_line.decode("utf-8", errors="ignore").rstrip("\r\n")
        if not line:
            if event_lines:
                payload_lines = [item[5:] for item in event_lines if item.startswith("data:")]
                if payload_lines:
                    yield "\n".join(payload_lines).strip()
                event_lines = []
            continue
        event_lines.append(line)
    if event_lines:
        payload_lines = [item[5:] for item in event_lines if item.startswith("data:")]
        if payload_lines:
            yield "\n".join(payload_lines).strip()


def _iter_openai_stream_chunks(stream: Any) -> Iterable[dict[str, Any]]:
    for payload in _iter_sse_payloads(stream):
        if not payload or payload == "[DONE]":
            continue
        parsed = _json_loads(payload)
        if isinstance(parsed, dict):
            yield parsed


def iter_openai_to_anthropic_sse_events(
    request_body: dict[str, Any],
    openai_chunks: Iterable[dict[str, Any]],
    *,
    fallback_model: str,
) -> Iterable[tuple[str, dict[str, Any]]]:
    input_tokens = build_count_tokens_response(request_body)["input_tokens"]
    message_id: str | None = None
    model_name = fallback_model
    message_started = False
    text_block_index: int | None = None
    next_content_index = 0
    saw_tool_use = False
    finish_reason: Any = None
    output_fragments: list[str] = []
    output_tokens = 0
    tool_states: dict[int, ToolUseStreamState] = {}
    tool_order: list[int] = []

    def build_message_start_event() -> tuple[str, dict[str, Any]]:
        return (
            "message_start",
            {
                "type": "message_start",
                "message": {
                    "id": message_id or f"msg_{uuid.uuid4().hex}",
                    "type": "message",
                    "role": "assistant",
                    "model": model_name,
                    "content": [],
                    "stop_reason": None,
                    "stop_sequence": None,
                    "usage": {
                        "input_tokens": input_tokens,
                        "output_tokens": 0,
                    },
                },
            },
        )

    def stop_text_block() -> tuple[str, dict[str, Any]] | None:
        nonlocal text_block_index
        if text_block_index is None:
            return None
        stopped_index = text_block_index
        text_block_index = None
        return ("content_block_stop", {"type": "content_block_stop", "index": stopped_index})

    for chunk in openai_chunks:
        if not message_started:
            message_id = str(chunk.get("id") or f"msg_{uuid.uuid4().hex}")
            model_name = str(chunk.get("model") or fallback_model)
            yield build_message_start_event()
            message_started = True

        usage = chunk.get("usage")
        if isinstance(usage, dict) and usage.get("completion_tokens") is not None:
            output_tokens = int(usage.get("completion_tokens") or 0)

        choices = chunk.get("choices")
        if not isinstance(choices, list) or not choices:
            continue
        choice = choices[0]
        if not isinstance(choice, dict):
            continue
        finish_reason = choice.get("finish_reason") or finish_reason
        delta = choice.get("delta")
        if not isinstance(delta, dict):
            continue

        content_delta = delta.get("content")
        if isinstance(content_delta, str) and content_delta:
            if text_block_index is None:
                text_block_index = next_content_index
                next_content_index += 1
                yield (
                    "content_block_start",
                    {
                        "type": "content_block_start",
                        "index": text_block_index,
                        "content_block": {"type": TEXT_BLOCK_TYPE, "text": ""},
                    },
                )
            output_fragments.append(content_delta)
            yield (
                "content_block_delta",
                {
                    "type": "content_block_delta",
                    "index": text_block_index,
                    "delta": {"type": "text_delta", "text": content_delta},
                },
            )

        tool_calls = delta.get("tool_calls")
        if isinstance(tool_calls, list) and tool_calls:
            saw_tool_use = True
            text_stop_event = stop_text_block()
            if text_stop_event is not None:
                yield text_stop_event

            for tool_call in tool_calls:
                if not isinstance(tool_call, dict):
                    continue
                stream_index = int(tool_call.get("index") or 0)
                function_payload = tool_call.get("function")
                function_payload = function_payload if isinstance(function_payload, dict) else {}

                state = tool_states.get(stream_index)
                if state is None:
                    state = ToolUseStreamState(
                        index=next_content_index,
                        tool_id=str(tool_call.get("id") or f"toolu_{uuid.uuid4().hex[:24]}"),
                        name=str(function_payload.get("name") or ""),
                        input_parts=[],
                    )
                    tool_states[stream_index] = state
                    tool_order.append(stream_index)
                    next_content_index += 1
                elif not state.name and function_payload.get("name"):
                    state.name = str(function_payload.get("name") or "")

                if not state.started:
                    state.started = True
                    yield (
                        "content_block_start",
                        {
                            "type": "content_block_start",
                            "index": state.index,
                            "content_block": {
                                "type": TOOL_USE_BLOCK_TYPE,
                                "id": state.tool_id,
                                "name": state.name,
                                "input": {},
                            },
                        },
                    )

                arguments_delta = function_payload.get("arguments")
                if isinstance(arguments_delta, str) and arguments_delta:
                    state.input_parts.append(arguments_delta)
                    output_fragments.append(arguments_delta)
                    yield (
                        "content_block_delta",
                        {
                            "type": "content_block_delta",
                            "index": state.index,
                            "delta": {"type": "input_json_delta", "partial_json": arguments_delta},
                        },
                    )

    if not message_started:
        yield build_message_start_event()

    text_stop_event = stop_text_block()
    if text_stop_event is not None:
        yield text_stop_event

    for stream_index in tool_order:
        state = tool_states[stream_index]
        if state.started and not state.stopped:
            state.stopped = True
            yield ("content_block_stop", {"type": "content_block_stop", "index": state.index})

    if output_tokens <= 0:
        output_tokens = _count_tokens_approx("\n".join(output_fragments))

    yield (
        "message_delta",
        {
            "type": "message_delta",
            "delta": {
                "stop_reason": _stop_reason_from_finish_reason(finish_reason, saw_tool_use=saw_tool_use),
                "stop_sequence": None,
            },
            "usage": {
                "output_tokens": output_tokens,
            },
        },
    )
    yield ("message_stop", {"type": "message_stop"})


def _build_upstream_request(payload: dict[str, Any], config: ProxyConfig) -> urlrequest.Request:
    url = f"{config.upstream_base_url.rstrip('/')}/chat/completions"
    request_payload = _json_dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {config.upstream_api_key}",
        "Content-Type": "application/json",
    }
    return urlrequest.Request(url=url, method="POST", data=request_payload, headers=headers)


def _call_upstream_openai(payload: dict[str, Any], config: ProxyConfig) -> dict[str, Any]:
    req = _build_upstream_request(payload, config)
    try:
        with urlrequest.urlopen(req, timeout=config.timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except urlerror.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Upstream llama.cpp HTTP {exc.code}: {detail[:400]}") from exc
    except urlerror.URLError as exc:
        raise RuntimeError(f"Could not reach upstream llama.cpp endpoint at {url}: {exc}") from exc

    parsed = _json_loads(body)
    if not isinstance(parsed, dict):
        raise RuntimeError("Upstream llama.cpp response was not a JSON object.")
    return parsed


def _probe_upstream(config: ProxyConfig) -> tuple[bool, str]:
    url = f"{config.upstream_base_url.rstrip('/')}/models"
    req = urlrequest.Request(url=url, method="GET")
    try:
        with urlrequest.urlopen(req, timeout=min(config.timeout_seconds, 5.0)) as response:
            response.read()
    except Exception as exc:
        return False, str(exc)
    return True, ""


def _error_payload(message: str, *, error_type: str) -> dict[str, Any]:
    return {"type": "error", "error": {"type": error_type, "message": message}}


def _server_config_from_class(handler_cls: type[BaseHTTPRequestHandler]) -> ProxyConfig:
    config = getattr(handler_cls, "proxy_config", None)
    if not isinstance(config, ProxyConfig):
        raise RuntimeError("Proxy handler is missing configuration.")
    return config


class ClaudeLlamaProxyHandler(BaseHTTPRequestHandler):
    proxy_config: ProxyConfig
    server_version = "ClaudeLlamaProxy/0.1"
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        path = urlparse.urlsplit(self.path).path
        if path == "/healthz":
            config = _server_config_from_class(type(self))
            upstream_ok, upstream_error = _probe_upstream(config)
            self._send_json(
                200,
                {
                    "ok": True,
                    "upstream_ok": upstream_ok,
                    "upstream_error": upstream_error,
                    "upstream_base_url": config.upstream_base_url,
                    "upstream_model": config.upstream_model,
                },
            )
            return
        self._send_json(404, _error_payload(f"Unknown endpoint: {path}", error_type="not_found_error"))

    def do_POST(self) -> None:
        path = urlparse.urlsplit(self.path).path
        try:
            request_body = self._read_json_body()
            if path == "/v1/messages":
                self._handle_messages(request_body)
                return
            if path == "/v1/messages/count_tokens":
                self._send_json(200, build_count_tokens_response(request_body))
                return
            self._send_json(404, _error_payload(f"Unknown endpoint: {path}", error_type="not_found_error"))
        except ValueError as exc:
            self._send_json(400, _error_payload(str(exc), error_type="invalid_request_error"))
        except RuntimeError as exc:
            self._send_json(502, _error_payload(str(exc), error_type="api_error"))

    def _read_json_body(self) -> dict[str, Any]:
        raw_length = self.headers.get("Content-Length", "").strip()
        if not raw_length:
            raise ValueError("Missing Content-Length header.")
        try:
            content_length = int(raw_length)
        except ValueError as exc:
            raise ValueError("Invalid Content-Length header.") from exc
        payload = self.rfile.read(content_length).decode("utf-8")
        try:
            parsed = _json_loads(payload)
        except Exception as exc:
            raise ValueError("Request body was not valid JSON.") from exc
        if not isinstance(parsed, dict):
            raise ValueError("Request body must be a JSON object.")
        return parsed

    def _handle_messages(self, request_body: dict[str, Any]) -> None:
        config = _server_config_from_class(type(self))
        openai_payload = build_openai_payload(request_body, config)
        wants_stream = bool(request_body.get("stream"))
        if wants_stream:
            self._send_sse_from_upstream(request_body, openai_payload, config)
            return
        openai_response = _call_upstream_openai(openai_payload, config)
        anthropic_response = build_anthropic_message_response(
            request_body,
            openai_response,
            fallback_model=config.upstream_model,
        )
        self._send_json(200, anthropic_response)

    def _send_json(self, status_code: int, payload: dict[str, Any]) -> None:
        body = (_json_dumps(payload) + "\n").encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()

    def _send_sse(self, payload: dict[str, Any]) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        for event_name, event_payload in iter_sse_events(payload):
            self._write_sse_event(event_name, event_payload)

    def _write_sse_event(self, event_name: str, event_payload: dict[str, Any]) -> None:
        self.wfile.write(f"event: {event_name}\n".encode("utf-8"))
        self.wfile.write(f"data: {_json_dumps(event_payload)}\n\n".encode("utf-8"))
        self.wfile.flush()

    def _send_sse_from_upstream(
        self,
        request_body: dict[str, Any],
        openai_payload: dict[str, Any],
        config: ProxyConfig,
    ) -> None:
        req = _build_upstream_request(openai_payload, config)
        try:
            upstream_response = urlrequest.urlopen(req, timeout=config.timeout_seconds)
        except urlerror.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Upstream llama.cpp HTTP {exc.code}: {detail[:400]}") from exc
        except urlerror.URLError as exc:
            raise RuntimeError(f"Could not reach upstream llama.cpp endpoint: {exc}") from exc

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        with upstream_response:
            for event_name, event_payload in iter_openai_to_anthropic_sse_events(
                request_body,
                _iter_openai_stream_chunks(upstream_response),
                fallback_model=config.upstream_model,
            ):
                self._write_sse_event(event_name, event_payload)


def build_config(args: argparse.Namespace) -> ProxyConfig:
    return ProxyConfig(
        bind_host=str(args.host or DEFAULT_BIND_HOST),
        bind_port=max(1, int(args.port or DEFAULT_BIND_PORT)),
        upstream_base_url=str(args.upstream_base_url or DEFAULT_UPSTREAM_BASE_URL).rstrip("/"),
        upstream_api_key=str(args.upstream_api_key or DEFAULT_UPSTREAM_API_KEY),
        upstream_model=str(args.upstream_model or DEFAULT_UPSTREAM_MODEL),
        timeout_seconds=max(1.0, float(args.timeout_seconds or DEFAULT_TIMEOUT_SECONDS)),
    )


def main() -> int:
    args = parse_args()
    config = build_config(args)

    class Handler(ClaudeLlamaProxyHandler):
        proxy_config = config

    server = ThreadingHTTPServer((config.bind_host, config.bind_port), Handler)
    print(
        _json_dumps(
            {
                "event": "proxy_started",
                "bind_host": config.bind_host,
                "bind_port": config.bind_port,
                "upstream_base_url": config.upstream_base_url,
                "upstream_model": config.upstream_model,
            }
        ),
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
