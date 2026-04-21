from __future__ import annotations

import json
import logging
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class StateStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
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
                brief TEXT NOT NULL,
                category_hint TEXT,
                hard_filters_json TEXT NOT NULL DEFAULT '{}',
                soft_preferences_json TEXT NOT NULL DEFAULT '{}',
                search_config_json TEXT NOT NULL DEFAULT '{}',
                scan_config_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_scan_at TEXT
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_marketplace_missions_status "
            "ON marketplace_missions(status)"
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
                status TEXT NOT NULL DEFAULT 'new',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL,
                UNIQUE(mission_id, listing_id)
            )
            """
        )
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
        # Holdings: cockpit-local portfolio state. NOT financial truth, NOT
        # memory reasoning. See SYSTEM_CONTRACT §1.2.
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS holdings_items (
                holding_id TEXT PRIMARY KEY,
                ticker TEXT NOT NULL,
                account_label TEXT,
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
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_holdings_status ON holdings_items(status)"
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

    def add_chat_message(
        self, thread_id: str, role: str, content: str, created_at: str
    ) -> None:
        with self._lock:
            self.conn.execute(
                "insert into chat_messages(thread_id, role, content, created_at) values(?,?,?,?)",
                (thread_id, role, content, created_at),
            )
            self.conn.commit()

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
                    holding_id, ticker, account_label, thesis_bucket, status,
                    quantity, avg_cost, cost_currency, opened_at, updated_at, note
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    holding_id,
                    ticker.upper(),
                    account_label,
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
