#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any


DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"


@dataclass
class SmokeResult:
    checks: list[dict[str, Any]] = field(default_factory=list)

    def add(
        self,
        name: str,
        ok: bool,
        detail: str,
        *,
        evidence: dict[str, Any] | None = None,
    ) -> None:
        self.checks.append(
            {
                "name": name,
                "ok": bool(ok),
                "detail": detail,
                "evidence": evidence or {},
            }
        )

    @property
    def ok(self) -> bool:
        return all(bool(item.get("ok")) for item in self.checks)

    @property
    def failures(self) -> list[dict[str, Any]]:
        return [item for item in self.checks if not bool(item.get("ok"))]


def _request_json(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    api_key: str = "",
    timeout: float = 30.0,
) -> dict[str, Any]:
    body = None
    headers = {"Accept": "application/json"}
    api_key = str(api_key or "").strip()
    if api_key:
        headers["X-API-Key"] = api_key
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed with HTTP {exc.code}: {raw[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{method} {url} failed: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{method} {url} returned non-JSON: {raw[:500]}") from exc
    return data if isinstance(data, dict) else {"data": data}


def _chat_data(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("type") == "done" and isinstance(payload.get("data"), dict):
        return payload["data"]
    data = payload.get("data")
    if isinstance(data, dict):
        return data
    return payload


def _routing(data: dict[str, Any]) -> dict[str, Any]:
    routing = data.get("routing_metadata")
    return routing if isinstance(routing, dict) else {}


def _source(data: dict[str, Any]) -> str:
    routing = _routing(data)
    return str(data.get("source") or routing.get("source") or "").strip().lower()


def _model(data: dict[str, Any]) -> str:
    routing = _routing(data)
    return str(data.get("model") or routing.get("model") or "").strip()


def _sources(data: dict[str, Any]) -> list[dict[str, Any]]:
    sources = data.get("sources")
    if not isinstance(sources, list):
        return []
    return [item for item in sources if isinstance(item, dict)]


def validate_api_only_config(
    result: SmokeResult,
    *,
    config: dict[str, Any],
    preferences: dict[str, Any],
    require_api_only: bool,
) -> None:
    if not require_api_only:
        result.add("api_only_config", True, "api-only config check skipped")
        return
    policy = str(
        config.get("routing_policy_override") or config.get("routing_policy") or ""
    ).strip()
    pref_override = str(preferences.get("chat_routing_policy_override") or "").strip()
    api_default = bool(preferences.get("api_default_enabled"))
    ok = policy == "api_only" and pref_override == "api_only" and api_default
    result.add(
        "api_only_config",
        ok,
        "backend and Cockpit preferences agree on api_only"
        if ok
        else "backend/preferences are not both api_only",
        evidence={
            "routing_policy": config.get("routing_policy"),
            "routing_policy_override": config.get("routing_policy_override"),
            "api_default_enabled": preferences.get("api_default_enabled"),
            "chat_routing_policy_override": preferences.get(
                "chat_routing_policy_override"
            ),
        },
    )


def validate_generic_prompt_response(result: SmokeResult, data: dict[str, Any]) -> None:
    source = _source(data)
    model = _model(data)
    routing = _routing(data)
    sources = _sources(data)
    text = str(data.get("text") or "")

    result.add(
        "generic_forced_local_not_local",
        source != "local",
        "forced-local generic prompt did not route to local",
        evidence={"source": source, "routing_reason": routing.get("routing_reason")},
    )
    result.add(
        "generic_model_present",
        bool(model) and model.lower() not in {"null", "none", "unknown", "local"},
        "generic prompt surfaced concrete model metadata",
        evidence={"model": model, "source": source},
    )
    result.add(
        "generic_not_orchestrator",
        source != "orchestrator",
        "generic prompt did not return orchestrator as the answer source",
        evidence={"source": source, "routing": routing},
    )
    result.add(
        "generic_no_visible_sources",
        len(sources) == 0,
        "generic prompt did not attach visible evidence sources",
        evidence={"visible_source_count": len(sources), "sources": sources[:3]},
    )
    result.add(
        "generic_no_coverage_noise",
        "Coverage and Failure Signals" not in text,
        "generic prompt did not expose evidence-gap boilerplate",
        evidence={"text_excerpt": text[:240]},
    )


def run_smoke(args: argparse.Namespace) -> SmokeResult:
    backend_url = str(args.backend_url or DEFAULT_BACKEND_URL).rstrip("/")
    api_key = str(args.api_key or "").strip()
    result = SmokeResult()

    health = _request_json("GET", f"{backend_url}/api/health", timeout=args.timeout)
    result.add(
        "backend_health",
        str(health.get("status") or "").lower() == "ok",
        "backend /api/health returned ok",
        evidence=health,
    )

    config = _request_json(
        "GET",
        f"{backend_url}/api/cockpit/config",
        api_key=api_key,
        timeout=args.timeout,
    )
    preferences = _request_json(
        "GET",
        f"{backend_url}/api/cockpit/preferences",
        api_key=api_key,
        timeout=args.timeout,
    )
    validate_api_only_config(
        result,
        config=config,
        preferences=preferences,
        require_api_only=not args.allow_non_api_only,
    )

    if not args.skip_chat:
        session_id = f"routing-smoke-{int(time.time())}"
        generic = _request_json(
            "POST",
            f"{backend_url}/api/cockpit/chat",
            payload={
                "message": "/local Reply exactly ok.",
                "mode": "analysis",
                "session_id": session_id,
                "stream": False,
            },
            api_key=api_key,
            timeout=args.chat_timeout,
        )
        validate_generic_prompt_response(result, _chat_data(generic))

    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cockpit routing/provenance smoke checks for API-only regressions."
    )
    parser.add_argument(
        "--backend-url",
        default=os.environ.get("COCKPIT_BACKEND_URL", DEFAULT_BACKEND_URL),
        help="Backend origin, default: COCKPIT_BACKEND_URL or http://127.0.0.1:8000.",
    )
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--chat-timeout", type=float, default=90.0)
    parser.add_argument(
        "--api-key",
        default=os.environ.get("COCKPIT_API_KEY") or os.environ.get("LOCAL_API_KEY") or "",
        help="Optional backend X-API-Key, default: COCKPIT_API_KEY or LOCAL_API_KEY.",
    )
    parser.add_argument(
        "--allow-non-api-only",
        action="store_true",
        help="Do not fail when the current operator config is not api_only.",
    )
    parser.add_argument(
        "--skip-chat",
        action="store_true",
        help="Only check health/config; avoids LLM/API calls.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_smoke(args)
    except Exception as exc:
        payload = {
            "ok": False,
            "error": str(exc),
            "checks": [],
        }
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    payload = {
        "ok": result.ok,
        "checks": result.checks,
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for check in result.checks:
            marker = "PASS" if check.get("ok") else "FAIL"
            print(f"[{marker}] {check.get('name')}: {check.get('detail')}")
        if not result.ok:
            print("\nFailures:", file=sys.stderr)
            for failure in result.failures:
                print(f"- {failure['name']}: {failure['detail']}", file=sys.stderr)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
