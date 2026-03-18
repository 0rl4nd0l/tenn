#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.router import load_model_routing_config
from app.services.router_state import _gpu_utilization_percent


DEFAULT_PROMPTS = {
    "router": "Classify this request and return JSON with task_type and urgency.",
    "coding": "Return JSON with a Python function name and a short patch plan for a CSV parser bug.",
    "reasoning": "Return JSON summarizing the key financial risks in a quarterly filing.",
    "deep_reasoning": (
        "Return JSON with a detailed multi-section analysis of a long filing, including balance-sheet risk, "
        "guidance quality, capital allocation, and the biggest open questions for follow-up."
    ),
}


def _normalize_url(base_url: str) -> str:
    return str(base_url or "").rstrip("/")


def _measure_ollama(base_url: str, model: str, prompt: str, timeout: float) -> dict[str, Any]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "format": "json",
        "options": {"temperature": 0},
    }
    ttft_seconds: float | None = None
    started_at = perf_counter()
    final_chunk: dict[str, Any] = {}

    with httpx.Client(timeout=timeout) as client:
        with client.stream("POST", f"{_normalize_url(base_url)}/api/generate", json=payload) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                if ttft_seconds is None:
                    ttft_seconds = max(perf_counter() - started_at, 0.0)
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if chunk.get("done"):
                    final_chunk = chunk
                    break

    latency_seconds = max(perf_counter() - started_at, 0.0)
    tokens_generated = int(final_chunk.get("eval_count") or 0)
    return {
        "ttft_seconds": ttft_seconds,
        "latency_seconds": latency_seconds,
        "tokens_generated": tokens_generated,
        "tokens_per_second": (tokens_generated / latency_seconds) if latency_seconds > 0 else 0.0,
    }


def _measure_llamacpp(base_url: str, model: str, prompt: str, timeout: float) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Return valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 1024,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    ttft_seconds: float | None = None
    started_at = perf_counter()
    usage: dict[str, Any] = {}
    text_parts: list[str] = []

    with httpx.Client(timeout=timeout) as client:
        with client.stream(
            "POST",
            f"{_normalize_url(base_url)}/v1/chat/completions",
            json=payload,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                if isinstance(line, bytes):
                    line = line.decode("utf-8", errors="ignore")
                line = str(line).strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = chunk.get("choices") if isinstance(chunk, dict) else None
                if isinstance(choices, list) and choices:
                    delta = choices[0].get("delta")
                    if isinstance(delta, dict) and delta.get("content") is not None:
                        if ttft_seconds is None:
                            ttft_seconds = max(perf_counter() - started_at, 0.0)
                        text_parts.append(str(delta.get("content") or ""))
                if isinstance(chunk.get("usage"), dict):
                    usage = dict(chunk["usage"])

    latency_seconds = max(perf_counter() - started_at, 0.0)
    tokens_generated = int(usage.get("completion_tokens") or 0)
    if tokens_generated <= 0:
        tokens_generated = max(len("".join(text_parts)) // 4, 0)
    return {
        "ttft_seconds": ttft_seconds,
        "latency_seconds": latency_seconds,
        "tokens_generated": tokens_generated,
        "tokens_per_second": (tokens_generated / latency_seconds) if latency_seconds > 0 else 0.0,
    }


def _benchmark_role(role_name: str, role: Any, prompt: str, timeout: float) -> dict[str, Any]:
    if role.provider == "ollama":
        result = _measure_ollama(role.base_url, role.model_name, prompt, timeout)
    elif role.provider == "llamacpp":
        result = _measure_llamacpp(role.base_url, role.model_name, prompt, timeout)
    else:
        raise RuntimeError(f"Unsupported provider for benchmarking: {role.provider}")

    result.update(
        {
            "provider": role.provider,
            "role": role_name,
            "prompt_length": len(prompt),
            "gpu_utilization": _gpu_utilization_percent(),
        }
    )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark routed generation models and write model_benchmark.json.")
    parser.add_argument("--timeout", type=float, default=120.0, help="Per-request timeout in seconds.")
    parser.add_argument(
        "--output",
        default=str(ROOT / "reports" / "model_benchmark.json"),
        help="Output path for the benchmark report.",
    )
    parser.add_argument(
        "--prompt-file",
        help="Optional JSON file with role->prompt overrides for router/coding/reasoning/deep_reasoning.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    prompts = dict(DEFAULT_PROMPTS)
    if args.prompt_file:
        overrides = json.loads(Path(args.prompt_file).read_text(encoding="utf-8"))
        if isinstance(overrides, dict):
            for role_name, prompt in overrides.items():
                if role_name in prompts and str(prompt or "").strip():
                    prompts[role_name] = str(prompt)

    config = load_model_routing_config()
    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    models: dict[str, dict[str, Any]] = {}
    for role_name in ("router", "coding", "reasoning", "deep_reasoning"):
        role = getattr(config, role_name)
        benchmark = _benchmark_role(role_name, role, prompts[role_name], args.timeout)
        entry = dict(models.get(role.model_name) or {})
        entry.update(benchmark)
        roles = set(entry.get("roles") or [])
        roles.add(role_name)
        entry["roles"] = sorted(roles)
        models[role.model_name] = entry

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "models": models,
    }
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
