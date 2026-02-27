#!/usr/bin/env python3
"""
Route coding prompts to local Ollama models by workload tier.

Typical use:
  python3 scripts/local_coding_router.py --route auto --prompt-file prompt.txt
  echo "Refactor this function for readability..." | python3 scripts/local_coding_router.py
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib import error, request


DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"

DEFAULT_MODELS = {
    "simple": "qwen2.5-coder:7b",
    "standard": "llama3.1:8b",
    "deep": "qwen2.5:32b",
    "fallback": "phi3:mini",
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


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


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


def post_json(url: str, payload: Mapping[str, Any] | None, timeout_seconds: float) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = request.Request(
        url=url,
        method="GET" if payload is None else "POST",
        data=data,
        headers={"Content-Type": "application/json"},
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


def fetch_available_models(base_url: str, timeout_seconds: float) -> set[str]:
    payload = post_json(f"{normalize_base_url(base_url)}/api/tags", payload=None, timeout_seconds=timeout_seconds)
    models = payload.get("models", [])
    out: set[str] = set()
    if isinstance(models, list):
        for item in models:
            if not isinstance(item, dict):
                continue
            for key in ("name", "model"):
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


def resolve_model(
    route: str,
    model_map: Mapping[str, str],
    explicit_model: str | None,
    available_models: set[str] | None,
) -> tuple[str, str]:
    if explicit_model:
        if not available_models or explicit_model in available_models:
            return explicit_model, "explicit model"
        for candidate_route in route_priority(route):
            candidate = model_map[candidate_route]
            if candidate in available_models:
                return candidate, f"explicit missing, downgraded to {candidate_route}"
        return explicit_model, "explicit model not present; continuing anyway"

    preferred = model_map[route]
    if not available_models:
        return preferred, "model probe unavailable/skipped"
    if preferred in available_models:
        return preferred, "preferred model present"
    for candidate_route in route_priority(route):
        candidate = model_map[candidate_route]
        if candidate in available_models:
            return candidate, f"preferred missing, downgraded to {candidate_route}"
    return preferred, "no configured models present in local catalog"


def build_payload(
    model: str,
    prompt: str,
    route: str,
    keep_alive: str,
    temperature: float,
    num_ctx: int | None,
    num_predict: int | None,
) -> dict[str, Any]:
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


def parse_response_text(payload: Mapping[str, Any]) -> str:
    val = payload.get("response")
    if isinstance(val, str):
        return val
    if val is None:
        return ""
    return json.dumps(val)


def tokens_per_second(payload: Mapping[str, Any]) -> float | None:
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
    ap = argparse.ArgumentParser(description="Local coding LLM router for Ollama.")
    ap.add_argument("prompt", nargs="?", help="Prompt text. If omitted, reads from stdin.")
    ap.add_argument("--prompt-file", help="Path to a prompt text file.")
    ap.add_argument(
        "--route",
        choices=["auto", "simple", "standard", "deep", "fallback"],
        default="auto",
        help="Routing policy. 'auto' classifies by prompt hints and size.",
    )
    ap.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL, help="Ollama base URL.")
    ap.add_argument("--model", default="", help="Override selected model directly.")
    ap.add_argument("--simple-model", default=DEFAULT_MODELS["simple"], help="Tier-A/simple model name.")
    ap.add_argument("--standard-model", default=DEFAULT_MODELS["standard"], help="Tier-B/standard model name.")
    ap.add_argument("--deep-model", default=DEFAULT_MODELS["deep"], help="Tier-C/deep model name.")
    ap.add_argument("--fallback-model", default=DEFAULT_MODELS["fallback"], help="Tier-D/fallback model name.")
    ap.add_argument("--timeout-seconds", type=float, default=180.0, help="HTTP timeout for Ollama calls.")
    ap.add_argument("--keep-alive", default="45m", help="Ollama keep_alive value.")
    ap.add_argument("--num-ctx", type=int, default=None, help="Override context window.")
    ap.add_argument("--num-predict", type=int, default=None, help="Optional max output tokens.")
    ap.add_argument("--temperature", type=float, default=0.2, help="Sampling temperature.")
    ap.add_argument(
        "--skip-model-probe",
        action="store_true",
        help="Skip /api/tags model catalog probe and call selected model directly.",
    )
    ap.add_argument(
        "--print-meta",
        action="store_true",
        help="Print routing and timing metadata as JSON to stderr.",
    )
    ap.add_argument("--quiet", action="store_true", help="Suppress one-line route summary on stderr.")
    return ap.parse_args(argv)


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
            available_models = fetch_available_models(args.ollama_url, timeout_seconds=min(args.timeout_seconds, 30.0))
        except Exception:
            available_models = None

    selected_model, model_reason = resolve_model(
        route=decision.route,
        model_map=model_map,
        explicit_model=args.model.strip() or None,
        available_models=available_models,
    )

    payload = build_payload(
        model=selected_model,
        prompt=prompt,
        route=decision.route,
        keep_alive=args.keep_alive,
        temperature=float(args.temperature),
        num_ctx=args.num_ctx,
        num_predict=args.num_predict,
    )

    try:
        response = post_json(
            f"{normalize_base_url(args.ollama_url)}/api/generate",
            payload=payload,
            timeout_seconds=float(args.timeout_seconds),
        )
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    output = parse_response_text(response)
    if output:
        sys.stdout.write(output)
        if not output.endswith("\n"):
            sys.stdout.write("\n")

    tps = tokens_per_second(response)
    meta = {
        "route": decision.route,
        "route_reason": decision.reason,
        "model": selected_model,
        "model_reason": model_reason,
        "prompt_chars": len(prompt),
        "prompt_est_tokens": estimate_tokens(prompt),
        "eval_count": response.get("eval_count"),
        "eval_duration_ns": response.get("eval_duration"),
        "tokens_per_second": None if tps is None else round(tps, 2),
    }

    if args.print_meta:
        print(json.dumps(meta, indent=2), file=sys.stderr)
    elif not args.quiet:
        speed = "n/a" if tps is None else f"{tps:.2f} tok/s"
        print(
            f"[route={decision.route}] [model={selected_model}] [speed={speed}]",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
