#!/usr/bin/env python3
"""Read-only DuckDB analysis over real-gold extraction eval artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
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
    return parser.parse_args()


def _load_rows(
    paths: list[Path],
) -> tuple[list[tuple[Any, ...]], list[tuple[Any, ...]]]:
    document_rows: list[tuple[Any, ...]] = []
    metric_rows: list[tuple[Any, ...]] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        run_id = path.stem
        for document in payload.get("documents", []):
            document_rows.append(
                (
                    run_id,
                    document.get("document_id"),
                    document.get("period_type"),
                    document.get("period_end"),
                    document.get("trust_outcome"),
                    document.get("expected_trust"),
                    bool(document.get("context_correct")),
                    document.get("extraction_status"),
                )
            )
            for metric_name, metric_result in document.get(
                "metric_results", {}
            ).items():
                metric_rows.append(
                    (
                        run_id,
                        document.get("document_id"),
                        document.get("period_type"),
                        document.get("trust_outcome"),
                        metric_name,
                        metric_result.get("status"),
                        metric_result.get("reason"),
                    )
                )
    return document_rows, metric_rows


def _markdown_table(headers: list[str], rows: list[tuple[Any, ...]]) -> str:
    lines = [f"| {' | '.join(headers)} |", f"| {' | '.join(['---'] * len(headers))} |"]
    for row in rows:
        lines.append(f"| {' | '.join(str(value) for value in row)} |")
    return "\n".join(lines)


def main() -> int:
    args = _parse_args()
    duckdb = _require_duckdb()
    document_rows, metric_rows = _load_rows(args.results_json)

    con = duckdb.connect(database=":memory:")
    con.execute(
        "create table documents (run_id varchar, document_id varchar, period_type varchar, period_end varchar, trust_outcome varchar, expected_trust varchar, context_correct boolean, extraction_status varchar)"
    )
    con.execute(
        "create table metrics (run_id varchar, document_id varchar, period_type varchar, trust_outcome varchar, metric_name varchar, status varchar, reason varchar)"
    )
    if document_rows:
        con.executemany(
            "insert into documents values (?, ?, ?, ?, ?, ?, ?, ?)", document_rows
        )
    if metric_rows:
        con.executemany("insert into metrics values (?, ?, ?, ?, ?, ?, ?)", metric_rows)

    failure_rows = con.execute(
        "select metric_name, status, count(*) as failures from metrics where status <> 'correct' group by 1, 2 order by failures desc, metric_name, status"
    ).fetchall()
    concern_rows = con.execute(
        "select d.document_id, d.period_type, d.trust_outcome, d.expected_trust, coalesce(string_agg(distinct case when m.status <> 'correct' then m.metric_name || ':' || m.status end, ', ' order by case when m.status <> 'correct' then m.metric_name || ':' || m.status end), '-') as failures from documents d left join metrics m on d.run_id = m.run_id and d.document_id = m.document_id where d.trust_outcome in ('abstain', 'quarantine') or exists (select 1 from metrics mx where mx.run_id = d.run_id and mx.document_id = d.document_id and mx.status <> 'correct') group by 1, 2, 3, 4 order by d.trust_outcome desc, d.document_id"
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
        "## Abstain Or Quarantine Documents",
        "",
        _markdown_table(
            ["document", "period", "trust", "expected", "failures"],
            concern_rows or [("-", "-", "-", "-", "-")],
        ),
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
