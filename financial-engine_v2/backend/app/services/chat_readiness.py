from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import create_engine, text

from app.core.config import PROJECT_ROOT, settings


ReadinessStatus = str
HttpProbe = Callable[[str, str], tuple[bool, float, str | None]]

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

CAPABILITY_IDS = (
    "financial_fact",
    "filing_document_summary",
    "local_news_rag",
    "portfolio_holdings_context",
    "memory_context",
    "strategy_action_preview",
    "model_route_runtime",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_ticker(value: str | None) -> str | None:
    ticker = str(value or "").strip().upper()
    if not ticker:
        return None
    return ticker if re.fullmatch(r"[A-Z0-9]{2,6}", ticker) else None


def _bool_setting(settings_obj: Any, name: str, default: bool = False) -> bool:
    return bool(getattr(settings_obj, name, default))


def _str_setting(settings_obj: Any, name: str, default: str = "") -> str:
    return str(getattr(settings_obj, name, default) or "").strip()


def _sqlite_path_from_url(database_url: str) -> Path | None:
    raw = str(database_url or "").strip()
    if not raw.lower().startswith("sqlite:///"):
        return None
    path_text = raw[len("sqlite:///") :]
    if not path_text or path_text == ":memory:" or path_text.startswith("file:"):
        return None
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    return path


def _assert_identifier(value: str) -> str:
    if not _IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"Unsafe SQL identifier: {value!r}")
    return value


def _readonly_sqlite_url(path: str | Path) -> str:
    resolved = Path(path).expanduser().resolve()
    return f"sqlite:///file:{resolved.as_posix()}?mode=ro&uri=true"


def _count_sqlite_rows(
    path: str | Path,
    table: str,
    *,
    ticker: str | None = None,
    ticker_column: str | None = None,
    where_sql: str = "",
    where_params: tuple[Any, ...] = (),
) -> dict[str, Any]:
    resolved = Path(path).expanduser()
    if not resolved.exists():
        return {"available": False, "count": 0, "error": "sqlite file missing"}

    table_name = _assert_identifier(table)
    clauses: list[str] = []
    params: list[Any] = []
    if ticker and ticker_column:
        column_name = _assert_identifier(ticker_column)
        clauses.append(f"UPPER({column_name}) = ?")
        params.append(ticker)
    if where_sql:
        clauses.append(where_sql)
        params.extend(where_params)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""

    try:
        engine = create_engine(_readonly_sqlite_url(resolved), pool_pre_ping=True)
        with engine.connect() as conn:
            row = conn.exec_driver_sql(
                f"SELECT COUNT(1) AS count FROM {table_name}{where}",  # noqa: S608
                tuple(params),
            ).mappings().first()
        return {"available": True, "count": int(row["count"] if row else 0), "error": None}
    except Exception as exc:
        return {"available": False, "count": 0, "error": str(exc)}


class ReadinessSqlProbe:
    """Read-only row-count probe for the configured backend database."""

    def __init__(self, database_url: str) -> None:
        self.database_url = str(database_url or "").strip()

    def count_rows(
        self,
        table: str,
        *,
        ticker: str | None = None,
        ticker_column: str = "ticker",
    ) -> dict[str, Any]:
        table_name = _assert_identifier(table)
        ticker_column_name = _assert_identifier(ticker_column)
        sqlite_path = _sqlite_path_from_url(self.database_url)
        if sqlite_path is not None:
            return _count_sqlite_rows(
                sqlite_path,
                table_name,
                ticker=ticker,
                ticker_column=ticker_column_name,
            )

        if not self.database_url:
            return {"available": False, "count": 0, "error": "database_url missing"}

        clauses = []
        params: dict[str, Any] = {}
        if ticker:
            clauses.append(f"UPPER({ticker_column_name}) = :ticker")
            params["ticker"] = ticker
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        try:
            engine = create_engine(self.database_url, pool_pre_ping=True)
            with engine.connect() as conn:
                row = conn.execute(
                    text(f"SELECT COUNT(1) AS count FROM {table_name}{where}"),
                    params,
                ).mappings().first()
            return {"available": True, "count": int(row["count"] if row else 0), "error": None}
        except Exception as exc:
            return {"available": False, "count": 0, "error": str(exc)}


