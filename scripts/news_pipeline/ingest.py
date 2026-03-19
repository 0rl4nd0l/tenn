from __future__ import annotations

import datetime as dt
import itertools
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from .db import NewsArticleStore
from .entity_linker import EntityLinker
from .providers.base import ProviderClient
from .relevance import score_article_relevance
from .utils import day_windows, now_utc_iso

# Keys passed to store.increment_run_counters and store.record_window (stats may also contain last_error).
RUN_COUNTER_KEYS = ("fetched", "inserted", "deduped", "rejected", "errors")


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
) -> Dict[str, Any]:
    """Process one provider time window. Status 'completed' means no fetch/parse exceptions;
    empty windows are recorded as provider_empty_response in failures but do not set status to partial_failed."""
    stats: Dict[str, Any] = {"fetched": 0, "inserted": 0, "deduped": 0, "rejected": 0, "errors": 0}
    try:
        rows = provider.fetch_window(
            window_start_utc=window_start_utc,
            window_end_utc=window_end_utc,
            tickers=tickers,
        )
    except Exception as exc:
        stats["errors"] += 1
        err_msg = str(exc)
        stats["last_error"] = err_msg
        provider_diag = getattr(provider, "last_fetch_diagnostics", None)
        failure_payload: Dict[str, Any] = {
            "provider": provider.name,
            "window_start_utc": window_start_utc,
            "window_end_utc": window_end_utc,
            "error": err_msg,
        }
        if isinstance(provider_diag, dict) and provider_diag:
            failure_payload["provider_diagnostics"] = provider_diag
        failures.add(
            "provider_fetch_error",
            failure_payload,
        )
        return stats

    if not rows:
        provider_diag = getattr(provider, "last_fetch_diagnostics", None)
        empty_payload: Dict[str, Any] = {
            "provider": provider.name,
            "window_start_utc": window_start_utc,
            "window_end_utc": window_end_utc,
        }
        if isinstance(provider_diag, dict) and provider_diag:
            empty_payload["provider_diagnostics"] = provider_diag
        failures.add(
            "provider_empty_response",
            empty_payload,
        )
        print(f"[ingest] {provider.name} window {window_start_utc}..{window_end_utc} items=0 (empty)", flush=True)
        return stats

    print(f"[ingest] {provider.name} window {window_start_utc}..{window_end_utc} items={len(rows)}", flush=True)
    fetched_at = now_utc_iso()
    progress_interval = 50
    for i, item in enumerate(rows):
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
            # When lane is high_precision but only high_recall links exist, we still persist those links
            # and keep the article; entity_link_filtered is recorded for observability only.
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
            store.replace_article_relevance(
                upsert.article_id,
                score_article_relevance(
                    article_id=upsert.article_id,
                    title=candidate.title,
                    description=candidate.description,
                    body=candidate.body,
                    links=links,
                ),
            )
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

        if (i + 1) % progress_interval == 0:
            print(f"[ingest] {provider.name} progress {i + 1}/{len(rows)} inserted={stats['inserted']} deduped={stats['deduped']} rejected={stats['rejected']} errors={stats['errors']}", flush=True)

    print(f"[ingest] {provider.name} done fetched={stats['fetched']} inserted={stats['inserted']} deduped={stats['deduped']} rejected={stats['rejected']} errors={stats['errors']}", flush=True)
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
    max_days: int | None = None,
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
    windows_iter = day_windows(from_day, to_day)
    if max_days is not None and max_days > 0:
        windows_iter = itertools.islice(windows_iter, max_days)
    try:
        for window_start_utc, window_end_utc in windows_iter:
            if (window_start_utc, window_end_utc) in completed:
                continue
            day_label = (window_start_utc or "")[:10] or "?"
            print(f"[backfill] {provider.name} processing day {day_label} ...", flush=True)
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
            counter_kw = {k: int(stats.get(k, 0)) for k in RUN_COUNTER_KEYS}
            store.increment_run_counters(
                rid,
                fetched=counter_kw["fetched"],
                inserted=counter_kw["inserted"],
                deduped=counter_kw["deduped"],
                rejected=counter_kw["rejected"],
                errors=counter_kw["errors"],
            )
            store.record_window(
                run_id=rid,
                provider=provider.name,
                window_start_utc=window_start_utc,
                window_end_utc=window_end_utc,
                status=_window_status_from_stats(stats),
                fetched=counter_kw["fetched"],
                inserted=counter_kw["inserted"],
                deduped=counter_kw["deduped"],
                rejected=counter_kw["rejected"],
                errors=counter_kw["errors"],
            )
            f, i, d, r, e = (
                stats.get("fetched", 0),
                stats.get("inserted", 0),
                stats.get("deduped", 0),
                stats.get("rejected", 0),
                stats.get("errors", 0),
            )
            line = f"[backfill] {provider.name} {day_label} fetched={f} inserted={i} deduped={d} rejected={r} errors={e}"
            if e and stats.get("last_error"):
                line += f" | error={stats.get('last_error')!r}"
            print(line, flush=True)
    except BaseException:
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
        counter_kw = {k: int(stats.get(k, 0)) for k in RUN_COUNTER_KEYS}
        store.increment_run_counters(
            rid,
            fetched=counter_kw["fetched"],
            inserted=counter_kw["inserted"],
            deduped=counter_kw["deduped"],
            rejected=counter_kw["rejected"],
            errors=counter_kw["errors"],
        )
        store.record_window(
            run_id=rid,
            provider=provider.name,
            window_start_utc=window_start_utc,
            window_end_utc=window_end_utc,
            status=_window_status_from_stats(stats),
            fetched=counter_kw["fetched"],
            inserted=counter_kw["inserted"],
            deduped=counter_kw["deduped"],
            rejected=counter_kw["rejected"],
            errors=counter_kw["errors"],
        )
    except BaseException:
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
        counter_kw = {k: int(stats.get(k, 0)) for k in RUN_COUNTER_KEYS}
        store.increment_run_counters(
            rid,
            fetched=counter_kw["fetched"],
            inserted=counter_kw["inserted"],
            deduped=counter_kw["deduped"],
            rejected=counter_kw["rejected"],
            errors=counter_kw["errors"],
        )
        store.record_window(
            run_id=rid,
            provider=provider.name,
            window_start_utc=window_start_utc,
            window_end_utc=window_end_utc,
            status=_window_status_from_stats(stats),
            fetched=counter_kw["fetched"],
            inserted=counter_kw["inserted"],
            deduped=counter_kw["deduped"],
            rejected=counter_kw["rejected"],
            errors=counter_kw["errors"],
        )
    except BaseException:
        store.finish_provider_run(rid, "failed")
        raise
    store.finish_provider_run(rid, "success" if run_errors <= 0 else "partial_failed")
    return rid, failures
