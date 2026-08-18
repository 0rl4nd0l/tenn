#!/usr/bin/env python3
"""Read-only DuckDB analysis over real-gold extraction eval artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "financial-engine_v2" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.asx_holdout_confidentiality import (  # noqa: E402
    DevelopmentAggregateResult,
)

DEFAULT_RESULTS_JSON = REPO_ROOT / "reports" / "extraction_real_eval_results.json"


def _require_duckdb() -> Any:
    try:
        import duckdb
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "duckdb is not installed. Install dev-only eval deps with "
            "`financial-engine_v2/.venv/bin/pip install -r financial-engine_v2/backend/requirements-dev.txt`."
        ) from exc
    return duckdb


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze real extraction eval JSON artifacts with in-memory DuckDB.",
    )
    parser.add_argument(
        "results_json",
        nargs="+",
        type=Path,
        default=[DEFAULT_RESULTS_JSON],
        help="One or more extraction_real_eval_results.json artifacts.",
    )
    parser.add_argument("--summary-path", type=Path, default=None)
    parser.add_argument(
        "--corpus-classification",
        choices=["non_holdout", "holdout"],
        required=True,
    )
    parser.add_argument(
        "--access-mode",
        choices=["development", "protected"],
        required=True,
    )
    parser.add_argument("--development-aggregate-json", type=Path, default=None)
    return parser.parse_args()


def _load_rows(
    paths: list[Path],
) -> tuple[list[tuple[Any, ...]], list[tuple[Any, ...]], list[tuple[Any, ...]]]:
    document_rows: list[tuple[Any, ...]] = []
    metric_rows: list[tuple[Any, ...]] = []
    trigger_rows: list[tuple[Any, ...]] = []
    for index, path in enumerate(paths, start=1):
        payload = json.loads(path.read_text(encoding="utf-8"))
        summary = (
            payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
        )
        run_stamp = summary.get("generated_at") or f"run{index}"
        run_id = f"{path.stem}:{run_stamp}"
        for document in payload.get("documents", []):
            metric_results = (
                document.get("metric_results")
                if isinstance(document.get("metric_results"), dict)
                else {}
            )
            wrong_count = 0
            missing_count = 0
            abstain_count = 0
            for metric_result in metric_results.values():
                status = str(metric_result.get("status") or "")
                if status == "wrong":
                    wrong_count += 1
                elif status == "missing":
                    missing_count += 1
                elif status == "abstain":
                    abstain_count += 1
            document_rows.append(
                (
                    run_id,
                    document.get("document_id"),
                    document.get("ticker"),
                    document.get("period_type"),
                    document.get("period_end"),
                    document.get("trust_outcome"),
                    document.get("expected_trust"),
                    bool(document.get("context_correct")),
                    document.get("extraction_status"),
                    wrong_count,
                    missing_count,
                    abstain_count,
                    wrong_count + missing_count + abstain_count,
                    len(document.get("context_mismatches") or []),
                )
            )
            for metric_name, metric_result in metric_results.items():
                metric_rows.append(
                    (
                        run_id,
                        document.get("document_id"),
                        document.get("ticker"),
                        document.get("period_type"),
                        document.get("trust_outcome"),
                        metric_name,
                        metric_result.get("status"),
                        metric_result.get("reason"),
                    )
                )
            for trigger in document.get("trust_triggers") or []:
                trigger_rows.append(
                    (
                        run_id,
                        document.get("document_id"),
                        document.get("ticker"),
                        document.get("period_type"),
                        document.get("trust_outcome"),
                        trigger,
                    )
                )
    return document_rows, metric_rows, trigger_rows


def _load_development_aggregate(paths: list[Path]) -> dict[str, Any] | None:
    aggregate: dict[str, Any] | None = None
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        try:
            current = DevelopmentAggregateResult.from_mapping(payload).to_dict()
        except ValueError:
            return None
        if aggregate is not None and current != aggregate:
            raise ValueError("development aggregate inputs differ")
        aggregate = current
    return aggregate


def _aggregate_markdown(aggregate: dict[str, Any]) -> str:
    rows = "\n".join(
        f"- {field}: {json.dumps(aggregate[field], sort_keys=True)}"
        for field in sorted(DevelopmentAggregateResult.ALLOWED_FIELDS)
    )
    return f"# Development Aggregate Result\n\n{rows}\n"


def _markdown_table(headers: list[str], rows: list[tuple[Any, ...]]) -> str:
    lines = [f"| {' | '.join(headers)} |", f"| {' | '.join(['---'] * len(headers))} |"]
    for row in rows:
        lines.append(f"| {' | '.join(str(value) for value in row)} |")
    return "\n".join(lines)


def main() -> int:
    args = _parse_args()
    aggregate = None
    if args.corpus_classification == "holdout" and args.access_mode != "protected":
        if args.development_aggregate_json is None:
            raise SystemExit(
                "--development-aggregate-json is required for public holdout analysis"
            )
        aggregate = DevelopmentAggregateResult.from_mapping(
            json.loads(args.development_aggregate_json.read_text(encoding="utf-8"))
        ).to_dict()
    else:
        aggregate = _load_development_aggregate(args.results_json)
    if aggregate is not None:
        summary = _aggregate_markdown(aggregate)
        if args.summary_path is not None:
            args.summary_path.parent.mkdir(parents=True, exist_ok=True)
            args.summary_path.write_text(summary, encoding="utf-8")
        print(summary)
        return 0
    duckdb = _require_duckdb()
    document_rows, metric_rows, trigger_rows = _load_rows(args.results_json)

    con = duckdb.connect(database=":memory:")
    con.execute(
        "create table documents (run_id varchar, document_id varchar, ticker varchar, period_type varchar, period_end varchar, trust_outcome varchar, expected_trust varchar, context_correct boolean, extraction_status varchar, wrong_count integer, missing_count integer, abstain_count integer, failed_metric_count integer, context_mismatch_count integer)"
    )
    con.execute(
        "create table metrics (run_id varchar, document_id varchar, ticker varchar, period_type varchar, trust_outcome varchar, metric_name varchar, status varchar, reason varchar)"
    )
    con.execute(
        "create table trust_triggers (run_id varchar, document_id varchar, ticker varchar, period_type varchar, trust_outcome varchar, trigger varchar)"
    )
    if document_rows:
        con.executemany(
            "insert into documents values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            document_rows,
        )
    if metric_rows:
        con.executemany(
            "insert into metrics values (?, ?, ?, ?, ?, ?, ?, ?)", metric_rows
        )
    if trigger_rows:
        con.executemany(
            "insert into trust_triggers values (?, ?, ?, ?, ?, ?)", trigger_rows
        )

    failure_rows = con.execute(
        "select metric_name, status, count(*) as failures from metrics where status <> 'correct' group by 1, 2 order by failures desc, metric_name, status"
    ).fetchall()
    metric_distribution_rows = con.execute(
        "select status, count(*) as count from metrics group by 1 order by count desc, status"
    ).fetchall()
    trust_distribution_rows = con.execute(
        "select trust_outcome, count(*) as count from documents group by 1 order by count desc, trust_outcome"
    ).fetchall()
    concern_rows = con.execute(
        "select d.document_id, coalesce(d.ticker, '-'), d.period_type, d.trust_outcome, d.expected_trust, d.failed_metric_count, d.context_mismatch_count, coalesce(string_agg(distinct case when m.status <> 'correct' then m.metric_name || ':' || m.status end, ', ' order by case when m.status <> 'correct' then m.metric_name || ':' || m.status end), '-') as failures from documents d left join metrics m on d.run_id = m.run_id and d.document_id = m.document_id where d.trust_outcome in ('abstain', 'quarantine') or d.failed_metric_count > 0 group by 1, 2, 3, 4, 5, 6, 7 order by d.failed_metric_count desc, d.context_mismatch_count desc, d.document_id"
    ).fetchall()
    cluster_rows = con.execute(
        "select coalesce(ticker, '-'), period_type, trust_outcome, count(*) as documents, sum(failed_metric_count) as failed_metrics from documents group by 1, 2, 3 order by failed_metrics desc, documents desc, 1, 2, 3"
    ).fetchall()
    trigger_summary_rows = con.execute(
        "select trigger, count(*) as count from trust_triggers group by 1 order by count desc, trigger"
    ).fetchall()
    pattern_rows = con.execute(
        "select period_type, trust_outcome, status, count(*) as count from metrics group by 1, 2, 3 order by period_type, trust_outcome, status"
    ).fetchall()

    lines = [
        "# Real Extraction Eval DuckDB Summary",
        "",
        f"- Inputs: {', '.join(str(path) for path in args.results_json)}",
        f"- Documents: {len(document_rows)}",
        f"- Metric rows: {len(metric_rows)}",
        "",
        "## Metrics That Fail Most",
        "",
        _markdown_table(
            ["metric", "status", "failures"], failure_rows or [("-", "-", 0)]
        ),
        "",
        "## Metric Outcome Distribution",
        "",
        _markdown_table(["status", "count"], metric_distribution_rows or [("-", 0)]),
        "",
        "## Document Trust Distribution",
        "",
        _markdown_table(["trust", "count"], trust_distribution_rows or [("-", 0)]),
        "",
        "## Most Failed Documents",
        "",
        _markdown_table(
            [
                "document",
                "ticker",
                "period",
                "trust",
                "expected",
                "failed_metrics",
                "context_mismatches",
                "failures",
            ],
            concern_rows or [("-", "-", "-", "-", "-", 0, 0, "-")],
        ),
        "",
        "## Failure Clusters By Ticker And Form",
        "",
        _markdown_table(
            ["ticker", "period", "trust", "documents", "failed_metrics"],
            cluster_rows or [("-", "-", "-", 0, 0)],
        ),
        "",
        "## Trust Trigger Summary",
        "",
        _markdown_table(["trigger", "count"], trigger_summary_rows or [("-", 0)]),
        "",
        "## Failure Patterns By Period And Trust",
        "",
        _markdown_table(
            ["period", "trust", "status", "count"], pattern_rows or [("-", "-", "-", 0)]
        ),
        "",
    ]
    summary = "\n".join(lines)
    if args.summary_path is not None:
        args.summary_path.parent.mkdir(parents=True, exist_ok=True)
        args.summary_path.write_text(summary, encoding="utf-8")
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
