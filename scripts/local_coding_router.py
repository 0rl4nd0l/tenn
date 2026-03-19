#!/usr/bin/env python3
"""
Route coding prompts to local models by workload tier.

Typical use:
  python3 scripts/local_coding_router.py --route auto --prompt-file prompt.txt
  echo "Refactor this function for readability..." | python3 scripts/local_coding_router.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib import error, request


DEFAULT_PROVIDER = "openai"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_OPENAI_BASE_URL = "http://127.0.0.1:8001/v1"
DEFAULT_LOCAL_OPENAI_API_KEY = "local-openai-key"

DEFAULT_MODELS_BY_PROVIDER = {
    "openai": {
        "simple": "qwen2.5-coder-14b",
        "standard": "qwen2.5-coder-14b",
        "deep": "qwen2.5-coder-14b",
        "fallback": "qwen2.5-coder-14b",
    },
    "ollama": {
        "simple": "qwen2.5-coder:14b",
        "standard": "llama3.1:8b",
        "deep": "qwen2.5:32b",
        "fallback": "phi3:mini",
    },
}

DEFAULT_NUM_CTX = {
    "simple": 8192,
    "standard": 12288,
    "deep": 16384,
    "fallback": 4096,
}

SIMPLE_HINTS = (
    "summarize",
    "rewrite",
    "reformat",
    "format",
    "clean up",
    "boilerplate",
    "scaffold",
    "rename",
    "docstring",
    "comment",
    "unit test",
    "tests for",
    "json schema",
)

DEEP_HINTS = (
    "architecture",
    "root cause",
    "race condition",
    "deadlock",
    "query plan",
    "performance regression",
    "security review",
    "threat model",
    "design proposal",
    "migrate",
    "multi-step",
    "cross-file",
)


@dataclass(frozen=True)
class RouteDecision:
    route: str
    reason: str


def _auth_headers(api_key: str) -> dict[str, str]:
    token = str(api_key or "").strip()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def default_model_map(provider: str) -> dict[str, str]:
    if provider == "ollama":
        return dict(DEFAULT_MODELS_BY_PROVIDER["ollama"])
    return dict(DEFAULT_MODELS_BY_PROVIDER["openai"])


def _looks_like_local_endpoint(base_url: str) -> bool:
    value = str(base_url or "").strip().lower()
    return value.startswith("http://127.0.0.1") or value.startswith("http://localhost")


def estimate_tokens(text: str) -> int:
    # Coarse approximation for routing only.
    return max(1, len(text) // 4)


def count_hits(lower_text: str, phrases: Sequence[str]) -> int:
    return sum(1 for p in phrases if p in lower_text)


def choose_route(prompt: str, requested_route: str) -> RouteDecision:
    if requested_route != "auto":
        return RouteDecision(route=requested_route, reason="explicit route")

    text = prompt.lower()
    simple_hits = count_hits(text, SIMPLE_HINTS)
    deep_hits = count_hits(text, DEEP_HINTS)
    token_est = estimate_tokens(prompt)

    if deep_hits >= 2 or (deep_hits >= 1 and token_est >= 1200):
        return RouteDecision(route="deep", reason=f"deep hints={deep_hits}, est_tokens={token_est}")
    if simple_hits >= 1 or token_est >= 1200:
        return RouteDecision(route="simple", reason=f"simple hints={simple_hits}, est_tokens={token_est}")
    return RouteDecision(route="standard", reason=f"default route, est_tokens={token_est}")


def request_json(
    url: str,
    payload: Mapping[str, Any] | None,
    timeout_seconds: float,
    headers: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    req = request.Request(
        url=url,
        method="GET" if payload is None else "POST",
        data=data,
        headers=req_headers,
    )
    try:
        with request.urlopen(req, timeout=timeout_seconds) as resp:
            body = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8")
        except Exception:
            detail = str(exc)
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail[:400]}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Could not reach {url}: {exc}") from exc

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Non-JSON response from {url}: {body[:400]}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError(f"Unexpected response type from {url}: {type(parsed).__name__}")
    return parsed


def post_json(url: str, payload: Mapping[str, Any] | None, timeout_seconds: float) -> dict[str, Any]:
    return request_json(url=url, payload=payload, timeout_seconds=timeout_seconds)


def fetch_available_models(provider: str, base_url: str, api_key: str, timeout_seconds: float) -> set[str]:
    if provider == "openai":
        payload = request_json(
            f"{normalize_base_url(base_url)}/models",
            payload=None,
            timeout_seconds=timeout_seconds,
            headers=_auth_headers(api_key),
        )
        models = payload.get("data", [])
    else:
        payload = post_json(f"{normalize_base_url(base_url)}/api/tags", payload=None, timeout_seconds=timeout_seconds)
        models = payload.get("models", [])

    out: set[str] = set()
    if isinstance(models, list):
        for item in models:
            if not isinstance(item, dict):
                continue
            for key in ("name", "model", "id"):
                value = item.get(key)
                if isinstance(value, str) and value.strip():
                    out.add(value.strip())
    return out


def route_priority(route: str) -> list[str]:
    if route == "simple":
        return ["simple", "fallback", "standard", "deep"]
    if route == "deep":
        return ["deep", "standard", "simple", "fallback"]
    if route == "fallback":
        return ["fallback", "simple", "standard", "deep"]
    return ["standard", "simple", "fallback", "deep"]


def infer_route_for_model(model: str, model_map: Mapping[str, str], default_route: str) -> str:
    for route, configured_model in model_map.items():
        if configured_model == model:
            return route
    return default_route


def resolve_model(
    route: str,
    model_map: Mapping[str, str],
    explicit_model: str | None,
    available_models: set[str] | None,
) -> tuple[str, str, str]:
    if explicit_model:
        if not available_models or explicit_model in available_models:
            return (
                explicit_model,
                "explicit model",
                infer_route_for_model(explicit_model, model_map, default_route=route),
            )
        for candidate_route in route_priority(route):
            candidate = model_map[candidate_route]
            if candidate in available_models:
                return candidate, f"explicit missing, downgraded to {candidate_route}", candidate_route
        return (
            explicit_model,
            "explicit model not present; continuing anyway",
            infer_route_for_model(explicit_model, model_map, default_route=route),
        )

    preferred = model_map[route]
    if not available_models:
        return preferred, "model probe unavailable/skipped", route
    if preferred in available_models:
        return preferred, "preferred model present", route
    for candidate_route in route_priority(route):
        candidate = model_map[candidate_route]
        if candidate in available_models:
            return candidate, f"preferred missing, downgraded to {candidate_route}", candidate_route
    return preferred, "no configured models present in local catalog", route


def is_retryable_runner_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(
        marker in text
        for marker in (
            "runner process has terminated",
            "timed out waiting for llama runner to start",
            "exit status 2",
        )
    )


def build_candidate_chain(
    selected_route: str,
    selected_model: str,
    model_map: Mapping[str, str],
    available_models: set[str] | None,
    explicit_model: str | None,
) -> list[tuple[str, str]]:
    if explicit_model:
        return [(selected_route, selected_model)]

    out: list[tuple[str, str]] = []
    seen_models: set[str] = set()

    def add(route: str, model: str) -> None:
        if model in seen_models:
            return
        if available_models is not None and model not in available_models:
            return
        out.append((route, model))
        seen_models.add(model)

    add(selected_route, selected_model)
    for candidate_route in route_priority(selected_route):
        add(candidate_route, model_map[candidate_route])
    for candidate_route, candidate_model in model_map.items():
        add(candidate_route, candidate_model)
    return out


def build_payload(
    model: str,
    prompt: str,
    route: str,
    keep_alive: str,
    temperature: float,
    num_ctx: int | None,
    num_predict: int | None,
    *,
    provider: str = "ollama",
) -> dict[str, Any]:
    if provider == "openai":
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "temperature": temperature,
        }
        if num_predict is not None:
            payload["max_tokens"] = int(num_predict)
        return payload

    ctx = num_ctx if num_ctx is not None else DEFAULT_NUM_CTX[route]
    options: dict[str, Any] = {"temperature": temperature, "num_ctx": int(ctx)}
    if num_predict is not None:
        options["num_predict"] = int(num_predict)
    return {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": keep_alive,
        "options": options,
    }


def parse_response_text(payload: Mapping[str, Any], *, provider: str = "ollama") -> str:
    if provider == "openai":
        choices = payload.get("choices")
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
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts)
        return ""

    val = payload.get("response")
    if isinstance(val, str):
        return val
    if val is None:
        return ""
    return json.dumps(val)


def tokens_per_second(payload: Mapping[str, Any], *, provider: str = "ollama") -> float | None:
    if provider == "openai":
        return None
    eval_count = payload.get("eval_count")
    eval_duration = payload.get("eval_duration")
    if not isinstance(eval_count, int) or eval_count <= 0:
        return None
    if not isinstance(eval_duration, int) or eval_duration <= 0:
        return None
    seconds = eval_duration / 1_000_000_000
    if seconds <= 0:
        return None
    return eval_count / seconds


def read_prompt(prompt_arg: str | None, prompt_file: str | None) -> str:
    if prompt_arg and prompt_file:
        raise RuntimeError("Use either positional prompt or --prompt-file, not both.")
    if prompt_file:
        return Path(prompt_file).expanduser().read_text(encoding="utf-8")
    if prompt_arg:
        return prompt_arg
    if sys.stdin.isatty():
        raise RuntimeError("No prompt provided. Pass text or pipe stdin.")
    return sys.stdin.read()


def build_model_map(args: argparse.Namespace) -> dict[str, str]:
    return {
        "simple": args.simple_model,
        "standard": args.standard_model,
        "deep": args.deep_model,
        "fallback": args.fallback_model,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Local coding LLM router.")
    ap.add_argument("prompt", nargs="?", help="Prompt text. If omitted, reads from stdin.")
    ap.add_argument("--prompt-file", help="Path to a prompt text file.")
    ap.add_argument(
        "--route",
        choices=["auto", "simple", "standard", "deep", "fallback"],
        default="auto",
        help="Routing policy. 'auto' classifies by prompt hints and size.",
    )
    ap.add_argument(
        "--provider",
        choices=["openai", "ollama"],
        default=os.environ.get("LOCAL_CODING_ROUTER_PROVIDER", DEFAULT_PROVIDER),
        help="Inference provider.",
    )
    ap.add_argument("--base-url", default="", help="Inference server base URL.")
    ap.add_argument("--api-key", default="", help="API key for openai-compatible providers.")
    ap.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL, help=argparse.SUPPRESS)
    ap.add_argument("--model", default="", help="Override selected model directly.")
    ap.add_argument("--simple-model", default="", help="Tier-A/simple model name.")
    ap.add_argument("--standard-model", default="", help="Tier-B/standard model name.")
    ap.add_argument("--deep-model", default="", help="Tier-C/deep model name.")
    ap.add_argument("--fallback-model", default="", help="Tier-D/fallback model name.")
    ap.add_argument("--timeout-seconds", type=float, default=180.0, help="HTTP timeout for model calls.")
    ap.add_argument("--keep-alive", default="45m", help="Ollama keep_alive value.")
    ap.add_argument("--num-ctx", type=int, default=None, help="Override context window.")
    ap.add_argument("--num-predict", type=int, default=None, help="Optional max output tokens.")
    ap.add_argument("--temperature", type=float, default=0.2, help="Sampling temperature.")
    ap.add_argument(
        "--skip-model-probe",
        action="store_true",
        help="Skip model catalog probe and call the selected model directly.",
    )
    ap.add_argument(
        "--print-meta",
        action="store_true",
        help="Print routing and timing metadata as JSON to stderr.",
    )
    ap.add_argument("--quiet", action="store_true", help="Suppress one-line route summary on stderr.")
    args = ap.parse_args(argv)

    if not args.base_url.strip():
        if args.provider == "openai":
            args.base_url = os.environ.get("LOCAL_CODING_ROUTER_OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL)
        else:
            args.base_url = args.ollama_url
    if args.provider == "openai" and not args.api_key.strip():
        args.api_key = os.environ.get("LOCAL_CODING_ROUTER_OPENAI_API_KEY", "")
    if args.provider == "openai" and not args.api_key.strip() and _looks_like_local_endpoint(args.base_url):
        args.api_key = DEFAULT_LOCAL_OPENAI_API_KEY
    if args.provider == "ollama":
        args.api_key = ""

    defaults = default_model_map(args.provider)
    if not args.simple_model.strip():
        args.simple_model = defaults["simple"]
    if not args.standard_model.strip():
        args.standard_model = defaults["standard"]
    if not args.deep_model.strip():
        args.deep_model = defaults["deep"]
    if not args.fallback_model.strip():
        args.fallback_model = defaults["fallback"]
    return args


def generate_completion(
    provider: str,
    base_url: str,
    api_key: str,
    payload: Mapping[str, Any],
    timeout_seconds: float,
) -> dict[str, Any]:
    if provider == "openai":
        return request_json(
            f"{normalize_base_url(base_url)}/chat/completions",
            payload=payload,
            timeout_seconds=timeout_seconds,
            headers=_auth_headers(api_key),
        )
    return post_json(
        f"{normalize_base_url(base_url)}/api/generate",
        payload=payload,
        timeout_seconds=timeout_seconds,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        prompt = read_prompt(args.prompt, args.prompt_file)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not prompt.strip():
        print("error: prompt is empty", file=sys.stderr)
        return 2

    decision = choose_route(prompt, args.route)
    model_map = build_model_map(args)

    available_models: set[str] | None = None
    if not args.skip_model_probe:
        try:
            available_models = fetch_available_models(
                args.provider,
                args.base_url,
                args.api_key,
                timeout_seconds=min(args.timeout_seconds, 30.0),
            )
        except Exception:
            available_models = None

    explicit_model = args.model.strip() or None
    selected_model, model_reason, effective_route = resolve_model(
        route=decision.route,
        model_map=model_map,
        explicit_model=explicit_model,
        available_models=available_models,
    )

    candidate_chain = build_candidate_chain(
        selected_route=effective_route,
        selected_model=selected_model,
        model_map=model_map,
        available_models=available_models,
        explicit_model=explicit_model,
    )
    attempted_chain: list[dict[str, str]] = []
    response: dict[str, Any] | None = None
    initial_model_reason = model_reason

    for idx, (candidate_route, candidate_model) in enumerate(candidate_chain):
        attempted_chain.append({"route": candidate_route, "model": candidate_model})
        payload = build_payload(
            model=candidate_model,
            prompt=prompt,
            route=candidate_route,
            keep_alive=args.keep_alive,
            temperature=float(args.temperature),
            num_ctx=args.num_ctx,
            num_predict=args.num_predict,
            provider=args.provider,
        )
        try:
            response = generate_completion(
                provider=args.provider,
                base_url=args.base_url,
                api_key=args.api_key,
                payload=payload,
                timeout_seconds=float(args.timeout_seconds),
            )
            selected_model = candidate_model
            effective_route = candidate_route
            if idx > 0:
                model_reason = f"{initial_model_reason}; runtime fallback to {candidate_route}"
            break
        except Exception as exc:
            if explicit_model or not is_retryable_runner_error(exc) or idx >= len(candidate_chain) - 1:
                print(f"error: {exc}", file=sys.stderr)
                return 1

    if response is None:
        print("error: no response from model runner", file=sys.stderr)
        return 1

    output = parse_response_text(response, provider=args.provider)
    if output:
        sys.stdout.write(output)
        if not output.endswith("\n"):
            sys.stdout.write("\n")

    tps = tokens_per_second(response, provider=args.provider)
    meta = {
        "route": decision.route,
        "effective_route": effective_route,
        "provider": args.provider,
        "route_reason": decision.reason,
        "model": selected_model,
        "model_reason": model_reason,
        "attempted_models": attempted_chain,
        "prompt_chars": len(prompt),
        "prompt_est_tokens": estimate_tokens(prompt),
        "eval_count": response.get("eval_count") if args.provider == "ollama" else None,
        "eval_duration_ns": response.get("eval_duration") if args.provider == "ollama" else None,
        "tokens_per_second": None if tps is None else round(tps, 2),
    }

    if args.print_meta:
        print(json.dumps(meta, indent=2), file=sys.stderr)
    elif not args.quiet:
        speed = "n/a" if tps is None else f"{tps:.2f} tok/s"
        print(
            f"[route={decision.route}] [provider={args.provider}] [model={selected_model}] [speed={speed}]",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
