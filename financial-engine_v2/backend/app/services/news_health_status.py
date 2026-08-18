"""Read-only status contract for news/A2M health surfaces."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app.core.config import PROJECT_ROOT
from shared.news_artifacts import resolve_news_artifact_root


A2M_NEWS_HEALTH_STATUS: dict[str, str] = {
    "qdrant_retrieval": "ok",
    "canonical_sqlite_projection": "missing",
    "legacy_sqlite_projection": "evidence_present_not_current_consumer",
    "cockpit_query_route": "ok_via_rag_query",
    "cockpit_status_routes": "implemented",
    "chat_synthesis": "DATA_MISSING",
    "projection_repair": "not_run",
}

DO_NOT_REPORT = (
    "A2M missing",
    "A2M projection fixed",
    "legacy SQLite is canonical",
    "chat synthesis proven",
)

STATIC_DO_REPORT = (
    "A2M is visible through Qdrant-backed /rag/query according to the "
    "integrated read-only smoke.",
    "Legacy SQLite evidence exists but is provenance-only, not the "
    "canonical current consumer.",
    "Cockpit query route reachability works through /rag/query.",
    "Cockpit/news health status is represented by /api/cockpit/news/status.",
    "Projection repair/rebuild has not run and must stay a separate task.",
    "Chat synthesis remains DATA_MISSING until a separate safe smoke proves it.",
)

CANONICAL_SQLITE_PROJECTION_PATHS = (
    "news.sqlite",
    "news_articles.sqlite",
)

EVIDENCE_REPORT_PATHS = {
    "a2m_projection_path_remediation": (
        "reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/"
        "status.json"
    ),
    "a2m_readonly_smoke": (
        "reports/agent_jobs/a2m_news_projection_readonly_smoke_v1_20260525/"
        "status.json"
    ),
    "a2m_canonical_integration": (
        "reports/agent_jobs/"
        "a2m_news_projection_canonical_integration_and_status_reporting_v1_20260525/"
        "status.json"
    ),
    "a2m_status_reporting": (
        "reports/agent_jobs/"
        "a2m_news_projection_status_reporting_safe_extension_v1_20260525/"
        "status.json"
    ),
}


def _default_workspace_root() -> Path:
    override = os.getenv("COCKPIT_WORKSPACE_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return PROJECT_ROOT.parent.resolve()


def _default_news_artifact_root(workspace_root: Path) -> tuple[Path, str]:
    return resolve_news_artifact_root(workspace_root=workspace_root)


def _path_status(news_artifact_root: Path, relative_path: str) -> dict[str, Any]:
    path = news_artifact_root / relative_path
    return {
        "path": relative_path,
        "absolute_path": str(path),
        "exists": path.exists(),
    }


def _canonical_sqlite_status(news_artifact_root: Path) -> tuple[str, list[dict[str, Any]]]:
    paths = [
        _path_status(news_artifact_root, relative_path)
        for relative_path in CANONICAL_SQLITE_PROJECTION_PATHS
    ]
    existing_count = sum(1 for item in paths if item["exists"])
    if existing_count == 0:
        return "missing", paths
    if existing_count == len(paths):
        return "present", paths
    return "partial", paths


def _do_report(canonical_status: str) -> list[str]:
    if canonical_status == "missing":
        canonical_message = "Canonical NVMe SQLite projection files are absent."
    elif canonical_status == "partial":
        canonical_message = "Canonical NVMe SQLite projection files are partially present."
    else:
        canonical_message = "Canonical NVMe SQLite projection files are present."
    return [*STATIC_DO_REPORT[:1], canonical_message, *STATIC_DO_REPORT[1:]]


def _redacted_operator_diagnostics() -> dict[str, str]:
    return {
        "status": "redacted",
        "reason": "operator_diagnostics_only",
    }


def _public_news_artifact_root_source(source: object) -> str:
    source_text = str(source or "unknown")
    if "/" in source_text or "\\" in source_text:
        return "resolved_live_artifact_root"
    return source_text


def _redact_public_news_health_status(payload: dict[str, Any]) -> dict[str, Any]:
    public_payload = dict(payload)
    news_artifact_root = payload.get("news_artifact_root")
    root_source = (
        news_artifact_root.get("source")
        if isinstance(news_artifact_root, dict)
        else "unknown"
    )
    public_payload["news_artifact_root"] = {
        "status": "redacted",
        "source": _public_news_artifact_root_source(root_source),
    }
    public_payload["canonical_sqlite_projection_paths"] = _redacted_operator_diagnostics()
    public_payload["evidence_reports"] = _redacted_operator_diagnostics()

    qdrant_status = dict(public_payload.get("qdrant_retrieval") or {})
    qdrant_status.pop("collection", None)
    public_payload["qdrant_retrieval"] = qdrant_status
    return public_payload


def build_a2m_news_health_status(
    workspace_root: Path | None = None,
    *,
    include_diagnostics: bool = False,
) -> dict[str, Any]:
    """Build a read-only A2M/news status payload without live data mutation."""

    root = (workspace_root or _default_workspace_root()).resolve()
    if workspace_root is not None:
        news_artifact_root = (root / "reports" / "qual_context").resolve()
        news_artifact_root_source = "workspace_root_argument"
    else:
        news_artifact_root, news_artifact_root_source = _default_news_artifact_root(root)
    canonical_status, canonical_paths = _canonical_sqlite_status(news_artifact_root)
    health = dict(A2M_NEWS_HEALTH_STATUS)
    health["canonical_sqlite_projection"] = canonical_status

    payload: dict[str, Any] = {
        "schema_version": 1,
        "status": "ok",
        "generated_from": "read_only_status_contract",
        "live_probe_performed": False,
        "a2m_news_health": health,
        "news_artifact_root": {
            "path": str(news_artifact_root),
            "source": news_artifact_root_source,
        },
        "canonical_sqlite_projection_paths": canonical_paths,
        "legacy_sqlite_projection": {
            "status": "evidence_present_not_current_consumer",
            "consumer_status": "not_current_consumer",
            "evidence_scope": "prior_readonly_smoke_and_integrated_reports",
            "live_legacy_db_read_performed": False,
        },
        "qdrant_retrieval": {
            "status": "ok",
            "consumer_route": "/rag/query",
            "collection": "news_chunks",
            "evidence_scope": "prior_readonly_smoke_and_integrated_reports",
            "live_qdrant_probe_performed": False,
        },
        "routes": {
            "backend_rag_query": {
                "route": "POST /rag/query",
                "status": "implemented",
                "news_source": "Qdrant-backed news_chunks",
            },
            "backend_api_cockpit_news_status": {
                "route": "GET /api/cockpit/news/status",
                "status": "implemented",
            },
            "backend_api_news_status": {
                "route": "GET /api/news/status",
                "status": "intentionally_absent_in_current_profile",
            },
            "backend_api_cockpit_status": {
                "route": "GET /api/cockpit/status",
                "status": "missing_not_required_by_this_contract",
            },
            "next_rag_query": {
                "route": "POST /rag/query",
                "status": "available_via_next_rewrite",
            },
            "next_api_cockpit_news_status": {
                "route": "GET /api/cockpit/news/status",
                "status": "available_via_next_api_rewrite_when_backend_is_reachable",
            },
        },
        "chat_synthesis": {
            "status": "DATA_MISSING",
            "reason": "No separate safe chat synthesis smoke was run; chat/session paths may write state.",
        },
        "projection_repair": {
            "status": "not_run",
            "forbidden_here": True,
        },
        "evidence_reports": {
            name: _path_status(root, relative_path)
            for name, relative_path in EVIDENCE_REPORT_PATHS.items()
        },
        "reporting_contract": {
            "do_report": _do_report(canonical_status),
            "do_not_report": list(DO_NOT_REPORT),
        },
    }
    if include_diagnostics:
        return payload
    return _redact_public_news_health_status(payload)
