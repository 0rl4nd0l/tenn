from __future__ import annotations

import logging
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

# Import cockpit core logic
from cockpit.core.actions import ActionRegistry
from cockpit.core.chat import ChatController, ChatResponse
from cockpit.core.config import DEFAULT_CONFIG, load_env
from cockpit.core.tools import ToolRouter
from cockpit.integrations.backend_api import BackendApiClient
from cockpit.integrations.db_reader import DbReader
from cockpit.integrations.file_indexer import FileIndexer
from cockpit.integrations.llamacpp_client import LlamaCppClient
from cockpit.integrations.web_fetcher import WebFetcher
from cockpit.storage.state import StateStore
from cockpit.storage.artifacts import ArtifactStore

from app.core.config import settings
from app.services.llamacpp_runtime import resolve_llm_runtime_config

logger = logging.getLogger(__name__)

class CockpitService:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        # Load environment from financial-engine_v2 root
        repo_root = Path(__file__).resolve().parents[3]
        load_env(repo_root)

        config = deepcopy(DEFAULT_CONFIG)
        config["paths"]["allow_roots"] = [str(repo_root)]
        config["paths"]["default_workspace"] = str(repo_root)
        config["memory"]["state_db"] = str(Path.home() / ".financial_engine_cockpit" / "state.db")
        config["backend"]["api_base_url"] = "http://localhost:8000"

        self.repo_root = repo_root
        self.artifact_store = ArtifactStore(
            repo_root=repo_root,
            exports_dir=config["exports"]["dir"],
            reports_dir=config["reports"]["dir"],
        )
        self.state_store = StateStore(config["memory"]["state_db"])
        self.db_reader = DbReader(settings.database_url)
        self.file_indexer = FileIndexer(config["paths"]["allow_roots"])
        self.web_fetcher = WebFetcher()

        llm_url, llm_model = resolve_llm_runtime_config(
            base_url=settings.llamacpp_url,
            model=None,
        )
        self.llm_client = LlamaCppClient(
            llm_url,
            llm_model,
            api_key=str(config["llm"].get("llamacpp_api_key", "")),
        )

        self.action_registry = ActionRegistry(
            repo_root=repo_root,
            confirm_required=config["actions"].get("confirm_required", True),
        )
        self.backend_api_client = BackendApiClient(
            base_url=str(config["backend"]["api_base_url"]),
        )
        self.tool_router = ToolRouter(
            db_reader=self.db_reader,
            file_indexer=self.file_indexer,
            web_fetcher=self.web_fetcher,
            repo_root=repo_root,
            web_default_enabled=config["web"].get("enabled_default", False),
            backend_api_client=self.backend_api_client,
            state_store=self.state_store,
        )
        self.chat_controller = ChatController(
            ollama_client=self.llm_client,
            tool_router=self.tool_router,
            action_registry=self.action_registry,
            llm_timeout_seconds=float(config["llm"].get("timeout_seconds", 300)),
            state_store=self.state_store,
            thread_id="global-main",
            cockpit_llm=None,
        )

        logger.info("CockpitService initialized successfully")

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
        on_chunk: Callable[[str], None] | None = None
    ) -> ChatResponse:
        """Run a chat turn and return the full response, while optionally streaming chunks."""
        return self.chat_controller.build_chat_response(
            message=message,
            prior_ticker=ticker,
            on_chunk=on_chunk,
        )
