#!/usr/bin/env python3
"""Dispatch local news memo extraction for articles missing persisted memos."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from load_news_to_qdrant import (  # noqa: E402
    DEFAULT_NEWS_ARTICLES_DB,
    _read_news_memo_source_ids,
    _source_id_for_article,
    build_memo_coverage_diagnostics,
    build_news_projection_target,
    dispatch_news_memos,
    resolve_news_memo_max_article_chars,
    write_summary_json,
)
from news_pipeline.utils import now_utc_iso  # noqa: E402

DEFAULT_MEMO_DISPATCH_BATCH_SIZE = 25


def _eligible_for_memo(article: dict[str, Any]) -> bool:
    return bool(_source_id_for_article(article) and str(article.get("text") or "").strip())


def _select_articles_for_dispatch(
    articles: list[dict[str, Any]],
    *,
    memos_path: str | Path | None,
    force: bool,
    limit: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    memo_state = _read_news_memo_source_ids(memos_path)
    persisted_ids = set(memo_state.get("source_ids") or set())
    eligible = [article for article in articles if _eligible_for_memo(article)]
    if force:
        candidates = eligible
    else:
        candidates = [
            article
            for article in eligible
            if _source_id_for_article(article) not in persisted_ids
        ]
    if limit > 0:
        candidates = candidates[:limit]
    return candidates, {
        "eligible": len(eligible),
        "persisted": len(
            {
                _source_id_for_article(article)
                for article in eligible
                if _source_id_for_article(article) in persisted_ids
            }
        ),
        "selected": len(candidates),
        "limit": int(limit),
        "force": bool(force),
        "memos_path": str(memo_state.get("path") or ""),
        "memos_file_exists": bool(memo_state.get("exists")),
        "read_errors": int(memo_state.get("read_errors") or 0),
    }


def _sum_int(results: list[dict[str, Any]], key: str) -> int:
    return sum(int(result.get(key) or 0) for result in results)


def _can_continue_after_observed_task_failure(result: dict[str, Any]) -> bool:
    """Continue bounded batches only when failures are fully observed per task."""
    if result.get("status") in {"complete", "empty"}:
        return True
    if not bool(result.get("completion_observable")):
        return False
    if int(result.get("dispatch_failed") or 0) > 0:
        return False
    if int(result.get("tasks_pending") or 0) > 0:
        return False
    if int(result.get("tasks_unobserved") or 0) > 0:
        return False
    return int(result.get("tasks_failed") or 0) > 0


def _dispatch_selected_articles(
    selected_articles: list[dict[str, Any]],
    *,
    memos_path: str | Path | None,
    wait_for_completion: bool,
    wait_timeout_seconds: float,
    poll_interval_seconds: float,
    force_dispatch: bool,
    max_article_chars: int,
    dispatch_batch_size: int,
) -> dict[str, Any]:
    if not selected_articles:
        return dispatch_news_memos(
            [],
            memos_path=memos_path,
            wait_for_completion=wait_for_completion,
            wait_timeout_seconds=wait_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
            force_dispatch=force_dispatch,
            max_article_chars=max_article_chars,
        )

    if not wait_for_completion or dispatch_batch_size <= 0:
        return dispatch_news_memos(
            selected_articles,
            memos_path=memos_path,
            wait_for_completion=wait_for_completion,
            wait_timeout_seconds=wait_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
            force_dispatch=force_dispatch,
            max_article_chars=max_article_chars,
        )

    batch_results: list[dict[str, Any]] = []
    for start in range(0, len(selected_articles), dispatch_batch_size):
        batch = selected_articles[start : start + dispatch_batch_size]
        result = dispatch_news_memos(
            batch,
            memos_path=memos_path,
            wait_for_completion=True,
            wait_timeout_seconds=wait_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
            force_dispatch=force_dispatch,
            max_article_chars=max_article_chars,
        )
        batch_results.append(result)
        if not _can_continue_after_observed_task_failure(result):
            break

    completed_all = len(batch_results) * dispatch_batch_size >= len(selected_articles)
    degraded = any(
        result.get("status") not in {"complete", "empty"} for result in batch_results
    )
    status = "degraded" if degraded else ("complete" if completed_all else "partial")
    return {
        "status": status,
        "batched": True,
        "batch_size": dispatch_batch_size,
        "batches_attempted": len(batch_results),
        "batches_total": (len(selected_articles) + dispatch_batch_size - 1)
        // dispatch_batch_size,
        "batches_continued_after_observed_failures": sum(
            1
            for result in batch_results[:-1]
            if result.get("status") not in {"complete", "empty"}
            and _can_continue_after_observed_task_failure(result)
        ),
        "eligible": _sum_int(batch_results, "eligible"),
        "skipped": _sum_int(batch_results, "skipped"),
        "dispatched": _sum_int(batch_results, "dispatched"),
        "dispatch_failed": _sum_int(batch_results, "dispatch_failed"),
        "dispatch_candidates": _sum_int(batch_results, "dispatch_candidates"),
        "already_persisted_skipped": _sum_int(
            batch_results, "already_persisted_skipped"
        ),
        "persisted_before_dispatch": _sum_int(
            batch_results, "persisted_before_dispatch"
        ),
        "persisted_after_dispatch": _sum_int(
            batch_results, "persisted_after_dispatch"
        ),
        "missing_after_dispatch": _sum_int(batch_results, "missing_after_dispatch"),
        "tasks_observed": _sum_int(batch_results, "tasks_observed"),
        "tasks_completed": _sum_int(batch_results, "tasks_completed"),
        "tasks_failed": _sum_int(batch_results, "tasks_failed"),
        "tasks_pending": _sum_int(batch_results, "tasks_pending"),
        "tasks_unobserved": _sum_int(batch_results, "tasks_unobserved"),
        "task_ids_count": _sum_int(batch_results, "task_ids_count"),
        "dispatch_failed_samples": [
            sample
            for result in batch_results
            for sample in list(result.get("dispatch_failed_samples") or [])[:10]
        ][:10],
        "task_failure_samples": [
            sample
            for result in batch_results
            for sample in list(result.get("task_failure_samples") or [])[:10]
        ][:10],
        "completion_observable": all(
            bool(result.get("completion_observable")) for result in batch_results
        ),
        "wait_requested": True,
        "wait_timeout_seconds": wait_timeout_seconds,
        "wait_poll_interval_seconds": poll_interval_seconds,
        "force_dispatch": force_dispatch,
        "max_article_chars": max_article_chars,
        "memos_path": str(batch_results[-1].get("memos_path") or "")
        if batch_results
        else "",
        "memos_file_exists": bool(batch_results[-1].get("memos_file_exists"))
        if batch_results
        else False,
        "read_errors": _sum_int(batch_results, "read_errors"),
        "batch_results": batch_results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Backfill missing local news memos without touching Qdrant or SQLite fallback."
    )
    parser.add_argument("--db-path", default=str(DEFAULT_NEWS_ARTICLES_DB))
    parser.add_argument(
        "--since-hours",
        type=int,
        default=36,
        help="Eligible article window; 0 means all articles",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum memo tasks to dispatch; 0 means no limit",
    )
    parser.add_argument(
        "--memo-diagnostics-path",
        default="",
        help="Host-readable news_memos.jsonl path for coverage and skip checks",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Dispatch even when an article already has a persisted memo",
    )
    parser.add_argument(
        "--memo-max-article-chars",
        type=int,
        default=None,
        help=(
            "Maximum article characters sent to each memo task "
            "(default: NEWS_MEMO_MAX_ARTICLE_CHARS or 5000)"
        ),
    )
    parser.add_argument(
        "--wait-for-memos",
        action="store_true",
        help="Wait for dispatched Celery tasks with a bounded timeout",
    )
    parser.add_argument(
        "--memo-wait-timeout-seconds",
        type=float,
        default=120.0,
        help="Maximum seconds to wait when --wait-for-memos is set",
    )
    parser.add_argument(
        "--memo-wait-poll-interval-seconds",
        type=float,
        default=2.0,
        help="Polling interval while waiting for memo completion",
    )
    parser.add_argument(
        "--dispatch-batch-size",
        type=int,
        default=DEFAULT_MEMO_DISPATCH_BATCH_SIZE,
        help=(
            "Maximum memo tasks dispatched before waiting for completion when "
            "--wait-for-memos is set; 0 disables batching"
        ),
    )
    parser.add_argument("--summary-json", default="")
    args = parser.parse_args(argv)

    if int(args.limit) < 0:
        parser.error("--limit must be >= 0")
    if int(args.dispatch_batch_size) < 0:
        parser.error("--dispatch-batch-size must be >= 0")
    if float(args.memo_wait_timeout_seconds) < 0:
        parser.error("--memo-wait-timeout-seconds must be >= 0")
    if float(args.memo_wait_poll_interval_seconds) <= 0:
        parser.error("--memo-wait-poll-interval-seconds must be > 0")
    try:
        memo_max_article_chars = resolve_news_memo_max_article_chars(
            args.memo_max_article_chars
        )
    except ValueError as exc:
        parser.error(str(exc))

    since = int(args.since_hours) if int(args.since_hours) > 0 else None
    memos_path = args.memo_diagnostics_path or None
    target = build_news_projection_target(args.db_path, since_hours=since)
    articles = list(target["articles"])
    coverage_before = build_memo_coverage_diagnostics(articles, memos_path=memos_path)
    selected_articles, selection = _select_articles_for_dispatch(
        articles,
        memos_path=memos_path,
        force=bool(args.force),
        limit=int(args.limit),
    )
    memo_result = _dispatch_selected_articles(
        selected_articles,
        memos_path=memos_path,
        wait_for_completion=bool(args.wait_for_memos),
        wait_timeout_seconds=float(args.memo_wait_timeout_seconds),
        poll_interval_seconds=float(args.memo_wait_poll_interval_seconds),
        force_dispatch=bool(args.force),
        max_article_chars=memo_max_article_chars,
        dispatch_batch_size=int(args.dispatch_batch_size),
    )
    coverage_after = build_memo_coverage_diagnostics(articles, memos_path=memos_path)
    summary = {
        "generated_at_utc": now_utc_iso(),
        "db_path": str(Path(args.db_path).expanduser()),
        "since_hours": int(args.since_hours),
        "coverage_before": coverage_before,
        "selection": selection,
        "memo_extraction": memo_result,
        "coverage_after": coverage_after,
    }
    if args.summary_json:
        write_summary_json(args.summary_json, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if bool(args.wait_for_memos) and memo_result.get("status") not in {"complete", "empty"}:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
