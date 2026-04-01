from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Any, Callable

# Import cockpit core logic
from cockpit.core.actions import ActionRegistry
from cockpit.core.chat import ChatController, ChatResponse
from cockpit.core.config import DEFAULT_CONFIG, load_env
from cockpit.core.tools import ToolRouter
from cockpit.integrations.llamacpp_client import LlamaCppClient
from cockpit.storage.state import StateStore
from cockpit.storage.artifacts import ArtifactStore

from app.core.config import settings

logger = logging.getLogger(__name__)

class CockpitService:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        # Load environment from financial-engine_v2 root
        repo_root = Path(__file__).resolve().parents[3]
        load_env(repo_root)
        
        # Initialize storage
        storage_dir = Path.home() / ".financial_engine_cockpit"
        storage_dir.mkdir(parents=True, exist_ok=True)
        self.state_store = StateStore(str(storage_dir / "state.db"))
        self.artifact_store = ArtifactStore(str(storage_dir / "artifacts"))
        
        # Initialize LLM client (using llama.cpp)
        self.llm_client = LlamaCppClient(
            base_url=settings.llamacpp_url,
            model=settings.llm_model,
        )
        
        # Initialize Action Registry
        self.action_registry = ActionRegistry(
            # Pass any required config
        )
        
        # Initialize Tool Router
        # Note: In a production environment, we'd want to inject the backend's 
        # actual service instances here instead of creating wrappers.
        # For now, we'll use the TUI's logic but point it at our own backend.
        from cockpit.integrations.backend_api import BackendApiClient
        self.backend_api_client = BackendApiClient(base_url="http://localhost:8000")
        
        self.tool_router = ToolRouter(
            backend_api_client=self.backend_api_client,
            # Add other necessary integrations if needed
        )
        
        # Initialize Chat Controller
        self.chat_controller = ChatController(
            ollama_client=self.llm_client,
            tool_router=self.tool_router,
            action_registry=self.action_registry,
            state_store=self.state_store,
            cockpit_llm=DEFAULT_CONFIG["llm"],
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