def _capability(
    capability_id: str,
    label: str,
    *,
    status: ReadinessStatus,
    ready: bool,
    blockers: list[str] | None = None,
    evidence: dict[str, Any] | None = None,
    activation_actions: list[str] | None = None,
    answer_scope: str = "answer",
) -> dict[str, Any]:
    return {
        "id": capability_id,
        "label": label,
        "status": status,
        "ready": ready,
        "answer_scope": answer_scope,
        "blockers": blockers or [],
        "evidence": evidence or {},
        "activation_actions": activation_actions or [],
    }


def _status_from_count(
    count_result: dict[str, Any],
    *,
    missing_table_blocker: str,
    empty_blocker: str,
    activation_action: str,
) -> tuple[ReadinessStatus, bool, list[str], dict[str, Any], list[str]]:
    count = int(count_result.get("count") or 0)
    available = bool(count_result.get("available"))
    evidence = {
        "available": available,
        "row_count": count,
        "error": count_result.get("error"),
    }
    if not available:
        return "DATA_MISSING", False, [missing_table_blocker], evidence, [activation_action]
    if count <= 0:
        return "DATA_MISSING", False, [empty_blocker], evidence, [activation_action]
    return "READY", True, [], evidence, []


def _state_db_default_path() -> str:
    return (
        str(os.getenv("COCKPIT_STATE_DB") or "").strip()
        or str(Path.home() / ".financial_engine_cockpit" / "state.db")
    )


def _memory_root_default_path(settings_obj: Any) -> str:
    configured = str(os.getenv("TENN_RESEARCH_MEMORY_ROOT") or "").strip()
    if configured:
        return configured
    data_root = _str_setting(settings_obj, "data_root", str(PROJECT_ROOT / "data"))
    return str(Path(data_root).expanduser() / "reports" / "research_memory")


def _probe_holdings(state_db_path: str, ticker: str | None) -> dict[str, Any]:
    return _count_sqlite_rows(
        state_db_path,
        "holdings_items",
        ticker=ticker,
        ticker_column="ticker",
        where_sql="status != ?",
        where_params=("archived",),
    )


def _probe_memory(memory_root: str, ticker: str | None) -> dict[str, Any]:
    root = Path(memory_root).expanduser()
    probes = {
        "company_memory": _count_sqlite_rows(
            root / "company_memory.sqlite",
            "memory_entries",
            ticker=ticker,
            ticker_column="company_id",
            where_sql="status = ?",
            where_params=("active",),
        ),
        "user_thesis_memory": _count_sqlite_rows(
            root / "user_thesis_memory.sqlite",
            "thesis_entries",
            ticker=ticker,
            ticker_column="ticker",
            where_sql="status = ?",
            where_params=("active",),
        ),
    }
    if ticker:
        probes["market_memory"] = _count_sqlite_rows(
            root / "market_memory.sqlite",
            "sector_states",
            where_sql="status = ? AND linked_tickers_json LIKE ?",
            where_params=("active", f"%{ticker}%"),
        )
    else:
        probes["market_memory"] = _count_sqlite_rows(
            root / "market_memory.sqlite",
            "sector_states",
            where_sql="status = ?",
            where_params=("active",),
        )
    total = sum(int(item.get("count") or 0) for item in probes.values())
    return {
        "available": any(bool(item.get("available")) for item in probes.values()),
        "count": total,
        "error": "; ".join(
            str(item.get("error"))
            for item in probes.values()
            if item.get("error") and item.get("error") != "sqlite file missing"
        )
        or None,
        "stores": probes,
        "memory_root": str(root),
    }


