from __future__ import annotations

import json
import secrets
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .models import ArticleCandidate, ArticleRelevance, EntityLink, UpsertResult
from .relevance import serialize_ticker_relevance
from .utils import (
    compute_exact_hash,
    compute_near_hash,
    now_utc_iso,
    parse_datetime_utc,
    sha1_hex,
    sha256_hex,
)

PROVIDER_PRIORITY = {
    "eodhd": 30,
    "gdelt": 20,
    "worldmonitor": 15,
    "rss": 10,
}


class NewsArticleStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA synchronous = NORMAL")
        self.initialize()

    def close(self) -> None:
        self.conn.close()

    def initialize(self) -> None:
        cur = self.conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS articles (
                article_id TEXT PRIMARY KEY,
                canonical_url TEXT,
                url_hash TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                body TEXT,
                source_name TEXT NOT NULL DEFAULT '',
                language TEXT NOT NULL DEFAULT '',
                published_at_utc TEXT NOT NULL,
                fetched_at_utc TEXT NOT NULL,
                provider_best TEXT NOT NULL,
                provider_item_id TEXT,
                content_hash_exact TEXT NOT NULL,
                content_hash_near TEXT NOT NULL,
                quality_score REAL NOT NULL DEFAULT 0,
                lane TEXT NOT NULL CHECK(lane IN ('high_precision', 'high_recall'))
            );

            CREATE TABLE IF NOT EXISTS article_versions (
                version_id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                provider_item_id TEXT,
                provider_payload_json TEXT NOT NULL,
                fetched_at_utc TEXT NOT NULL,
                provider_published_at_raw TEXT,
                FOREIGN KEY(article_id) REFERENCES articles(article_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS entity_links (
                article_id TEXT NOT NULL,
                ticker TEXT NOT NULL,
                confidence REAL NOT NULL,
                lane TEXT NOT NULL CHECK(lane IN ('high_precision', 'high_recall')),
                method TEXT NOT NULL,
                matched_alias TEXT,
                matched_span_start INTEGER,
                matched_span_end INTEGER,
                matched_span_start_norm INTEGER NOT NULL DEFAULT -1,
                matched_span_end_norm INTEGER NOT NULL DEFAULT -1,
                published_at_utc TEXT NOT NULL,
                PRIMARY KEY(
                    article_id,
                    ticker,
                    lane,
                    method,
                    matched_span_start_norm,
                    matched_span_end_norm
                ),
                FOREIGN KEY(article_id) REFERENCES articles(article_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS article_relevance (
                article_id TEXT NOT NULL,
                ticker TEXT NOT NULL,
                lane TEXT NOT NULL,
                relevance_score REAL NOT NULL,
                relation_type TEXT NOT NULL DEFAULT '',
                is_primary INTEGER NOT NULL DEFAULT 0,
                confidence REAL NOT NULL DEFAULT 0,
                evidence_json TEXT NOT NULL DEFAULT '',
                PRIMARY KEY(article_id, ticker, lane),
                FOREIGN KEY(article_id) REFERENCES articles(article_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS provider_runs (
                run_id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                mode TEXT NOT NULL CHECK(mode IN ('daily', 'backfill', 'probe')),
                params_json TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                fetched INTEGER NOT NULL DEFAULT 0,
                inserted INTEGER NOT NULL DEFAULT 0,
                deduped INTEGER NOT NULL DEFAULT 0,
                rejected INTEGER NOT NULL DEFAULT 0,
                errors INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'running'
            );

            CREATE TABLE IF NOT EXISTS rejected_items (
                reject_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                provider TEXT NOT NULL,
                provider_item_id TEXT,
                url TEXT,
                reason TEXT NOT NULL,
                diagnostics_json TEXT,
                fetched_at_utc TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS provider_run_windows (
                run_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                window_start_utc TEXT NOT NULL,
                window_end_utc TEXT NOT NULL,
                status TEXT NOT NULL,
                fetched INTEGER NOT NULL DEFAULT 0,
                inserted INTEGER NOT NULL DEFAULT 0,
                deduped INTEGER NOT NULL DEFAULT 0,
                rejected INTEGER NOT NULL DEFAULT 0,
                errors INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(run_id, provider, window_start_utc, window_end_utc)
            );
            """
        )
        cur.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at_utc);
            CREATE INDEX IF NOT EXISTS idx_articles_provider_pub ON articles(provider_best, published_at_utc);
            CREATE INDEX IF NOT EXISTS idx_articles_url_hash ON articles(url_hash);
            CREATE INDEX IF NOT EXISTS idx_articles_exact_hash ON articles(content_hash_exact);
            CREATE INDEX IF NOT EXISTS idx_articles_near_hash ON articles(content_hash_near);

            CREATE INDEX IF NOT EXISTS idx_article_versions_article ON article_versions(article_id);
            CREATE INDEX IF NOT EXISTS idx_article_versions_provider_item ON article_versions(provider, provider_item_id);

            CREATE INDEX IF NOT EXISTS idx_entity_links_ticker_pub ON entity_links(ticker, published_at_utc);
            CREATE INDEX IF NOT EXISTS idx_article_relevance_ticker_lane ON article_relevance(ticker, lane, relevance_score DESC);
            CREATE INDEX IF NOT EXISTS idx_rejected_provider_reason ON rejected_items(provider, reason);
            CREATE INDEX IF NOT EXISTS idx_rejected_fetched ON rejected_items(fetched_at_utc);
            """
        )
        self.conn.commit()

    def start_provider_run(
        self,
        provider: str,
        mode: str,
        params: Dict[str, Any],
        run_id: str = "",
    ) -> str:
        rid = str(run_id or "").strip() or f"{provider}_{mode}_{sha1_hex(now_utc_iso() + secrets.token_hex(4))[:12]}"
        existing = self.conn.execute("SELECT run_id FROM provider_runs WHERE run_id = ?", (rid,)).fetchone()
        if existing is None:
            self.conn.execute(
                """
                INSERT INTO provider_runs(
                    run_id, provider, mode, params_json, started_at, status
                ) VALUES (?, ?, ?, ?, ?, 'running')
                """,
                (rid, provider, mode, json.dumps(params, ensure_ascii=False, sort_keys=True), now_utc_iso()),
            )
            self.conn.commit()
        return rid

    def finish_provider_run(self, run_id: str, status: str) -> None:
        self.conn.execute(
            "UPDATE provider_runs SET status = ?, finished_at = ? WHERE run_id = ?",
            (status, now_utc_iso(), run_id),
        )
        self.conn.commit()

    def finalize_stale_running_runs(self, *, older_than_hours: int = 2, to_status: str = "failed") -> int:
        hours = int(max(1, older_than_hours))
        status = str(to_status or "").strip().lower()
        if status not in {"failed", "partial_failed"}:
            raise ValueError("to_status must be one of: failed, partial_failed")
        cutoff_mod = f"-{hours} hours"
        stale_count = int(
            (
                self.conn.execute(
                    """
                    SELECT COUNT(*)
                      FROM provider_runs
                     WHERE status = 'running'
                       AND datetime(replace(replace(started_at, 'T', ' '), 'Z', '')) < datetime('now', ?)
                    """,
                    (cutoff_mod,),
                ).fetchone()
                or [0]
            )[0]
            or 0
        )
        if stale_count <= 0:
            return 0
        self.conn.execute(
            """
            UPDATE provider_runs
               SET status = ?, finished_at = ?
             WHERE status = 'running'
               AND datetime(replace(replace(started_at, 'T', ' '), 'Z', '')) < datetime('now', ?)
            """,
            (status, now_utc_iso(), cutoff_mod),
        )
        self.conn.commit()
        return stale_count

    def increment_run_counters(
        self,
        run_id: str,
        *,
        fetched: int = 0,
        inserted: int = 0,
        deduped: int = 0,
        rejected: int = 0,
        errors: int = 0,
        **kwargs: object,
    ) -> None:
        # Ignore extra kwargs (e.g. last_error from stats) so callers can pass **stats safely.
        self.conn.execute(
            """
            UPDATE provider_runs
               SET fetched = fetched + ?,
                   inserted = inserted + ?,
                   deduped = deduped + ?,
                   rejected = rejected + ?,
                   errors = errors + ?
             WHERE run_id = ?
            """,
            (int(fetched), int(inserted), int(deduped), int(rejected), int(errors), run_id),
        )
        self.conn.commit()

    def record_window(
        self,
        *,
        run_id: str,
        provider: str,
        window_start_utc: str,
        window_end_utc: str,
        status: str,
        fetched: int = 0,
        inserted: int = 0,
        deduped: int = 0,
        rejected: int = 0,
        errors: int = 0,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO provider_run_windows(
                run_id, provider, window_start_utc, window_end_utc,
                status, fetched, inserted, deduped, rejected, errors
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id, provider, window_start_utc, window_end_utc)
            DO UPDATE SET
                status=excluded.status,
                fetched=excluded.fetched,
                inserted=excluded.inserted,
                deduped=excluded.deduped,
                rejected=excluded.rejected,
                errors=excluded.errors
            """,
            (
                run_id,
                provider,
                window_start_utc,
                window_end_utc,
                status,
                int(fetched),
                int(inserted),
                int(deduped),
                int(rejected),
                int(errors),
            ),
        )
        self.conn.commit()

    def completed_windows(self, run_id: str, provider: str) -> set[Tuple[str, str]]:
        rows = self.conn.execute(
            """
            SELECT window_start_utc, window_end_utc
              FROM provider_run_windows
             WHERE run_id = ? AND provider = ? AND status = 'completed'
            """,
            (run_id, provider),
        ).fetchall()
        return {(str(row[0]), str(row[1])) for row in rows}

    def reject_item(
        self,
        *,
        run_id: str,
        provider: str,
        provider_item_id: str,
        url: str,
        reason: str,
        diagnostics: Dict[str, Any],
        fetched_at_utc: str,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO rejected_items(
                run_id, provider, provider_item_id, url, reason, diagnostics_json, fetched_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                provider,
                provider_item_id or "",
                url or "",
                reason,
                json.dumps(diagnostics, ensure_ascii=False, sort_keys=True),
                fetched_at_utc or now_utc_iso(),
            ),
        )
        self.conn.commit()

    def _provider_rank(self, provider: str) -> int:
        return PROVIDER_PRIORITY.get(str(provider or "").strip().lower(), 0)

    def _compute_quality_score(self, candidate: ArticleCandidate) -> float:
        body_len = len(str(candidate.body or "").strip())
        desc_len = len(str(candidate.description or "").strip())
        title_len = len(str(candidate.title or "").strip())
        score = min(1.0, (body_len / 2400.0) + (desc_len / 1000.0) + (title_len / 400.0))
        return round(float(score), 6)

    def _compute_quality_score_from_fields(self, *, title: str, description: str, body: str) -> float:
        body_len = len(str(body or "").strip())
        desc_len = len(str(description or "").strip())
        title_len = len(str(title or "").strip())
        score = min(1.0, (body_len / 2400.0) + (desc_len / 1000.0) + (title_len / 400.0))
        return round(float(score), 6)

    def _find_existing_article(
        self,
        *,
        canonical_url: str,
        url_hash: str,
        exact_hash: str,
        near_hash: str,
    ) -> Tuple[Optional[sqlite3.Row], str]:
        if canonical_url:
            row = self.conn.execute(
                "SELECT * FROM articles WHERE url_hash = ? LIMIT 1",
                (url_hash,),
            ).fetchone()
            if row is not None:
                return row, "dedupe_url"
        row = self.conn.execute(
            "SELECT * FROM articles WHERE content_hash_exact = ? LIMIT 1",
            (exact_hash,),
        ).fetchone()
        if row is not None:
            return row, "dedupe_exact"
        row = self.conn.execute(
            "SELECT * FROM articles WHERE content_hash_near = ? LIMIT 1",
            (near_hash,),
        ).fetchone()
        if row is not None:
            return row, "dedupe_near"
        return None, ""

    def _canonical_identity_key(self, canonical_url: str, exact_hash: str) -> str:
        if canonical_url:
            return canonical_url
        return f"exact:{exact_hash}"

    def upsert_article(self, candidate: ArticleCandidate, lane: str) -> UpsertResult:
        if not str(candidate.published_at_utc or "").strip():
            raise ValueError("published_at_utc is required for canonical articles")
        published = parse_datetime_utc(candidate.published_at_utc)
        if not published:
            raise ValueError("published_at_utc must be parseable")
        fetched = parse_datetime_utc(candidate.fetched_at_utc) or now_utc_iso()

        canonical_url = str(candidate.canonical_url or "").strip()
        exact_hash = compute_exact_hash(candidate.title, candidate.description)
        near_hash = compute_near_hash(candidate.title, candidate.description, candidate.body)
        if canonical_url:
            url_hash = sha256_hex(canonical_url)
        else:
            url_hash = sha256_hex(f"no-url:{exact_hash}")

        existing, dedupe_reason = self._find_existing_article(
            canonical_url=canonical_url,
            url_hash=url_hash,
            exact_hash=exact_hash,
            near_hash=near_hash,
        )

        provider = str(candidate.provider or "").strip().lower()
        if existing is None:
            identity_key = self._canonical_identity_key(canonical_url, exact_hash)
            article_id = "art_" + sha1_hex(identity_key)[:24]
            self.conn.execute(
                """
                INSERT INTO articles(
                    article_id, canonical_url, url_hash, title, description, body, source_name, language,
                    published_at_utc, fetched_at_utc, provider_best, provider_item_id,
                    content_hash_exact, content_hash_near, quality_score, lane
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    article_id,
                    canonical_url,
                    url_hash,
                    str(candidate.title or "").strip(),
                    str(candidate.description or "").strip(),
                    str(candidate.body or "").strip(),
                    str(candidate.source_name or "").strip(),
                    str(candidate.language or "").strip(),
                    published,
                    fetched,
                    provider,
                    str(candidate.provider_item_id or "").strip(),
                    exact_hash,
                    near_hash,
                    self._compute_quality_score(candidate),
                    lane,
                ),
            )
            self.conn.commit()
            return UpsertResult(
                article_id=article_id,
                inserted=True,
                dedupe_reason="",
                provider_best=provider,
            )

        article_id = str(existing["article_id"])
        existing_provider = str(existing["provider_best"] or "").strip().lower()
        existing_rank = self._provider_rank(existing_provider)
        incoming_rank = self._provider_rank(provider)
        existing_body_len = len(str(existing["body"] or "").strip())
        incoming_body_len = len(str(candidate.body or "").strip())
        existing_fetched = parse_datetime_utc(str(existing["fetched_at_utc"] or "")) or ""
        incoming_fetched = fetched

        choose_incoming = False
        if incoming_rank > existing_rank:
            choose_incoming = True
        elif incoming_rank == existing_rank and incoming_body_len > existing_body_len:
            choose_incoming = True
        elif incoming_rank == existing_rank and incoming_body_len == existing_body_len and incoming_fetched > existing_fetched:
            choose_incoming = True

        title = str(existing["title"] or "").strip()
        description = str(existing["description"] or "").strip()
        body = str(existing["body"] or "").strip()
        source_name = str(existing["source_name"] or "").strip()
        language = str(existing["language"] or "").strip()
        provider_best = existing_provider or provider
        provider_item_id = str(existing["provider_item_id"] or "").strip() or str(candidate.provider_item_id or "")

        if choose_incoming:
            title = str(candidate.title or "").strip() or title
            description = str(candidate.description or "").strip() or description
            body = str(candidate.body or "").strip() or body
            source_name = str(candidate.source_name or "").strip() or source_name
            language = str(candidate.language or "").strip() or language
            provider_best = provider or provider_best
            provider_item_id = str(candidate.provider_item_id or "").strip() or provider_item_id

        if not source_name:
            source_name = str(candidate.source_name or "").strip()
        if not language:
            language = str(candidate.language or "").strip()

        existing_published = parse_datetime_utc(str(existing["published_at_utc"] or "")) or published
        # Keep earliest timestamp if multiple providers disagree.
        published_at_utc = min(existing_published, published)
        fetched_at_utc = max(parse_datetime_utc(str(existing["fetched_at_utc"] or "")) or fetched, fetched)

        self.conn.execute(
            """
            UPDATE articles
               SET canonical_url = ?,
                   url_hash = ?,
                   title = ?,
                   description = ?,
                   body = ?,
                   source_name = ?,
                   language = ?,
                   published_at_utc = ?,
                   fetched_at_utc = ?,
                   provider_best = ?,
                   provider_item_id = ?,
                   content_hash_exact = ?,
                   content_hash_near = ?,
                   quality_score = ?,
                   lane = ?
             WHERE article_id = ?
            """,
            (
                canonical_url or str(existing["canonical_url"] or ""),
                url_hash,
                title,
                description,
                body,
                source_name,
                language,
                published_at_utc,
                fetched_at_utc,
                provider_best,
                provider_item_id,
                compute_exact_hash(title, description),
                compute_near_hash(title, description, body),
                self._compute_quality_score_from_fields(title=title, description=description, body=body),
                lane,
                article_id,
            ),
        )
        self.conn.commit()
        return UpsertResult(
            article_id=article_id,
            inserted=False,
            dedupe_reason=dedupe_reason,
            provider_best=provider_best,
        )

    def insert_article_version(self, article_id: str, candidate: ArticleCandidate) -> None:
        self.conn.execute(
            """
            INSERT INTO article_versions(
                article_id, provider, provider_item_id, provider_payload_json, fetched_at_utc, provider_published_at_raw
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                article_id,
                str(candidate.provider or "").strip().lower(),
                str(candidate.provider_item_id or "").strip(),
                json.dumps(candidate.raw_payload, ensure_ascii=False, sort_keys=True),
                parse_datetime_utc(candidate.fetched_at_utc) or now_utc_iso(),
                str(candidate.provider_published_at_raw or ""),
            ),
        )
        self.conn.commit()

    def replace_entity_links(self, article_id: str, links: Sequence[EntityLink]) -> None:
        self.conn.execute("DELETE FROM entity_links WHERE article_id = ?", (article_id,))
        if links:
            self.conn.executemany(
                """
                INSERT INTO entity_links(
                    article_id, ticker, confidence, lane, method, matched_alias,
                    matched_span_start, matched_span_end, matched_span_start_norm, matched_span_end_norm,
                    published_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        link.article_id,
                        link.ticker,
                        float(link.confidence),
                        link.lane,
                        link.method,
                        link.matched_alias,
                        link.matched_span_start,
                        link.matched_span_end,
                        int(link.matched_span_start if link.matched_span_start is not None else -1),
                        int(link.matched_span_end if link.matched_span_end is not None else -1),
                        link.published_at_utc,
                    )
                    for link in links
                ],
            )
        self.conn.commit()

    def replace_article_relevance(self, article_id: str, rows: Sequence[ArticleRelevance]) -> None:
        self.conn.execute("DELETE FROM article_relevance WHERE article_id = ?", (article_id,))
        if rows:
            self.conn.executemany(
                """
                INSERT INTO article_relevance(
                    article_id, ticker, lane, relevance_score, relation_type, is_primary, confidence, evidence_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        row.article_id,
                        row.ticker,
                        row.lane,
                        float(row.relevance_score),
                        row.relation_type,
                        1 if bool(row.is_primary) else 0,
                        float(row.confidence),
                        str(row.evidence_json or ""),
                    )
                    for row in rows
                ],
            )
        self.conn.commit()

    def get_articles_for_chunk_build(
        self,
        *,
        lane: str,
        provider_filter: Sequence[str] | None = None,
        from_utc: str = "",
        to_utc: str = "",
    ) -> List[Dict[str, Any]]:
        where = []
        args: List[Any] = []
        # Language gate: only include English, empty, or NULL language articles.
        where.append("(language IN ('en', '') OR language IS NULL)")
        if provider_filter:
            marks = ",".join(["?"] * len(provider_filter))
            where.append(f"provider_best IN ({marks})")
            args.extend([str(item).strip().lower() for item in provider_filter])
        if from_utc:
            where.append("published_at_utc >= ?")
            args.append(from_utc)
        if to_utc:
            where.append("published_at_utc <= ?")
            args.append(to_utc)
        sql = "SELECT * FROM articles"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY published_at_utc DESC, article_id DESC"
        articles = [dict(row) for row in self.conn.execute(sql, tuple(args)).fetchall()]
        if not articles:
            return []

        article_ids = [str(row["article_id"]) for row in articles]
        marks = ",".join(["?"] * len(article_ids))
        tickers_by_article: Dict[str, List[str]] = {aid: [] for aid in article_ids}
        link_rows = self.conn.execute(
            f"""
            SELECT article_id, ticker
              FROM entity_links
             WHERE lane = ? AND article_id IN ({marks})
             GROUP BY article_id, ticker
            """,
            tuple([lane] + article_ids),
        ).fetchall()
        for row in link_rows:
            aid = str(row["article_id"])
            tickers_by_article.setdefault(aid, []).append(str(row["ticker"]))

        relevance_by_article: Dict[str, List[Dict[str, Any]]] = {aid: [] for aid in article_ids}
        relevance_rows = self.conn.execute(
            f"""
            SELECT article_id, ticker, relevance_score, relation_type, is_primary, confidence, evidence_json
              FROM article_relevance
             WHERE lane = ? AND article_id IN ({marks})
             ORDER BY article_id ASC, is_primary DESC, relevance_score DESC, ticker ASC
            """,
            tuple([lane] + article_ids),
        ).fetchall()
        for row in relevance_rows:
            aid = str(row["article_id"])
            relevance_by_article.setdefault(aid, []).append(
                {
                    "ticker": str(row["ticker"] or ""),
                    "score": float(row["relevance_score"] or 0.0),
                    "relation_type": str(row["relation_type"] or ""),
                    "is_primary": bool(int(row["is_primary"] or 0)),
                    "confidence": float(row["confidence"] or 0.0),
                    "evidence_json": str(row["evidence_json"] or ""),
                }
            )

        # When building chunks for the high_precision lane, allow a soft demotion:
        # if an article has no high_precision links but does have high_recall links,
        # use those recall links so the article is still associated with tickers.
        if lane == "high_precision":
            missing_ids = [aid for aid in article_ids if not tickers_by_article.get(aid)]
            if missing_ids:
                marks_missing = ",".join(["?"] * len(missing_ids))
                hr_rows = self.conn.execute(
                    f"""
                    SELECT article_id, ticker
                      FROM entity_links
                     WHERE lane = 'high_recall' AND article_id IN ({marks_missing})
                     GROUP BY article_id, ticker
                    """,
                    tuple(missing_ids),
                ).fetchall()
                for row in hr_rows:
                    aid = str(row["article_id"])
                    tickers_by_article.setdefault(aid, []).append(str(row["ticker"]))
            missing_relevance_ids = [aid for aid in article_ids if not relevance_by_article.get(aid)]
            if missing_relevance_ids:
                marks_missing = ",".join(["?"] * len(missing_relevance_ids))
                hr_relevance_rows = self.conn.execute(
                    f"""
                    SELECT article_id, ticker, relevance_score, relation_type, is_primary, confidence, evidence_json
                      FROM article_relevance
                     WHERE lane = 'high_recall' AND article_id IN ({marks_missing})
                     ORDER BY article_id ASC, is_primary DESC, relevance_score DESC, ticker ASC
                    """,
                    tuple(missing_relevance_ids),
                ).fetchall()
                for row in hr_relevance_rows:
                    aid = str(row["article_id"])
                    relevance_by_article.setdefault(aid, []).append(
                        {
                            "ticker": str(row["ticker"] or ""),
                            "score": float(row["relevance_score"] or 0.0),
                            "relation_type": str(row["relation_type"] or ""),
                            "is_primary": bool(int(row["is_primary"] or 0)),
                            "confidence": float(row["confidence"] or 0.0),
                            "evidence_json": str(row["evidence_json"] or ""),
                        }
                    )

        for item in articles:
            aid = str(item["article_id"])
            linked_tickers = sorted(set(tickers_by_article.get(aid, [])))
            relevance_rows_for_article = sorted(
                relevance_by_article.get(aid, []),
                key=lambda row: (
                    0 if bool(row.get("is_primary")) else 1,
                    -float(row.get("score") or 0.0),
                    str(row.get("ticker") or ""),
                ),
            )
            item["linked_tickers"] = linked_tickers
            if relevance_rows_for_article:
                top = relevance_rows_for_article[0]
                item["primary_ticker"] = str(top.get("ticker") or "")
                item["primary_relevance_score"] = float(top.get("score") or 0.0)
                item["primary_relation_type"] = str(top.get("relation_type") or "")
                item["ticker_relevance_json"] = serialize_ticker_relevance(
                    [
                        ArticleRelevance(
                            article_id=aid,
                            ticker=str(row.get("ticker") or ""),
                            lane=lane,
                            relevance_score=float(row.get("score") or 0.0),
                            relation_type=str(row.get("relation_type") or ""),
                            is_primary=bool(row.get("is_primary")),
                            confidence=float(row.get("confidence") or 0.0),
                            evidence_json=str(row.get("evidence_json") or ""),
                        )
                        for row in relevance_rows_for_article
                    ]
                )
            else:
                item["primary_ticker"] = linked_tickers[0] if linked_tickers else ""
                item["primary_relevance_score"] = 0.0
                item["primary_relation_type"] = ""
                item["ticker_relevance_json"] = ""
        return articles

    def run_row(self, run_id: str) -> Dict[str, Any]:
        row = self.conn.execute(
            "SELECT * FROM provider_runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        return dict(row) if row is not None else {}
