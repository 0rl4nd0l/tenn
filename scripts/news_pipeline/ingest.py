from __future__ import annotations

import datetime as dt
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from .db import NewsArticleStore
from .entity_linker import EntityLinker
from .providers.base import ProviderClient
from .utils import day_windows, now_utc_iso, parse_datetime_utc


REQUIRED_FAILURE_BUCKETS = (
    "provider_empty_response",
    "missing_published_at",
    "invalid_published_at",
    "dedupe_url",
    "dedupe_exact",
    "dedupe_near",
    "entity_link_filtered",
    "chunk_build_skipped",
)


@dataclass
class FailureBucketTracker:
    counts: Counter[str] = field(default_factory=Counter)
    samples: Dict[str, List[Dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    sample_limit: int = 5

    def add(self, reason: str, payload: Dict[str, Any]) -> None:
        key = str(reason or "unknown").strip() or "unknown"
        self.counts[key] += 1
        if len(self.samples[key]) < int(max(1, self.sample_limit)):
            self.samples[key].append(payload)

    def as_dict(self) -> Dict[str, Any]:
        out_counts = {key: int(self.counts.get(key, 0)) for key in sorted(set(self.counts) | set(REQUIRED_FAILURE_BUCKETS))}
        return {
            "counts": out_counts,
            "samples": {key: self.samples.get(key, []) for key in sorted(out_counts)},
        }

    def write_sample_files(self, out_dir: Path) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        for reason in sorted(set(self.counts) | set(REQUIRED_FAILURE_BUCKETS)):
            rows = self.samples.get(reason, [])
            path = out_dir / f"{reason}.jsonl"
            with path.open("w", encoding="utf-8") as fh:
                for row in rows:
                    fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _window_status_from_stats(stats: Dict[str, int]) -> str:
    if int(stats.get("errors", 0)) > 0:
        return "failed"
    return "completed"


def _process_provider_window(
    *,
    store: NewsArticleStore,
    linker: EntityLinker,
    provider: ProviderClient,
    run_id: str,
    lane: str,
    window_start_utc: str,
    window_end_utc: str,
    tickers: Sequence[str],
    failures: FailureBucketTracker,
) -> Dict[str, int]:
    stats = {"fetched": 0, "inserted": 0, "deduped": 0, "rejected": 0, "errors": 0}
    try:
        rows = provider.fetch_window(
            window_start_utc=window_start_utc,
            window_end_utc=window_end_utc,
            tickers=tickers,
        )
    except Exception as exc:
        stats["errors"] += 1
        failures.add(
            "provider_fetch_error",
            {
                "provider": provider.name,
                "window_start_utc": window_start_utc,
                "window_end_utc": window_end_utc,
                "error": str(exc),
            },
        )
        return stats

    if not rows:
        failures.add(
            "provider_empty_response",
            {"provider": provider.name, "window_start_utc": window_start_utc, "window_end_utc": window_end_utc},
        )
        return stats

    fetched_at = now_utc_iso()
    for item in rows:
        stats["fetched"] += 1
        try:
            parsed = provider.parse_item(item, fetched_at_utc=fetched_at)
        except Exception as exc:
            stats["errors"] += 1
            failures.add(
                "provider_parse_error",
                {
                    "provider": provider.name,
                    "error": str(exc),
                    "provider_item_id": str(item.get("id") or item.get("news_id") or ""),
                },
            )
            continue

        if parsed.candidate is None:
            reason = str(parsed.reject_reason or "rejected")
            stats["rejected"] += 1
            provider_item_id = str(item.get("id") or item.get("news_id") or item.get("guid") or "")
            url = str(item.get("url") or item.get("link") or "")
            store.reject_item(
                run_id=run_id,
                provider=provider.name,
                provider_item_id=provider_item_id,
                url=url,
                reason=reason,
                diagnostics=dict(parsed.diagnostics or {}),
                fetched_at_utc=fetched_at,
            )
            failures.add(
                reason,
                {
                    "provider": provider.name,
                    "provider_item_id": provider_item_id,
                    "url": url,
                    "diagnostics": dict(parsed.diagnostics or {}),
                },
            )
            continue

        candidate = parsed.candidate
        try:
            upsert = store.upsert_article(candidate, lane=lane)
            store.insert_article_version(upsert.article_id, candidate)
            links = linker.link_article(
                article_id=upsert.article_id,
                title=candidate.title,
                description=candidate.description,
                body=candidate.body,
                published_at_utc=candidate.published_at_utc,
            )
            if lane == "high_precision" and not [lnk for lnk in links if lnk.lane == "high_precision"]:
                failures.add(
                    "entity_link_filtered",
                    {
                        "provider": provider.name,
                        "article_id": upsert.article_id,
                        "title": candidate.title,
                        "url": candidate.canonical_url,
                    },
                )
            store.replace_entity_links(upsert.article_id, links)
        except Exception as exc:
            stats["errors"] += 1
            stats["rejected"] += 1
            store.reject_item(
                run_id=run_id,
                provider=provider.name,
                provider_item_id=candidate.provider_item_id,
                url=candidate.canonical_url,
                reason="ingest_error",
                diagnostics={"error": str(exc)},
                fetched_at_utc=fetched_at,
            )
            failures.add(
                "ingest_error",
                {
                    "provider": provider.name,
                    "provider_item_id": candidate.provider_item_id,
                    "url": candidate.canonical_url,
                    "error": str(exc),
                },
            )
            continue

        if upsert.inserted:
            stats["inserted"] += 1
        else:
            stats["deduped"] += 1
            if upsert.dedupe_reason:
                failures.add(
                    upsert.dedupe_reason,
                    {
                        "provider": provider.name,
                        "article_id": upsert.article_id,
                        "url": candidate.canonical_url,
                        "provider_item_id": candidate.provider_item_id,
                    },
                )

    return stats


def run_provider_backfill(
    *,
    store: NewsArticleStore,
    linker: EntityLinker,
    provider: ProviderClient,
    lane: str,
    tickers: Sequence[str],
    from_day: str,
    to_day: str,
    resume: bool,
    run_id: str = "",
) -> Tuple[str, FailureBucketTracker]:
    params = {
        "lane": lane,
        "tickers_count": len(tickers),
        "from": from_day,
        "to": to_day,
        "resume": bool(resume),
    }
    rid = store.start_provider_run(provider.name, "backfill", params=params, run_id=run_id)
    completed = store.completed_windows(rid, provider.name) if resume else set()
    failures = FailureBucketTracker()
    run_errors = 0
    try:
        for window_start_utc, window_end_utc in day_windows(from_day, to_day):
            if (window_start_utc, window_end_utc) in completed:
                continue
            stats = _process_provider_window(
                store=store,
                linker=linker,
                provider=provider,
                run_id=rid,
                lane=lane,
                window_start_utc=window_start_utc,
                window_end_utc=window_end_utc,
                tickers=tickers,
                failures=failures,
            )
            run_errors += int(stats.get("errors", 0))
            store.increment_run_counters(rid, **stats)
            store.record_window(
                run_id=rid,
                provider=provider.name,
                window_start_utc=window_start_utc,
                window_end_utc=window_end_utc,
                status=_window_status_from_stats(stats),
                **stats,
            )
    except Exception:
        store.finish_provider_run(rid, "failed")
        raise
    store.finish_provider_run(rid, "success" if run_errors <= 0 else "partial_failed")
    return rid, failures


def run_provider_daily(
    *,
    store: NewsArticleStore,
    linker: EntityLinker,
    provider: ProviderClient,
    lane: str,
    tickers: Sequence[str],
    since_hours: int,
    run_id: str = "",
) -> Tuple[str, FailureBucketTracker]:
    now = dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0)
    start = now - dt.timedelta(hours=int(max(1, since_hours)))
    window_start_utc = start.isoformat().replace("+00:00", "Z")
    window_end_utc = now.isoformat().replace("+00:00", "Z")

    params = {
        "lane": lane,
        "tickers_count": len(tickers),
        "since_hours": int(since_hours),
        "window_start_utc": window_start_utc,
        "window_end_utc": window_end_utc,
    }
    rid = store.start_provider_run(provider.name, "daily", params=params, run_id=run_id)
    failures = FailureBucketTracker()
    run_errors = 0
    try:
        stats = _process_provider_window(
            store=store,
            linker=linker,
            provider=provider,
            run_id=rid,
            lane=lane,
            window_start_utc=window_start_utc,
            window_end_utc=window_end_utc,
            tickers=tickers,
            failures=failures,
        )
        run_errors += int(stats.get("errors", 0))
        store.increment_run_counters(rid, **stats)
        store.record_window(
            run_id=rid,
            provider=provider.name,
            window_start_utc=window_start_utc,
            window_end_utc=window_end_utc,
            status=_window_status_from_stats(stats),
            **stats,
        )
    except Exception:
        store.finish_provider_run(rid, "failed")
        raise
    store.finish_provider_run(rid, "success" if run_errors <= 0 else "partial_failed")
    return rid, failures


def run_provider_probe(
    *,
    store: NewsArticleStore,
    linker: EntityLinker,
    provider: ProviderClient,
    lane: str,
    tickers: Sequence[str],
    window_days: int,
    run_id: str = "",
) -> Tuple[str, FailureBucketTracker]:
    now = dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0)
    start = now - dt.timedelta(days=int(max(1, window_days)))
    window_start_utc = start.isoformat().replace("+00:00", "Z")
    window_end_utc = now.isoformat().replace("+00:00", "Z")
    params = {
        "lane": lane,
        "tickers_count": len(tickers),
        "window_days": int(window_days),
        "window_start_utc": window_start_utc,
        "window_end_utc": window_end_utc,
    }
    rid = store.start_provider_run(provider.name, "probe", params=params, run_id=run_id)
    failures = FailureBucketTracker()
    run_errors = 0
    try:
        stats = _process_provider_window(
            store=store,
            linker=linker,
            provider=provider,
            run_id=rid,
            lane=lane,
            window_start_utc=window_start_utc,
            window_end_utc=window_end_utc,
            tickers=tickers,
            failures=failures,
        )
        run_errors += int(stats.get("errors", 0))
        store.increment_run_counters(rid, **stats)
        store.record_window(
            run_id=rid,
            provider=provider.name,
            window_start_utc=window_start_utc,
            window_end_utc=window_end_utc,
            status=_window_status_from_stats(stats),
            **stats,
        )
    except Exception:
        store.finish_provider_run(rid, "failed")
        raise
    store.finish_provider_run(rid, "success" if run_errors <= 0 else "partial_failed")
    return rid, failures
