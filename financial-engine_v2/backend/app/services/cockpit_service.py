from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Any, Callable

# Import cockpit core logic
from cockpit.core.actions import ActionRegistry
from cockpit.core.chat import ChatController, ChatResponse
from cockpit.core.config import RuntimeFlags, apply_runtime_flags, load_config, load_env
from cockpit.core.tools import ToolRouter
from cockpit.integrations.backend_api import BackendApiClient
from cockpit.integrations.db_reader import DbReader
from cockpit.integrations.file_indexer import FileIndexer
from cockpit.integrations.llamacpp_client import LlamaCppClient
from cockpit.integrations.qual_context_bootstrap import (
    build_qual_context_reader,
    context_enabled,
)
from cockpit.integrations.web_fetcher import WebFetcher
from cockpit.storage.state import StateStore
from cockpit.storage.artifacts import ArtifactStore

logger = logging.getLogger(__name__)


def _env_flag(name: str, default: bool = False) -> bool:
    raw = str(os.getenv(name, "")).strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on", "y"}


def _normalize_database_url(repo_root: Path, database_url: str) -> str:
    value = (database_url or "").strip()
    if not value:
        value = "sqlite:///./data/fe_local.db"

    if value.startswith("sqlite:///"):
        path_part = value[len("sqlite:///") :]
        if path_part.startswith("./") or not path_part.startswith("/"):
            resolved = (repo_root / path_part).resolve()
            resolved.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{resolved}"

        abs_path = Path(path_part)
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        return value

    return value


class CockpitService:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        repo_root = Path(__file__).resolve().parents[3]
        load_env(repo_root)

        config_path_value = str(
            os.getenv("COCKPIT_CONFIG") or "config/cockpit.yaml"
        ).strip()
        config_path = Path(config_path_value)
        if not config_path.is_absolute():
            config_path = (repo_root / config_path).resolve()

        cfg = load_config(str(config_path))
        cfg = apply_runtime_flags(
            cfg,
            RuntimeFlags(
                config_path=str(config_path),
                profile=str(os.getenv("COCKPIT_PROFILE") or "default").strip()
                or "default",
                read_only=_env_flag("COCKPIT_READ_ONLY", False),
                no_web=_env_flag("COCKPIT_NO_WEB", False),
                repo_root=repo_root,
            ),
        )

        db_cfg = cfg.get("db") if isinstance(cfg.get("db"), dict) else {}
        db_url = _normalize_database_url(
            repo_root, str(db_cfg.get("database_url") or "")
        )
        cfg.setdefault("db", {})
        cfg["db"]["database_url"] = db_url

        llm_cfg = cfg.get("llm") if isinstance(cfg.get("llm"), dict) else {}
        llm_provider = str(llm_cfg.get("provider") or "llamacpp").strip().lower()
        llm_model = str(llm_cfg.get("model") or "").strip()
        if llm_provider == "llamacpp":
            llm_url = str(llm_cfg.get("llamacpp_url") or "").strip()
        else:
            llm_url = str(
                llm_cfg.get("llamacpp_url") or llm_cfg.get("ollama_url") or ""
            ).strip()

        backend_cfg = cfg.get("backend") if isinstance(cfg.get("backend"), dict) else {}
        backend_api_url = str(backend_cfg.get("api_base_url") or "").strip()

        self.repo_root = repo_root
        self.config = cfg
        self.artifact_store = ArtifactStore(
            repo_root=repo_root,
            exports_dir=cfg["exports"]["dir"],
            reports_dir=cfg["reports"]["dir"],
        )
        self.state_store = StateStore(cfg["memory"]["state_db"])
        self.db_reader = DbReader(db_url)
        self.file_indexer = FileIndexer(cfg["paths"]["allow_roots"])
        self.web_fetcher = WebFetcher()

        self.llm_client = LlamaCppClient(
            llm_url,
            llm_model,
            api_key=str(llm_cfg.get("llamacpp_api_key") or ""),
        )

        self.action_registry = ActionRegistry(
            repo_root=repo_root,
            confirm_required=cfg["actions"].get("confirm_required", True),
        )

        self.backend_api_client = None
        if backend_api_url:
            self.backend_api_client = BackendApiClient(
                base_url=backend_api_url,
                api_key=str(backend_cfg.get("api_key") or "").strip(),
            )

        rag_cfg = cfg.get("rag") if isinstance(cfg.get("rag"), dict) else {}
        qual_company = None
        qual_news = None
        if self.backend_api_client is not None:
            qc_cfg = (
                rag_cfg.get("qualitative_context")
                if isinstance(rag_cfg.get("qualitative_context"), dict)
                else None
            )
            if context_enabled(qc_cfg, default=False):
                try:
                    qual_company = build_qual_context_reader(
                        repo_root=repo_root,
                        qc_cfg=qc_cfg,
                        backend_api_client=self.backend_api_client,
                        context_name="qualitative_context",
                    )
                except Exception as exc:
                    logger.warning(
                        "CockpitService: qual_context (company) disabled: %s", exc
                    )

            news_cfg = (
                rag_cfg.get("news_context")
                if isinstance(rag_cfg.get("news_context"), dict)
                else None
            )
            if context_enabled(news_cfg, default=False):
                try:
                    qual_news = build_qual_context_reader(
                        repo_root=repo_root,
                        qc_cfg=news_cfg,
                        backend_api_client=self.backend_api_client,
                        context_name="news_context",
                    )
                except Exception as exc:
                    logger.warning(
                        "CockpitService: qual_context (news) disabled: %s", exc
                    )

        self.tool_router = ToolRouter(
            db_reader=self.db_reader,
            file_indexer=self.file_indexer,
            web_fetcher=self.web_fetcher,
            repo_root=repo_root,
            web_default_enabled=cfg["web"].get("enabled_default", False),
            backend_api_client=self.backend_api_client,
            qual_context_company_reader=qual_company,
            qual_context_news_reader=qual_news,
            state_store=self.state_store,
        )
        self.chat_controller = ChatController(
            ollama_client=self.llm_client,
            tool_router=self.tool_router,
            action_registry=self.action_registry,
            llm_timeout_seconds=float(llm_cfg.get("timeout_seconds", 300)),
            state_store=self.state_store,
            thread_id="global-main",
            cockpit_llm=cfg.get("cockpit_llm"),
        )

        logger.info("CockpitService initialized successfully (config=%s)", config_path)

    @classmethod
    def get_instance(cls) -> CockpitService:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def chat_stream(
        self,
        message: str,
        ticker: str | None = None,
        session_id: str | None = None,
        on_chunk: Callable[[str], None] | None = None,
        on_status: Callable[[str], None] | None = None,
        enable_web: bool | None = None,
        model: str | None = None,
    ) -> ChatResponse:
        """Run a chat turn and return the full response, while optionally streaming chunks."""
        return self.chat_controller.build_chat_response(
            message=message,
            enable_web=bool(enable_web) if enable_web is not None else False,
            prior_ticker=ticker,
            on_chunk=on_chunk,
            on_status=on_status,
        )
