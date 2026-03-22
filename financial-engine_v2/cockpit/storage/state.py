from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any


class StateStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
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
        self.conn.commit()

    def add_chat_message(self, thread_id: str, role: str, content: str, created_at: str) -> None:
        with self._lock:
            self.conn.execute(
                "insert into chat_messages(thread_id, role, content, created_at) values(?,?,?,?)",
                (thread_id, role, content, created_at),
            )
            self.conn.commit()

    def get_chat_messages(self, thread_id: str, limit: int = 200) -> list[dict[str, Any]]:
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
                   exit_code, stdout_path, stderr_path, artifacts_json
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

    def add_export(self, thread_id: str, question: str, markdown_path: str, json_path: str, created_at: str) -> None:
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
                (thread_id, ticker.upper(), action_id, status, json.dumps(summary), created_at),
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
