from __future__ import annotations

import os
from pathlib import Path


NEWS_ARTIFACT_ROOT_ENV = "TENN_NEWS_ARTIFACT_ROOT"
NEWS_ARTICLES_DB_ENV = "TENN_NEWS_ARTICLES_DB"
NEWS_CONTEXT_DB_ENV = "TENN_NEWS_CONTEXT_DB"
NEWS_RUNS_ROOT_ENV = "TENN_NEWS_RUNS_ROOT"

LIVE_NEWS_ARTIFACT_ROOT_CANDIDATES: tuple[Path, ...] = (
    Path("/workspace-reports") / "qual_context",
    Path("/reports") / "qual_context",
    Path("/workspace") / "reports" / "qual_context",
    Path("/mnt/tenn-nvme2") / "tenn" / "financial-engine_v2" / "reports" / "qual_context",
)


def env_path(name: str) -> Path | None:
    raw = str(os.getenv(name) or "").strip()
    if not raw:
        return None
    return Path(raw).expanduser().resolve()


def resolve_news_artifact_root(
    *,
    repo_root: Path | None = None,
    workspace_root: Path | None = None,
    prefer_workspace: bool = False,
) -> tuple[Path, str]:
    env_root = env_path(NEWS_ARTIFACT_ROOT_ENV)
    if env_root is not None:
        return env_root, NEWS_ARTIFACT_ROOT_ENV

    if prefer_workspace and workspace_root is not None:
        return (workspace_root / "reports" / "qual_context").resolve(), "workspace_root_argument"

    for candidate in LIVE_NEWS_ARTIFACT_ROOT_CANDIDATES:
        try:
            if candidate.exists():
                resolved = candidate.resolve()
                return resolved, str(resolved)
        except OSError:
            continue

    if workspace_root is not None:
        return (workspace_root / "reports" / "qual_context").resolve(), "workspace_default"
    if repo_root is not None:
        return (repo_root / "reports" / "qual_context").resolve(), "repo_default"
    return (Path.cwd() / "reports" / "qual_context").resolve(), "cwd_default"


def default_news_articles_db(news_artifact_root: Path) -> Path:
    return env_path(NEWS_ARTICLES_DB_ENV) or (news_artifact_root / "news_articles.sqlite")


def default_news_context_db(news_artifact_root: Path) -> Path:
    return env_path(NEWS_CONTEXT_DB_ENV) or (news_artifact_root / "news.sqlite")


def default_news_runs_root(news_artifact_root: Path) -> Path:
    return env_path(NEWS_RUNS_ROOT_ENV) or (news_artifact_root / "news_runs")
