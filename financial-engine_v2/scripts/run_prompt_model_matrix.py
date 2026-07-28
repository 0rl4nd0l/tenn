"""Run the real-gold extraction eval across a matrix of (prompt_variant × model) cells.

Posts to `/api/extraction-eval/real-gold` once per cell and aggregates the
per-cell summaries into a single JSON report.

The outer loop iterates over *models* and the inner loop over *prompt
variants*. This model-major ordering matches the llama.cpp router mode
(`--models-max 1`): only one GGUF is loaded at a time, so keeping the model
pinned across successive variants avoids repeated VRAM swaps.

Usage:

    python scripts/run_prompt_model_matrix.py \
        --prompt-variants default \
        --models qwen2.5-14b-instruct,qwen3-30b-a3b-instruct \
        --limit 3 \
        --out reports/prompt_model_matrix_$(date +%Y%m%d_%H%M%S).json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
ROOT_SCRIPTS = REPO_ROOT.parent / "scripts"
if str(ROOT_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(ROOT_SCRIPTS))
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from _run_metadata import build_run_metadata  # noqa: E402
from app.services.asx_holdout_confidentiality import (  # noqa: E402
    DevelopmentAggregateResult,
)


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT_S = 60 * 60  # real-gold extraction can take a long time


def _parse_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run prompt×model extraction eval matrix.",
    )
    parser.add_argument(
        "--prompt-variants",
        required=True,
        help=(
            "Comma-separated prompt bundle ids registered with prompt_registry. "
            "Use 'default' for the canonical bundle."
        ),
    )
    parser.add_argument(
        "--models",
        required=True,
        help=(
            "Comma-separated llama.cpp model ids, e.g. "
            "'qwen2.5-14b-instruct,qwen3-30b-a3b-instruct'. Each id becomes the "
            "model_override for one outer loop iteration."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Per-cell document limit forwarded as RealGoldEvalRequest.limit (0 = all).",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.01,
        help="Numeric tolerance forwarded to the eval endpoint.",
    )
    parser.add_argument(
        "--method",
        default="auto",
        help="Extraction method passed to the endpoint (auto|docling|pymupdf|anthropic).",
    )
    parser.add_argument(
        "--strict-method",
        action="store_true",
        help="Forward strict_method=True to the endpoint (no parser fallback).",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Backend base URL (default: {DEFAULT_BASE_URL}).",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("LLM_API_KEY", ""),
        help="API key for the backend (defaults to $LLM_API_KEY).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_S,
        help=f"HTTP timeout per cell in seconds (default: {DEFAULT_TIMEOUT_S}).",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan the matrix and print the cells without calling the endpoint.",
    )
    parser.add_argument(
        "--corpus-classification",
        choices=["non_holdout", "holdout"],
        default=None,
    )
    parser.add_argument("--access-mode", default=None)
    parser.add_argument("--development-aggregate-json", type=Path, default=None)
    return parser


def _run_cell(
    client: httpx.Client,
    *,
    base_url: str,
    api_key: str,
    prompt_variant_id: str,
    model_override: str,
    limit: int,
    tolerance: float,
    method: str,
    strict_method: bool,
    corpus_classification: str | None = None,
    access_mode: str | None = None,
    development_aggregate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "limit": limit,
        "tolerance": tolerance,
        "method": method,
        "strict_method": strict_method,
        "prompt_variant_id": prompt_variant_id,
        "model_override": model_override,
    }
    if corpus_classification is not None:
        payload["corpus_classification"] = corpus_classification
    if access_mode is not None:
        payload["access_mode"] = access_mode
    if development_aggregate is not None:
        payload["development_aggregate"] = development_aggregate
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key

    start = time.monotonic()
    response = client.post(
        f"{base_url.rstrip('/')}/api/extraction-eval/real-gold",
        headers=headers,
        json=payload,
    )
    elapsed_s = time.monotonic() - start

    try:
        response.raise_for_status()
        body = response.json()
        error: str | None = None
    except httpx.HTTPStatusError as exc:
        body = {"detail": response.text}
        error = f"HTTP {response.status_code}: {exc}"
    except json.JSONDecodeError as exc:
        body = {"detail": response.text[:2000]}
        error = f"non-JSON response: {exc}"

    if corpus_classification == "holdout" and access_mode != "protected":
        return DevelopmentAggregateResult.from_mapping(
            development_aggregate or {}
        ).to_dict()
    if isinstance(body, dict):
        try:
            return DevelopmentAggregateResult.from_mapping(body).to_dict()
        except ValueError:
            pass
    return {
        "prompt_variant_id": prompt_variant_id,
        "model_override": model_override,
        "request": payload,
        "http_status": response.status_code,
        "elapsed_s": round(elapsed_s, 3),
        "error": error,
        "summary": (body or {}).get("summary") if isinstance(body, dict) else None,
        "documents": (body or {}).get("documents") if isinstance(body, dict) else None,
        "raw": body if error else None,
    }


def main() -> int:
    args = _build_arg_parser().parse_args()

    variants = _parse_csv(args.prompt_variants)
    models = _parse_csv(args.models)
    development_aggregate = (
        json.loads(args.development_aggregate_json.read_text(encoding="utf-8"))
        if args.development_aggregate_json is not None
        else None
    )
    holdout_public = (
        args.corpus_classification == "holdout" and args.access_mode != "protected"
    )
    if not variants:
        raise SystemExit("--prompt-variants produced an empty list")
    if not models:
        raise SystemExit("--models produced an empty list")

    # Model-major ordering: outer=model, inner=variant. Keeps the router pinned
    # to one GGUF across all variants for that model.
    cells = [(model, variant) for model in models for variant in variants]

    plan = {
        "started_at": _utc_now(),
        "run_metadata": build_run_metadata(REPO_ROOT, __file__),
        "base_url": args.base_url,
        "models": models,
        "prompt_variants": variants,
        "cell_count": len(cells),
        "settings": {
            "limit": args.limit,
            "tolerance": args.tolerance,
            "method": args.method,
            "strict_method": bool(args.strict_method),
            "timeout_s": args.timeout,
        },
    }

    if args.dry_run:
        if holdout_public:
            aggregate = DevelopmentAggregateResult.from_mapping(
                development_aggregate or {}
            ).to_dict()
            print(json.dumps(aggregate, indent=2, sort_keys=True))
            return 0
        print(json.dumps({**plan, "cells_planned": cells}, indent=2))
        return 0

    report_path = Path(args.out).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    with httpx.Client(timeout=args.timeout) as client:
        for idx, (model, variant) in enumerate(cells, start=1):
            if not holdout_public:
                print(
                    f"[{idx}/{len(cells)}] model={model} variant={variant} ...",
                    flush=True,
                )
            cell_result = _run_cell(
                client,
                base_url=args.base_url,
                api_key=args.api_key,
                prompt_variant_id=variant,
                model_override=model,
                limit=args.limit,
                tolerance=args.tolerance,
                method=args.method,
                strict_method=bool(args.strict_method),
                corpus_classification=args.corpus_classification,
                access_mode=args.access_mode,
                development_aggregate=development_aggregate,
            )
            try:
                aggregate = DevelopmentAggregateResult.from_mapping(cell_result)
            except ValueError:
                aggregate = None
            if aggregate is not None:
                report_path.write_text(
                    json.dumps(aggregate.to_dict(), indent=2, sort_keys=True),
                    encoding="utf-8",
                )
                print(json.dumps(aggregate.to_dict(), sort_keys=True))
                return 0
            results.append(cell_result)

            # Incremental save — each cell is expensive; never lose a completed one.
            partial_report = {
                **plan,
                "finished_at": None,
                "completed_cells": idx,
                "cells": results,
            }
            report_path.write_text(
                json.dumps(partial_report, indent=2, default=str),
                encoding="utf-8",
            )

    final_report = {
        **plan,
        "finished_at": _utc_now(),
        "completed_cells": len(results),
        "cells": results,
    }
    report_path.write_text(
        json.dumps(final_report, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"Matrix report written to: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
