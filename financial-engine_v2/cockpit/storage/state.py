from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
SQLITE_BUSY_TIMEOUT_MS = 30_000


class StateStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=SQLITE_BUSY_TIMEOUT_MS / 1000,
        )
        self.conn.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            create table if not exists chat_messages (
                id integer primary key autoincrement,
                thread_id text not null,
                role text not null,
                content text not null,
                created_at text not null
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_chat_thread ON chat_messages(thread_id)"
        )
        cur.execute(
            """
            create table if not exists chat_sessions (
                thread_id text primary key,
                created_at text not null,
                updated_at text not null
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated ON chat_sessions(updated_at)"
        )
        cur.execute(
            """
            create table if not exists jobs (
                job_id text primary key,
                action_id text not null,
                args_json text not null,
                started_at text not null,
                ended_at text,
                status text not null,
                exit_code integer,
                stdout_path text,
                stderr_path text,
                artifacts_json text not null
            )
            """
        )
        # Additive migration: progress fields for real-time job tracking.
        for col, typedef in [
            ("progress_stage", "TEXT DEFAULT NULL"),
            ("progress_pct", "REAL DEFAULT NULL"),
        ]:
            try:
                cur.execute(f"ALTER TABLE jobs ADD COLUMN {col} {typedef}")
            except sqlite3.OperationalError:
                pass  # column already exists

        cur.execute(
            """
            create table if not exists analysis_exports (
                id integer primary key autoincrement,
                thread_id text not null,
                question text not null,
                markdown_path text not null,
                json_path text not null,
                created_at text not null
            )
            """
        )
        cur.execute(
            """
            create table if not exists watchlist (
                ticker text primary key,
                added_at text not null
            )
            """
        )
        cur.execute(
            """
            create table if not exists update_events (
                id integer primary key autoincrement,
                thread_id text not null,
                ticker text not null,
                action_id text not null,
                status text not null,
                summary_json text not null,
                created_at text not null
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS entity_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                observation_type TEXT NOT NULL,
                content TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'chat',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_entity_obs_ticker ON entity_observations(ticker)"
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS session_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_date TEXT NOT NULL,
                summary TEXT NOT NULL,
                tickers_mentioned TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS global_strategy (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                criterion TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'general',
                priority INTEGER NOT NULL DEFAULT 5,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ticker_strategy (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                criterion TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'general',
                priority INTEGER NOT NULL DEFAULT 5,
                decision TEXT,
                decision_rationale TEXT,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_ticker_strategy_ticker ON ticker_strategy(ticker)"
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pending_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL UNIQUE,
                summary TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS marketplace_missions (
                mission_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                mission_type TEXT NOT NULL DEFAULT 'find_good_deals',
                brief TEXT NOT NULL,
                user_goal TEXT,
                category_hint TEXT,
                hard_filters_json TEXT NOT NULL DEFAULT '{}',
                soft_preferences_json TEXT NOT NULL DEFAULT '{}',
                search_config_json TEXT NOT NULL DEFAULT '{}',
                scan_config_json TEXT NOT NULL DEFAULT '{}',
                benchmark_sources_json TEXT NOT NULL DEFAULT '["centre_com"]',
                deployment_args_json TEXT NOT NULL DEFAULT '{}',
                last_error TEXT,
                created_from_chat_message_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_scan_at TEXT
            )
            """
        )
        # Additive migration: workflow metadata fields for marketplace missions.
        for col, typedef in [
            ("mission_type", "TEXT NOT NULL DEFAULT 'find_good_deals'"),
            ("user_goal", "TEXT"),
            ("benchmark_sources_json", "TEXT NOT NULL DEFAULT '[\"centre_com\"]'"),
            ("deployment_args_json", "TEXT NOT NULL DEFAULT '{}'"),
            ("last_error", "TEXT"),
            ("created_from_chat_message_id", "TEXT"),
        ]:
            try:
                cur.execute(f"ALTER TABLE marketplace_missions ADD COLUMN {col} {typedef}")
            except sqlite3.OperationalError:
                pass  # column already exists
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_marketplace_missions_status "
            "ON marketplace_missions(status)"
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS marketplace_mission_product_links (
                mission_id TEXT PRIMARY KEY,
                tracked_product_id TEXT NOT NULL,
                link_type TEXT NOT NULL DEFAULT 'primary',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_marketplace_mission_product_links_product "
            "ON marketplace_mission_product_links(tracked_product_id, link_type)"
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS marketplace_mission_candidate_products (
                mission_id TEXT NOT NULL,
                tracked_product_id TEXT NOT NULL,
                candidate_key TEXT NOT NULL,
                category TEXT NOT NULL,
                candidate_rank INTEGER NOT NULL,
                fit_score REAL NOT NULL,
                fit_label TEXT NOT NULL,
                hard_constraints_json TEXT NOT NULL DEFAULT '[]',
                soft_preferences_json TEXT NOT NULL DEFAULT '[]',
                explanation TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (mission_id, tracked_product_id)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_marketplace_mission_candidates_mission "
            "ON marketplace_mission_candidate_products(mission_id, candidate_rank)"
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS marketplace_seen_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mission_id TEXT NOT NULL,
                listing_id TEXT NOT NULL,
                listing_url TEXT NOT NULL,
                title TEXT,
                price_text TEXT,
                price_value REAL,
                location TEXT,
                seller_name TEXT,
                query_text TEXT,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                detail_hash TEXT,
                raw_snapshot_json TEXT NOT NULL DEFAULT '{}',
                last_status TEXT NOT NULL DEFAULT 'seen',
                last_score INTEGER,
                last_decision_band TEXT,
                last_error TEXT,
                match_id TEXT,
                UNIQUE(mission_id, listing_id)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_marketplace_seen_mission "
            "ON marketplace_seen_listings(mission_id, last_seen_at DESC)"
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS marketplace_matches (
                match_id TEXT PRIMARY KEY,
                mission_id TEXT NOT NULL,
                listing_id TEXT NOT NULL,
                listing_url TEXT NOT NULL,
                title TEXT NOT NULL,
                price TEXT,
                price_value REAL,
                location TEXT,
                seller_name TEXT,
                captured_at TEXT NOT NULL,
                score INTEGER NOT NULL,
                decision_band TEXT NOT NULL,
                reasons_for_json TEXT NOT NULL DEFAULT '[]',
                reasons_against_json TEXT NOT NULL DEFAULT '[]',
                confidence REAL,
                raw_text_snapshot TEXT NOT NULL,
                screenshot_path TEXT,
                listing_media_json TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'new',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL,
                UNIQUE(mission_id, listing_id)
            )
            """
        )
        try:
            cur.execute(
                "ALTER TABLE marketplace_matches ADD COLUMN listing_media_json TEXT NOT NULL DEFAULT '[]'"
            )
        except sqlite3.OperationalError:
            pass  # column already exists
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_marketplace_matches_mission "
            "ON marketplace_matches(mission_id, captured_at DESC)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_marketplace_matches_status "
            "ON marketplace_matches(status, decision_band)"
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS marketplace_alerts (
                alert_id TEXT PRIMARY KEY,
                mission_id TEXT NOT NULL,
                match_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'new',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                trigger_reason TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_marketplace_alerts_status "
            "ON marketplace_alerts(status, created_at DESC)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_marketplace_alerts_mission "
            "ON marketplace_alerts(mission_id, created_at DESC)"
        )
        # Cockpit-local retail benchmark subsystem (operational only, not financial truth).
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS canonical_products (
                canonical_product_id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                vendor TEXT,
                model TEXT,
                sku TEXT,
                product_name TEXT NOT NULL,
                attributes_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_canonical_products_category "
            "ON canonical_products(category)"
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS retailer_products (
                retailer_product_id TEXT PRIMARY KEY,
                retailer_name TEXT NOT NULL,
                canonical_product_id TEXT NOT NULL,
                product_name TEXT NOT NULL,
                product_url TEXT,
                sku TEXT,
                attributes_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                UNIQUE(retailer_name, product_url)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_retailer_products_retailer "
            "ON retailer_products(retailer_name)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_retailer_products_canonical "
            "ON retailer_products(canonical_product_id)"
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS retailer_price_observations (
                observation_id TEXT PRIMARY KEY,
                retailer_product_id TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                price REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'AUD',
                in_stock INTEGER NOT NULL DEFAULT 1,
                observation_source TEXT NOT NULL DEFAULT 'seed_fallback'
            )
            """
        )
        try:
            cur.execute(
                "ALTER TABLE retailer_price_observations "
                "ADD COLUMN observation_source TEXT NOT NULL DEFAULT 'seed_fallback'"
            )
        except sqlite3.OperationalError:
            pass  # column already exists
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_retailer_price_observations_product "
            "ON retailer_price_observations(retailer_product_id, observed_at DESC)"
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS listing_product_matches (
                listing_match_id TEXT PRIMARY KEY,
                match_id TEXT NOT NULL,
                listing_id TEXT NOT NULL,
                mission_id TEXT,
                matched_retailer_product_id TEXT,
                category TEXT,
                confidence REAL NOT NULL DEFAULT 0,
                review_status TEXT NOT NULL DEFAULT 'pending_review',
                warning TEXT,
                rationale_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(match_id)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_listing_product_matches_review "
            "ON listing_product_matches(review_status, confidence)"
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS listing_benchmark_scores (
                score_id TEXT PRIMARY KEY,
                match_id TEXT NOT NULL,
                listing_id TEXT NOT NULL,
                matched_retailer_product_id TEXT,
                centre_com_price REAL,
                centre_com_median_30d REAL,
                listing_price REAL,
                delta_pct REAL,
                freshness_hours REAL,
                confidence REAL,
                low_confidence INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_listing_benchmark_scores_match "
            "ON listing_benchmark_scores(match_id, created_at DESC)"
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS marketplace_match_value_assessments (
                assessment_id TEXT PRIMARY KEY,
                match_id TEXT NOT NULL UNIQUE,
                mission_id TEXT,
                tracked_product_id TEXT,
                benchmark_snapshot_id TEXT,
                value_state TEXT NOT NULL,
                value_score REAL,
                value_label TEXT NOT NULL,
                value_confidence TEXT NOT NULL,
                assessment_json TEXT NOT NULL DEFAULT '{}',
                computed_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_marketplace_match_value_assessments_mission "
            "ON marketplace_match_value_assessments(mission_id, tracked_product_id)"
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS marketplace_match_feedback (
                match_id TEXT PRIMARY KEY,
                feedback TEXT NOT NULL CHECK (feedback IN ('interested', 'not_interested')),
                note TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_marketplace_match_feedback_feedback "
            "ON marketplace_match_feedback(feedback, updated_at DESC)"
        )
        # Holdings: cockpit-local portfolio state. NOT financial truth, NOT
        # memory reasoning. See SYSTEM_CONTRACT §1.2.
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS holdings_items (
                holding_id TEXT PRIMARY KEY,
                ticker TEXT NOT NULL,
                account_label TEXT,
                market_exchange TEXT,
                thesis_bucket TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                quantity REAL,
                avg_cost REAL,
                cost_currency TEXT,
                opened_at TEXT,
                updated_at TEXT NOT NULL,
                note TEXT
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_holdings_ticker ON holdings_items(ticker)"
        )
        for col, typedef in [
            ("market_exchange", "TEXT"),
        ]:
            try:
                cur.execute(f"ALTER TABLE holdings_items ADD COLUMN {col} {typedef}")
            except sqlite3.OperationalError:
                pass
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_holdings_status ON holdings_items(status)"
        )
        # Route-alias preferences: cockpit-local intent routing preferences.
        # These are confirmation-gated operational preferences, not thesis,
        # company, market, financial truth, or retrieval memory.
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS route_alias_preferences (
                preference_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                source_utterance TEXT NOT NULL,
                alias_phrase TEXT NOT NULL,
                normalized_alias_phrase TEXT NOT NULL,
                canonical_intent TEXT NOT NULL CHECK (canonical_intent IN ('holdings')),
                scope TEXT NOT NULL,
                confirmation_status TEXT NOT NULL CHECK (
                    confirmation_status IN ('proposed', 'confirmed', 'rejected')
                ),
                enabled INTEGER NOT NULL DEFAULT 0,
                provenance_message_id TEXT
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_route_alias_preferences_lookup "
            "ON route_alias_preferences(canonical_intent, normalized_alias_phrase, "
            "confirmation_status, enabled)"
        )
        # Market-update reports + queued follow-up actions. See
        # SYSTEM_CONTRACT §1.2 — these are cockpit-local report snapshots
        # produced by the orchestrator, not authoritative financial data.
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS market_update_reports (
                report_id TEXT PRIMARY KEY,
                run_type TEXT NOT NULL CHECK (run_type IN ('noon','final','manual')),
                report_date TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                summary_json TEXT NOT NULL,
                markdown_path TEXT,
                json_path TEXT
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_market_update_reports_run_type "
            "ON market_update_reports(run_type, created_at DESC)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_market_update_reports_date "
            "ON market_update_reports(report_date, created_at DESC)"
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS market_update_followups (
                followup_id TEXT PRIMARY KEY,
                report_id TEXT NOT NULL,
                ticker TEXT,
                action_type TEXT NOT NULL,
                priority_score REAL NOT NULL DEFAULT 0,
                reason_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_market_update_followups_report "
            "ON market_update_followups(report_id, priority_score DESC)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_market_update_followups_status "
            "ON market_update_followups(status, priority_score DESC)"
        )
        self.conn.commit()

    # ------------------------------------------------------------------ #
    # Retention cleanup                                                    #
    # ------------------------------------------------------------------ #

    def cleanup(
        self,
        *,
        chat_days: int = 90,
        obs_days: int = 30,
        events_days: int = 90,
        jobs_days: int = 90,
        summaries_days: int = 30,
    ) -> None:
        """Age out stale data. Safe to call at startup."""
        table_specs = [
            ("chat_messages", "created_at", chat_days),
            ("entity_observations", "created_at", obs_days),
            ("update_events", "created_at", events_days),
            ("jobs", "started_at", jobs_days),
            ("session_summaries", "created_at", summaries_days),
        ]
        with self._lock:
            for table, col, days in table_specs:
                cutoff = (datetime.now() - timedelta(days=days)).isoformat()
                cur = self.conn.execute(
                    f"DELETE FROM {table} WHERE {col} < ?",  # noqa: S608
                    (cutoff,),
                )
                if cur.rowcount:
                    logger.info(
                        "cleanup: deleted %d rows from %s (older than %d days)",
                        cur.rowcount,
                        table,
                        days,
                    )
            self.conn.commit()

    def _ensure_chat_session_unlocked(self, thread_id: str, updated_at: str) -> bool:
        existing = self.conn.execute(
            "select 1 from chat_sessions where thread_id = ? limit 1",
            (thread_id,),
        ).fetchone()
        self.conn.execute(
            """
            insert into chat_sessions(thread_id, created_at, updated_at)
            values(?,?,?)
            on conflict(thread_id) do update set updated_at = excluded.updated_at
            """,
            (thread_id, updated_at, updated_at),
        )
        return existing is None

    def ensure_chat_session(self, thread_id: str, updated_at: str | None = None) -> bool:
        stamp = str(updated_at or "").strip() or datetime.now(timezone.utc).isoformat()
        with self._lock:
            created = self._ensure_chat_session_unlocked(thread_id, stamp)
            self.conn.commit()
            return created

    def add_chat_message(
        self, thread_id: str, role: str, content: str, created_at: str
    ) -> None:
        stamp = str(created_at or "").strip() or datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._ensure_chat_session_unlocked(thread_id, stamp)
            self.conn.execute(
                "insert into chat_messages(thread_id, role, content, created_at) values(?,?,?,?)",
                (thread_id, role, content, stamp),
            )
            self.conn.commit()

    def replace_latest_chat_message(
        self,
        thread_id: str,
        role: str,
        content: str,
    ) -> bool:
        text = str(content or "").strip()
        if not text:
            return False
        with self._lock:
            row = self.conn.execute(
                """
                select id
                from chat_messages
                where thread_id = ? and role = ?
                order by id desc
                limit 1
                """,
                (thread_id, role),
            ).fetchone()
            if row is None:
                return False
            self.conn.execute(
                "update chat_messages set content = ? where id = ?",
                (text, row["id"]),
            )
            self.conn.commit()
        return True

    def get_chat_messages(
        self, thread_id: str, limit: int = 200
    ) -> list[dict[str, Any]]:
        # Fetch the most recent `limit` messages, then reverse so the result
        # is chronological (oldest→newest).  Previously used ASC which returned
        # the oldest 200 rows — useless for context when history is long.
        rows = self.conn.execute(
            """
            select thread_id, role, content, created_at
            from chat_messages
            where thread_id = ?
            order by id desc
            limit ?
            """,
            (thread_id, limit),
        ).fetchall()
        return list(reversed([dict(r) for r in rows]))

    def count_chat_messages(self, thread_id: str) -> int:
        row = self.conn.execute(
            """
            select count(*)
            from chat_messages
            where thread_id = ?
            """,
            (thread_id,),
        ).fetchone()
        return int(row[0]) if row else 0

    def list_chat_sessions(self, limit: int = 100) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 500))
        rows = self.conn.execute(
            """
            with ranked as (
                select
                    thread_id,
                    content,
                    role,
                    created_at,
                    id,
                    row_number() over (partition by thread_id order by id desc) as rn_desc,
                    row_number() over (
                        partition by thread_id
                        order by case when role = 'user' then id else 2147483647 end asc
                    ) as rn_user
                from chat_messages
            ),
            message_stats as (
                select
                    thread_id,
                    max(created_at) as message_updated_at,
                    count(*) as message_count,
                    max(case when rn_desc = 1 then content end) as last_message,
                    max(case when rn_user = 1 and role = 'user' then content end) as title_seed,
                    max(id) as max_id
                from ranked
                group by thread_id
            ),
            combined as (
                select
                    s.thread_id as thread_id,
                    coalesce(m.message_updated_at, s.updated_at) as updated_at,
                    coalesce(m.message_count, 0) as message_count,
                    m.last_message as last_message,
                    m.title_seed as title_seed,
                    coalesce(m.max_id, -1) as sort_id
                from chat_sessions s
                left join message_stats m on m.thread_id = s.thread_id
                union all
                select
                    m.thread_id as thread_id,
                    m.message_updated_at as updated_at,
                    m.message_count as message_count,
                    m.last_message as last_message,
                    m.title_seed as title_seed,
                    m.max_id as sort_id
                from message_stats m
                left join chat_sessions s on s.thread_id = m.thread_id
                where s.thread_id is null
            )
            select
                thread_id,
                updated_at,
                message_count,
                last_message,
                title_seed
            from combined
            order by updated_at desc, sort_id desc
            limit ?
            """,
            (safe_limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_chat_messages_with_ids(
        self, thread_id: str, limit: int = 200
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 2000))
        rows = self.conn.execute(
            """
            select id, thread_id, role, content, created_at
            from chat_messages
            where thread_id = ?
            order by id desc
            limit ?
            """,
            (thread_id, safe_limit),
        ).fetchall()
        return list(reversed([dict(r) for r in rows]))

    def delete_chat_session(self, thread_id: str) -> int:
        with self._lock:
            cur = self.conn.execute(
                "delete from chat_messages where thread_id = ?",
                (thread_id,),
            )
            self.conn.execute(
                "delete from chat_sessions where thread_id = ?",
                (thread_id,),
            )
            self.conn.commit()
            return int(cur.rowcount or 0)

    def has_chat_session(self, thread_id: str) -> bool:
        row = self.conn.execute(
            """
            select 1
            where exists(select 1 from chat_sessions where thread_id = ?)
               or exists(select 1 from chat_messages where thread_id = ?)
            """,
            (thread_id, thread_id),
        ).fetchone()
        return row is not None

    def add_job(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self.conn.execute(
                """
                insert or replace into jobs(
                    job_id, action_id, args_json, started_at, ended_at, status,
                    exit_code, stdout_path, stderr_path, artifacts_json
                ) values(?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    payload["job_id"],
                    payload["action_id"],
                    json.dumps(payload.get("args", {})),
                    payload["started_at"],
                    payload.get("ended_at"),
                    payload["status"],
                    payload.get("exit_code"),
                    payload.get("stdout_path"),
                    payload.get("stderr_path"),
                    json.dumps(payload.get("artifacts", [])),
                ),
            )
            self.conn.commit()

    def list_jobs(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            select job_id, action_id, args_json, started_at, ended_at, status,
                   exit_code, stdout_path, stderr_path, artifacts_json,
                   progress_stage, progress_pct
            from jobs
            order by started_at desc
            limit ?
            """,
            (limit,),
        ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["args"] = json.loads(item.pop("args_json"))
            item["artifacts"] = json.loads(item.pop("artifacts_json"))
            out.append(item)
        return out

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            select job_id, action_id, args_json, started_at, ended_at, status,
                   exit_code, stdout_path, stderr_path, artifacts_json,
                   progress_stage, progress_pct
            from jobs
            where job_id = ?
            limit 1
            """,
            (job_id,),
        ).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["args"] = json.loads(item.pop("args_json"))
        item["artifacts"] = json.loads(item.pop("artifacts_json"))
        return item

    def update_job_progress(
        self, job_id: str, stage: str, pct: float | None = None
    ) -> None:
        """Update progress fields for a running job (lightweight targeted UPDATE)."""
        with self._lock:
            self.conn.execute(
                "UPDATE jobs SET progress_stage = ?, progress_pct = ? WHERE job_id = ?",
                (stage, pct, job_id),
            )
            self.conn.commit()

    def update_job_status(
        self,
        job_id: str,
        status: str,
        exit_code: int | None = None,
        ended_at: str | None = None,
    ) -> None:
        """Update job status and exit metadata without touching progress fields."""
        with self._lock:
            self.conn.execute(
                "UPDATE jobs SET status = ?, exit_code = ?, ended_at = ? WHERE job_id = ?",
                (status, exit_code, ended_at, job_id),
            )
            self.conn.commit()

    def add_export(
        self,
        thread_id: str,
        question: str,
        markdown_path: str,
        json_path: str,
        created_at: str,
    ) -> None:
        with self._lock:
            self.conn.execute(
                "insert into analysis_exports(thread_id, question, markdown_path, json_path, created_at) values(?,?,?,?,?)",
                (thread_id, question, markdown_path, json_path, created_at),
            )
            self.conn.commit()

    def list_exports(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            select thread_id, question, markdown_path, json_path, created_at
            from analysis_exports
            order by id desc
            limit ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_latest_export(self, thread_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            select thread_id, question, markdown_path, json_path, created_at
            from analysis_exports
            where thread_id = ?
            order by id desc
            limit 1
            """,
            (thread_id,),
        ).fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------ #
    # Watchlist                                                            #
    # ------------------------------------------------------------------ #

    def add_watch_ticker(self, ticker: str, added_at: str) -> bool:
        """Add ticker to watchlist (normalised to uppercase). Returns True if inserted, False if duplicate."""
        upper = ticker.upper()
        with self._lock:
            cur = self.conn.execute(
                "insert or ignore into watchlist(ticker, added_at) values(?,?)",
                (upper, added_at),
            )
            self.conn.commit()
            return cur.rowcount == 1

    def list_watch_tickers(self) -> list[dict[str, Any]]:
        """Return watchlist rows sorted alphabetically by ticker."""
        rows = self.conn.execute(
            "select ticker, added_at from watchlist order by ticker asc"
        ).fetchall()
        return [dict(r) for r in rows]

    def remove_watch_ticker(self, ticker: str) -> bool:
        """Remove ticker from watchlist. Returns True if removed, False if not found."""
        upper = ticker.upper()
        with self._lock:
            cur = self.conn.execute("delete from watchlist where ticker = ?", (upper,))
            self.conn.commit()
            return cur.rowcount == 1

    def clear_watch_tickers(self) -> int:
        """Remove all tickers from watchlist. Returns count removed."""
        with self._lock:
            cur = self.conn.execute("delete from watchlist")
            self.conn.commit()
            return cur.rowcount

    # ------------------------------------------------------------------ #
    # Marketplace match feedback                                          #
    # ------------------------------------------------------------------ #

    def set_marketplace_match_feedback(
        self,
        match_id: str,
        feedback: str,
        *,
        note: str | None = None,
        updated_at: str | None = None,
    ) -> dict[str, Any]:
        normalized_match_id = str(match_id or "").strip()
        normalized_feedback = str(feedback or "").strip().lower()
        if not normalized_match_id:
            raise ValueError("match_id is required")
        if normalized_feedback not in {"interested", "not_interested"}:
            raise ValueError(f"invalid marketplace match feedback: {feedback}")
        stamp = str(updated_at or "").strip() or datetime.now(timezone.utc).isoformat()
        clean_note = str(note).strip() if note is not None else None
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO marketplace_match_feedback(
                    match_id, feedback, note, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(match_id) DO UPDATE SET
                    feedback = excluded.feedback,
                    note = excluded.note,
                    updated_at = excluded.updated_at
                """,
                (
                    normalized_match_id,
                    normalized_feedback,
                    clean_note or None,
                    stamp,
                    stamp,
                ),
            )
            self.conn.commit()
        feedback_row = self.get_marketplace_match_feedback(normalized_match_id)
        if feedback_row is None:
            raise RuntimeError("failed to persist marketplace match feedback")
        return feedback_row

    def get_marketplace_match_feedback(self, match_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT match_id, feedback, note, created_at, updated_at
            FROM marketplace_match_feedback
            WHERE match_id = ?
            LIMIT 1
            """,
            (str(match_id or "").strip(),),
        ).fetchone()
        return dict(row) if row else None

    def list_marketplace_match_feedback(
        self,
        match_ids: list[str],
    ) -> dict[str, dict[str, Any]]:
        normalized = [str(match_id or "").strip() for match_id in match_ids]
        normalized = [match_id for match_id in normalized if match_id]
        if not normalized:
            return {}
        placeholders = ",".join("?" for _ in normalized)
        rows = self.conn.execute(
            f"""
            SELECT match_id, feedback, note, created_at, updated_at
            FROM marketplace_match_feedback
            WHERE match_id IN ({placeholders})
            """,  # noqa: S608 - placeholders are generated from argument count only.
            tuple(normalized),
        ).fetchall()
        return {str(row["match_id"]): dict(row) for row in rows}

    def clear_marketplace_match_feedback(self, match_id: str) -> bool:
        with self._lock:
            cur = self.conn.execute(
                "DELETE FROM marketplace_match_feedback WHERE match_id = ?",
                (str(match_id or "").strip(),),
            )
            self.conn.commit()
            return cur.rowcount == 1

    # ------------------------------------------------------------------ #
    # Holdings (cockpit-local portfolio state)                             #
    # ------------------------------------------------------------------ #
    # Holdings are personal portfolio entries the user manually curates in
    # the cockpit. They are NOT a source of truth for financial data, NOT
    # memory reasoning, and never feed back into the canonical pipeline.
    # See SYSTEM_CONTRACT §1.2 (cockpit role: client + orchestration only).

    _HOLDING_COLUMNS = (
        "holding_id",
        "ticker",
        "account_label",
        "market_exchange",
        "thesis_bucket",
        "status",
        "quantity",
        "avg_cost",
        "cost_currency",
        "opened_at",
        "updated_at",
        "note",
    )

    _HOLDING_UPDATABLE_COLUMNS = (
        "ticker",
        "account_label",
        "market_exchange",
        "thesis_bucket",
        "status",
        "quantity",
        "avg_cost",
        "cost_currency",
        "opened_at",
        "note",
    )

    def add_holding(
        self,
        ticker: str,
        *,
        account_label: str | None = None,
        market_exchange: str | None = None,
        thesis_bucket: str | None = None,
        quantity: float | None = None,
        avg_cost: float | None = None,
        cost_currency: str | None = None,
        opened_at: str | None = None,
        note: str | None = None,
    ) -> str:
        """Insert a holding. Returns the generated holding_id.

        Multiple rows for the same ticker are allowed (e.g., one per account).
        """
        holding_id = str(uuid.uuid4())
        updated_at = datetime.now().isoformat()
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO holdings_items(
                    holding_id, ticker, account_label, market_exchange, thesis_bucket, status,
                    quantity, avg_cost, cost_currency, opened_at, updated_at, note
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    holding_id,
                    ticker.upper(),
                    account_label,
                    market_exchange,
                    thesis_bucket,
                    "active",
                    quantity,
                    avg_cost,
                    cost_currency,
                    opened_at,
                    updated_at,
                    note,
                ),
            )
            self.conn.commit()
        return holding_id

    def list_holdings(
        self,
        *,
        ticker: str | None = None,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        """Return holdings ordered alphabetically by ticker, then opened_at."""
        clauses: list[str] = []
        params: list[Any] = []
        if not include_archived:
            clauses.append("status != 'archived'")
        if ticker is not None:
            clauses.append("ticker = ?")
            params.append(ticker.upper())
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        cols = ", ".join(self._HOLDING_COLUMNS)
        rows = self.conn.execute(
            f"SELECT {cols} FROM holdings_items {where} ORDER BY ticker ASC, opened_at ASC",  # noqa: S608
            tuple(params),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_holding(self, holding_id: str) -> dict[str, Any] | None:
        cols = ", ".join(self._HOLDING_COLUMNS)
        row = self.conn.execute(
            f"SELECT {cols} FROM holdings_items WHERE holding_id = ? LIMIT 1",  # noqa: S608
            (holding_id,),
        ).fetchone()
        return dict(row) if row else None

    def update_holding(self, holding_id: str, **fields: Any) -> bool:
        """Partial update. Returns True iff a row was modified.

        Only fields in ``_HOLDING_UPDATABLE_COLUMNS`` are accepted; unknown
        kwargs are ignored. ``updated_at`` is refreshed automatically.
        Tickers are normalised to uppercase. An empty kwargs call is a no-op
        and returns False.
        """
        accepted: dict[str, Any] = {
            k: v for k, v in fields.items() if k in self._HOLDING_UPDATABLE_COLUMNS
        }
        if not accepted:
            return False
        if "ticker" in accepted and isinstance(accepted["ticker"], str):
            accepted["ticker"] = accepted["ticker"].upper()
        accepted["updated_at"] = datetime.now().isoformat()
        assignments = ", ".join(f"{col} = ?" for col in accepted)
        values = list(accepted.values()) + [holding_id]
        with self._lock:
            cur = self.conn.execute(
                f"UPDATE holdings_items SET {assignments} WHERE holding_id = ?",  # noqa: S608
                values,
            )
            self.conn.commit()
            return cur.rowcount == 1

    def archive_holding(self, holding_id: str) -> bool:
        """Soft-delete by flipping status to 'archived'. Returns True on hit."""
        return self.update_holding(holding_id, status="archived")

    def remove_holding(self, holding_id: str) -> bool:
        """Hard-delete a holding. Returns True iff a row was removed."""
        with self._lock:
            cur = self.conn.execute(
                "DELETE FROM holdings_items WHERE holding_id = ?", (holding_id,)
            )
            self.conn.commit()
            return cur.rowcount == 1

    # ------------------------------------------------------------------ #
    # Route-alias preferences (confirmation-gated operational routing)     #
    # ------------------------------------------------------------------ #

    _ROUTE_ALIAS_COLUMNS = (
        "preference_id",
        "created_at",
        "updated_at",
        "source_utterance",
        "alias_phrase",
        "normalized_alias_phrase",
        "canonical_intent",
        "scope",
        "confirmation_status",
        "enabled",
        "provenance_message_id",
    )
    _ROUTE_ALIAS_ALLOWED_INTENTS = {"holdings"}
    _ROUTE_ALIAS_ALLOWED_STATUSES = {"proposed", "confirmed", "rejected"}

    @staticmethod
    def normalize_route_alias_phrase(value: str) -> str:
        cleaned = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower())
        return " ".join(cleaned.split())

    @classmethod
    def _validate_route_alias_intent(cls, canonical_intent: str) -> str:
        intent = str(canonical_intent or "").strip().lower()
        if intent not in cls._ROUTE_ALIAS_ALLOWED_INTENTS:
            allowed = ", ".join(sorted(cls._ROUTE_ALIAS_ALLOWED_INTENTS))
            raise ValueError(f"unsupported canonical_intent '{canonical_intent}'; expected one of: {allowed}")
        return intent

    @classmethod
    def _validate_route_alias_status(cls, status: str) -> str:
        normalized = str(status or "").strip().lower()
        if normalized not in cls._ROUTE_ALIAS_ALLOWED_STATUSES:
            allowed = ", ".join(sorted(cls._ROUTE_ALIAS_ALLOWED_STATUSES))
            raise ValueError(f"unsupported confirmation_status '{status}'; expected one of: {allowed}")
        return normalized

    @staticmethod
    def _route_alias_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        data["enabled"] = bool(data.get("enabled"))
        return data

    def propose_route_alias_preference(
        self,
        *,
        source_utterance: str,
        alias_phrase: str,
        canonical_intent: str,
        scope: str = "user",
        provenance_message_id: str | None = None,
    ) -> dict[str, Any]:
        intent = self._validate_route_alias_intent(canonical_intent)
        alias = str(alias_phrase or "").strip()
        normalized_alias = self.normalize_route_alias_phrase(alias)
        if not normalized_alias:
            raise ValueError("alias_phrase is required")
        source = str(source_utterance or "").strip() or alias
        normalized_scope = str(scope or "user").strip().lower() or "user"
        now = datetime.now(timezone.utc).isoformat()
        preference_id = str(uuid.uuid4())
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO route_alias_preferences(
                    preference_id, created_at, updated_at, source_utterance,
                    alias_phrase, normalized_alias_phrase, canonical_intent, scope,
                    confirmation_status, enabled, provenance_message_id
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    preference_id,
                    now,
                    now,
                    source,
                    alias,
                    normalized_alias,
                    intent,
                    normalized_scope,
                    "proposed",
                    0,
                    provenance_message_id,
                ),
            )
            self.conn.commit()
        row = self.get_route_alias_preference(preference_id)
        if row is None:
            raise RuntimeError("route alias preference was created but could not be reloaded")
        return row

    def get_route_alias_preference(self, preference_id: str) -> dict[str, Any] | None:
        cols = ", ".join(self._ROUTE_ALIAS_COLUMNS)
        row = self.conn.execute(
            f"SELECT {cols} FROM route_alias_preferences WHERE preference_id = ? LIMIT 1",  # noqa: S608
            (preference_id,),
        ).fetchone()
        return self._route_alias_row_to_dict(row) if row else None

    def list_route_alias_preferences(
        self,
        *,
        canonical_intent: str | None = None,
        active_only: bool = False,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if canonical_intent:
            clauses.append("canonical_intent = ?")
            params.append(self._validate_route_alias_intent(canonical_intent))
        if active_only:
            clauses.append("confirmation_status = 'confirmed'")
            clauses.append("enabled = 1")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        cols = ", ".join(self._ROUTE_ALIAS_COLUMNS)
        rows = self.conn.execute(
            f"SELECT {cols} FROM route_alias_preferences {where} ORDER BY updated_at DESC",  # noqa: S608
            tuple(params),
        ).fetchall()
        return [self._route_alias_row_to_dict(row) for row in rows]

    def list_active_route_aliases(
        self,
        *,
        canonical_intent: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.list_route_alias_preferences(
            canonical_intent=canonical_intent,
            active_only=True,
        )

    def _set_route_alias_preference_state(
        self,
        preference_id: str,
        *,
        confirmation_status: str | None = None,
        enabled: bool | None = None,
    ) -> dict[str, Any] | None:
        assignments: list[str] = ["updated_at = ?"]
        values: list[Any] = [datetime.now(timezone.utc).isoformat()]
        if confirmation_status is not None:
            assignments.append("confirmation_status = ?")
            values.append(self._validate_route_alias_status(confirmation_status))
        if enabled is not None:
            assignments.append("enabled = ?")
            values.append(1 if enabled else 0)
        values.append(preference_id)
        with self._lock:
            cur = self.conn.execute(
                f"UPDATE route_alias_preferences SET {', '.join(assignments)} WHERE preference_id = ?",  # noqa: S608
                tuple(values),
            )
            self.conn.commit()
        if cur.rowcount != 1:
            return None
        return self.get_route_alias_preference(preference_id)

    def confirm_route_alias_preference(self, preference_id: str) -> dict[str, Any] | None:
        return self._set_route_alias_preference_state(
            preference_id,
            confirmation_status="confirmed",
            enabled=True,
        )

    def reject_route_alias_preference(self, preference_id: str) -> dict[str, Any] | None:
        return self._set_route_alias_preference_state(
            preference_id,
            confirmation_status="rejected",
            enabled=False,
        )

    def disable_route_alias_preference(self, preference_id: str) -> dict[str, Any] | None:
        return self._set_route_alias_preference_state(preference_id, enabled=False)

    def delete_route_alias_preference(self, preference_id: str) -> bool:
        with self._lock:
            cur = self.conn.execute(
                "DELETE FROM route_alias_preferences WHERE preference_id = ?",
                (preference_id,),
            )
            self.conn.commit()
        return cur.rowcount == 1

    # ------------------------------------------------------------------ #
    # Market-update reports + followups                                    #
    # ------------------------------------------------------------------ #
    # Cockpit-local snapshots of the verbal market-update orchestrator's
    # output. The orchestrator (P5) writes one report row per run and
    # optionally queues per-ticker follow-up actions (e.g., research,
    # watchlist add/remove proposals). See SYSTEM_CONTRACT §1.2.

    _REPORT_COLUMNS = (
        "report_id",
        "run_type",
        "report_date",
        "status",
        "created_at",
        "summary_json",
        "markdown_path",
        "json_path",
    )

    _FOLLOWUP_COLUMNS = (
        "followup_id",
        "report_id",
        "ticker",
        "action_type",
        "priority_score",
        "reason_json",
        "status",
        "created_at",
    )

    @staticmethod
    def _row_to_report(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["summary"] = json.loads(item.pop("summary_json"))
        return item

    @staticmethod
    def _row_to_followup(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["reason"] = json.loads(item.pop("reason_json"))
        return item

    def save_market_update_report(
        self,
        *,
        run_type: str,
        report_date: str,
        status: str,
        summary: dict[str, Any],
        markdown_path: str | None = None,
        json_path: str | None = None,
    ) -> str:
        """Persist a report run. Returns the generated report_id.

        ``run_type`` must be one of 'noon', 'final', 'manual' (CHECK
        constraint). Each call inserts a new row; day-level uniqueness is a
        higher-layer policy, not a schema constraint.
        """
        report_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO market_update_reports(
                    report_id, run_type, report_date, status, created_at,
                    summary_json, markdown_path, json_path
                ) VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    report_id,
                    run_type,
                    report_date,
                    status,
                    created_at,
                    json.dumps(summary),
                    markdown_path,
                    json_path,
                ),
            )
            self.conn.commit()
        return report_id

    def get_latest_market_update_report(
        self, run_type: str | None = None
    ) -> dict[str, Any] | None:
        """Most recent report (optionally filtered by run_type), or None."""
        cols = ", ".join(self._REPORT_COLUMNS)
        if run_type is None:
            row = self.conn.execute(
                f"SELECT {cols} FROM market_update_reports "  # noqa: S608
                "ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        else:
            row = self.conn.execute(
                f"SELECT {cols} FROM market_update_reports WHERE run_type = ? "  # noqa: S608
                "ORDER BY created_at DESC LIMIT 1",
                (run_type,),
            ).fetchone()
        return self._row_to_report(row) if row else None

    def list_market_update_reports(
        self,
        *,
        run_type: str | None = None,
        report_date: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Reports newest-first. Optional filters on run_type and report_date."""
        clauses: list[str] = []
        params: list[Any] = []
        if run_type is not None:
            clauses.append("run_type = ?")
            params.append(run_type)
        if report_date is not None:
            clauses.append("report_date = ?")
            params.append(report_date)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        cols = ", ".join(self._REPORT_COLUMNS)
        rows = self.conn.execute(
            f"SELECT {cols} FROM market_update_reports {where} "  # noqa: S608
            "ORDER BY created_at DESC LIMIT ?",
            (*params, limit),
        ).fetchall()
        return [self._row_to_report(r) for r in rows]

    def add_market_update_followup(
        self,
        *,
        report_id: str,
        action_type: str,
        reason: dict[str, Any],
        ticker: str | None = None,
        priority_score: float = 0.0,
    ) -> str:
        """Queue a follow-up action linked to a report. Returns followup_id."""
        followup_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO market_update_followups(
                    followup_id, report_id, ticker, action_type,
                    priority_score, reason_json, status, created_at
                ) VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    followup_id,
                    report_id,
                    ticker.upper() if ticker else None,
                    action_type,
                    priority_score,
                    json.dumps(reason),
                    "queued",
                    created_at,
                ),
            )
            self.conn.commit()
        return followup_id

    def list_market_update_followups(
        self,
        *,
        report_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Followups ordered by priority desc. Optional filters on report/status."""
        clauses: list[str] = []
        params: list[Any] = []
        if report_id is not None:
            clauses.append("report_id = ?")
            params.append(report_id)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        cols = ", ".join(self._FOLLOWUP_COLUMNS)
        rows = self.conn.execute(
            f"SELECT {cols} FROM market_update_followups {where} "  # noqa: S608
            "ORDER BY priority_score DESC, created_at ASC LIMIT ?",
            (*params, limit),
        ).fetchall()
        return [self._row_to_followup(r) for r in rows]

    def update_market_update_followup_status(
        self, followup_id: str, status: str
    ) -> bool:
        """Update status (e.g., queued → accepted/rejected/done). Returns True on hit."""
        with self._lock:
            cur = self.conn.execute(
                "UPDATE market_update_followups SET status = ? WHERE followup_id = ?",
                (status, followup_id),
            )
            self.conn.commit()
            return cur.rowcount == 1

    # ------------------------------------------------------------------ #
    # Update events                                                        #
    # ------------------------------------------------------------------ #

    def add_update_event(
        self,
        thread_id: str,
        ticker: str,
        action_id: str,
        status: str,
        summary: dict[str, Any],
        created_at: str,
    ) -> None:
        """Record a completed update event with a structured summary."""
        with self._lock:
            self.conn.execute(
                """
                insert into update_events(thread_id, ticker, action_id, status, summary_json, created_at)
                values(?,?,?,?,?,?)
                """,
                (
                    thread_id,
                    ticker.upper(),
                    action_id,
                    status,
                    json.dumps(summary),
                    created_at,
                ),
            )
            self.conn.commit()

    def list_update_events(
        self,
        thread_id: str,
        *,
        ticker: str | None = None,
        limit: int = 10,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return recent update events for a thread, optionally filtered by ticker/status."""
        clauses = ["thread_id = ?"]
        params: list[Any] = [thread_id]
        if ticker is not None:
            clauses.append("ticker = ?")
            params.append(ticker.upper())
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        where = " AND ".join(clauses)
        rows = self.conn.execute(
            f"""
            select thread_id, ticker, action_id, status, summary_json, created_at
            from update_events
            where {where}
            order by id desc
            limit ?
            """,
            (*params, limit),
        ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["summary"] = json.loads(item.pop("summary_json"))
            out.append(item)
        return out

    # ------------------------------------------------------------------ #
    # Entity observations                                                  #
    # ------------------------------------------------------------------ #

    def add_entity_observation(
        self,
        ticker: str,
        observation_type: str,
        content: str,
        source: str = "chat",
    ) -> None:
        """Store a fact extracted from a conversation turn about a ticker."""
        with self._lock:
            self.conn.execute(
                "INSERT INTO entity_observations (ticker, observation_type, content, source) VALUES (?, ?, ?, ?)",
                (ticker.upper(), observation_type, content[:300], source),
            )
            self.conn.commit()

    def get_entity_observations(self, ticker: str, limit: int = 8) -> list[dict]:
        """Retrieve recent observations about a ticker."""
        rows = self.conn.execute(
            "SELECT observation_type, content, created_at FROM entity_observations "
            "WHERE ticker = ? ORDER BY created_at DESC LIMIT ?",
            (ticker.upper(), limit),
        ).fetchall()
        return [{"type": r[0], "content": r[1], "date": r[2][:10]} for r in rows]

    # ------------------------------------------------------------------ #
    # User preferences                                                     #
    # ------------------------------------------------------------------ #

    def set_preference(self, key: str, value: str) -> None:
        """Set or update a user preference."""
        with self._lock:
            self.conn.execute(
                "INSERT INTO user_preferences (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')",
                (key, value),
            )
            self.conn.commit()

    def get_preferences(self) -> dict[str, str]:
        """Return all user preferences as a dict."""
        rows = self.conn.execute("SELECT key, value FROM user_preferences").fetchall()
        return {r[0]: r[1] for r in rows}

    def get_preference(self, key: str, default: str = "") -> str:
        """Return a single preference value."""
        return self.get_preferences().get(key, default)

    # ------------------------------------------------------------------ #
    # Session summaries                                                    #
    # ------------------------------------------------------------------ #

    def add_session_summary(self, summary: str, tickers: list[str]) -> None:
        """Store a session summary for cross-session context."""
        with self._lock:
            self.conn.execute(
                "INSERT INTO session_summaries (session_date, summary, tickers_mentioned) VALUES (date('now'), ?, ?)",
                (summary[:1000], json.dumps(tickers)),
            )
            self.conn.commit()

    def get_recent_session_summaries(self, limit: int = 3) -> list[dict]:
        """Return the N most recent session summaries."""
        rows = self.conn.execute(
            "SELECT session_date, summary, tickers_mentioned FROM session_summaries "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {"date": r[0], "summary": r[1], "tickers": json.loads(r[2])} for r in rows
        ]

    # ------------------------------------------------------------------ #
    # Transcript reviews                                                   #
    # ------------------------------------------------------------------ #

    def list_pending_reviews(self) -> list[dict]:
        """Return all reviews with 'pending' status."""
        rows = self.conn.execute(
            "SELECT id, source_id, summary, created_at FROM pending_reviews WHERE status = 'pending' ORDER BY created_at ASC"
        ).fetchall()
        return [dict(r) for r in rows]

    def approve_review(self, source_id: str) -> bool:
        """Mark a review as 'approved'. Returns True if a row was updated."""
        with self._lock:
            cur = self.conn.execute(
                "UPDATE pending_reviews SET status = 'approved', updated_at = datetime('now') WHERE source_id = ? AND status = 'pending'",
                (source_id,),
            )
            self.conn.commit()
            return cur.rowcount == 1

    def reject_review(self, source_id: str) -> bool:
        """Mark a review as 'rejected'. Returns True if a row was updated."""
        with self._lock:
            cur = self.conn.execute(
                "UPDATE pending_reviews SET status = 'rejected', updated_at = datetime('now') WHERE source_id = ? AND status = 'pending'",
                (source_id,),
            )
            self.conn.commit()
            return cur.rowcount == 1

    def approve_all_reviews(self) -> int:
        """Mark all pending reviews as 'approved'. Returns count updated."""
        with self._lock:
            cur = self.conn.execute(
                "UPDATE pending_reviews SET status = 'approved', updated_at = datetime('now') WHERE status = 'pending'"
            )
            self.conn.commit()
            return cur.rowcount