def _probe_http_status(
    http_probe: HttpProbe | None,
    url: str,
    path: str,
) -> dict[str, Any]:
    if not http_probe:
        return {
            "ok": False,
            "latency_ms": 0.0,
            "error": "live_probe_not_configured",
            "endpoint": url,
            "path": path,
        }
    ok, latency_ms, error = http_probe(url, path)
    return {
        "ok": bool(ok),
        "latency_ms": latency_ms,
        "error": error,
        "endpoint": url,
        "path": path,
    }


def build_chat_readiness_status(
    *,
    ticker: str | None = None,
    settings_obj: Any = settings,
    sql_probe: Any | None = None,
    http_probe: HttpProbe | None = None,
    state_db_path: str | None = None,
    memory_root: str | None = None,
) -> dict[str, Any]:
    """Build a read-only, capability-scoped readiness contract for Cockpit chat."""

    normalized_ticker = _normalize_ticker(ticker)
    db_probe = sql_probe or ReadinessSqlProbe(_str_setting(settings_obj, "database_url"))
    capabilities: dict[str, dict[str, Any]] = {}

    financial_count = db_probe.count_rows(
        "asx_periodic_financials",
        ticker=normalized_ticker,
        ticker_column="ticker",
    )
    status, ready, blockers, evidence, activation = _status_from_count(
        financial_count,
        missing_table_blocker="asx_periodic_financials table unavailable",
        empty_blocker="no extracted financial rows for requested ticker",
        activation_action="Run reviewed metric extraction for the ticker before numeric financial questions.",
    )
    capabilities["financial_fact"] = _capability(
        "financial_fact",
        "Financial facts",
        status=status,
        ready=ready,
        blockers=blockers,
        evidence=evidence,
        activation_actions=activation,
    )

    document_count = db_probe.count_rows(
        "documents",
        ticker=normalized_ticker,
        ticker_column="ticker",
    )
    status, ready, blockers, evidence, activation = _status_from_count(
        document_count,
        missing_table_blocker="documents table unavailable",
        empty_blocker="no filings/documents for requested ticker",
        activation_action="Import/backfill reviewed ticker filings before filing-summary questions.",
    )
    capabilities["filing_document_summary"] = _capability(
        "filing_document_summary",
        "Filing and document summaries",
        status=status,
        ready=ready,
        blockers=blockers,
        evidence=evidence,
        activation_actions=activation,
    )

    rag_blockers: list[str] = []
    if not _bool_setting(settings_obj, "enable_embeddings"):
        rag_blockers.append("ENABLE_EMBEDDINGS=false")
    if not _bool_setting(settings_obj, "enable_qdrant"):
        rag_blockers.append("ENABLE_QDRANT=false")
    qdrant_url = _str_setting(settings_obj, "qdrant_url")
    qdrant_probe = {
        "ok": False,
        "latency_ms": 0.0,
        "error": "disabled" if rag_blockers else "not_configured",
        "endpoint": qdrant_url,
        "collection": _str_setting(settings_obj, "qdrant_collection"),
    }
    if not rag_blockers and qdrant_url:
        qdrant_probe = _probe_http_status(http_probe, qdrant_url, "/collections")
        qdrant_probe["collection"] = _str_setting(settings_obj, "qdrant_collection")
        if not qdrant_probe["ok"]:
            rag_blockers.append(str(qdrant_probe.get("error") or "qdrant probe failed"))
    elif not qdrant_url:
        rag_blockers.append("QDRANT_URL not configured")
    capabilities["local_news_rag"] = _capability(
        "local_news_rag",
        "Local news and RAG",
        status="READY" if not rag_blockers else "DATA_MISSING",
        ready=not rag_blockers,
        blockers=rag_blockers,
        evidence=qdrant_probe,
        activation_actions=[] if not rag_blockers else [
            "Enable embeddings and Qdrant, then verify /rag/query before local-news/RAG answers.",
        ],
    )

    holdings_probe = _probe_holdings(state_db_path or _state_db_default_path(), normalized_ticker)
    status, ready, blockers, evidence, activation = _status_from_count(
        holdings_probe,
        missing_table_blocker="cockpit holdings state unavailable",
        empty_blocker="no active holdings for requested ticker",
        activation_action="Attach/import a holdings CSV before portfolio-context questions.",
    )
    capabilities["portfolio_holdings_context"] = _capability(
        "portfolio_holdings_context",
        "Portfolio and holdings context",
        status=status,
        ready=ready,
        blockers=blockers,
        evidence=evidence,
        activation_actions=activation,
        answer_scope="local_personal_data",
    )

    if not _bool_setting(settings_obj, "enable_session_memory", True):
        capabilities["memory_context"] = _capability(
            "memory_context",
            "Memory context",
            status="DATA_MISSING",
            ready=False,
            blockers=["ENABLE_SESSION_MEMORY=false"],
            evidence={"enabled": False},
            activation_actions=["Enable session memory only for context; do not use it as numeric truth."],
            answer_scope="context_only",
        )
    else:
        memory_probe = _probe_memory(memory_root or _memory_root_default_path(settings_obj), normalized_ticker)
        status = "PARTIAL" if int(memory_probe.get("count") or 0) > 0 else "DATA_MISSING"
        capabilities["memory_context"] = _capability(
            "memory_context",
            "Memory context",
            status=status,
            ready=status == "PARTIAL",
            blockers=[] if status == "PARTIAL" else ["no active memory entries for requested ticker"],
            evidence=memory_probe,
            activation_actions=[] if status == "PARTIAL" else [
                "Capture memory through approved memory routes; treat it as context-only.",
            ],
            answer_scope="context_only",
        )

    capabilities["strategy_action_preview"] = _capability(
        "strategy_action_preview",
        "Strategy and action preview",
        status="READY",
        ready=True,
        blockers=[],
        evidence={
            "route": "/api/cockpit/action/preview",
            "confirmation_required": True,
            "live_preview_probe_performed": False,
        },
        activation_actions=[
            "Use action preview and explicit confirmation before any mutating action.",
        ],
        answer_scope="action_preview",
    )

    llamacpp_url = _str_setting(settings_obj, "llamacpp_url")
    model_probe = _probe_http_status(http_probe, llamacpp_url, "/v1/models")
    model_blockers = [] if model_probe["ok"] else [str(model_probe.get("error") or "model route unavailable")]
    capabilities["model_route_runtime"] = _capability(
        "model_route_runtime",
        "Model route and runtime",
        status="READY" if model_probe["ok"] else "DEGRADED",
        ready=bool(model_probe["ok"]),
        blockers=model_blockers,
        evidence=model_probe,
        activation_actions=[] if model_probe["ok"] else [
            "Start or repair the configured local model endpoint before relying on generated answers.",
        ],
    )

    core_for_normal_analysis = (
        "financial_fact",
        "filing_document_summary",
        "local_news_rag",
        "model_route_runtime",
    )
    normal_analysis_allowed = all(capabilities[key]["ready"] for key in core_for_normal_analysis)
    answer_ready = normal_analysis_allowed
    primary_blockers = [
        key for key in core_for_normal_analysis if not capabilities[key]["ready"]
    ]
    blocker_count = sum(len(item["blockers"]) for item in capabilities.values())
    ready_count = sum(1 for item in capabilities.values() if item["ready"])

    return {
        "schema_version": 1,
        "generated_at": _utc_now(),
        "generated_from": "read_only_chat_readiness_contract",
        "ticker": normalized_ticker,
        "answer_ready": answer_ready,
        "normal_analysis_allowed": normal_analysis_allowed,
        "capabilities": capabilities,
        "summary": {
            "ready_capability_count": ready_count,
            "capability_count": len(capabilities),
            "blocker_count": blocker_count,
            "primary_blockers": primary_blockers,
            "normal_analysis_requires": list(core_for_normal_analysis),
            "safe_activation_actions": [
                action
                for capability in capabilities.values()
                for action in capability.get("activation_actions", [])
            ],
        },
        "reporting_contract": {
            "forbidden_actions_performed": [],
            "read_only": True,
            "no_repair_or_backfill_performed": True,
            "memory_context_is_context_only": True,
        },
    }
