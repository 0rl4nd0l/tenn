from __future__ import annotations

import json
import logging
import os
import re
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

try:
    from enum import StrEnum
except ImportError:  # Python < 3.11
    from enum import Enum

    class StrEnum(str, Enum):  # type: ignore[no-redef]
        pass


from pathlib import Path

logger = logging.getLogger(__name__)
from typing import Any

try:
    from cockpit.core.agent.memory.store import MemoryStore
except ImportError:
    MemoryStore = None  # type: ignore[misc,assignment]

from cockpit.core.config import effective_anthropic_api_key, load_env
from cockpit.core.session_memory import (
    _log_startup_status as _ov_log_startup_status,
    build_turn_payload,
    get_session_context,
    record_turn,
)
from cockpit.core.backend_proposals import (
    build_backend_access_proposal_request,
    build_backend_runtime_remediation_request,
)
from cockpit.core.agent_loop import parse_backend_prefix
from cockpit.core.action_preview import normalize_action_preview
from cockpit.core.command_router import CommandRoute, route_command
from cockpit.core.conversation_commands import derive_conversational_command
from cockpit.core.request_standards import (
    build_request_standard_prompt_guidance,
    select_request_standard_type,
)
from cockpit.core.sources import SourcesFormatter
from shared.ticker_inference import COMMON_TICKER_STOPWORDS, detect_primary_ticker


class ResponseMode(StrEnum):
    FAST = "fast"
    DEEP_ANALYSIS = "deep_analysis"
    ACTION = "action"
    VERIFICATION = "verification"
    WEB = "web"


@dataclass
class ChatResponse:
    text: str
    evidence: list[dict[str, Any]]
    action_preview: dict[str, Any] | None = None
    mode: str = ResponseMode.FAST
    prompt: str | None = None
    routing_metadata: dict[str, Any] | None = None
    tool_traces: list[dict[str, Any]] | None = None


@dataclass
class _ContextResult:
    """Lightweight result wrapper for gather_local_context calls."""

    payload: dict[str, Any]
    ok: bool = True


@dataclass
class _AttachedSourceBundle:
    context: str = ""
    evidence: list[dict[str, Any]] = field(default_factory=list)
    unresolved_ids: list[str] = field(default_factory=list)


STAGED_CHUNKS_DIR = Path("~/.tenn/memory/staged_chunks").expanduser()
ATTACHED_SOURCE_MAX_CHARS = 3_500
ATTACHED_SOURCE_TOTAL_MAX_CHARS = 8_000
ATTACHED_SOURCE_MAX_SEGMENTS = 6


def _apply_backend_prefix(message: str, force_backend: str | None) -> str:
    text = str(message or "").strip()
    if force_backend == "api":
        return f"/cloud {text}" if text else "/cloud"
    if force_backend == "local":
        return f"/local {text}" if text else "/local"
    return message


def _normalize_attached_source_kind(raw: Any) -> str:
    cleaned = str(raw or "").strip().lower()
    if cleaned in {"ephemeral", "concat", "primary"}:
        return cleaned
    return "concat"


def _load_staged_attachment_rows(source_id: str) -> list[dict[str, Any]]:
    path = STAGED_CHUNKS_DIR / f"{source_id}.jsonl"
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for raw_line in path.read_text("utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                rows.append(payload)
    except (OSError, json.JSONDecodeError):
        logger.warning("Failed to read staged attachment source %s", source_id)
        return []
    return rows


def _build_attached_source_bundle(
    attached_sources: list[dict[str, Any]] | None,
) -> _AttachedSourceBundle:
    if not attached_sources:
        return _AttachedSourceBundle()

    sections: list[str] = []
    evidence: list[dict[str, Any]] = []
    unresolved_ids: list[str] = []
    total_chars = 0
    for item in attached_sources:
        if not isinstance(item, dict):
            continue
        source_id = str(item.get("source_id") or "").strip()
        if not source_id:
            continue
        source_kind = _normalize_attached_source_kind(item.get("source_kind"))
        rows = _load_staged_attachment_rows(source_id)
        if not rows:
            unresolved_ids.append(source_id)
            continue

        first_payload = (
            rows[0].get("payload") if isinstance(rows[0].get("payload"), dict) else rows[0]
        )
        if not isinstance(first_payload, dict):
            unresolved_ids.append(source_id)
            continue

        title = str(first_payload.get("source_name") or source_id).strip() or source_id
        source_type = (
            str(first_payload.get("source_type") or "attached_source").strip()
            or "attached_source"
        )
        published_at = str(first_payload.get("published_at") or "").strip()

        segments: list[str] = []
        seen_texts: set[str] = set()
        source_chars = 0
        truncated = False
        for row in rows:
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else row
            if not isinstance(payload, dict):
                continue
            text = re.sub(r"\s+", " ", str(payload.get("text") or "")).strip()
            if not text:
                continue
            key = text.lower()
            if key in seen_texts:
                continue
            seen_texts.add(key)
            remaining = ATTACHED_SOURCE_MAX_CHARS - source_chars
            if remaining <= 0 or len(segments) >= ATTACHED_SOURCE_MAX_SEGMENTS:
                truncated = True
                break
            if len(text) > remaining:
                text = text[: max(remaining - 3, 0)].rstrip()
                if text:
                    text += "..."
                truncated = True
            if not text:
                continue
            segments.append(text)
            source_chars += len(text)

        if not segments:
            unresolved_ids.append(source_id)
            continue

        excerpt = "\n".join(f"- {segment}" for segment in segments)
        if total_chars + len(excerpt) > ATTACHED_SOURCE_TOTAL_MAX_CHARS:
            remaining_total = ATTACHED_SOURCE_TOTAL_MAX_CHARS - total_chars
            if remaining_total < 120:
                break
            excerpt = excerpt[: max(remaining_total - 3, 0)].rstrip()
            if excerpt:
                excerpt += "..."
            truncated = True

        total_chars += len(excerpt)
        truncated_note = "\n[truncated]" if truncated else ""
        sections.append(
            f"[{title}] source_id={source_id} kind={source_kind}\n{excerpt}{truncated_note}"
        )
        evidence.append(
            {
                "type": "attached_source",
                "details": {
                    "title": title,
                    "source_id": source_id,
                    "source_kind": source_kind,
                    "snippet": segments[0][:240],
                    "sources": {
                        "rag_hits": [
                            {
                                "title": title,
                                "source_id": source_id,
                                "score": 1.0,
                                "doc_type": source_type,
                                "published_at": published_at,
                                "text": "\n".join(segments),
                            }
                        ]
                    },
                },
            }
        )

    if not sections:
        return _AttachedSourceBundle(unresolved_ids=unresolved_ids)

    return _AttachedSourceBundle(
        context=(
            "Attached source evidence provided by the user. "
            "Treat it as current-turn evidence:\n\n"
            + "\n\n".join(sections)
        ),
        evidence=evidence,
        unresolved_ids=unresolved_ids,
    )


ACTION_KEYWORDS = {
    "full_history": ["backfill", "full history", "history sync"],
    "update_ticker_financials": [
        "refresh financials",
        "update financial data",
        "financial refresh",
    ],
    "rebuild_ticker_financials": [
        "rebuild financials",
        "rebuild ticker financials",
        "reprocess docs financials",
    ],
    "audit_ticker_financials": [
        "audit financials",
        "financial qa",
        "check financial quality",
    ],
    "daily_news_ingest": [
        "daily news ingest",
        "ingest daily news",
        "run news ingestion",
        "news ingestion",
        "news ingewstion",
        "today news ingest",
    ],
    "historical_news_ingest": [
        "historical news ingest",
        "news backfill",
        "backfill news",
        "news history ingest",
    ],
    "load_news_to_qdrant": [
        "load news to qdrant",
        "sync news chunks to qdrant",
        "news to qdrant",
        "push news to qdrant",
        "upload news chunks",
    ],
    "daily_announcement_ingest": [
        "daily announcement ingest",
        "daily announcements",
        "daily asx announcements",
        "asx announcements today",
    ],
    "single_ticker_announcement_backfill": [
        "single ticker backfill",
        "ticker announcement backfill",
        "backfill ticker announcements",
        "refresh announcements",
        "update announcements",
    ],
    "universe_announcement_enrichment_backfill": [
        "asx enrichment chunked",
        "chunked enrichment",
        "5 year asx enrichment",
        "universe announcement backfill",
        "announcement enrichment backfill",
    ],
    "metric_extraction": [
        "metric extraction",
        "extract metrics",
        "extract financial metrics",
        "financial metric extraction",
    ],
    "sort_asx_docs": [
        "sort asx docs",
        "classify announcements",
        "sort announcements",
        "organise asx docs",
    ],
    "resume_pending": ["resume pending", "retry pending", "pending downloads"],
    "recover_headed": ["recover headed", "headed recovery"],
}


class ChatController:
    _ASX_TIMEZONE = ZoneInfo("Australia/Sydney")

    def __init__(
        self,
        ollama_client,
        tool_router,
        action_registry,
        llm_timeout_seconds: float = 300.0,
        state_store=None,
        thread_id: str = "global-main",
        memory_store=None,
        cockpit_llm: dict[str, Any] | None = None,
        repo_root: Path | None = None,
        query_orchestrator=None,
    ) -> None:
        # Same .env as backend (financial-engine_v2/.env) — must run before ANTHROPIC_* checks.
        load_env(Path(__file__).resolve().parents[2])

        self.repo_root = repo_root or Path(__file__).resolve().parents[2]
        self.ollama_client = ollama_client
        self.tool_router = tool_router
        self.action_registry = action_registry
        self._cockpit_llm: dict[str, Any] = dict(cockpit_llm or {})
        self.llm_timeout_seconds = float(llm_timeout_seconds)
        self.last_ticker: str | None = None
        self._state_store = state_store
        self._thread_id = thread_id
        self._memory = memory_store
        self._query_orchestrator = query_orchestrator
        self._ov_session_id: str = self._load_or_create_session_id()
        self._latest_sources_payloads: list[dict[str, Any]] = []
        self._recent_youtube_video_options: list[dict[str, Any]] = []
        _ov_log_startup_status()
        # Prevents concurrent context-gather calls from stacking up.
        self._context_gather_lock = threading.Lock()

        # Agent loop — default mode since agent routing is the canonical path.
        # COCKPIT_AGENT_MODE=keyword reverts to legacy Ollama-direct path.
        self._agent_loop = None
        self._hybrid_router = None
        self._dossier_service = None
        self._strategy_service = None
        if state_store is not None:
            try:
                from cockpit.core.strategy import StrategyService

                self._strategy_service = StrategyService(state_store)
            except Exception as exc:
                logger.warning("StrategyService init failed: %s", exc)
        agent_mode = os.environ.get("COCKPIT_AGENT_MODE", "structured")
        if agent_mode == "structured":
            try:
                from cockpit.core.agent.hybrid_router import HybridRouter
                from cockpit.core.agent_loop import AgentLoop
                from cockpit.core.tool_executor import ToolExecutor

                # Build HybridRouter with local llama.cpp client + optional API client.
                api_client = None
                anthropic_api_key = effective_anthropic_api_key(self._cockpit_llm)
                if anthropic_api_key:
                    try:
                        from cockpit.core.agent.anthropic_client import AnthropicClient

                        defaults = (
                            self._cockpit_llm.get("defaults")
                            if isinstance(self._cockpit_llm.get("defaults"), dict)
                            else {}
                        )
                        anthropic_model = (
                            os.environ.get("ANTHROPIC_MODEL", "").strip()
                            or str(defaults.get("anthropic_model") or "").strip()
                        )
                        api_client = (
                            AnthropicClient(
                                model=anthropic_model,
                                api_key=anthropic_api_key,
                            )
                            if anthropic_model
                            else AnthropicClient(api_key=anthropic_api_key)
                        )
                    except Exception as exc:
                        logger.warning("AnthropicClient init failed: %s", exc)

                from cockpit.core.llm_profile import resolve_hybrid_router_policy

                # Import GPU activity checker so HybridRouter can route chat
                # to the cloud API while extraction or another GPU-heavy task
                # owns the local llama.cpp runtime.
                gpu_exclusive_checker = None
                extraction_checker = None
                try:
                    from app.services.router_state import is_gpu_exclusive_active

                    gpu_exclusive_checker = is_gpu_exclusive_active
                except Exception:
                    pass  # Backend not available (e.g. standalone cockpit)
                if gpu_exclusive_checker is None:
                    try:
                        from app.services.router_state import is_extraction_active

                        extraction_checker = is_extraction_active
                    except Exception:
                        pass  # Backend not available (e.g. standalone cockpit)

                gpu_preemption_checker = None
                try:
                    from cockpit.integrations.llamacpp_manager import (
                        check_chat_gpu_preemption,
                    )

                    llm_base_url = str(getattr(ollama_client, "base_url", "") or "")
                    chat_port = urlparse(llm_base_url).port or 8001

                    def _gpu_preemption_checker() -> str | None:
                        state = check_chat_gpu_preemption(str(chat_port))
                        if bool(state.get("should_defer")):
                            return str(state.get("reason") or "gpu_preempted")
                        return None

                    gpu_preemption_checker = _gpu_preemption_checker
                except Exception:
                    pass

                hybrid_router = HybridRouter(
                    llm_client=ollama_client,
                    api_client=api_client,
                    policy=resolve_hybrid_router_policy(
                        api_available=api_client is not None,
                        cockpit_llm=self._cockpit_llm,
                    ),
                    llm_timeout=self.llm_timeout_seconds,
                    extraction_active_fn=extraction_checker,
                    gpu_exclusive_active_fn=gpu_exclusive_checker,
                    gpu_preemption_fn=gpu_preemption_checker,
                )
                self._hybrid_router = hybrid_router

                # Research capabilities — Brave Search, HN, dossier.
                brave_client = None
                hn_client = None
                dossier_svc = None
                deep_runner = None
                try:
                    from cockpit.integrations.brave_search import BraveSearchClient

                    brave_client = BraveSearchClient(
                        web_fetcher=tool_router.web_fetcher
                    )
                    tool_router.brave_search_client = brave_client
                except Exception as exc:
                    logger.warning("BraveSearchClient init failed: %s", exc)
                try:
                    from cockpit.integrations.hn_search import HNSearchClient

                    hn_client = HNSearchClient()
                    tool_router.hn_search_client = hn_client
                except Exception as exc:
                    logger.warning("HNSearchClient init failed: %s", exc)
                try:
                    from cockpit.core.research.dossier import CompanyDossierService

                    dossier_svc = CompanyDossierService()
                    self._dossier_service = dossier_svc
                    tool_router.dossier_service = dossier_svc
                except Exception as exc:
                    logger.warning("CompanyDossierService init failed: %s", exc)
                try:
                    from cockpit.core.research.deep_research import DeepResearchRunner

                    deep_runner = DeepResearchRunner(
                        tool_router=tool_router,
                        backend_client=tool_router.backend_api_client,
                        dossier_service=dossier_svc,
                        brave_client=brave_client,
                        hn_client=hn_client,
                        strategy_service=self._strategy_service,
                    )
                except Exception as exc:
                    logger.warning("DeepResearchRunner init failed: %s", exc)

                alert_rdr = None
                try:
                    from cockpit.core.research.alerts import AlertReader

                    alert_rdr = AlertReader()
                except Exception as exc:
                    logger.warning("AlertReader init failed: %s", exc)

                wl_trigger = None
                try:
                    from cockpit.core.watchlist_trigger import WatchlistTrigger

                    if (
                        state_store is not None
                        and tool_router.backend_api_client is not None
                    ):
                        wl_trigger = WatchlistTrigger(
                            state_store=state_store,
                            strategy_service=self._strategy_service,
                            backend_api_client=tool_router.backend_api_client,
                            alert_reader=alert_rdr or AlertReader(),
                            dossier_service=dossier_svc,
                        )
                except Exception as exc:
                    logger.warning("WatchlistTrigger init failed: %s", exc)

                # Signal engine + strategy services.
                ticker_scorer = None
                screen_runner = None
                thesis_svc = None
                risk_gate_svc = None
                reflection_svc = None
                try:
                    from cockpit.core.research.signal_engine import (
                        ScreenRunner,
                        TickerScorer,
                    )

                    ticker_scorer = TickerScorer(
                        tool_router,
                        state_store=state_store,
                        strategy_service=self._strategy_service,
                    )
                    screen_runner = ScreenRunner(ticker_scorer, state_store=state_store)
                except Exception as exc:
                    logger.warning("Signal engine init failed: %s", exc)
                try:
                    from cockpit.core.research.thesis import ThesisService

                    thesis_svc = ThesisService()
                except Exception as exc:
                    logger.warning("ThesisService init failed: %s", exc)
                try:
                    from cockpit.core.research.risk_gate import RiskGate

                    risk_gate_svc = RiskGate(
                        backend_client=tool_router.backend_api_client,
                        dossier_service=dossier_svc,
                    )
                except Exception as exc:
                    logger.warning("RiskGate init failed: %s", exc)
                try:
                    from cockpit.core.research.reflection import ReflectionService
                    from cockpit.core.research.situation_memory import SituationMemory

                    sit_mem = SituationMemory()
                    if risk_gate_svc is not None:
                        risk_gate_svc._situation_memory = sit_mem
                    reflection_svc = ReflectionService(
                        situation_memory=sit_mem,
                        thesis_service=thesis_svc,
                        scorer=ticker_scorer,
                        tool_router=tool_router,
                    )
                except Exception as exc:
                    logger.warning("ReflectionService init failed: %s", exc)

                extraction_ctrl = None
                try:
                    from cockpit.core.agent.extraction_controller import ExtractionController

                    extraction_ctrl = ExtractionController(
                        pipeline_fn=lambda doc_id, ticker: "",
                        max_concurrent=4,
                    )
                except Exception as exc:
                    logger.warning("ExtractionController init failed: %s", exc)

                # HybridRouter exposes chat() so it can serve as AgentLoop's llm_client.
                self._agent_loop = AgentLoop(
                    llm_client=hybrid_router,
                    tool_executor=ToolExecutor(
                        tool_router,
                        action_registry,
                        dossier_service=dossier_svc,
                        deep_research_runner=deep_runner,
                        alert_reader=alert_rdr,
                        strategy_service=self._strategy_service,
                        watchlist_trigger=wl_trigger,
                        ticker_scorer=ticker_scorer,
                        screen_runner=screen_runner,
                        thesis_service=thesis_svc,
                        risk_gate=risk_gate_svc,
                        reflection_service=reflection_svc,
                        extraction_controller=extraction_ctrl,
                    ),
                    system_instruction_builder=lambda: self._build_system_instruction(
                        ResponseMode.FAST,
                        None,
                        {},
                    ),
                    llm_timeout=self.llm_timeout_seconds,
                )
                from cockpit.core.llm_profile import cockpit_llm_profile_label

                logger.info(
                    "Agent loop initialised (mode=structured, policy=%s, profile=%s, api=%s)",
                    hybrid_router._policy,
                    cockpit_llm_profile_label(self._cockpit_llm),
                    "available" if api_client else "none",
                )
            except ImportError:
                logger.error(
                    "Agent loop modules not importable — COCKPIT_AGENT_MODE=structured "
                    "requires cockpit.core.agent_loop and cockpit.core.tool_executor. "
                    "Falling back to keyword mode."
                )

    # ---------------------------------------------------------------------- #
    # Session ID persistence                                                   #
    # ---------------------------------------------------------------------- #

    _OV_SESSION_FILE = Path("~/.openviking/workspaces/cockpit/active_session_id")

    @classmethod
    def _session_id_path(cls) -> Path:
        return cls._OV_SESSION_FILE.expanduser()

    @classmethod
    def _load_or_create_session_id(cls) -> str:
        """Return the persisted session ID, or mint and persist a new one.

        The ID is stored at ~/.openviking/workspaces/cockpit/active_session_id so
        that cockpit restarts reuse the same OpenViking session and can retrieve
        prior turns.  A fresh ID is written if the file is absent or its content
        is not a valid 32-char hex string.
        """
        path = cls._session_id_path()
        try:
            raw = path.read_text().strip()
            if len(raw) == 32 and all(c in "0123456789abcdef" for c in raw):
                logger.debug("cockpit.session: reusing persisted session_id=%s", raw)
                return raw
        except FileNotFoundError:
            pass
        except Exception as exc:
            logger.warning("cockpit.session: could not read session file: %s", exc)

        new_id = uuid.uuid4().hex
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(new_id)
            logger.info(
                "cockpit.session: new session_id=%s persisted to %s", new_id, path
            )
        except Exception as exc:
            logger.warning("cockpit.session: could not persist session_id: %s", exc)
        return new_id

    def rotate_session(self) -> str:
        """Mint a new session ID, persist it, and return it.

        Call this to create an explicit session break (e.g. /new-session command).
        """
        new_id = uuid.uuid4().hex
        path = self._session_id_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(new_id)
        except Exception as exc:
            logger.warning(
                "cockpit.session: could not persist rotated session_id: %s", exc
            )
        self._ov_session_id = new_id
        logger.info("cockpit.session: session rotated to session_id=%s", new_id)
        return new_id

    TICKER_STOPWORDS = COMMON_TICKER_STOPWORDS | {
        "AS",
        "ASK",
        "ANALYSE",
        "ANALYZE",
        "CANDLE",
        "CHART",
        "CHECK",
        "CLOUD",
        "HAVE",
        "HI",
        "I",
        "IT",
        "LATEST",
        "MANY",
        "MOST",
        "OF",
        "PLEASE",
        "PLOT",
        "LOCAL",
        "ADVISOR",
        "OPS",
        "RECENT",
        "THIS",
        "TO",
        "TODAY",
        "UPDATE",
        "WE",
        "WHATS",
        "YOU",
        "YOUR",
        "DO",
        "DID",
        "ANY",
        "ALL",
        "COUNT",
        "NUMBER",
        "RUN",
        "SOME",
        "JUST",
        "WELL",
        "FINE",
        "HERE",
        "THERE",
        "WHEN",
        "WHERE",
        "WERE",
        "BEEN",
        "MORE",
        "ALSO",
        "VERY",
        "MUCH",
        "LIKE",
        "ONLY",
        "THAN",
        "THEN",
        "TAKE",
        "WANT",
        "NEED",
        "KNOW",
        "LOOK",
        "FIND",
        "KEEP",
        "MAKE",
        "BACK",
        "OVER",
        "AFTER",
        "BEFORE",
        "COULD",
        "WOULD",
        "WILL",
        "CAN",
        "MAY",
        "MIGHT",
        "BUT",
        "NOT",
        "YES",
        "NO",
        "OK",
        "YEP",
        "YEA",
        "YEAH",
        "NAH",
        "ABLE",
        "HELP",
        "THING",
        "THINK",
        "GOOD",
        "BAD",
        "WORK",
        "LONG",
        "BIG",
        "OLD",
        "NEW",
        "OWN",
        "OUR",
        "ITS",
        "THEY",
        "THEM",
        "THEIR",
        "SAME",
        "RIGHT",
        "HAS",
        "HAD",
        "GOT",
        "LET",
        "WAY",
        "END",
        "DONE",
        "WENT",
        "GOES",
        "BEING",
        "STILL",
        "EACH",
        "EVEN",
        "EVERY",
    }

    # ------------------------------------------------------------------ #
    # Post-processing classifiers                                          #
    # ------------------------------------------------------------------ #

    _PROMPT_ECHO_MARKERS = (
        "cockpit context",
        "as of my last update",
        "my knowledge cutoff",
        "i don't have access to real-time",
        "i cannot access real-time",
        "as an ai",
    )

    @staticmethod
    def _looks_like_prompt_echo(text: str) -> bool:
        """Return True if the LLM appears to have echoed the system prompt back."""
        lower = text.lower()
        if lower.startswith("final context prompt"):
            return True
        count = sum(1 for m in ChatController._PROMPT_ECHO_MARKERS if m in lower)
        return count >= 2

    @staticmethod
    def _has_verification_disclaimer(text: str) -> bool:
        """Return True if the text contains a 'cannot be verified' disclaimer."""
        return "cannot be verified based on available data" in text.lower()

    @staticmethod
    def _extract_ticker_observations(ticker: str, assistant_text: str) -> list[dict]:
        """
        Extract financial observations from LLM response text using rule-based matching.
        Returns list of {'type': str, 'content': str}.
        """
        import re as _re

        # Financial signal vocabulary by type
        SIGNAL_WORDS = {
            "revenue": ["revenue", "sales", "turnover", "top-line", "top line"],
            "profitability": [
                "profit",
                "ebit",
                "ebitda",
                "npat",
                "margin",
                "earnings",
                "loss",
            ],
            "cashflow": ["cash flow", "cashflow", "fcf", "operating cash", "free cash"],
            "debt": [
                "debt",
                "leverage",
                "net debt",
                "borrowings",
                "net cash",
                "gearing",
            ],
            "guidance": [
                "guidance",
                "outlook",
                "forecast",
                "expects",
                "target",
                "projected",
            ],
            "risk": [
                "risk",
                "headwind",
                "concern",
                "impairment",
                "write-down",
                "write-off",
            ],
            "catalyst": [
                "catalyst",
                "upgrade",
                "acquisition",
                "merger",
                "buyback",
                "dividend",
            ],
            "valuation": [
                "cheap",
                "expensive",
                "overvalued",
                "undervalued",
                "discount",
                "premium",
                "p/e",
                "ev/ebit",
            ],
        }

        observations = []
        ticker_upper = ticker.upper()
        ticker_lower = ticker.lower()

        # Split into sentences
        sentences = _re.split(r"(?<=[.!?])\s+", assistant_text)

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20 or len(sentence) > 300:
                continue

            # Sentence must mention the ticker
            if ticker_upper not in sentence and ticker_lower not in sentence:
                continue

            # Check for signal words
            for obs_type, words in SIGNAL_WORDS.items():
                if any(w in sentence.lower() for w in words):
                    observations.append(
                        {
                            "type": obs_type,
                            "content": sentence,
                        }
                    )
                    break  # one type per sentence

        # Cap at 3 observations per turn to avoid noise
        return observations[:3]

    # ------------------------------------------------------------------ #
    # Context gather with timeout                                          #
    # ------------------------------------------------------------------ #

    def _gather_local_context_with_timeout(
        self, ticker: str | None, query: str, deep_mode: bool
    ) -> _ContextResult:
        """
        Run tool_router.gather_local_context in a background thread with a timeout.

        - If already running: returns immediately with note="context_gather_busy".
        - If timeout exceeded: returns note="context_gather_timeout" (worker keeps running,
          lock stays held until the worker exits — so the next call sees "busy").
        - If exception: returns note="context_gather_error" with db_error field.
        - On success: returns the router result directly.
        """
        timeout = float(os.environ.get("COCKPIT_CONTEXT_GATHER_TIMEOUT_SECONDS", "30"))

        # Non-blocking acquire: if already locked the worker is still running.
        if not self._context_gather_lock.acquire(blocking=False):
            return _ContextResult(
                ok=False, payload={"note": "context_gather_busy", "ticker": ticker}
            )

        result_holder: list[Any] = [None]
        error_holder: list[BaseException | None] = [None]

        def _run() -> None:
            try:
                result_holder[0] = self.tool_router.gather_local_context(
                    ticker=ticker, query=query, deep_mode=deep_mode
                )
            except Exception as exc:
                error_holder[0] = exc
            finally:
                # Release unconditionally so the next call can proceed.
                self._context_gather_lock.release()

        worker = threading.Thread(target=_run, daemon=True)
        worker.start()
        worker.join(timeout=timeout)

        if worker.is_alive():
            # Worker timed out — lock still held by worker thread until it finishes.
            return _ContextResult(
                ok=False, payload={"note": "context_gather_timeout", "ticker": ticker}
            )

        if error_holder[0] is not None:
            return _ContextResult(
                ok=False,
                payload={
                    "note": "context_gather_error",
                    "ticker": ticker,
                    "db_error": str(error_holder[0]),
                },
            )

        return result_holder[0]

    def _detect_ticker(
        self, message: str, prior_ticker: str | None = None
    ) -> str | None:
        detected = detect_primary_ticker(message, stopwords=self.TICKER_STOPWORDS)
        return detected or prior_ticker

    def _resolve_ticker_context(
        self,
        message: str,
        prior_ticker: str | None = None,
    ) -> tuple[str | None, bool]:
        """Resolve ticker context for a message.

        Returns ``(ticker, explicit)`` where ``explicit`` is True only when the
        ticker was directly stated in the current message. Prior ticker context
        is reused only for follow-up style requests.
        """
        explicit_ticker = self._detect_ticker(message, prior_ticker=None)
        if explicit_ticker:
            return explicit_ticker, True

        prior = prior_ticker or self.last_ticker
        if prior and self._FOLLOW_UP_RE.search(message):
            return prior, False
        return None, False

    _GLOBAL_NEWS_RE = re.compile(
        r"\basx\s+news\b|\bmarket\s+news\b|\ball\s+news\b", re.IGNORECASE
    )
    _GLOBAL_ANNOUNCEMENT_RE = re.compile(
        r"\basx\s+announc|\ball\s+announc|\bmarket.?wide\s+announc", re.IGNORECASE
    )
    _DOCUMENT_GROUNDING_RE = re.compile(
        r"\b(?:based on|from|in)\s+(?:the\s+)?(?:announcement|document|release|filing|report|results?|presentation)\b"
        r"|\b(?:what does|what did)\s+(?:the\s+)?(?:announcement|document|release|filing|report|results?|presentation)\s+say\b"
        r"|\b(?:summari(?:s|z)e|quote)\s+(?:the\s+)?(?:announcement|document|release|filing|report|results?|presentation)\b",
        re.IGNORECASE,
    )
    _RECENT_UPDATE_QUERY_RE = re.compile(
        r"\b(?:"
        r"what(?:'s| is)?\s+happened|"
        r"what\s+happened|"
        r"what(?:'s| is)?\s+new|"
        r"what(?:'s| is)?\s+going\s+on|"
        r"latest\s+on|"
        r"recent\s+update|"
        r"update\s+me\s+on|"
        r"this\s+week|last\s+week|past\s+week|previous\s+week|"
        r"recently|lately"
        r")\b",
        re.IGNORECASE,
    )

    def _is_global_news_request(self, message: str) -> bool:
        """Return True when the message targets market-wide news rather than a specific company."""
        return bool(self._GLOBAL_NEWS_RE.search(message))

    def _is_global_announcement_request(self, message: str) -> bool:
        """Return True when the message targets market-wide ASX announcements."""
        return bool(self._GLOBAL_ANNOUNCEMENT_RE.search(message))

    def _query_requires_document_grounding(self, message: str) -> bool:
        return bool(self._DOCUMENT_GROUNDING_RE.search(str(message or "")))

    def _query_requests_recent_update(self, message: str) -> bool:
        return bool(self._RECENT_UPDATE_QUERY_RE.search(str(message or "")))

    @staticmethod
    def _orchestration_has_substantive_evidence(orchestration_result) -> bool:
        if orchestration_result is None:
            return False
        recovery = getattr(orchestration_result, "missing_data_recovery", None)
        if isinstance(recovery, dict) and bool(recovery.get("attempted")):
            return True
        entities = getattr(orchestration_result, "entities", {}) or {}
        has_sector_scope = bool(str(entities.get("sector") or "").strip())
        if has_sector_scope and not bool(
            getattr(orchestration_result, "sufficient_for_analysis", True)
        ):
            return True
        return bool(
            orchestration_result.financial_truth_results.get("items")
            or orchestration_result.financial_truth_results.get(
                "latest_financial_snapshot"
            )
            or orchestration_result.company_memory_results.get("items")
            or orchestration_result.market_memory_results.get("items")
        )

    @staticmethod
    def _local_payload_has_price_evidence(local_payload: dict[str, Any]) -> bool:
        price = local_payload.get("price")
        if isinstance(price, dict) and price.get("ok") is False:
            return False

        history = price.get("recent_history") if isinstance(price, dict) else None
        if isinstance(history, list) and history:
            return True

        current = price.get("current") if isinstance(price, dict) else None
        if isinstance(current, dict) and any(
            current.get(key) is not None
            for key in ("price", "previous_close", "change_percent")
        ):
            return True

        price_state = local_payload.get("price_state")
        return bool(
            isinstance(price_state, dict)
            and any(
                price_state.get(key) is not None
                for key in ("last_close", "trend_regime", "momentum_1d", "momentum_20d")
            )
        )

    @staticmethod
    def _build_recent_price_summary_block(local_payload: dict[str, Any]) -> str | None:
        price = local_payload.get("price")
        if not isinstance(price, dict) or price.get("ok") is False:
            return None

        symbol = str(price.get("symbol") or "").strip()
        history = price.get("recent_history")
        rows = history if isinstance(history, list) else []

        dated_closes: list[tuple[str, float]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            date_str = str(row.get("timestamp") or "").strip()[:10]
            close = row.get("close")
            if not date_str or close is None:
                continue
            try:
                dated_closes.append((date_str, float(close)))
            except (TypeError, ValueError):
                continue

        if len(dated_closes) >= 2:
            dated_closes.sort(key=lambda item: item[0])
            window = dated_closes[-5:] if len(dated_closes) >= 5 else dated_closes
            first_date = window[0][0]
            last_date = window[-1][0]
            first_close = window[0][1]
            last_close = window[-1][1]
            period_return = (
                ((last_close / first_close) - 1.0) * 100.0 if first_close else 0.0
            )
            high = max(close for _, close in window)
            low = min(close for _, close in window)
            label = symbol or "ticker"
            return (
                f"Recent price action for {label}:\n"
                f"  - Last week ({first_date} to {last_date}): {period_return:+.2f}% close-to-close\n"
                f"  - High: {high:.4f}  Low: {low:.4f}  Last close: {last_close:.4f}"
            )

        current = price.get("current")
        if not isinstance(current, dict):
            return None

        price_now = current.get("price")
        change_percent = current.get("change_percent")
        try:
            price_now_value = float(price_now) if price_now is not None else None
        except (TypeError, ValueError):
            price_now_value = None
        try:
            change_pct_value = (
                float(change_percent) if change_percent is not None else None
            )
        except (TypeError, ValueError):
            change_pct_value = None

        if price_now_value is None:
            return None

        label = symbol or "ticker"
        if change_pct_value is None:
            return f"Recent price action for {label}:\n  - Last traded price: {price_now_value:.4f}"
        return (
            f"Recent price action for {label}:\n"
            f"  - Last traded price: {price_now_value:.4f}\n"
            f"  - Daily move: {change_pct_value:+.2f}%"
        )

    @staticmethod
    def _build_recent_news_summary_block(local_payload: dict[str, Any]) -> str:
        news_payload = local_payload.get("qual_context_news")
        hits = news_payload.get("hits") if isinstance(news_payload, dict) else None

        if not isinstance(hits, list) or not hits:
            merged = local_payload.get("qual_context")
            merged_hits = merged.get("hits") if isinstance(merged, dict) else []
            if isinstance(merged_hits, list):
                hits = [
                    row
                    for row in merged_hits
                    if isinstance(row, dict)
                    and (
                        "news"
                        in str(
                            row.get("source_corpus")
                            or row.get("corpus")
                            or row.get("source_type")
                            or ""
                        ).lower()
                    )
                ]
            else:
                hits = []

        if not hits:
            return (
                "Recent news context:\n"
                "  - No recent indexed news hits were available in the local corpus for this ticker."
            )

        lines = ["Recent news context:"]
        seen_keys: set[str] = set()
        count = 0
        for row in hits:
            if not isinstance(row, dict):
                continue
            title = str(row.get("title") or row.get("source_name") or "").strip()
            snippet = re.sub(
                r"\s+",
                " ",
                str(row.get("text") or row.get("snippet") or "").strip(),
            )[:220]
            published_at = str(row.get("published_at") or "").strip()[:10]
            dedupe_key = (
                str(row.get("url") or "").strip()
                or title.lower()
                or snippet.lower()
            )
            if not dedupe_key or dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            headline = f"  - {published_at}: {title}" if published_at and title else f"  - {title or snippet}"
            lines.append(headline)
            if snippet:
                lines.append(f"    {snippet}")
            count += 1
            if count >= 3:
                break

        if count == 0:
            return (
                "Recent news context:\n"
                "  - No recent indexed news hits were available in the local corpus for this ticker."
            )
        return "\n".join(lines)

    @staticmethod
    def _recent_update_offer_suffix(
        action_preview: dict[str, Any] | None,
        *,
        ticker: str,
    ) -> str:
        if not isinstance(action_preview, dict):
            return ""
        action_id = str(action_preview.get("action_id") or "").strip()
        if action_id == "single_ticker_announcement_backfill":
            return (
                f"\n\nIf you want, I can backfill ASX announcements for {ticker} next "
                "to fill the local announcement gap."
            )
        if action_id == "update_ticker_financials":
            return (
                f"\n\nIf you want, I can refresh the latest ASX announcements for {ticker} next."
            )
        return ""

    # Chart intent keywords — checked before general action detection.
    # NOTE: "price history" is a price-query pattern, not a chart request.
    _GREETING_RE = re.compile(
        r"^\s*(?:"
        r"hi|hello|hey|g'?day|yo|sup|howdy|"
        r"good\s+(?:morning|afternoon|evening)|"
        r"what'?s?\s+up|"
        r"how\s+are\s+you(?:\s+doing)?|"
        r"how\s+r\s+u|hru"
        r")\s*[!?.]*\s*$",
        re.IGNORECASE,
    )
    _DAY_QUERY_RE = re.compile(
        r"^\s*(?:what\s+day\s+(?:is\s+it|is\s+today)|what'?s\s+the\s+day)\s*[!?.]*\s*$",
        re.IGNORECASE,
    )
    _DATE_QUERY_RE = re.compile(
        r"^\s*(?:what\s+date\s+(?:is\s+it|is\s+today)|what'?s\s+the\s+date)\s*[!?.]*\s*$",
        re.IGNORECASE,
    )
    _TIME_QUERY_RE = re.compile(
        r"^\s*(?:what\s+time\s+(?:is\s+it|is\s+it\s+now)|what'?s\s+the\s+time)\s*[!?.]*\s*$",
        re.IGNORECASE,
    )

    # Detects follow-up messages that implicitly reference the prior ticker.
    # Only matches topic-referential phrases (financial terms, entity pronouns,
    # explicit continuation requests).  Discourse markers like "sure", "okay",
    # "yes", "go ahead" are intentionally excluded — they are conversational
    # fillers, not entity references, and caused false prior-ticker reattachment.
    _FOLLOW_UP_RE = re.compile(
        r"\b(?:"
        r"it|its|they|their|them|"
        r"the company|the stock|this company|this stock|same ticker|same company|"
        r"what about|how about|and what|and how|"
        r"tell me more|more detail|elaborate|expand on|drill down|"
        r"financials?|revenue|earnings|cashflow|cash flow|dividends?|"
        r"balance sheet|results?|"
        r"sources?|evidence|documents?|announcements?|filings?|"
        r"gather\s+(?:the\s+)?sources?|collect\s+(?:the\s+)?sources?|"
        r"health|performance|outlook|guidance|price|chart|candlestick|candle|plot|"
        r"compared to|versus|vs"
        r")\b",
        re.IGNORECASE,
    )

    _CHART_KEYWORDS = re.compile(
        r"\b(?:candlestick|candle|chart|plot)\b"
        r"|show\s+\S+\s*chart",
        re.IGNORECASE,
    )
    _AFFIRMATIVE_REPLY_RE = re.compile(
        r"^\s*(?:ok(?:ay)?|yes|yep|yeah|sure|go ahead|please do|do it|sounds good|alright|all right|fine|works for me)\s*[!?.]*\s*$",
        re.IGNORECASE,
    )
    _NEGATIVE_REPLY_RE = re.compile(
        r"^\s*(?:no|nope|nah|no thanks|not now|stop|cancel|skip|don't|do not)\b.*$",
        re.IGNORECASE,
    )
    _CONFIRMABLE_ASSISTANT_RE = re.compile(
        r"(?:\?|would you like|do you want|should I|shall I|can I|want me to|if you'd like|if you want|let me know and I can|I can offer to|I can provide|I can give you)",
        re.IGNORECASE,
    )
    _SUMMARY_OFFER_RE = re.compile(
        r"(?:offer to give you a summary|give you a summary|provide (?:you )?a summary|summar(?:y|ize).*(?:helpful|if you'd like|if you want))",
        re.IGNORECASE,
    )
    _ARTICLE_TEXT_REQUEST_RE = re.compile(
        r"(?:\bprint\b|\bshow\b|\bgive me\b|\bread\b|\bdisplay\b|\bpaste\b).*(?:\bfull\b|\bentire\b|\bcontents?\b).*(?:\barticle\b|\bstory\b)"
        r"|\bprint the contents of the article\b"
        r"|\bprint the full [a-z]+ article\b",
        re.IGNORECASE,
    )
    _ARTICLE_DOMAIN_HINTS = {
        "kalkine": "kalkinemedia.com",
        "stockhead": "stockhead.com.au",
        "afr": "afr.com",
        "market index": "marketindex.com.au",
    }

    def detect_chart_intent(self, message: str) -> bool:
        """Return True if *message* looks like a chart request."""
        return bool(self._CHART_KEYWORDS.search(message))

    def _classify_confirmation_reply(self, message: str) -> str | None:
        text = str(message or "").strip()
        if not text:
            return None
        if self._NEGATIVE_REPLY_RE.match(text):
            return "no"
        if self._AFFIRMATIVE_REPLY_RE.match(text):
            return "yes"
        return None

    def _recent_confirmation_context(
        self, current_message: str
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        if self._state_store is None:
            return None, None
        try:
            history_msgs = self._state_store.get_chat_messages(
                self._thread_id, limit=10
            )
        except Exception:
            return None, None
        if not history_msgs:
            return None, None

        current_text = str(current_message or "").strip()
        if (
            current_text
            and history_msgs[-1].get("role") == "user"
            and str(history_msgs[-1].get("content") or "").strip() == current_text
        ):
            history_msgs = history_msgs[:-1]
        if not history_msgs:
            return None, None

        assistant_idx: int | None = None
        for idx in range(len(history_msgs) - 1, -1, -1):
            if history_msgs[idx].get("role") == "assistant":
                assistant_idx = idx
                break
        if assistant_idx is None:
            return None, None

        prior_user = None
        for idx in range(assistant_idx - 1, -1, -1):
            if history_msgs[idx].get("role") == "user":
                prior_user = history_msgs[idx]
                break
        return prior_user, history_msgs[assistant_idx]

    def _assistant_invited_confirmation(self, assistant_text: str) -> bool:
        return bool(self._CONFIRMABLE_ASSISTANT_RE.search(str(assistant_text or "")))

    def _find_recent_article_reference(self, message: str) -> dict[str, str] | None:
        if self._state_store is None:
            return None
        try:
            history_msgs = self._state_store.get_chat_messages(
                self._thread_id, limit=10
            )
        except Exception:
            return None

        text = str(message or "").lower()
        preferred_domain = ""
        for hint, domain in self._ARTICLE_DOMAIN_HINTS.items():
            if hint in text:
                preferred_domain = domain
                break

        url_pattern = re.compile(r"https?://\S+")
        for row in reversed(history_msgs):
            if row.get("role") != "assistant":
                continue
            content = str(row.get("content") or "")
            urls = [
                match.group(0).rstrip(").,") for match in url_pattern.finditer(content)
            ]
            if not urls:
                continue
            chosen_url = ""
            if preferred_domain:
                for url in urls:
                    if preferred_domain in url.lower():
                        chosen_url = url
                        break
            if not chosen_url:
                chosen_url = urls[0]
            if not chosen_url:
                continue
            domain = urlparse(chosen_url).netloc.lower()
            return {"url": chosen_url, "domain": domain}
        return None

    def _try_article_text_request(self, message: str) -> ChatResponse | None:
        if not self._ARTICLE_TEXT_REQUEST_RE.search(str(message or "")):
            return None

        article_ref = self._find_recent_article_reference(message)
        if article_ref is None:
            return ChatResponse(
                text="I couldn't identify which local article you mean. If you want, paste the article URL or ask me to summarize the article you just referenced instead.",
                evidence=[],
                mode=ResponseMode.FAST,
            )

        url = article_ref.get("url", "")
        article = (
            self.tool_router.get_local_news_article(url)
            if hasattr(self.tool_router, "get_local_news_article")
            else {"ok": False, "error": "local article reader unavailable", "url": url}
        )
        if not bool(article.get("ok")):
            target_url = str(article.get("url") or url).strip()
            text = "I couldn't print that article from the local corpus"
            error = str(article.get("error") or "").strip()
            if error:
                text += f": {error}."
            else:
                text += "."
            if target_url:
                text += f"\n{target_url}"
            return ChatResponse(
                text=text,
                evidence=[{"type": "article_request", "details": article_ref}],
                mode=ResponseMode.FAST,
            )

        title = str(article.get("title") or "").strip()
        published_at = str(article.get("published_at") or "").strip()
        provider = str(article.get("provider") or "").strip()
        body = str(article.get("body") or "").strip()
        lines: list[str] = []
        if title:
            lines.append(title)
        meta_bits = [
            bit
            for bit in (published_at[:10] if published_at else "", provider, url)
            if bit
        ]
        if meta_bits:
            lines.append(" | ".join(meta_bits))
        if body:
            if lines:
                lines.append("")
            lines.append(body)
        return ChatResponse(
            text="\n".join(lines),
            evidence=[
                {"type": "article_request", "details": {**article_ref, **article}}
            ],
            mode=ResponseMode.FAST,
        )

    @staticmethod
    def _extract_summary_points(text: str, *, max_points: int = 2) -> list[str]:
        cleaned = re.sub(r"\s+", " ", str(text or "").strip())
        if not cleaned:
            return []
        sentences = [
            sentence.strip(" -")
            for sentence in re.split(r"(?<=[.!?])\s+", cleaned)
            if sentence.strip()
        ]
        points = [sentence for sentence in sentences if len(sentence) >= 40][
            :max_points
        ]
        if points:
            return points
        return [cleaned[:220]]

    def _try_summary_offer_followup(
        self, message: str, prior_ticker: str | None
    ) -> ChatResponse | None:
        decision = self._classify_confirmation_reply(message)
        if decision is None:
            return None

        prior_user, prior_assistant = self._recent_confirmation_context(message)
        assistant_text = str((prior_assistant or {}).get("content") or "")
        if not assistant_text or not self._SUMMARY_OFFER_RE.search(assistant_text):
            return None
        if decision == "no":
            return ChatResponse(
                text="Okay, I won't do that.",
                evidence=[],
                mode=ResponseMode.FAST,
            )

        prior_user_text = str((prior_user or {}).get("content") or "")
        inferred_ticker, _ = self._resolve_ticker_context(
            prior_user_text, prior_ticker=prior_ticker
        )
        requested_stockhead = "stockhead" in prior_user_text.lower()
        resolved_ticker = inferred_ticker or prior_ticker
        query = resolved_ticker or prior_user_text or ""
        if requested_stockhead and resolved_ticker:
            query = f"{resolved_ticker} stockhead article"

        try:
            payload = self.tool_router.get_news_context(
                query=query,
                top_k=5,
                ticker=resolved_ticker,
            )
        except Exception:
            return None

        raw_hits = payload.get("hits") if isinstance(payload, dict) else []
        hits = (
            [row for row in raw_hits if isinstance(row, dict)]
            if isinstance(raw_hits, list)
            else []
        )
        if requested_stockhead:
            stockhead_hits = [
                hit
                for hit in hits
                if "stockhead.com.au" in str(hit.get("url") or "").lower()
            ]
            if stockhead_hits:
                hits = stockhead_hits
            elif resolved_ticker and query != resolved_ticker:
                try:
                    fallback_payload = self.tool_router.get_news_context(
                        query=resolved_ticker,
                        top_k=5,
                        ticker=resolved_ticker,
                    )
                except Exception:
                    fallback_payload = {}
                fallback_raw_hits = (
                    fallback_payload.get("hits")
                    if isinstance(fallback_payload, dict)
                    else []
                )
                fallback_hits = [
                    row
                    for row in fallback_raw_hits
                    if isinstance(row, dict)
                    and "stockhead.com.au" in str(row.get("url") or "").lower()
                ]
                if fallback_hits:
                    hits = fallback_hits
        if not hits:
            target = resolved_ticker or "that article"
            return ChatResponse(
                text=f"Okay. I couldn't find a matching indexed article to summarize for {target}.",
                evidence=[],
                mode=ResponseMode.FAST,
            )

        hit = hits[0]
        title = str(hit.get("title") or "the requested article").strip()
        published_at = str(hit.get("published_at") or "").strip()
        url = str(hit.get("url") or "").strip()
        summary_points = self._extract_summary_points(
            str(hit.get("text") or hit.get("snippet") or "")
        )

        lines = [f"Here’s the summary for {title}:"]
        if published_at:
            lines.append(f"Published: {published_at[:10]}")
        for point in summary_points:
            lines.append(f"- {point}")
        if url:
            lines.append(url)

        return ChatResponse(
            text="\n".join(lines),
            evidence=[
                {
                    "type": "news_summary",
                    "details": {
                        "title": title,
                        "published_at": published_at,
                        "url": url,
                        "ticker": resolved_ticker,
                    },
                }
            ],
            mode=ResponseMode.FAST,
        )

    def _rewrite_confirmation_followup(
        self, message: str, prior_ticker: str | None
    ) -> str | None:
        decision = self._classify_confirmation_reply(message)
        if decision is None:
            return None

        _prior_user, prior_assistant = self._recent_confirmation_context(message)
        assistant_text = str((prior_assistant or {}).get("content") or "")
        if not assistant_text or not self._assistant_invited_confirmation(
            assistant_text
        ):
            return None

        answer = (
            "yes, please proceed with that"
            if decision == "yes"
            else "no, do not proceed with that"
        )
        if prior_ticker:
            return (
                f"Regarding your last question or offer about {prior_ticker}: {assistant_text}\n"
                f"My answer is {answer}."
            )
        return (
            f"Regarding your last question or offer: {assistant_text}\n"
            f"My answer is {answer}."
        )

    def detect_action_intent(self, message: str) -> str | None:
        text = message.lower()
        for action_id, words in ACTION_KEYWORDS.items():
            if any(w in text for w in words):
                return action_id
        return None

    # --- Price history patterns ---
    _ON_DATE_RE = re.compile(
        r"(?:price|was|close|closing)\b.*?\b(\d{4}-\d{2}-\d{2})",
        re.IGNORECASE,
    )
    _RANGE_RE = re.compile(
        r"between\s+(\d{4}-\d{2}-\d{2})\s+and\s+(\d{4}-\d{2}-\d{2})",
        re.IGNORECASE,
    )
    _FULL_HISTORY_RE = re.compile(
        r"\bprice\s+history\b",
        re.IGNORECASE,
    )
    _RELATIVE_WEEK_RE = re.compile(
        r"\b(?:last|past|previous)\s+week\b",
        re.IGNORECASE,
    )
    _SIMPLE_PRICE_RE = re.compile(
        r"^\s*(?:current\s+price|today'?s?\s+price|last\s+(?:price|close)|"
        r"what.{0,15}price|price(?:\s+(?:today|now|current|currently))?)\s*[?!.]*\s*$",
        re.IGNORECASE,
    )
    _TICKER_LEADING_PRICE_RE = re.compile(
        r"^\s*(?:[A-Za-z0-9]{2,5})\s+(?:share\s+)?price(?:\s+(?:today|now|current|currently))?\s*[?!.]*\s*$",
        re.IGNORECASE,
    )
    _DIRECT_NEWS_RE = re.compile(
        r"^\s*(?:latest\s+)?(?:news(?:\s+for)?\s+(?P<prefix>[A-Za-z0-9]{2,5})|(?P<suffix>[A-Za-z0-9]{2,5})\s+news)\s*[?!.]*\s*$",
        re.IGNORECASE,
    )
    _DIRECT_FILESTATS_RE = re.compile(
        r"^\s*(?:(?P<ticker_prefix>[A-Za-z0-9]{1,10})\s+filestats?|filestats?\s+(?P<ticker_suffix>[A-Za-z0-9]{1,10}))\s*[?!.]*\s*$",
        re.IGNORECASE,
    )
    _EXPLICIT_WEB_SEARCH_PATTERNS = (
        re.compile(
            r"^\s*(?:search|find|look\s+up)\s+(?:the\s+)?web(?:\s+for)?\s+(?P<query>.+?)\s*[?!.]*\s*$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^\s*web\s+search(?:\s+for)?\s+(?P<query>.+?)\s*[?!.]*\s*$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^\s*search\s+online(?:\s+for)?\s+(?P<query>.+?)\s*[?!.]*\s*$",
            re.IGNORECASE,
        ),
    )
    _BARE_WEB_SEARCH_RE = re.compile(
        r"^\s*(?:search\s+web|web\s+search)\s*[?!.]*\s*$",
        re.IGNORECASE,
    )

    def _try_news_shortcircuit(
        self, message: str, ticker: str | None
    ) -> ChatResponse | None:
        if ticker is None:
            return None
        if not self._DIRECT_NEWS_RE.fullmatch(message.strip()):
            return None

        try:
            payload = self.tool_router.get_news_context(
                query=ticker,
                top_k=5,
                ticker=ticker,
            )
        except Exception:
            return None

        raw_hits = payload.get("hits") if isinstance(payload, dict) else []
        hits = (
            [row for row in raw_hits if isinstance(row, dict)]
            if isinstance(raw_hits, list)
            else []
        )
        if not hits:
            preview = normalize_action_preview(
                {
                    "tool": "run_news_ingest",
                    "arguments": {"since_hours": 24, "tickers": ticker},
                    "requires_confirmation": True,
                    "explanation": f"Populate the indexed news corpus for {ticker}.",
                }
            )
            return ChatResponse(
                text=(
                    f"I couldn't find recent indexed news for {ticker}. That is not evidence "
                    "there is no news; the news corpus may be stale or missing this ticker. "
                    "I can run a ticker-scoped news ingest. Use /confirm to execute."
                ),
                evidence=[
                    {
                        "type": "news_search",
                        "details": {
                            "ticker": ticker,
                            "hits": [],
                            "data_insufficient": True,
                        },
                    }
                ],
                action_preview=preview,
                mode=ResponseMode.ACTION,
            )

        lines = [f"Recent {ticker}-linked news:"]
        summarized_hits: list[dict[str, Any]] = []
        for hit in hits[:5]:
            title = str(hit.get("title") or "Untitled").strip()
            published_at = str(hit.get("published_at") or "").strip()
            url = str(hit.get("url") or "").strip()
            snippet = re.sub(
                r"\s+", " ", str(hit.get("text") or hit.get("snippet") or "").strip()
            )[:180]
            lines.append(f"- {title}")
            if published_at:
                lines.append(f"  published: {published_at[:10]}")
            if snippet:
                lines.append(f"  {snippet}")
            if url:
                lines.append(f"  {url}")
            summarized_hits.append(
                {
                    "title": title,
                    "published_at": published_at,
                    "url": url,
                    "snippet": snippet,
                    "score": hit.get("score") or hit.get("final_score"),
                }
            )

        return ChatResponse(
            text="\n".join(lines),
            evidence=[
                {
                    "type": "news_search",
                    "details": {"ticker": ticker, "hits": summarized_hits},
                }
            ],
            mode=ResponseMode.FAST,
        )

    @classmethod
    def _extract_explicit_web_search_query(cls, message: str) -> str | None:
        text = str(message or "").strip()
        if not text:
            return None
        if cls._BARE_WEB_SEARCH_RE.fullmatch(text):
            return ""
        for pattern in cls._EXPLICIT_WEB_SEARCH_PATTERNS:
            match = pattern.fullmatch(text)
            if not match:
                continue
            query = str(match.group("query") or "").strip().rstrip("?.!,")
            return query
        return None

    @staticmethod
    def _query_signals_fresh_web_context(message: str) -> bool:
        text = str(message or "").strip().lower()
        if not text:
            return False
        freshness_markers = (
            "latest",
            "recent",
            "today",
            "current",
            "this week",
            "breaking",
            "new announcement",
            "market update",
            "market wrap",
            "market summary",
            "market movers",
            "market snapshot",
            "news",
        )
        return any(marker in text for marker in freshness_markers)

    def _try_price_history_shortcircuit(
        self, message: str, ticker: str | None
    ) -> ChatResponse | None:
        """Detect price-on-date, range, or full-history queries and short-circuit."""
        if ticker is None:
            return None

        # Fetch price context (10y window gives us maximum coverage for queries).
        try:
            bundle = self.tool_router.get_price_context_for_window(
                ticker,
                range_="10y",
                interval="1d",
                max_history_rows=3000,
            )
        except Exception:
            return None

        price = bundle.get("price") if isinstance(bundle, dict) else {}
        price = price if isinstance(price, dict) else {}
        symbol = str(price.get("symbol") or f"{ticker}.AX")
        history = price.get("recent_history") if isinstance(price, dict) else None
        if history is None:
            history = price.get("history") if isinstance(price, dict) else []
        if not isinstance(history, list):
            history = []

        # Build sorted (date_str, close) pairs.
        dated_closes: list[tuple[str, float]] = []
        for row in history:
            if not isinstance(row, dict):
                continue
            ts = str(row.get("timestamp") or "")
            close = row.get("close")
            if not ts or close is None:
                continue
            date_str = ts[:10]
            try:
                dated_closes.append((date_str, float(close)))
            except (ValueError, TypeError):
                continue
        dated_closes.sort(key=lambda item: item[0])

        if not dated_closes:
            return None

        msg_lower = message.lower()

        # --- Relative weekly summary: "price summary for last week" ---
        if self._RELATIVE_WEEK_RE.search(message) and any(
            marker in msg_lower
            for marker in ("price", "close", "summary", "performance", "trading")
        ):
            week_window = dated_closes[-5:] if len(dated_closes) >= 2 else dated_closes
            if len(week_window) >= 2:
                first_date = week_window[0][0]
                final_date = week_window[-1][0]
                first_close = week_window[0][1]
                last_close = week_window[-1][1]
                period_return = (
                    ((last_close / first_close) - 1.0) * 100.0
                    if first_close != 0
                    else 0.0
                )
                high = max(c for _, c in week_window)
                low = min(c for _, c in week_window)
                text = (
                    f"Last-week price summary for {symbol}\n"
                    f"Coverage: {first_date} to {final_date} ({len(week_window)} points)\n"
                    f"Period return (close-to-close): {period_return:+.2f}%\n"
                    f"High: {high:.4f}  Low: {low:.4f}  Last close: {last_close:.4f}"
                )
                return ChatResponse(
                    text=text,
                    evidence=[
                        {
                            "type": "local_context",
                            "details": {
                                "price_history_query": {
                                    "kind": "relative_week",
                                    "ticker": ticker,
                                    "start": first_date,
                                    "end": final_date,
                                }
                            },
                        }
                    ],
                    mode=ResponseMode.FAST,
                )

        # --- Range query: "between DATE and DATE" ---
        range_match = self._RANGE_RE.search(message)
        if range_match:
            start_date = range_match.group(1)
            end_date = range_match.group(2)
            in_range = [(d, c) for d, c in dated_closes if start_date <= d <= end_date]
            if not in_range:
                text = f"No price history for {symbol} between {start_date} and {end_date}."
                return ChatResponse(
                    text=text,
                    evidence=[
                        {
                            "type": "local_context",
                            "details": {
                                "price_history_query": {
                                    "kind": "range",
                                    "ticker": ticker,
                                    "start": start_date,
                                    "end": end_date,
                                }
                            },
                        }
                    ],
                    mode=ResponseMode.FAST,
                )
            first_close = in_range[0][1]
            last_close = in_range[-1][1]
            period_return = (
                ((last_close / first_close) - 1.0) * 100.0 if first_close != 0 else 0.0
            )
            high = max(c for _, c in in_range)
            low = min(c for _, c in in_range)
            text = (
                f"Historical range for {symbol}: {start_date} to {end_date}\n"
                f"Period return (close-to-close): {period_return:+.2f}%\n"
                f"High: {high:.4f}  Low: {low:.4f}  Points: {len(in_range)}"
            )
            return ChatResponse(
                text=text,
                evidence=[
                    {
                        "type": "local_context",
                        "details": {
                            "price_history_query": {
                                "kind": "range",
                                "ticker": ticker,
                                "start": start_date,
                                "end": end_date,
                            }
                        },
                    }
                ],
                mode=ResponseMode.FAST,
            )

        # --- On-date query: "price on DATE" ---
        on_date_match = self._ON_DATE_RE.search(message)
        if on_date_match:
            query_date = on_date_match.group(1)
            # Find exact or nearest preceding date.
            exact = [(d, c) for d, c in dated_closes if d == query_date]
            if exact:
                date_str, close_val = exact[0]
                text = (
                    f"Historical close for {symbol} on {query_date}: {close_val:.4f}\n"
                    f"Matched candle date: {date_str} (exact)"
                )
                return ChatResponse(
                    text=text,
                    evidence=[
                        {
                            "type": "local_context",
                            "details": {
                                "price_history_query": {
                                    "kind": "on_date",
                                    "ticker": ticker,
                                    "date": query_date,
                                }
                            },
                        }
                    ],
                    mode=ResponseMode.FAST,
                )
            # Try nearest preceding date.
            preceding = [(d, c) for d, c in dated_closes if d <= query_date]
            if preceding:
                date_str, close_val = preceding[-1]
                text = (
                    f"Historical close for {symbol} on {query_date}: {close_val:.4f}\n"
                    f"Matched candle date: {date_str} (nearest)"
                )
                return ChatResponse(
                    text=text,
                    evidence=[
                        {
                            "type": "local_context",
                            "details": {
                                "price_history_query": {
                                    "kind": "on_date",
                                    "ticker": ticker,
                                    "date": query_date,
                                }
                            },
                        }
                    ],
                    mode=ResponseMode.FAST,
                )
            text = f"No price history exists on or before {query_date} for {symbol}."
            return ChatResponse(
                text=text,
                evidence=[
                    {
                        "type": "local_context",
                        "details": {
                            "price_history_query": {
                                "kind": "on_date",
                                "ticker": ticker,
                                "date": query_date,
                            }
                        },
                    }
                ],
                mode=ResponseMode.FAST,
            )

        # --- Simple current price query: "price?", "current price", etc. ---
        stripped_message = message.strip()
        if self._SIMPLE_PRICE_RE.search(
            stripped_message
        ) or self._TICKER_LEADING_PRICE_RE.search(stripped_message):
            last_date, last_close = dated_closes[-1]
            text = f"**{symbol}** last close: **{last_close:.4f}** ({last_date})"
            return ChatResponse(
                text=text,
                evidence=[
                    {
                        "type": "local_context",
                        "details": {
                            "price_query": {
                                "ticker": ticker,
                                "kind": "current",
                                "close": last_close,
                                "date": last_date,
                            }
                        },
                    }
                ],
                mode=ResponseMode.FAST,
            )

        # --- Full history query: "price history TICKER" ---
        if self._FULL_HISTORY_RE.search(message):
            first_date = dated_closes[0][0]
            last_date = dated_closes[-1][0]
            n_points = len(dated_closes)
            first_close = dated_closes[0][1]
            last_close = dated_closes[-1][1]
            total_return = (
                ((last_close / first_close) - 1.0) * 100.0 if first_close != 0 else 0.0
            )
            high = max(c for _, c in dated_closes)
            low = min(c for _, c in dated_closes)
            text = (
                f"Full historical summary for {symbol}\n"
                f"Coverage: {first_date} to {last_date} ({n_points} points)\n"
                f"Total return: {total_return:+.2f}%\n"
                f"High: {high:.4f}  Low: {low:.4f}"
            )
            return ChatResponse(
                text=text,
                evidence=[
                    {
                        "type": "local_context",
                        "details": {
                            "price_history_query": {
                                "kind": "full_summary",
                                "ticker": ticker,
                            }
                        },
                    }
                ],
                mode=ResponseMode.FAST,
            )

        return None

    @staticmethod
    def classify_request(message: str, *, enable_web: bool = False) -> ResponseMode:
        text = str(message or "").strip().lower()
        if not text:
            return ResponseMode.FAST

        if (
            any(url_prefix in text for url_prefix in ("http://", "https://"))
            and enable_web
        ):
            return ResponseMode.WEB

        verification_markers = (
            "verify",
            "verification",
            "did it work",
            "check status",
            "status",
            "what failed",
            "why did",
            "error",
            "failed",
            "failure",
        )
        if any(marker in text for marker in verification_markers):
            return ResponseMode.VERIFICATION

        deep_markers = (
            "deep analysis",
            "analyse",
            "analyze",
            "compare",
            "walk through",
            "walk me through",
            "explain",
            "what changed",
            "impact",
            "thesis",
            "full report",
        )
        if any(marker in text for marker in deep_markers):
            return ResponseMode.DEEP_ANALYSIS

        return ResponseMode.FAST

    @staticmethod
    def _is_ultra_short_prompt(message: str) -> bool:
        stripped = str(message or "").strip()
        if not stripped or any(prefix in stripped for prefix in ("http://", "https://")):
            return False
        tokens = re.findall(r"[A-Za-z0-9]+", stripped)
        if len(tokens) != 1:
            return False
        token = tokens[0]
        if token.isdigit():
            return False
        return len(token) <= 2

    @staticmethod
    def _query_depends_on_attached_source(message: str) -> bool:
        stripped = str(message or "").strip().lower()
        if not stripped:
            return True
        if re.search(
            r"\b(this|that|it|attached|source|video|article|listing|clip|podcast|transcript)\b",
            stripped,
        ):
            return True
        return bool(
            re.search(
                r"\b(tell me about|summari[sz]e|what stands out|what do you think|"
                r"compare|analyse|analyze|walk me through|break down|explain)\b",
                stripped,
            )
        )

    def _try_fast_clarification_shortcircuit(
        self,
        message: str,
        *,
        ticker: str | None,
        attached_bundle: _AttachedSourceBundle,
    ) -> ChatResponse | None:
        if ticker:
            return None

        if self._is_ultra_short_prompt(message):
            return ChatResponse(
                text=(
                    "Please enter a clearer question. Examples: "
                    '"tell me about CSL", "show BHP news", or '
                    '"summarize the attached source".'
                ),
                evidence=[],
                mode=ResponseMode.FAST,
            )

        if (
            attached_bundle.unresolved_ids
            and not attached_bundle.context.strip()
            and self._query_depends_on_attached_source(message)
        ):
            if len(attached_bundle.unresolved_ids) == 1:
                source_label = f"`{attached_bundle.unresolved_ids[0]}`"
            else:
                source_label = "the attached sources"
            return ChatResponse(
                text=(
                    f"I can't analyse {source_label} from current evidence because "
                    "its transcript or chunk text is not available in this chat turn yet. "
                    "Re-ingest the source in this tab, or attach one with available chunks, "
                    "then ask again."
                ),
                evidence=[],
                mode=ResponseMode.FAST,
            )

        return None

    def _compute_announcement_sync_status(
        self, ticker: str, docs: list[dict], message: str
    ) -> dict:  # noqa: ARG002
        """Return {status, needs_update_offer} based on recency of docs."""
        if not docs:
            return {"status": "missing", "needs_update_offer": True}
        freshness_threshold_hours = 72
        now = datetime.now(timezone.utc)
        latest_doc = docs[0]
        published_at_str = str(latest_doc.get("published_at") or "")
        try:
            published_at = datetime.fromisoformat(published_at_str)
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)
            age_hours = (now - published_at).total_seconds() / 3600
        except (ValueError, TypeError):
            return {"status": "stale", "needs_update_offer": True}
        if age_hours < freshness_threshold_hours:
            return {"status": "fresh", "needs_update_offer": False}
        return {"status": "stale", "needs_update_offer": True}

    def _build_ticker_update_offer(self, ticker: str, sync: dict) -> dict:
        """Build an offer dict for updating ticker announcements."""
        if not sync.get("needs_update_offer"):
            return {
                "note": f"Announcement sync check for {ticker}: up to date",
                "action_preview": None,
            }
        status = str(sync.get("status", "unknown"))
        if status == "missing":
            action_id = "single_ticker_announcement_backfill"
            args = {"ticker": ticker, "years": 3, "process_documents": True}
        else:
            action_id = "update_ticker_financials"
            args = {"ticker": ticker, "years": 1, "process_documents": True}
        action_preview: dict[str, Any] = {
            "action_id": action_id,
            "args": args,
        }
        if self.action_registry:
            try:
                preview = self.action_registry.preview(action_id, args)
                action_preview["command"] = preview.command
                action_preview["impact"] = preview.estimated_impact
                action_preview["timeout_seconds"] = preview.timeout_seconds
            except Exception:
                pass
        if action_id == "single_ticker_announcement_backfill":
            note = (
                f"Announcement sync check for {ticker}: missing local announcement history. "
                "Use /confirm to backfill or /cancel to skip."
            )
        else:
            note = (
                f"Announcement sync check for {ticker}: {status}. "
                "Use /confirm to update or /cancel to skip."
            )
        return {"note": note, "action_preview": action_preview}

    # ------------------------------------------------------------------ #
    # Slash command handling                                              #
    # ------------------------------------------------------------------ #

    def _handle_slash_command(self, message: str) -> ChatResponse | None:
        """Parse and dispatch slash commands. Returns None if unrecognised."""
        parts = message.split(None, 2)
        cmd = parts[0].lower() if parts else ""
        sub = parts[1].lower() if len(parts) > 1 else ""
        rest = parts[2].strip() if len(parts) > 2 else ""

        handler = self._SLASH_DISPATCH.get(cmd)
        if handler is not None:
            return handler(self, sub, rest)
        return None

    # -- Toggle commands ------------------------------------------------ #

    @staticmethod
    def _parse_positive_int(value: str) -> int | None:
        try:
            parsed = int(value.strip())
        except Exception:
            return None
        if parsed <= 0:
            return None
        return parsed

    def _set_latest_sources_payloads(self, evidence: list[dict[str, Any]]) -> None:
        self._latest_sources_payloads = SourcesFormatter.collect_sources_payloads(
            evidence
        )

    def _slash_web(self, sub: str, _rest: str) -> ChatResponse | None:
        if sub not in ("on", "off"):
            return ChatResponse(
                text="Usage: /web on|off", evidence=[], mode=ResponseMode.FAST
            )
        enabled = sub == "on"
        if hasattr(self.tool_router, "web_default_enabled"):
            self.tool_router.web_default_enabled = enabled
        return ChatResponse(
            text=f"Web search {'enabled' if enabled else 'disabled'}.",
            evidence=[],
            mode=ResponseMode.FAST,
        )

    def _slash_rag(self, sub: str, _rest: str) -> ChatResponse | None:
        if sub not in ("on", "off"):
            return ChatResponse(
                text="Usage: /rag on|off", evidence=[], mode=ResponseMode.FAST
            )
        enabled = sub == "on"
        if hasattr(self.tool_router, "qual_context_enabled"):
            self.tool_router.qual_context_enabled = enabled
        return ChatResponse(
            text=f"RAG context {'enabled' if enabled else 'disabled'}.",
            evidence=[],
            mode=ResponseMode.FAST,
        )

    def _slash_dbdiag(self, sub: str, _rest: str) -> ChatResponse | None:
        if sub not in ("on", "off"):
            return ChatResponse(
                text="Usage: /dbdiag on|off", evidence=[], mode=ResponseMode.FAST
            )
        enabled = sub == "on"
        if hasattr(self.tool_router, "db_diagnostics_enabled"):
            self.tool_router.db_diagnostics_enabled = enabled
        return ChatResponse(
            text=f"DB diagnostics {'enabled' if enabled else 'disabled'}.",
            evidence=[],
            mode=ResponseMode.FAST,
        )

    def _slash_sources(self, sub: str, rest: str) -> ChatResponse | None:
        if sub in ("on", "off"):
            enabled = sub == "on"
            if self._state_store is not None:
                self._state_store.set_preference(
                    "show_sources", "true" if enabled else "false"
                )
            return ChatResponse(
                text=f"Source display {'enabled' if enabled else 'disabled'}.",
                evidence=[],
                mode=ResponseMode.FAST,
            )

        if sub == "list":
            footer = SourcesFormatter.format_list(self._latest_sources_payloads)
            if footer:
                return ChatResponse(text=footer, evidence=[], mode=ResponseMode.FAST)
            return ChatResponse(
                text="No sources available for inspection. Ask a question first.",
                evidence=[],
                mode=ResponseMode.FAST,
            )

        if sub == "show":
            if not self._latest_sources_payloads:
                return ChatResponse(
                    text="No sources available for inspection. Ask a question first.",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            index = self._parse_positive_int(rest)
            if index is None:
                return ChatResponse(
                    text="Usage: /sources show <n>", evidence=[], mode=ResponseMode.FAST
                )
            show_text = SourcesFormatter.format_show(
                self._latest_sources_payloads, index
            )
            return ChatResponse(
                text=show_text,
                evidence=[],
                mode=ResponseMode.FAST,
            )

        if sub:
            if self._state_store is not None:
                current = self._state_store.get_preference("show_sources", "true")
            else:
                current = "true"
            return ChatResponse(
                text=(
                    f"Sources display: {'ON' if current == 'true' else 'OFF'}. "
                    "Use /sources on|off to toggle."
                ),
                evidence=[],
                mode=ResponseMode.FAST,
            )

        if self._state_store is not None:
            current = self._state_store.get_preference("show_sources", "true")
        else:
            current = "true"
        return ChatResponse(
            text=(
                f"Sources display: {'ON' if current == 'true' else 'OFF'}. "
                "Use /sources on|off to toggle."
            ),
            evidence=[],
            mode=ResponseMode.FAST,
        )

    # -- Info commands -------------------------------------------------- #

    def _slash_health(self, _sub: str, _rest: str) -> ChatResponse | None:
        lines: list[str] = ["Service health:"]
        for name, client_attr in [
            ("llama.cpp", "ollama_client"),
            ("backend", None),
        ]:
            client = (
                getattr(self, client_attr, None)
                if client_attr
                else getattr(self.tool_router, "backend_api_client", None)
            )
            if client is None:
                lines.append(f"  {name}: not configured")
                continue
            try:
                h = client.health(timeout=5.0)
                ok = h.get("ok", False) if isinstance(h, dict) else False
                status = "ok" if ok else f"degraded ({h})"
            except Exception as exc:
                status = f"unreachable ({exc})"
            lines.append(f"  {name}: {status}")
        return ChatResponse(text="\n".join(lines), evidence=[], mode=ResponseMode.FAST)

    def _slash_prompt(self, _sub: str, _rest: str) -> ChatResponse | None:
        prompt_text = self._build_system_instruction(ResponseMode.FAST, None, {})
        # Truncate for readability.
        if len(prompt_text) > 2000:
            prompt_text = prompt_text[:2000] + "\n... (truncated)"
        return ChatResponse(
            text=f"```\n{prompt_text}\n```", evidence=[], mode=ResponseMode.FAST
        )

    def _slash_access(self, _sub: str, _rest: str) -> ChatResponse | None:
        lines: list[str] = ["Access status:"]
        web = getattr(self.tool_router, "web_default_enabled", False)
        rag = getattr(self.tool_router, "qual_context_enabled", False)
        dbdiag = getattr(self.tool_router, "db_diagnostics_enabled", False)
        backend = getattr(self.tool_router, "backend_api_client", None) is not None
        brave = getattr(self.tool_router, "brave_search_client", None) is not None
        lines.append(f"  web: {'on' if web else 'off'}")
        lines.append(f"  rag: {'on' if rag else 'off'}")
        lines.append(f"  db_diagnostics: {'on' if dbdiag else 'off'}")
        lines.append(f"  backend_api: {'connected' if backend else 'not configured'}")
        lines.append(f"  brave_search: {'available' if brave else 'not configured'}")
        agent_mode = os.environ.get("COCKPIT_AGENT_MODE", "structured")
        lines.append(f"  agent_mode: {agent_mode}")
        lines.append(f"  agent_loop: {'active' if self._agent_loop else 'inactive'}")
        return ChatResponse(text="\n".join(lines), evidence=[], mode=ResponseMode.FAST)

    @staticmethod
    def _format_table(
        headers: list[str], rows: list[list[Any]], *, max_cell_chars: int = 120
    ) -> str:
        if not rows:
            return "(none)"

        def _clean(value: Any) -> str:
            text = str(value if value is not None else "")
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) > max_cell_chars:
                return text[: max_cell_chars - 3] + "..."
            return text or "-"

        cleaned_rows = [[_clean(col) for col in row] for row in rows]
        widths: list[int] = []
        for idx, header in enumerate(headers):
            column_width = len(_clean(header))
            for row in cleaned_rows:
                if idx < len(row):
                    column_width = max(column_width, len(row[idx]))
            widths.append(min(column_width, max_cell_chars))

        def _fit(text: str, width: int) -> str:
            clipped = text if len(text) <= width else text[: width - 3] + "..."
            return clipped.ljust(width)

        header_line = " | ".join(
            _fit(_clean(header), widths[idx]) for idx, header in enumerate(headers)
        )
        divider = "-+-".join("-" * width for width in widths)

        lines = [header_line, divider]
        for row in cleaned_rows:
            padded = []
            for idx, width in enumerate(widths):
                value = row[idx] if idx < len(row) else "-"
                padded.append(_fit(value, width))
            lines.append(" | ".join(padded))
        return "\n".join(lines)

    @staticmethod
    def _clip_rows(
        rows: list[dict[str, Any]],
        *,
        max_rows: int,
        keep_ends: bool = False,
    ) -> tuple[list[dict[str, Any]], int]:
        if max_rows <= 0 or len(rows) <= max_rows:
            return rows, 0
        if keep_ends and max_rows >= 2:
            head = max_rows // 2
            tail = max_rows - head
            clipped = rows[:head] + rows[-tail:]
            return clipped, len(rows) - len(clipped)
        clipped = rows[:max_rows]
        return clipped, len(rows) - max_rows

    @staticmethod
    def _build_ascii_trend(values: list[float], *, width: int = 64) -> str:
        if not values:
            return ""
        glyphs = " .:-=+*#%@"
        points: list[float] = []
        if len(values) <= width:
            points = values
        else:
            step = (len(values) - 1) / float(width - 1)
            for idx in range(width):
                points.append(values[int(round(idx * step))])

        low = min(points)
        high = max(points)
        span = high - low
        if span <= 1e-12:
            return "-" * len(points)

        out = []
        max_idx = len(glyphs) - 1
        for value in points:
            scaled = int(round(((value - low) / span) * max_idx))
            scaled = max(0, min(max_idx, scaled))
            out.append(glyphs[scaled])
        return "".join(out)

    @staticmethod
    def _format_numeric(value: Any, *, digits: int = 2) -> str:
        try:
            return f"{float(value):,.{digits}f}"
        except (TypeError, ValueError):
            return "-"

    @staticmethod
    def _format_percent(value: Any, *, digits: int = 2) -> str:
        try:
            return f"{float(value):+.{digits}f}%"
        except (TypeError, ValueError):
            return "-"

    @staticmethod
    def _is_valid_dump_ticker(value: str) -> bool:
        return bool(re.fullmatch(r"[A-Z0-9]{1,10}", str(value or "").strip().upper()))

    def _collect_cockpit_local_memory(self, ticker: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "agent_memory": [],
            "watchlist_history": [],
            "dossier_findings": [],
            "strategy_criteria": [],
            "strategy_decision": None,
            "errors": [],
        }

        if self._state_store is not None and hasattr(
            self._state_store, "get_entity_observations"
        ):
            try:
                observations = self._state_store.get_entity_observations(
                    ticker, limit=200
                )
                if isinstance(observations, list):
                    payload["agent_memory"] = [
                        row for row in observations if isinstance(row, dict)
                    ]
            except Exception as exc:
                payload["errors"].append(f"agent_memory: {exc}")

        if self._state_store is not None and hasattr(
            self._state_store, "list_update_events"
        ):
            try:
                events = self._state_store.list_update_events(
                    getattr(self, "_thread_id", ""), ticker=ticker, limit=100
                )
                if isinstance(events, list):
                    payload["watchlist_history"] = [
                        row for row in events if isinstance(row, dict)
                    ]
            except Exception as exc:
                payload["errors"].append(f"watchlist_history: {exc}")

        if self._dossier_service is not None:
            try:
                dossier = self._dossier_service.recall(ticker, limit=100)
                if isinstance(dossier, dict) and dossier.get("ok"):
                    findings = dossier.get("findings") or []
                    if isinstance(findings, list):
                        payload["dossier_findings"] = [
                            row for row in findings if isinstance(row, dict)
                        ]
            except Exception as exc:
                payload["errors"].append(f"dossier_findings: {exc}")

        if self._strategy_service is not None:
            try:
                criteria = self._strategy_service.get_ticker(ticker)
                if isinstance(criteria, list):
                    payload["strategy_criteria"] = [
                        row for row in criteria if isinstance(row, dict)
                    ]
                payload["strategy_decision"] = self._strategy_service.get_decision(
                    ticker
                )
            except Exception as exc:
                payload["errors"].append(f"strategy: {exc}")

        return payload

    def _format_company_dump_output(
        self,
        ticker: str,
        backend_dump: dict[str, Any],
        cockpit_local_memory: dict[str, Any],
        *,
        compact: bool,
    ) -> str:
        summary = backend_dump.get("summary") or {}
        docs = [
            row for row in (backend_dump.get("docs") or []) if isinstance(row, dict)
        ]
        financials = [
            row
            for row in (backend_dump.get("financials") or [])
            if isinstance(row, dict)
        ]
        announcements = [
            row
            for row in (backend_dump.get("announcement_context") or [])
            if isinstance(row, dict)
        ]
        risk_notes = [
            row
            for row in (backend_dump.get("risk_notes") or [])
            if isinstance(row, dict)
        ]
        price_history = [
            row
            for row in (backend_dump.get("price_history_1y") or [])
            if isinstance(row, dict)
        ]
        extraction_failures = [
            row
            for row in (backend_dump.get("extraction_failures") or [])
            if isinstance(row, dict)
        ]
        low_conf = [
            row
            for row in (backend_dump.get("low_confidence_financials") or [])
            if isinstance(row, dict)
        ]

        company_memory = backend_dump.get("company_memory") or {}
        market_memory = backend_dump.get("market_memory") or {}
        company_entries = [
            row
            for row in (company_memory.get("entries") or [])
            if isinstance(row, dict)
        ]
        company_change_log = [
            row
            for row in (company_memory.get("change_log") or [])
            if isinstance(row, dict)
        ]
        market_items = [
            row for row in (market_memory.get("items") or []) if isinstance(row, dict)
        ]

        local_agent = [
            row
            for row in (cockpit_local_memory.get("agent_memory") or [])
            if isinstance(row, dict)
        ]
        local_dossier = [
            row
            for row in (cockpit_local_memory.get("dossier_findings") or [])
            if isinstance(row, dict)
        ]
        local_watchlist = [
            row
            for row in (cockpit_local_memory.get("watchlist_history") or [])
            if isinstance(row, dict)
        ]
        local_strategy = [
            row
            for row in (cockpit_local_memory.get("strategy_criteria") or [])
            if isinstance(row, dict)
        ]

        limits = {
            "financials": 12,
            "price_history": 42,
            "docs": 24,
            "announcements": 12,
            "risk_notes": 12,
            "company_entries": 18,
            "company_change_log": 18,
            "market_items": 18,
            "local_agent": 12,
            "local_dossier": 12,
            "local_watchlist": 12,
            "local_strategy": 12,
            "extraction_failures": 18,
            "low_conf": 18,
        }

        def _limit(
            rows: list[dict[str, Any]], key: str, *, keep_ends: bool = False
        ) -> tuple[list[dict[str, Any]], int]:
            if not compact:
                return rows, 0
            return self._clip_rows(
                rows,
                max_rows=int(limits[key]),
                keep_ends=keep_ends,
            )

        financials_view, financials_omitted = _limit(financials, "financials")
        price_view, price_omitted = _limit(
            price_history,
            "price_history",
            keep_ends=True,
        )
        docs_view, docs_omitted = _limit(docs, "docs")
        announcements_view, announcements_omitted = _limit(
            announcements, "announcements"
        )
        risk_view, risk_omitted = _limit(risk_notes, "risk_notes")
        company_entries_view, company_entries_omitted = _limit(
            company_entries,
            "company_entries",
        )
        company_change_view, company_change_omitted = _limit(
            company_change_log,
            "company_change_log",
        )
        market_view, market_omitted = _limit(market_items, "market_items")
        local_agent_view, local_agent_omitted = _limit(local_agent, "local_agent")
        local_dossier_view, local_dossier_omitted = _limit(
            local_dossier, "local_dossier"
        )
        local_watchlist_view, local_watchlist_omitted = _limit(
            local_watchlist,
            "local_watchlist",
        )
        local_strategy_view, local_strategy_omitted = _limit(
            local_strategy,
            "local_strategy",
        )
        failures_view, failures_omitted = _limit(
            extraction_failures,
            "extraction_failures",
        )
        low_conf_view, low_conf_omitted = _limit(low_conf, "low_conf")

        lines: list[str] = [f"Company Data Dump: {ticker}"]
        lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
        if compact:
            lines.append(
                "View: clean (compact). Use `/filestats raw <TICKER>` for full rows."
            )
        else:
            lines.append("View: raw (full rows).")
        lines.append("")
        lines.append("Summary")
        lines.append(
            f"- Docs: {summary.get('doc_count', len(docs))} | Financial periods: {summary.get('financial_period_count', len(financials))} | Announcements: {summary.get('announcement_context_count', len(announcements))}"
        )
        lines.append(
            f"- Risk notes: {summary.get('risk_note_count', len(risk_notes))} | Extraction failures: {summary.get('extraction_failure_count', len(extraction_failures))} | Low-confidence rows: {summary.get('low_confidence_financial_count', len(low_conf))}"
        )
        lines.append(
            f"- Backend company memory: {summary.get('company_memory_entry_count', len(company_entries))} entries | Backend market memory: {summary.get('market_memory_item_count', len(market_items))} items"
        )
        lines.append(
            f"- 1Y price points: {summary.get('price_points_1y', len(price_history))} | Last close: {self._format_numeric(summary.get('last_close'), digits=4)} | 1Y return: {self._format_percent(summary.get('one_year_return_pct'))}"
        )
        lines.append("")

        lines.append("Financial Metrics")
        lines.append(
            self._format_table(
                [
                    "Period End",
                    "Type",
                    "Revenue",
                    "EBIT",
                    "NPAT",
                    "Operating CF",
                    "Capex",
                    "Cash End",
                    "Net Debt",
                    "Confidence",
                    "Source Doc",
                ],
                [
                    [
                        row.get("period_end"),
                        row.get("period_type"),
                        row.get("revenue"),
                        row.get("ebit"),
                        row.get("np_attributable"),
                        row.get("operating_cf"),
                        row.get("capex"),
                        row.get("cash_end"),
                        row.get("net_debt"),
                        row.get("confidence_metrics"),
                        row.get("source_document_id"),
                    ]
                    for row in financials_view
                ],
            )
        )
        if financials_omitted > 0:
            lines.append(
                f"... {financials_omitted} financial rows omitted in clean view."
            )
        lines.append("")

        lines.append("Price Summary (1Y Daily)")
        lines.append(
            f"- Coverage: {summary.get('price_coverage_start') or '-'} to {summary.get('price_coverage_end') or '-'}"
        )
        lines.append(
            f"- High close: {self._format_numeric(summary.get('high_close_1y'), digits=4)} | Low close: {self._format_numeric(summary.get('low_close_1y'), digits=4)}"
        )
        close_values: list[float] = []
        for row in price_history:
            try:
                close_val = float(row.get("close"))
            except (TypeError, ValueError):
                continue
            close_values.append(close_val)
        trend = self._build_ascii_trend(close_values, width=72)
        if trend:
            lines.append(f"- Trend: [{trend}]")
        lines.append(
            self._format_table(
                ["Date", "Open", "High", "Low", "Close", "Volume"],
                [
                    [
                        str(row.get("timestamp") or "")[:10],
                        self._format_numeric(row.get("open"), digits=4),
                        self._format_numeric(row.get("high"), digits=4),
                        self._format_numeric(row.get("low"), digits=4),
                        self._format_numeric(row.get("close"), digits=4),
                        row.get("volume"),
                    ]
                    for row in price_view
                ],
            )
        )
        if price_omitted > 0:
            lines.append(f"... {price_omitted} price rows omitted in clean view.")
        lines.append("")

        lines.append("PDFs / Documents")
        lines.append(
            self._format_table(
                ["Document ID", "Published", "Class", "Title", "PDF Path"],
                [
                    [
                        row.get("document_id"),
                        str(row.get("published_at") or "")[:10],
                        row.get("doc_class"),
                        row.get("title"),
                        row.get("pdf_path"),
                    ]
                    for row in docs_view
                ],
            )
        )
        if docs_omitted > 0:
            lines.append(f"... {docs_omitted} document rows omitted in clean view.")
        lines.append("")

        lines.append("Announcement Context")
        lines.append(
            self._format_table(
                ["Published", "Title", "Excerpt"],
                [
                    [
                        str(row.get("published_at") or "")[:10],
                        row.get("title"),
                        row.get("excerpt"),
                    ]
                    for row in announcements_view
                ],
                max_cell_chars=180,
            )
        )
        if announcements_omitted > 0:
            lines.append(
                f"... {announcements_omitted} announcement rows omitted in clean view."
            )
        lines.append("")

        lines.append("Narrative / Risk Notes")
        lines.append(
            self._format_table(
                ["Published", "Title", "Risk Summary", "Guidance", "Material Changes"],
                [
                    [
                        str(row.get("published_at") or "")[:10],
                        row.get("title"),
                        row.get("risk_summary"),
                        row.get("guidance_summary"),
                        row.get("material_changes"),
                    ]
                    for row in risk_view
                ],
                max_cell_chars=180,
            )
        )
        if risk_omitted > 0:
            lines.append(f"... {risk_omitted} risk-note rows omitted in clean view.")
        lines.append("")

        lines.append("Saved Memory — Backend")
        lines.append("Company Memory Entries")
        lines.append(
            self._format_table(
                [
                    "ID",
                    "Type",
                    "Status",
                    "Statement",
                    "Confidence",
                    "Materiality",
                    "Source",
                    "Source ID",
                    "Last Seen",
                ],
                [
                    [
                        row.get("entry_id"),
                        row.get("type"),
                        row.get("status"),
                        row.get("statement"),
                        row.get("confidence"),
                        row.get("materiality"),
                        row.get("source"),
                        row.get("source_id"),
                        row.get("last_seen_at"),
                    ]
                    for row in company_entries_view
                ],
                max_cell_chars=160,
            )
        )
        if company_entries_omitted > 0:
            lines.append(
                f"... {company_entries_omitted} backend company-memory rows omitted in clean view."
            )
        lines.append("Company Memory Change Log")
        lines.append(
            self._format_table(
                ["Change ID", "Entry ID", "Event", "Created", "Details"],
                [
                    [
                        row.get("change_id"),
                        row.get("entry_id"),
                        row.get("event_type"),
                        row.get("created_at"),
                        row.get("details"),
                    ]
                    for row in company_change_view
                ],
                max_cell_chars=180,
            )
        )
        if company_change_omitted > 0:
            lines.append(
                f"... {company_change_omitted} backend company-memory changes omitted in clean view."
            )
        lines.append("Market Memory")
        lines.append(
            self._format_table(
                ["Type", "Statement", "Confidence", "Materiality", "Source"],
                [
                    [
                        row.get("type"),
                        row.get("statement"),
                        row.get("confidence"),
                        row.get("materiality"),
                        row.get("source"),
                    ]
                    for row in market_view
                ],
                max_cell_chars=180,
            )
        )
        if market_omitted > 0:
            lines.append(
                f"... {market_omitted} backend market-memory rows omitted in clean view."
            )
        lines.append("")

        lines.append("Saved Memory — Cockpit Local")
        lines.append("Agent Memory")
        lines.append(
            self._format_table(
                ["Observed At", "Observation", "Kind"],
                [
                    [
                        row.get("created_at") or row.get("observed_at"),
                        row.get("observation")
                        or row.get("content")
                        or row.get("statement")
                        or row.get("summary")
                        or row,
                        row.get("kind") or row.get("type"),
                    ]
                    for row in local_agent_view
                ],
                max_cell_chars=180,
            )
        )
        if local_agent_omitted > 0:
            lines.append(
                f"... {local_agent_omitted} cockpit-local agent-memory rows omitted in clean view."
            )
        lines.append("Dossier Findings")
        lines.append(
            self._format_table(
                ["Date", "Category", "Finding", "Confidence", "Source"],
                [
                    [
                        str(row.get("ts") or row.get("date") or "")[:10],
                        row.get("category"),
                        row.get("finding"),
                        row.get("confidence"),
                        row.get("source"),
                    ]
                    for row in local_dossier_view
                ],
                max_cell_chars=180,
            )
        )
        if local_dossier_omitted > 0:
            lines.append(
                f"... {local_dossier_omitted} cockpit-local dossier rows omitted in clean view."
            )
        lines.append("Watchlist History")
        lines.append(
            self._format_table(
                ["Date", "Action", "Status", "Summary"],
                [
                    [
                        str(row.get("created_at") or row.get("date") or "")[:10],
                        row.get("action_id") or row.get("action"),
                        row.get("status"),
                        row.get("summary") or row.get("summary_json"),
                    ]
                    for row in local_watchlist_view
                ],
                max_cell_chars=180,
            )
        )
        if local_watchlist_omitted > 0:
            lines.append(
                f"... {local_watchlist_omitted} cockpit-local watchlist rows omitted in clean view."
            )
        lines.append("Strategy Criteria")
        lines.append(
            self._format_table(
                ["ID", "Criterion", "Priority", "Decision"],
                [
                    [
                        row.get("id"),
                        row.get("criterion"),
                        row.get("priority"),
                        row.get("decision"),
                    ]
                    for row in local_strategy_view
                ],
                max_cell_chars=180,
            )
        )
        if local_strategy_omitted > 0:
            lines.append(
                f"... {local_strategy_omitted} cockpit-local strategy rows omitted in clean view."
            )
        if cockpit_local_memory.get("strategy_decision"):
            lines.append(
                f"Current strategy decision: {cockpit_local_memory.get('strategy_decision')}"
            )
        lines.append("")

        lines.append("Data Quality")
        lines.append("Extraction Failures")
        lines.append(
            self._format_table(
                ["Run ID", "Document", "Status", "Created", "Error"],
                [
                    [
                        row.get("run_id"),
                        row.get("document_id"),
                        row.get("status"),
                        row.get("created_at"),
                        row.get("error"),
                    ]
                    for row in failures_view
                ],
                max_cell_chars=180,
            )
        )
        if failures_omitted > 0:
            lines.append(
                f"... {failures_omitted} extraction-failure rows omitted in clean view."
            )
        lines.append("Low-confidence Financial Rows")
        lines.append(
            self._format_table(
                ["Period End", "Type", "Confidence", "Source Doc"],
                [
                    [
                        row.get("period_end"),
                        row.get("period_type"),
                        row.get("confidence_metrics"),
                        row.get("source_document_id"),
                    ]
                    for row in low_conf_view
                ],
            )
        )
        if low_conf_omitted > 0:
            lines.append(
                f"... {low_conf_omitted} low-confidence rows omitted in clean view."
            )
        lines.append("")

        backend_errors = [e for e in (backend_dump.get("errors") or []) if e]
        local_errors = [e for e in (cockpit_local_memory.get("errors") or []) if e]
        if backend_errors or local_errors:
            lines.append("Errors")
            for item in backend_errors:
                lines.append(f"- backend: {item}")
            for item in local_errors:
                lines.append(f"- cockpit-local: {item}")
            lines.append("")

        return "\n".join(lines).strip()

    def _build_filestats_response(self, ticker: str, *, compact: bool) -> ChatResponse:
        backend_client = getattr(self.tool_router, "backend_api_client", None)
        if backend_client is None:
            return ChatResponse(
                text="Filestats unavailable: backend API client is not configured.",
                evidence=[],
                mode=ResponseMode.FAST,
            )

        try:
            backend_dump = backend_client.get_company_dump(ticker=ticker)
        except Exception as exc:
            return ChatResponse(
                text=f"Filestats failed for {ticker}: {exc}",
                evidence=[],
                mode=ResponseMode.FAST,
            )

        if not isinstance(backend_dump, dict):
            return ChatResponse(
                text=f"Filestats failed for {ticker}: backend returned non-object payload.",
                evidence=[],
                mode=ResponseMode.FAST,
            )

        local_memory = self._collect_cockpit_local_memory(ticker)
        dashboard_path, dashboard_error = self._write_filestats_dashboard(
            ticker,
            backend_dump,
            local_memory,
        )
        if dashboard_error:
            local_errors = local_memory.get("errors")
            if isinstance(local_errors, list):
                local_errors.append(f"dashboard: {dashboard_error}")

        text = self._format_company_dump_output(
            ticker,
            backend_dump,
            local_memory,
            compact=compact,
        )
        if dashboard_path:
            text = f"Dashboard: {dashboard_path}\n\n{text}"
        return ChatResponse(
            text=text,
            evidence=[
                {
                    "type": "company_dump",
                    "details": {
                        "ticker": ticker,
                        "view_mode": "compact" if compact else "raw",
                        "dashboard_path": dashboard_path,
                        "backend": backend_dump,
                        "cockpit_local_memory": local_memory,
                    },
                }
            ],
            mode=ResponseMode.FAST,
        )

    def _write_filestats_dashboard(
        self,
        ticker: str,
        backend_dump: dict[str, Any],
        cockpit_local_memory: dict[str, Any],
    ) -> tuple[str | None, str | None]:
        try:
            from cockpit.core.plotly_html import build_filestats_dashboard_html
        except Exception as exc:
            return None, f"dashboard builder unavailable: {exc}"

        report_root_raw = str(os.environ.get("COCKPIT_REPORT_DIR", "")).strip()
        if report_root_raw:
            base_dir = Path(report_root_raw).expanduser()
        else:
            base_dir = Path("/tmp/tenn/reports")
        out_dir = base_dir / "cockpit"

        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / f"{ticker}_{ts}_filestats_dashboard.html"

        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            html = build_filestats_dashboard_html(
                {
                    "ticker": ticker,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    **backend_dump,
                    "cockpit_local_memory": cockpit_local_memory,
                }
            )
            out_path.write_text(html, encoding="utf-8")
            return str(out_path), None
        except Exception as exc:
            return None, str(exc)

    def _slash_filestats(self, sub: str, rest: str) -> ChatResponse | None:
        raw = f"{sub} {rest}".strip()
        tokens = [tok for tok in raw.split() if tok]
        compact = True
        ticker = ""

        for token in tokens:
            candidate = token.strip().upper()
            if candidate in {"RAW", "FULL", "ALL"}:
                compact = False
                continue
            if ticker:
                return ChatResponse(
                    text=("Usage: /filestats <TICKER>\n       /filestats raw <TICKER>"),
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            ticker = candidate

        if not ticker:
            return ChatResponse(
                text=("Usage: /filestats <TICKER>\n       /filestats raw <TICKER>"),
                evidence=[],
                mode=ResponseMode.FAST,
            )
        if not self._is_valid_dump_ticker(ticker):
            return ChatResponse(
                text="Ticker must be 1-10 alphanumeric characters.",
                evidence=[],
                mode=ResponseMode.FAST,
            )
        return self._build_filestats_response(ticker, compact=compact)

    def _try_filestats_shortcircuit(self, message: str) -> ChatResponse | None:
        match = self._DIRECT_FILESTATS_RE.fullmatch(message.strip())
        if not match:
            return None
        ticker = (
            match.group("ticker_prefix") or match.group("ticker_suffix") or ""
        ).upper()
        if not ticker or not self._is_valid_dump_ticker(ticker):
            return ChatResponse(
                text="Ticker must be 1-10 alphanumeric characters.",
                evidence=[],
                mode=ResponseMode.FAST,
            )
        return self._build_filestats_response(ticker, compact=True)

    def _format_memory_output(
        self,
        ticker: str,
        backend_dump: dict[str, Any],
        cockpit_local_memory: dict[str, Any],
        *,
        compact: bool,
    ) -> str:
        company_memory = backend_dump.get("company_memory") or {}
        market_memory = backend_dump.get("market_memory") or {}
        company_entries = [
            row
            for row in (company_memory.get("entries") or [])
            if isinstance(row, dict)
        ]
        company_change_log = [
            row
            for row in (company_memory.get("change_log") or [])
            if isinstance(row, dict)
        ]
        market_items = [
            row for row in (market_memory.get("items") or []) if isinstance(row, dict)
        ]
        local_agent = [
            row
            for row in (cockpit_local_memory.get("agent_memory") or [])
            if isinstance(row, dict)
        ]
        local_dossier = [
            row
            for row in (cockpit_local_memory.get("dossier_findings") or [])
            if isinstance(row, dict)
        ]
        local_watchlist = [
            row
            for row in (cockpit_local_memory.get("watchlist_history") or [])
            if isinstance(row, dict)
        ]
        local_strategy = [
            row
            for row in (cockpit_local_memory.get("strategy_criteria") or [])
            if isinstance(row, dict)
        ]

        def _limit(rows: list[dict[str, Any]], max_rows: int) -> tuple[list[dict[str, Any]], int]:
            if not compact:
                return rows, 0
            return self._clip_rows(rows, max_rows=max_rows)

        company_entries_view, company_entries_omitted = _limit(company_entries, 18)
        company_change_view, company_change_omitted = _limit(company_change_log, 18)
        market_view, market_omitted = _limit(market_items, 18)
        local_agent_view, local_agent_omitted = _limit(local_agent, 12)
        local_dossier_view, local_dossier_omitted = _limit(local_dossier, 12)
        local_watchlist_view, local_watchlist_omitted = _limit(local_watchlist, 12)
        local_strategy_view, local_strategy_omitted = _limit(local_strategy, 12)

        lines: list[str] = [f"Memory View: {ticker}"]
        lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
        if compact:
            lines.append(
                "View: clean (compact). Use `/memory raw <TICKER>` for full rows."
            )
        else:
            lines.append("View: raw (full rows).")
        lines.append("")
        lines.append("Summary")
        lines.append(
            f"- Backend company memory: {company_memory.get('entries_total', len(company_entries))} entries | Change log: {company_memory.get('change_log_total', len(company_change_log))}"
        )
        lines.append(
            f"- Backend market memory: {market_memory.get('items_total', len(market_items))} items | Sector: {market_memory.get('sector') or '-'}"
        )
        lines.append(
            f"- Cockpit-local memory: agent {len(local_agent)} | dossier {len(local_dossier)} | watchlist history {len(local_watchlist)} | strategy {len(local_strategy)}"
        )
        lines.append("")

        lines.append("Backend Company Memory")
        lines.append(
            self._format_table(
                ["ID", "Status", "Type", "Statement", "Confidence", "Materiality", "Source", "Last Seen"],
                [
                    [
                        row.get("entry_id"),
                        row.get("status"),
                        row.get("type"),
                        row.get("statement"),
                        row.get("confidence"),
                        row.get("materiality"),
                        row.get("source"),
                        row.get("last_seen_at"),
                    ]
                    for row in company_entries_view
                ],
                max_cell_chars=180,
            )
        )
        if company_entries_omitted > 0:
            lines.append(
                f"... {company_entries_omitted} backend company-memory rows omitted in clean view."
            )

        lines.append("Backend Company Memory Changes")
        lines.append(
            self._format_table(
                ["Change ID", "Entry ID", "Event", "Created", "Details"],
                [
                    [
                        row.get("change_id"),
                        row.get("entry_id"),
                        row.get("event_type"),
                        row.get("created_at"),
                        row.get("details"),
                    ]
                    for row in company_change_view
                ],
                max_cell_chars=180,
            )
        )
        if company_change_omitted > 0:
            lines.append(
                f"... {company_change_omitted} backend company-memory change rows omitted in clean view."
            )

        lines.append("Backend Market Memory")
        lines.append(
            self._format_table(
                ["Scope", "Entity", "ID", "Status", "Type", "Statement", "Source", "Last Seen"],
                [
                    [
                        "sector" if row.get("sector") else "macro",
                        row.get("sector") or row.get("macro_topic"),
                        row.get("entry_id"),
                        row.get("status"),
                        row.get("type"),
                        row.get("statement"),
                        row.get("source"),
                        row.get("last_seen_at"),
                    ]
                    for row in market_view
                ],
                max_cell_chars=180,
            )
        )
        if market_omitted > 0:
            lines.append(
                f"... {market_omitted} backend market-memory rows omitted in clean view."
            )

        lines.append("Cockpit Local Memory")
        lines.append(
            self._format_table(
                ["Observed At", "Kind", "Observation"],
                [
                    [
                        row.get("created_at") or row.get("observed_at"),
                        row.get("kind") or row.get("type"),
                        row.get("observation")
                        or row.get("content")
                        or row.get("statement")
                        or row.get("summary")
                        or row,
                    ]
                    for row in local_agent_view
                ],
                max_cell_chars=180,
            )
        )
        if local_agent_omitted > 0:
            lines.append(
                f"... {local_agent_omitted} cockpit-local agent-memory rows omitted in clean view."
            )
        lines.append("Cockpit Dossier Findings")
        lines.append(
            self._format_table(
                ["Date", "Category", "Finding", "Confidence", "Source"],
                [
                    [
                        str(row.get("ts") or row.get("date") or "")[:10],
                        row.get("category"),
                        row.get("finding"),
                        row.get("confidence"),
                        row.get("source"),
                    ]
                    for row in local_dossier_view
                ],
                max_cell_chars=180,
            )
        )
        if local_dossier_omitted > 0:
            lines.append(
                f"... {local_dossier_omitted} cockpit-local dossier rows omitted in clean view."
            )
        lines.append("Cockpit Watchlist History")
        lines.append(
            self._format_table(
                ["Date", "Action", "Status", "Summary"],
                [
                    [
                        str(row.get("created_at") or row.get("date") or "")[:10],
                        row.get("action_id") or row.get("action"),
                        row.get("status"),
                        row.get("summary") or row.get("summary_json"),
                    ]
                    for row in local_watchlist_view
                ],
                max_cell_chars=180,
            )
        )
        if local_watchlist_omitted > 0:
            lines.append(
                f"... {local_watchlist_omitted} cockpit-local watchlist rows omitted in clean view."
            )
        lines.append("Cockpit Strategy Criteria")
        lines.append(
            self._format_table(
                ["ID", "Criterion", "Priority", "Decision"],
                [
                    [
                        row.get("id"),
                        row.get("criterion"),
                        row.get("priority"),
                        row.get("decision"),
                    ]
                    for row in local_strategy_view
                ],
                max_cell_chars=180,
            )
        )
        if local_strategy_omitted > 0:
            lines.append(
                f"... {local_strategy_omitted} cockpit-local strategy rows omitted in clean view."
            )

        backend_errors = [e for e in (backend_dump.get("errors") or []) if e]
        local_errors = [e for e in (cockpit_local_memory.get("errors") or []) if e]
        if backend_errors or local_errors:
            lines.append("Errors")
            for item in backend_errors:
                lines.append(f"- backend: {item}")
            for item in local_errors:
                lines.append(f"- cockpit-local: {item}")

        return "\n".join(lines).strip()

    def _build_memory_response(self, ticker: str, *, compact: bool) -> ChatResponse:
        backend_client = getattr(self.tool_router, "backend_api_client", None)
        if backend_client is None:
            return ChatResponse(
                text="Memory view unavailable: backend API client is not configured.",
                evidence=[],
                mode=ResponseMode.FAST,
            )

        try:
            backend_dump = backend_client.get_memory_dump(ticker=ticker)
        except Exception as exc:
            return ChatResponse(
                text=f"Memory view failed for {ticker}: {exc}",
                evidence=[],
                mode=ResponseMode.FAST,
            )

        if not isinstance(backend_dump, dict):
            return ChatResponse(
                text=f"Memory view failed for {ticker}: backend returned non-object payload.",
                evidence=[],
                mode=ResponseMode.FAST,
            )

        local_memory = self._collect_cockpit_local_memory(ticker)
        text = self._format_memory_output(
            ticker,
            backend_dump,
            local_memory,
            compact=compact,
        )
        return ChatResponse(
            text=text,
            evidence=[
                {
                    "type": "memory_dump",
                    "details": {
                        "ticker": ticker,
                        "view_mode": "compact" if compact else "raw",
                        "backend": backend_dump,
                        "cockpit_local_memory": local_memory,
                    },
                }
            ],
            mode=ResponseMode.FAST,
        )

    def _slash_memory(self, sub: str, rest: str) -> ChatResponse | None:
        raw = f"{sub} {rest}".strip()
        tokens = [tok for tok in raw.split() if tok]
        if not tokens:
            return ChatResponse(
                text=(
                    "Usage: /memory show <TICKER>\n"
                    "       /memory raw <TICKER>\n"
                    "       /memory add [company|market] <TICKER> <NOTE>\n"
                    "       /memory remove company <TICKER> <ENTRY_ID>\n"
                    "       /memory remove market [sector|macro] <ENTRY_ID>"
                ),
                evidence=[],
                mode=ResponseMode.FAST,
            )

        backend_client = getattr(self.tool_router, "backend_api_client", None)
        if backend_client is None:
            return ChatResponse(
                text="Memory management unavailable: backend API client is not configured.",
                evidence=[],
                mode=ResponseMode.FAST,
            )

        action = tokens.pop(0).lower()
        if action in {"show", "raw"}:
            compact = action != "raw"
            if tokens and tokens[0].strip().lower() == "raw":
                compact = False
                tokens.pop(0)
            if len(tokens) != 1:
                return ChatResponse(
                    text="Usage: /memory show <TICKER>\n       /memory raw <TICKER>",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            ticker = tokens[0].strip().upper()
            if not self._is_valid_dump_ticker(ticker):
                return ChatResponse(
                    text="Ticker must be 1-10 alphanumeric characters.",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            return self._build_memory_response(ticker, compact=compact)

        if action == "add":
            scope = "company"
            if tokens and tokens[0].strip().lower() in {"company", "market"}:
                scope = tokens.pop(0).strip().lower()
            if len(tokens) < 2:
                return ChatResponse(
                    text="Usage: /memory add [company|market] <TICKER> <NOTE>",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            ticker = tokens.pop(0).strip().upper()
            if not self._is_valid_dump_ticker(ticker):
                return ChatResponse(
                    text="Ticker must be 1-10 alphanumeric characters.",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            statement = " ".join(tokens).strip()
            if not statement:
                return ChatResponse(
                    text="Memory note must not be empty.",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            try:
                if scope == "market":
                    result = backend_client.add_market_memory_note(ticker, statement)
                else:
                    result = backend_client.add_company_memory_note(ticker, statement)
            except Exception as exc:
                return ChatResponse(
                    text=f"Memory add failed for {ticker}: {exc}",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            entry = result.get("entry") if isinstance(result, dict) else None
            entry_id = entry.get("entry_id") if isinstance(entry, dict) else None
            return ChatResponse(
                text=(
                    f"Added {scope} memory for {ticker}."
                    + (f" Entry ID: {entry_id}." if entry_id is not None else "")
                ),
                evidence=[{"type": "memory_mutation", "details": result}],
                mode=ResponseMode.FAST,
            )

        if action == "remove":
            scope = "company"
            if tokens and tokens[0].strip().lower() in {"company", "market"}:
                scope = tokens.pop(0).strip().lower()
            try:
                if scope == "market":
                    market_scope = "sector"
                    if tokens and tokens[0].strip().lower() in {"sector", "macro"}:
                        market_scope = tokens.pop(0).strip().lower()
                    if len(tokens) != 1:
                        raise ValueError
                    entry_id = int(tokens[0])
                    result = backend_client.expire_market_memory_entry(
                        entry_id,
                        scope=market_scope,
                    )
                    message = (
                        f"Expired market memory entry {entry_id} ({market_scope})."
                    )
                else:
                    if len(tokens) != 2:
                        raise ValueError
                    ticker = tokens[0].strip().upper()
                    if not self._is_valid_dump_ticker(ticker):
                        return ChatResponse(
                            text="Ticker must be 1-10 alphanumeric characters.",
                            evidence=[],
                            mode=ResponseMode.FAST,
                        )
                    entry_id = int(tokens[1])
                    result = backend_client.expire_company_memory_entry(ticker, entry_id)
                    message = f"Expired company memory entry {entry_id} for {ticker}."
            except ValueError:
                return ChatResponse(
                    text=(
                        "Usage: /memory remove company <TICKER> <ENTRY_ID>\n"
                        "       /memory remove market [sector|macro] <ENTRY_ID>"
                    ),
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            except Exception as exc:
                return ChatResponse(
                    text=f"Memory remove failed: {exc}",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            return ChatResponse(
                text=message,
                evidence=[{"type": "memory_mutation", "details": result}],
                mode=ResponseMode.FAST,
            )

        return ChatResponse(
            text=(
                "Usage: /memory show <TICKER>\n"
                "       /memory raw <TICKER>\n"
                "       /memory add [company|market] <TICKER> <NOTE>\n"
                "       /memory remove company <TICKER> <ENTRY_ID>\n"
                "       /memory remove market [sector|macro] <ENTRY_ID>"
            ),
            evidence=[],
            mode=ResponseMode.FAST,
        )

    # -- Watchlist commands --------------------------------------------- #

    def _slash_watch(self, sub: str, rest: str) -> ChatResponse | None:
        if self._state_store is None:
            return ChatResponse(
                text="Watchlist not available (no state store).",
                evidence=[],
                mode=ResponseMode.FAST,
            )

        if sub == "list":
            items = self._state_store.list_watch_tickers()
            if not items:
                return ChatResponse(
                    text="Watchlist is empty.", evidence=[], mode=ResponseMode.FAST
                )
            lines = [f"  {r['ticker']}  (added {r['added_at'][:10]})" for r in items]
            return ChatResponse(
                text=f"Watchlist ({len(items)}):\n" + "\n".join(lines),
                evidence=[{"type": "watchlist", "details": items}],
                mode=ResponseMode.FAST,
            )

        if sub == "add":
            ticker = rest.strip().upper()
            if not ticker:
                return ChatResponse(
                    text="Usage: /watch add <TICKER>",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            now = datetime.now(timezone.utc).isoformat()
            inserted = self._state_store.add_watch_ticker(ticker, now)
            msg = (
                f"Added {ticker} to watchlist."
                if inserted
                else f"{ticker} already on watchlist."
            )
            return ChatResponse(text=msg, evidence=[], mode=ResponseMode.FAST)

        if sub == "remove":
            ticker = rest.strip().upper()
            if not ticker:
                return ChatResponse(
                    text="Usage: /watch remove <TICKER>",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            removed = self._state_store.remove_watch_ticker(ticker)
            msg = (
                f"Removed {ticker} from watchlist."
                if removed
                else f"{ticker} not found on watchlist."
            )
            return ChatResponse(text=msg, evidence=[], mode=ResponseMode.FAST)

        if sub == "clear":
            count = self._state_store.clear_watch_tickers()
            return ChatResponse(
                text=f"Watchlist cleared ({count} removed).",
                evidence=[],
                mode=ResponseMode.FAST,
            )

        if sub == "scan":
            ticker_arg = rest.strip().upper() or None
            if self._agent_loop is not None and hasattr(
                self._agent_loop, "_tool_executor"
            ):
                executor = self._agent_loop._tool_executor
                tickers_csv = ticker_arg or ""
                result = executor.execute("scan_watchlist", {"tickers": tickers_csv})
                ok = result.get("ok", False)
                if ok:
                    scanned = result.get("tickers_scanned", [])
                    return ChatResponse(
                        text=f"Watchlist scan complete. Scanned: {', '.join(scanned) if scanned else 'none'}.",
                        evidence=[{"type": "watchlist_scan", "details": result}],
                        mode=ResponseMode.FAST,
                    )
                return ChatResponse(
                    text=f"Watchlist scan failed: {result.get('error', 'unknown')}",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            return ChatResponse(
                text="Watchlist scan not available (agent loop not initialised).",
                evidence=[],
                mode=ResponseMode.FAST,
            )

        return ChatResponse(
            text="Usage: /watch list|add|remove|clear|scan",
            evidence=[],
            mode=ResponseMode.FAST,
        )

    # -- Holdings commands ---------------------------------------------- #
    # Cockpit-local portfolio state (SYSTEM_CONTRACT §1.2). The cockpit is
    # the single owner of holdings rows; financial truth is sourced from the
    # backend. These handlers MUST NOT auto-mutate the watchlist or the
    # canonical financial stores. Persistence lives in P1
    # (StateStore.add_holding / list_holdings / archive_holding /
    # remove_holding).

    @staticmethod
    def _looks_like_holding_id(arg: str) -> bool:
        """Loose UUID-shape check (8-4-4-4-12). Tickers never collide."""
        if len(arg) != 36:
            return False
        return arg[8] == "-" and arg[13] == "-" and arg[18] == "-" and arg[23] == "-"

    @staticmethod
    def _holding_float(value: Any) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _format_holding_qty(value: float | None) -> str:
        if value is None:
            return "—"
        if abs(value - round(value)) < 1e-9:
            return f"{int(round(value)):,}"
        return f"{value:,.4f}".rstrip("0").rstrip(".")

    @staticmethod
    def _format_holding_money(
        value: float | None,
        currency: str | None,
        *,
        signed: bool = False,
    ) -> str:
        if value is None:
            return "—"
        ccy = str(currency or "").strip().upper()
        sign = "+" if signed and value > 0 else ""
        prefix = f"{ccy} " if ccy else ""
        return f"{sign}{prefix}{value:,.2f}"

    def _fetch_holdings_for_chat(self, *, ticker: str | None = None) -> list[dict[str, Any]]:
        backend_client = getattr(self.tool_router, "backend_api_client", None)
        list_cockpit_holdings = (
            getattr(backend_client, "list_cockpit_holdings", None)
            if backend_client is not None
            else None
        )
        if callable(list_cockpit_holdings):
            try:
                payload = list_cockpit_holdings(
                    ticker=ticker,
                    include_archived=False,
                    timeout=15.0,
                )
            except Exception as exc:
                logger.debug("Holdings backend read failed, using local store: %s", exc)
            else:
                if isinstance(payload, dict):
                    items = payload.get("items")
                    if isinstance(items, list):
                        normalized = [row for row in items if isinstance(row, dict)]
                        if normalized:
                            return normalized
        if ticker:
            return self._state_store.list_holdings(ticker=ticker)
        return self._state_store.list_holdings()

    def _render_holdings_overview(self, items: list[dict[str, Any]]) -> str:
        rows: list[dict[str, Any]] = []
        market_totals: dict[str, float] = {}
        cost_totals: dict[str, float] = {}
        pnl_totals: dict[str, float] = {}
        warnings = 0
        latest_price_as_of: str | None = None

        for raw in items:
            row = dict(raw)
            ticker = str(row.get("ticker") or "").strip().upper() or "?"
            account = str(row.get("account_label") or "").strip()
            label = f"{ticker}/{account}" if account else ticker
            quantity = self._holding_float(row.get("quantity"))
            avg_cost = self._holding_float(row.get("avg_cost"))
            current_price = self._holding_float(row.get("current_price"))
            market_value = self._holding_float(row.get("market_value"))
            unrealized_pnl = self._holding_float(row.get("unrealized_pnl"))
            cost_currency = str(row.get("cost_currency") or "").strip().upper() or None
            price_currency = str(row.get("price_currency") or "").strip().upper() or None
            warning = str(row.get("valuation_warning") or "").strip()
            if warning:
                warnings += 1
            price_as_of = str(row.get("price_as_of") or "").strip()
            if price_as_of and (
                latest_price_as_of is None or price_as_of > latest_price_as_of
            ):
                latest_price_as_of = price_as_of

            implied_cost_value = None
            if quantity is not None and avg_cost is not None:
                implied_cost_value = quantity * avg_cost
                if cost_currency:
                    cost_totals[cost_currency] = (
                        cost_totals.get(cost_currency, 0.0) + implied_cost_value
                    )
            if market_value is not None and price_currency:
                market_totals[price_currency] = (
                    market_totals.get(price_currency, 0.0) + market_value
                )
            if unrealized_pnl is not None and price_currency:
                pnl_totals[price_currency] = (
                    pnl_totals.get(price_currency, 0.0) + unrealized_pnl
                )

            rows.append(
                {
                    "label": label[:18],
                    "quantity": quantity,
                    "avg_cost": avg_cost,
                    "current_price": current_price,
                    "market_value": market_value,
                    "unrealized_pnl": unrealized_pnl,
                    "cost_currency": cost_currency,
                    "price_currency": price_currency,
                    "holding_id": str(row.get("holding_id") or ""),
                    "sort_value": market_value
                    if market_value is not None
                    else implied_cost_value or -1.0,
                }
            )

        priced_positions = sum(
            1 for row in rows if row["market_value"] is not None and row["price_currency"]
        )
        rows.sort(key=lambda row: (row["sort_value"], row["label"]), reverse=True)

        lines: list[str] = [f"Portfolio overview ({len(items)} holdings)"]
        lines.append(
            f"Live pricing coverage: {priced_positions}/{len(items)} positions."
        )
        if latest_price_as_of:
            lines.append(f"Latest price timestamp: {latest_price_as_of}")
        if warnings:
            lines.append(
                f"Valuation notes: {warnings} position(s) have currency/price gaps."
            )

        if market_totals:
            lines.append("Market value:")
            for ccy in sorted(market_totals):
                lines.append(
                    f"  {self._format_holding_money(market_totals[ccy], ccy)}"
                )
        if cost_totals:
            lines.append("Cost basis:")
            for ccy in sorted(cost_totals):
                lines.append(f"  {self._format_holding_money(cost_totals[ccy], ccy)}")
        if pnl_totals:
            lines.append("Unrealized P/L:")
            for ccy in sorted(pnl_totals):
                lines.append(
                    f"  {self._format_holding_money(pnl_totals[ccy], ccy, signed=True)}"
                )

        lines.append("")
        header = (
            f"{'Code':<18} {'Qty':>12} {'Cost':>16} {'Price':>16} "
            f"{'Value':>16} {'P/L':>16} {'ID':<8}"
        )
        lines.append(header)
        lines.append("-" * len(header))
        for row in rows:
            holding_id = row["holding_id"][:8] or "—"
            lines.append(
                f"{row['label']:<18} "
                f"{self._format_holding_qty(row['quantity']):>12} "
                f"{self._format_holding_money(row['avg_cost'], row['cost_currency']):>16} "
                f"{self._format_holding_money(row['current_price'], row['price_currency']):>16} "
                f"{self._format_holding_money(row['market_value'], row['price_currency']):>16} "
                f"{self._format_holding_money(row['unrealized_pnl'], row['price_currency'], signed=True):>16} "
                f"{holding_id:<8}"
            )
        lines.append("")
        lines.append("Tip: use `/holdings remove <ID>` or `/holdings archive <ID>`.")
        return "\n".join(lines)

    def _slash_holdings(self, sub: str, rest: str) -> ChatResponse | None:
        if self._state_store is None:
            return ChatResponse(
                text="Holdings not available (no state store).",
                evidence=[],
                mode=ResponseMode.FAST,
            )

        if sub in ("", "list"):
            ticker = rest.strip().upper() or None
            items = self._fetch_holdings_for_chat(ticker=ticker)
            if not items:
                return ChatResponse(
                    text="No holdings recorded.",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            return ChatResponse(
                text=self._render_holdings_overview(items),
                evidence=[{"type": "holdings", "details": items}],
                mode=ResponseMode.FAST,
            )

        if sub == "add":
            tokens = rest.split()
            if not tokens:
                return ChatResponse(
                    text="Usage: /holdings add <TICKER> [QTY [AVG_COST]]",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            ticker = tokens[0].upper()
            quantity: float | None = None
            avg_cost: float | None = None
            if len(tokens) >= 2:
                try:
                    quantity = float(tokens[1])
                except ValueError:
                    return ChatResponse(
                        text=f"Invalid quantity '{tokens[1]}'. Use a number.",
                        evidence=[],
                        mode=ResponseMode.FAST,
                    )
            if len(tokens) >= 3:
                try:
                    avg_cost = float(tokens[2])
                except ValueError:
                    return ChatResponse(
                        text=f"Invalid avg cost '{tokens[2]}'. Use a number.",
                        evidence=[],
                        mode=ResponseMode.FAST,
                    )
            holding_id = self._state_store.add_holding(
                ticker, quantity=quantity, avg_cost=avg_cost
            )
            return ChatResponse(
                text=f"Added {ticker} to holdings (id {holding_id}).",
                evidence=[],
                mode=ResponseMode.FAST,
            )

        if sub in ("remove", "archive"):
            arg = rest.strip()
            if not arg:
                return ChatResponse(
                    text=f"Usage: /holdings {sub} <TICKER|HOLDING_ID>",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            verb_past = "Removed" if sub == "remove" else "Archived"
            mutate = (
                self._state_store.remove_holding
                if sub == "remove"
                else self._state_store.archive_holding
            )
            if self._looks_like_holding_id(arg):
                ok = mutate(arg)
                msg = (
                    f"{verb_past} holding {arg}."
                    if ok
                    else f"Holding {arg} not found."
                )
                return ChatResponse(text=msg, evidence=[], mode=ResponseMode.FAST)
            ticker = arg.upper()
            items = self._state_store.list_holdings(ticker=ticker)
            if not items:
                return ChatResponse(
                    text=f"No active holding for {ticker}.",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            if len(items) > 1:
                lines = [f"Multiple holdings for {ticker}. Specify holding_id:"]
                for h in items:
                    account = h.get("account_label") or "—"
                    qty = h.get("quantity")
                    qty_str = f" qty={qty}" if qty is not None else ""
                    lines.append(
                        f"  /holdings {sub} {h['holding_id']}  [{account}]{qty_str}"
                    )
                return ChatResponse(
                    text="\n".join(lines), evidence=[], mode=ResponseMode.FAST
                )
            holding_id = items[0]["holding_id"]
            mutate(holding_id)
            return ChatResponse(
                text=f"{verb_past} {ticker} from holdings.",
                evidence=[],
                mode=ResponseMode.FAST,
            )

        return ChatResponse(
            text="Usage: /holdings list|add|remove|archive [args]",
            evidence=[],
            mode=ResponseMode.FAST,
        )

    # -- Market-update commands ----------------------------------------- #
    # Cockpit-local snapshots of orchestrator output (P2 tables). The
    # orchestrator (P5) gathers per-ticker snapshots via yfinance, scores
    # them with `compute_significance`, persists a report, and queues
    # follow-ups for high-significance tickers.

    _MARKET_UPDATE_RUN_TYPES = ("noon", "final", "manual")

    def _build_market_update_orchestrator(self):
        """Construct an orchestrator using yfinance as the snapshot source.

        Lazy: yfinance is only imported on first use. Tests can override
        this method to inject a stub orchestrator.
        """
        from cockpit.core.market_update_orchestrator import (  # noqa: PLC0415
            MarketUpdateOrchestrator,
        )
        from cockpit.core.yfinance_snapshot_provider import (  # noqa: PLC0415
            YFinanceSnapshotProvider,
        )

        provider = YFinanceSnapshotProvider()
        return MarketUpdateOrchestrator(
            state_store=self._state_store,
            snapshot_provider=provider,
            market_universe_loader=self._load_default_market_update_universe,
        )

    @staticmethod
    def _load_default_market_update_universe() -> list[str]:
        """Load cockpit's default market-wide ticker universe.

        Used as the /market-update final fallback when no explicit tickers
        are supplied and the watchlist is empty.
        """
        local_path = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "raw"
            / "asx_ticker_universe.txt"
        )
        workspace_root = str(os.getenv("COCKPIT_WORKSPACE_ROOT") or "").strip()
        candidates = [
            local_path,
            Path("/data/raw/asx_ticker_universe.txt"),  # Docker compose mount
        ]
        if workspace_root:
            candidates.append(
                Path(workspace_root)
                / "financial-engine_v2"
                / "data"
                / "raw"
                / "asx_ticker_universe.txt"
            )

        lines: list[str] = []
        loaded_path: Path | None = None
        last_error: Exception | None = None
        for path in candidates:
            try:
                if not path.exists():
                    continue
                lines = path.read_text(encoding="utf-8").splitlines()
                loaded_path = path
                break
            except OSError as exc:
                last_error = exc
                continue
        if loaded_path is None:
            if last_error is not None:
                logger.warning(
                    "market-update universe file unavailable (%s): %s",
                    candidates,
                    last_error,
                )
            else:
                logger.warning(
                    "market-update universe file not found; checked: %s",
                    [str(p) for p in candidates],
                )
            return []

        tickers: list[str] = []
        seen: set[str] = set()
        for raw in lines:
            # Allow inline comments and comma-separated rows.
            cleaned = raw.split("#", 1)[0].replace(",", " ").strip()
            if not cleaned:
                continue
            for token in cleaned.split():
                ticker = token.strip().upper()
                if not ticker or ticker in seen:
                    continue
                seen.add(ticker)
                tickers.append(ticker)
        return tickers

    @staticmethod
    def _render_market_update_report(report: dict[str, Any]) -> str:
        summary = report.get("summary") or {}
        headline = summary.get("headline") or "(no headline)"
        lines = [
            f"[{report['run_type']}] {report['report_date']}"
            f"  status={report['status']}",
            f"  {headline}",
        ]
        ticker_rows = summary.get("tickers") or []
        if isinstance(ticker_rows, list):
            movers = [row for row in ticker_rows if isinstance(row, dict)]
        else:
            movers = []
        def _significance_value(row: dict[str, Any]) -> float:
            try:
                return float(row.get("significance") or 0.0)
            except (TypeError, ValueError):
                return 0.0

        movers.sort(key=_significance_value, reverse=True)
        if movers:
            lines.append("  Ranked movers:")
            for row in movers[:5]:
                ticker = str(row.get("ticker") or "?").strip().upper() or "?"
                pct_change = row.get("pct_change")
                try:
                    pct_text = f"{float(pct_change):+.2f}%"
                except (TypeError, ValueError):
                    pct_text = "pct n/a"
                significance = row.get("significance")
                try:
                    sig_text = f"sig {float(significance):.2f}"
                except (TypeError, ValueError):
                    sig_text = "sig n/a"
                reasons = row.get("reasons")
                reason_items = [
                    str(item).strip()
                    for item in reasons
                    if str(item).strip()
                ] if isinstance(reasons, list) else []
                reason_text = f" — {', '.join(reason_items[:3])}" if reason_items else ""
                lines.append(f"    {ticker}: {pct_text} ({sig_text}){reason_text}")
        return "\n".join(lines)

    def _format_market_update_report(
        self, report: dict[str, Any] | None, *, header: str
    ) -> ChatResponse:
        routing_metadata = {
            "source": "cockpit",
            "model": "deterministic:market-update",
            "cost_usd": 0.0,
            "routing_reason": "slash:market-update",
        }
        if report is None:
            return ChatResponse(
                text="No market-update reports found.",
                evidence=[],
                mode=ResponseMode.FAST,
                routing_metadata=routing_metadata,
            )
        text = f"{header}:\n{self._render_market_update_report(report)}"
        return ChatResponse(
            text=text,
            evidence=[{"type": "market_update_report", "details": report}],
            mode=ResponseMode.FAST,
            routing_metadata=routing_metadata,
        )

    _MARKET_UPDATE_FOLLOWUP_RE = re.compile(
        r"^\s*(?:tell\s+me\s+(?:more\s+)?about\s+it|explain\s+it|more\s+detail(?:s)?)\s*[\\?!.]*\s*$",
        re.IGNORECASE,
    )

    def _recent_context_mentions_market_update(self) -> bool:
        if self._state_store is None:
            return False
        try:
            history_msgs = self._state_store.get_chat_messages(
                self._thread_id,
                limit=8,
            )
        except Exception:
            return False
        for item in reversed(history_msgs or []):
            if str(item.get("role") or "").lower() != "assistant":
                continue
            content = str(item.get("content") or "").lower()
            if not content:
                continue
            if (
                "market-update" in content
                or "market update" in content
                or ("asx" in content and "market" in content)
            ):
                return True
        return False

    def _try_market_update_followup(self, message: str) -> ChatResponse | None:
        if self._state_store is None:
            return None
        if not self._MARKET_UPDATE_FOLLOWUP_RE.fullmatch(str(message or "").strip()):
            return None
        if not self._recent_context_mentions_market_update():
            return None
        report = self._state_store.get_latest_market_update_report(None)
        return self._format_market_update_report(
            report,
            header="Latest market update detail",
        )

    @staticmethod
    def _format_market_update_errors(errors: tuple[str, ...]) -> str | None:
        if not errors:
            return None

        snapshot_gaps: list[str] = []
        other_errors: list[str] = []
        for item in errors:
            ticker, sep, reason = str(item).partition(":")
            if sep and reason.strip() == "no snapshot available":
                snapshot_gaps.append(ticker.strip().upper())
            else:
                other_errors.append(str(item))

        parts: list[str] = []
        if snapshot_gaps:
            shown = ", ".join(snapshot_gaps[:12])
            suffix = "..." if len(snapshot_gaps) > 12 else ""
            parts.append(
                f"Snapshot gaps ({len(snapshot_gaps)} ticker(s)): {shown}{suffix}"
            )
        if other_errors:
            shown = "; ".join(other_errors[:3])
            suffix = "..." if len(other_errors) > 3 else ""
            parts.append(f"Run errors ({len(other_errors)}): {shown}{suffix}")
        return "\n".join(parts) if parts else None

    def _slash_market_update(self, sub: str, rest: str) -> ChatResponse | None:
        if self._state_store is None:
            return ChatResponse(
                text="Market-update reports not available (no state store).",
                evidence=[],
                mode=ResponseMode.FAST,
            )

        if sub in ("", "latest"):
            report = self._state_store.get_latest_market_update_report(None)
            return self._format_market_update_report(
                report, header="Latest market update"
            )

        if sub == "list":
            run_type = rest.strip().lower() or None
            kwargs: dict[str, Any] = {}
            if run_type:
                kwargs["run_type"] = run_type
            reports = self._state_store.list_market_update_reports(**kwargs)
            if not reports:
                scope = f" ({run_type})" if run_type else ""
                return ChatResponse(
                    text=f"No market-update reports found{scope}.",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            lines = [f"Market-update reports ({len(reports)}):"]
            for r in reports:
                summary = r.get("summary") or {}
                headline = summary.get("headline") or r.get("status", "?")
                lines.append(
                    f"  [{r['run_type']}] {r['report_date']}  {headline}"
                    f"  ({r['report_id']})"
                )
            return ChatResponse(
                text="\n".join(lines),
                evidence=[{"type": "market_update_reports", "details": reports}],
                mode=ResponseMode.FAST,
            )

        if sub == "show":
            run_type = rest.strip().lower() or None
            report = self._state_store.get_latest_market_update_report(run_type)
            scope = run_type or "market"
            return self._format_market_update_report(
                report, header=f"Latest {scope} update"
            )

        if sub in self._MARKET_UPDATE_RUN_TYPES:
            routing_metadata = {
                "source": "cockpit",
                "model": "deterministic:market-update",
                "cost_usd": 0.0,
                "routing_reason": "slash:market-update",
            }
            try:
                orchestrator = self._build_market_update_orchestrator()
            except Exception as exc:  # noqa: BLE001 — surface boot failure
                logger.exception("market-update orchestrator init failed")
                return ChatResponse(
                    text=f"Market-update orchestrator unavailable: {exc}",
                    evidence=[],
                    mode=ResponseMode.FAST,
                    routing_metadata=routing_metadata,
                )

            tickers_arg = [t.strip() for t in rest.split() if t.strip()] or None
            try:
                result = orchestrator.run(sub, tickers=tickers_arg)
            except Exception as exc:  # noqa: BLE001 — surface run failure
                logger.exception("market-update run failed")
                return ChatResponse(
                    text=f"Market-update run failed: {exc}",
                    evidence=[],
                    mode=ResponseMode.FAST,
                    routing_metadata=routing_metadata,
                )

            parts = [
                f"Market-update '{sub}' run: status={result.status}, "
                f"tickers={result.gathered_tickers}, "
                f"followups={result.queued_followups}.",
            ]
            formatted_errors = self._format_market_update_errors(result.errors)
            if formatted_errors:
                parts.append(formatted_errors)

            report = None
            if result.report_id is not None:
                report = self._state_store.get_latest_market_update_report(sub)
            if report is not None:
                parts.append("")
                parts.append(self._render_market_update_report(report))
            else:
                parts.append(f"No '{sub}' report persisted (status={result.status}).")

            evidence: list[dict[str, Any]] = []
            if report is not None:
                evidence.append({"type": "market_update_report", "details": report})
            return ChatResponse(
                text="\n".join(parts),
                evidence=evidence,
                mode=ResponseMode.FAST,
                routing_metadata=routing_metadata,
            )

        return ChatResponse(
            text="Usage: /market-update [list|show|latest|noon|final|manual]",
            evidence=[],
            mode=ResponseMode.FAST,
        )

    # -- Strategy commands ---------------------------------------------- #

    def _slash_strategy(self, sub: str, rest: str) -> ChatResponse | None:
        if self._strategy_service is None:
            return ChatResponse(
                text="Strategy service not available.",
                evidence=[],
                mode=ResponseMode.FAST,
            )

        if sub == "list":
            ticker = rest.strip().upper() or None
            global_criteria = self._strategy_service.get_global(limit=20)
            ticker_criteria = (
                self._strategy_service.get_ticker(ticker) if ticker else []
            )
            lines: list[str] = []
            if global_criteria:
                lines.append("Global criteria:")
                for c in global_criteria:
                    lines.append(
                        f"  [{c['id']}] {c['criterion']} (priority={c['priority']})"
                    )
            if ticker_criteria:
                lines.append(f"\n{ticker} criteria:")
                for c in ticker_criteria:
                    dec = f" -> {c['decision']}" if c.get("decision") else ""
                    lines.append(f"  [{c['id']}] {c['criterion']}{dec}")
            if not lines:
                lines.append("No strategy criteria defined.")
            return ChatResponse(
                text="\n".join(lines), evidence=[], mode=ResponseMode.FAST
            )

        if sub == "add":
            if not rest:
                return ChatResponse(
                    text="Usage: /strategy add [TICKER] <criterion>",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            tokens = rest.split(None, 1)
            first = tokens[0].upper() if tokens else ""
            # If the first token looks like a ticker (2-5 uppercase alpha), treat it as one.
            if (
                len(first) >= 2
                and len(first) <= 5
                and first.isalpha()
                and len(tokens) > 1
            ):
                ticker = first
                criterion = tokens[1]
                row = self._strategy_service.add_ticker(ticker, criterion)
                return ChatResponse(
                    text=f"Added criterion for {ticker}: {criterion} (id={row['id']})",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            criterion = rest
            row = self._strategy_service.add_global(criterion)
            return ChatResponse(
                text=f"Added global criterion: {criterion} (id={row['id']})",
                evidence=[],
                mode=ResponseMode.FAST,
            )

        if sub == "decide":
            tokens = rest.split(None, 1)
            if len(tokens) < 2:
                return ChatResponse(
                    text="Usage: /strategy decide <TICKER> <buy|watchlist|avoid>",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            ticker = tokens[0].upper()
            decision = tokens[1].strip().lower()
            if decision not in ("buy", "watchlist", "avoid"):
                return ChatResponse(
                    text=f"Invalid decision '{decision}'. Use: buy, watchlist, avoid",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            row = self._strategy_service.record_decision(
                ticker, decision, f"Manual decision via /strategy decide"
            )
            return ChatResponse(
                text=f"Recorded decision for {ticker}: {decision}",
                evidence=[],
                mode=ResponseMode.FAST,
            )

        if sub == "delete":
            if not rest:
                return ChatResponse(
                    text="Usage: /strategy delete <id>",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            try:
                row_id = int(rest.strip())
            except ValueError:
                return ChatResponse(
                    text="Invalid id — must be numeric.",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            deleted = self._strategy_service.delete(row_id)
            msg = (
                f"Deleted criterion {row_id}."
                if deleted
                else f"Criterion {row_id} not found."
            )
            return ChatResponse(text=msg, evidence=[], mode=ResponseMode.FAST)

        return ChatResponse(
            text="Usage: /strategy list|add|decide|delete",
            evidence=[],
            mode=ResponseMode.FAST,
        )

    # -- Action commands ------------------------------------------------ #

    def _slash_run(self, sub: str, rest: str) -> ChatResponse | None:
        action_id = sub
        if not action_id:
            return ChatResponse(
                text="Usage: /run <action_id> [args]",
                evidence=[],
                mode=ResponseMode.FAST,
            )
        if not self.action_registry:
            return ChatResponse(
                text="Action registry not available.",
                evidence=[],
                mode=ResponseMode.FAST,
            )
        # Parse key=value args from rest.
        args: dict[str, Any] = {}
        for token in rest.split():
            if "=" in token:
                k, v = token.split("=", 1)
                args[k] = v
            else:
                args[token] = True
        try:
            preview = self.action_registry.preview(action_id, args)
        except (ValueError, KeyError) as exc:
            return ChatResponse(
                text=f"Action '{action_id}' error: {exc}",
                evidence=[],
                mode=ResponseMode.FAST,
            )
        return ChatResponse(
            text=f"Action ready: {action_id}\nCommand: {' '.join(preview.command)}\nUse /confirm to execute.",
            evidence=[],
            action_preview={
                "action_id": action_id,
                "args": args,
                "command": preview.command,
                "impact": preview.estimated_impact,
                "timeout_seconds": preview.timeout_seconds,
            },
            mode=ResponseMode.ACTION,
        )

    def _slash_confirm(self, _sub: str, _rest: str) -> ChatResponse | None:
        # The UI layer handles confirm by re-sending the action_preview to the execute endpoint.
        # This command is a no-op signal — the ChatController does not store pending actions.
        return ChatResponse(
            text="No pending action to confirm. Actions are confirmed via the UI action panel.",
            evidence=[],
            mode=ResponseMode.FAST,
        )

    def _slash_cancel(self, _sub: str, _rest: str) -> ChatResponse | None:
        return ChatResponse(
            text="Cancelled. No pending action.",
            evidence=[],
            mode=ResponseMode.FAST,
        )

    # -- File commands -------------------------------------------------- #

    def _slash_read(self, sub: str, rest: str) -> ChatResponse | None:
        path = sub
        if not path:
            return ChatResponse(
                text="Usage: /read <path> [max_chars=N]",
                evidence=[],
                mode=ResponseMode.FAST,
            )
        max_chars = 4000
        for token in rest.split():
            if token.startswith("max_chars="):
                try:
                    max_chars = int(token.split("=", 1)[1])
                except ValueError:
                    pass
        try:
            path_obj = Path(path).expanduser()
            if not path_obj.is_absolute():
                path_obj = self.repo_root / path_obj
            content = path_obj.read_text(errors="replace")
            if len(content) > max_chars:
                content = (
                    content[:max_chars] + f"\n... (truncated at {max_chars} chars)"
                )
            return ChatResponse(
                text=f"```\n{content}\n```",
                evidence=[
                    {
                        "type": "file_read",
                        "details": {"path": path, "chars": len(content)},
                    }
                ],
                mode=ResponseMode.FAST,
            )
        except FileNotFoundError:
            return ChatResponse(
                text=f"File not found: {path}", evidence=[], mode=ResponseMode.FAST
            )
        except PermissionError:
            return ChatResponse(
                text=f"Permission denied: {path}", evidence=[], mode=ResponseMode.FAST
            )
        except Exception as exc:
            return ChatResponse(
                text=f"Error reading {path}: {exc}", evidence=[], mode=ResponseMode.FAST
            )

    # -- Preference commands -------------------------------------------- #

    def _slash_prefer(self, sub: str, rest: str) -> ChatResponse | None:
        raw = f"{sub} {rest}".strip() if rest else sub
        if "=" not in raw:
            return ChatResponse(
                text="Usage: /prefer <key>=<value>", evidence=[], mode=ResponseMode.FAST
            )
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            return ChatResponse(
                text="Usage: /prefer <key>=<value>", evidence=[], mode=ResponseMode.FAST
            )
        if self._state_store is not None:
            self._state_store.set_preference(key, value)
        return ChatResponse(
            text=f"Preference set: {key}={value}", evidence=[], mode=ResponseMode.FAST
        )

    # -- Review commands ------------------------------------------------ #

    def _slash_review(self, sub: str, rest: str) -> ChatResponse | None:
        backend_client = getattr(self.tool_router, "backend_api_client", None)
        if backend_client is not None:
            if sub == "list" or not sub:
                try:
                    resp = backend_client.get_pending_transcripts()
                    pending = resp.get("pending", []) if isinstance(resp, dict) else []
                except Exception as exc:
                    return ChatResponse(
                        text=f"Failed to list pending transcripts: {exc}",
                        evidence=[],
                        mode=ResponseMode.FAST,
                    )
                if not pending:
                    return ChatResponse(
                        text="No pending transcripts to review.",
                        evidence=[],
                        mode=ResponseMode.FAST,
                    )
                lines = [f"Pending transcript review ({len(pending)} items):"]
                for index, item in enumerate(pending, start=1):
                    if not isinstance(item, dict):
                        continue
                    sid = item.get("source_id", "?")
                    stype = item.get("source_type", "?")
                    title = str(item.get("title") or item.get("source_name") or "?")[:60]
                    chunks = item.get("chunk_count", 0)
                    staged = str(item.get("staged_at") or "")[:10]
                    meta_bits: list[str] = [f"staged {staged}", f"{chunks} chunks"]
                    weight = item.get("credibility_weight")
                    if isinstance(weight, int | float):
                        meta_bits.append(f"weight {float(weight):.2f}")
                    review_takeaways = item.get("review_takeaways")
                    if isinstance(review_takeaways, list) and review_takeaways:
                        meta_bits.append(f"{len(review_takeaways)} edited takeaways")
                    lines.append(
                        f"  [{index}] {sid} | {stype} | {title} | {' | '.join(meta_bits)}"
                    )
                lines.append(
                    "Use: /review takeaways <source_id>, /review weight <source_id> <0-1>, "
                    "/review edit <source_id> <n> <text>, /review approve <source_id>, "
                    "or /review reject <source_id>"
                )
                return ChatResponse(
                    text="\n".join(lines),
                    evidence=[{"type": "pending_transcripts", "details": pending}],
                    mode=ResponseMode.FAST,
                )

            if sub == "approve":
                source_id = rest.strip()
                if not source_id:
                    return ChatResponse(
                        text="Usage: /review approve <source_id>",
                        evidence=[],
                        mode=ResponseMode.FAST,
                    )
                try:
                    result = backend_client.approve_transcript(source_id)
                except Exception as exc:
                    return ChatResponse(
                        text=f"Approve failed: {exc}",
                        evidence=[],
                        mode=ResponseMode.FAST,
                    )
                indexed = result.get("points_upserted", 0) if isinstance(result, dict) else 0
                return ChatResponse(
                    text=f"Approved and indexed {indexed} chunks for {source_id}.",
                    evidence=[
                        {
                            "type": "transcript_review",
                            "details": result if isinstance(result, dict) else {},
                        }
                    ],
                    mode=ResponseMode.FAST,
                )

            if sub == "reject":
                source_id = rest.strip()
                if not source_id:
                    return ChatResponse(
                        text="Usage: /review reject <source_id>",
                        evidence=[],
                        mode=ResponseMode.FAST,
                    )
                try:
                    backend_client.reject_transcript(source_id)
                except Exception as exc:
                    return ChatResponse(
                        text=f"Reject failed: {exc}",
                        evidence=[],
                        mode=ResponseMode.FAST,
                    )
                return ChatResponse(
                    text=f"Rejected and purged staged chunks for {source_id}.",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )

            if sub == "takeaways":
                source_id = rest.strip()
                if not source_id:
                    return ChatResponse(
                        text="Usage: /review takeaways <source_id>",
                        evidence=[],
                        mode=ResponseMode.FAST,
                    )
                try:
                    result = backend_client.get_commentary_takeaways(source_id, limit=12)
                except Exception as exc:
                    return ChatResponse(
                        text=f"Takeaway lookup failed: {exc}",
                        evidence=[],
                        mode=ResponseMode.FAST,
                    )
                takeaways = result.get("takeaways", []) if isinstance(result, dict) else []
                if not takeaways:
                    return ChatResponse(
                        text=f"No takeaways available for {source_id}.",
                        evidence=[
                            {
                                "type": "transcript_review_takeaways",
                                "details": result if isinstance(result, dict) else {},
                            }
                        ],
                        mode=ResponseMode.FAST,
                    )
                lines = [f"Review takeaways for {source_id}:"]
                weight = result.get("credibility_weight") if isinstance(result, dict) else None
                if isinstance(weight, int | float):
                    lines.append(f"Current weight: {float(weight):.2f}")
                for index, item in enumerate(takeaways, start=1):
                    text = (
                        str(item.get("text") or "").strip()
                        if isinstance(item, dict)
                        else str(item or "").strip()
                    )
                    if text:
                        lines.append(f"{index}. {text}")
                lines.append(
                    f"Edit with /review edit {source_id} <n> <text>; "
                    f"adjust weight with /review weight {source_id} <0-1>."
                )
                return ChatResponse(
                    text="\n".join(lines),
                    evidence=[
                        {
                            "type": "transcript_review_takeaways",
                            "details": result if isinstance(result, dict) else {},
                        }
                    ],
                    mode=ResponseMode.FAST,
                )

            if sub == "weight":
                parts = rest.split(None, 1)
                if len(parts) != 2:
                    return ChatResponse(
                        text="Usage: /review weight <source_id> <0-1>",
                        evidence=[],
                        mode=ResponseMode.FAST,
                    )
                source_id, raw_weight = parts
                try:
                    weight = float(raw_weight)
                except ValueError:
                    return ChatResponse(
                        text="Usage: /review weight <source_id> <0-1>",
                        evidence=[],
                        mode=ResponseMode.FAST,
                    )
                if not 0.0 <= weight <= 1.0:
                    return ChatResponse(
                        text="Weight must be between 0 and 1.",
                        evidence=[],
                        mode=ResponseMode.FAST,
                    )
                try:
                    result = backend_client.update_transcript_review(
                        source_id,
                        credibility_weight=weight,
                    )
                except Exception as exc:
                    return ChatResponse(
                        text=f"Weight update failed: {exc}",
                        evidence=[],
                        mode=ResponseMode.FAST,
                    )
                return ChatResponse(
                    text=f"Updated {source_id} review weight to {weight:.2f}.",
                    evidence=[
                        {
                            "type": "transcript_review_update",
                            "details": result if isinstance(result, dict) else {},
                        }
                    ],
                    mode=ResponseMode.FAST,
                )

            if sub == "edit":
                parts = rest.split(None, 2)
                if len(parts) != 3:
                    return ChatResponse(
                        text="Usage: /review edit <source_id> <n> <text>",
                        evidence=[],
                        mode=ResponseMode.FAST,
                    )
                source_id, raw_index, replacement = parts
                try:
                    takeaway_index = int(raw_index)
                except ValueError:
                    return ChatResponse(
                        text="Usage: /review edit <source_id> <n> <text>",
                        evidence=[],
                        mode=ResponseMode.FAST,
                    )
                replacement = replacement.strip()
                if takeaway_index < 1 or not replacement:
                    return ChatResponse(
                        text="Usage: /review edit <source_id> <n> <text>",
                        evidence=[],
                        mode=ResponseMode.FAST,
                    )
                try:
                    current = backend_client.get_commentary_takeaways(source_id, limit=12)
                except Exception as exc:
                    return ChatResponse(
                        text=f"Takeaway lookup failed: {exc}",
                        evidence=[],
                        mode=ResponseMode.FAST,
                    )
                current_takeaways = (
                    current.get("takeaways", []) if isinstance(current, dict) else []
                )
                texts: list[str] = []
                for item in current_takeaways:
                    text = (
                        str(item.get("text") or "").strip()
                        if isinstance(item, dict)
                        else str(item or "").strip()
                    )
                    if text:
                        texts.append(text)
                if takeaway_index > len(texts):
                    return ChatResponse(
                        text=(
                            f"Takeaway {takeaway_index} is not available for "
                            f"{source_id}; use /review takeaways {source_id} first."
                        ),
                        evidence=[],
                        mode=ResponseMode.FAST,
                    )
                texts[takeaway_index - 1] = replacement
                try:
                    result = backend_client.update_transcript_review(
                        source_id,
                        takeaways=texts,
                    )
                except Exception as exc:
                    return ChatResponse(
                        text=f"Takeaway edit failed: {exc}",
                        evidence=[],
                        mode=ResponseMode.FAST,
                    )
                return ChatResponse(
                    text=f"Updated takeaway {takeaway_index} for {source_id}.",
                    evidence=[
                        {
                            "type": "transcript_review_update",
                            "details": result if isinstance(result, dict) else {},
                        }
                    ],
                    mode=ResponseMode.FAST,
                )

            if sub == "approve-all":
                try:
                    resp = backend_client.get_pending_transcripts()
                    pending = resp.get("pending", []) if isinstance(resp, dict) else []
                except Exception as exc:
                    return ChatResponse(
                        text=f"Failed to list pending transcripts: {exc}",
                        evidence=[],
                        mode=ResponseMode.FAST,
                    )
                total = 0
                for item in pending:
                    if not isinstance(item, dict) or not item.get("source_id"):
                        continue
                    try:
                        result = backend_client.approve_transcript(item["source_id"])
                        if isinstance(result, dict):
                            total += int(result.get("points_upserted", 0) or 0)
                    except Exception:
                        continue
                return ChatResponse(
                    text=f"Approved {len(pending)} source(s), indexed {total} chunks.",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )

            if sub == "expired":
                try:
                    result = backend_client.purge_expired_transcripts()
                except Exception as exc:
                    return ChatResponse(
                        text=f"Purge failed: {exc}",
                        evidence=[],
                        mode=ResponseMode.FAST,
                    )
                purged = result.get("purged", []) if isinstance(result, dict) else []
                text = (
                    f"Purged {len(purged)} expired staged source(s)."
                    if purged
                    else "No expired items."
                )
                return ChatResponse(text=text, evidence=[], mode=ResponseMode.FAST)

            return ChatResponse(
                text=(
                    "Usage: /review list|takeaways|weight|edit|approve|reject|approve-all|"
                    "expired [source_id]"
                ),
                evidence=[],
                mode=ResponseMode.FAST,
            )

        if self._state_store is None:
            return ChatResponse(
                text="Review not available (no state store).",
                evidence=[],
                mode=ResponseMode.FAST,
            )

        if sub == "list":
            try:
                pending = self._state_store.list_pending_reviews()
            except AttributeError:
                return ChatResponse(
                    text="Review listing not implemented in state store.",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            if not pending:
                return ChatResponse(
                    text="No pending reviews.", evidence=[], mode=ResponseMode.FAST
                )
            lines = [
                f"  [{r.get('id', '?')}] {r.get('source_id', '?')}: {r.get('summary', '')[:80]}"
                for r in pending
            ]
            return ChatResponse(
                text=f"Pending reviews ({len(pending)}):\n" + "\n".join(lines),
                evidence=[{"type": "reviews", "details": pending}],
                mode=ResponseMode.FAST,
            )

        if sub == "approve":
            source_id = rest.strip()
            if not source_id:
                return ChatResponse(
                    text="Usage: /review approve <source_id>",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            try:
                self._state_store.approve_review(source_id)
            except AttributeError:
                return ChatResponse(
                    text="Review approval not implemented in state store.",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            return ChatResponse(
                text=f"Approved review: {source_id}",
                evidence=[],
                mode=ResponseMode.FAST,
            )

        if sub == "reject":
            source_id = rest.strip()
            if not source_id:
                return ChatResponse(
                    text="Usage: /review reject <source_id>",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            try:
                self._state_store.reject_review(source_id)
            except AttributeError:
                return ChatResponse(
                    text="Review rejection not implemented in state store.",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            return ChatResponse(
                text=f"Rejected review: {source_id}",
                evidence=[],
                mode=ResponseMode.FAST,
            )

        if sub == "approve-all":
            try:
                self._state_store.approve_all_reviews()
            except AttributeError:
                return ChatResponse(
                    text="Bulk approval not implemented in state store.",
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            return ChatResponse(
                text="All pending reviews approved.",
                evidence=[],
                mode=ResponseMode.FAST,
            )

        return ChatResponse(
            text="Usage: /review list|approve|reject|approve-all",
            evidence=[],
            mode=ResponseMode.FAST,
        )

    # -- Reconnect command ---------------------------------------------- #

    def _slash_reconnect(self, _sub: str, _rest: str) -> ChatResponse | None:
        lines: list[str] = ["Reconnection attempt:"]
        # Re-probe health on each known client.
        for name, client in [
            ("llama.cpp", self.ollama_client),
            ("backend", getattr(self.tool_router, "backend_api_client", None)),
        ]:
            if client is None:
                lines.append(f"  {name}: not configured")
                continue
            try:
                h = client.health(timeout=5.0)
                ok = h.get("ok", False) if isinstance(h, dict) else False
                lines.append(f"  {name}: {'ok' if ok else 'degraded'}")
            except Exception as exc:
                lines.append(f"  {name}: failed ({exc})")
        return ChatResponse(text="\n".join(lines), evidence=[], mode=ResponseMode.FAST)

    def _try_runtime_clock_shortcircuit(self, message: str) -> ChatResponse | None:
        text = str(message or "").strip()
        if not text:
            return None

        if not (
            self._DAY_QUERY_RE.fullmatch(text)
            or self._DATE_QUERY_RE.fullmatch(text)
            or self._TIME_QUERY_RE.fullmatch(text)
        ):
            return None

        now = datetime.now(self._ASX_TIMEZONE)
        weekday = now.strftime("%A")
        month = now.strftime("%B")
        tz_name = now.tzname() or "Australia/Sydney"

        if self._TIME_QUERY_RE.fullmatch(text):
            hour_12 = now.hour % 12 or 12
            answer = (
                f"It is {hour_12}:{now.minute:02d} {now.strftime('%p')} {tz_name} "
                f"on {weekday}, {month} {now.day}, {now.year}."
            )
        elif self._DATE_QUERY_RE.fullmatch(text):
            answer = f"Today's date is {month} {now.day}, {now.year} ({tz_name})."
        else:
            answer = f"Today is {weekday}, {month} {now.day}, {now.year} ({tz_name})."

        evidence = [
            {
                "type": "runtime_clock",
                "details": {
                    "title": "Cockpit runtime clock",
                    "source_id": "runtime_clock:australia-sydney",
                    "snippet": (
                        "Backend runtime clock in Australia/Sydney reported "
                        f"{now.isoformat()}."
                    ),
                    "published_at": now.isoformat(),
                },
            }
        ]
        return ChatResponse(text=answer, evidence=evidence, mode=ResponseMode.FAST)

    # -- Dispatch table ------------------------------------------------- #

    _SLASH_DISPATCH: dict[str, Any] = {
        "/web": _slash_web,
        "/rag": _slash_rag,
        "/dbdiag": _slash_dbdiag,
        "/sources": _slash_sources,
        "/health": _slash_health,
        "/prompt": _slash_prompt,
        "/access": _slash_access,
        "/filestats": _slash_filestats,
        "/memory": _slash_memory,
        "/watch": _slash_watch,
        "/holdings": _slash_holdings,
        "/market-update": _slash_market_update,
        "/strategy": _slash_strategy,
        "/run": _slash_run,
        "/confirm": _slash_confirm,
        "/cancel": _slash_cancel,
        "/read": _slash_read,
        "/prefer": _slash_prefer,
        "/review": _slash_review,
        "/reconnect": _slash_reconnect,
    }

    def _build_system_instruction(
        self, mode: str, ticker: str | None, local_payload: dict
    ) -> str:  # noqa: ARG002
        """Build the ASX-domain-specific system prompt for the LLM."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        instruction = (
            "You are Tenn, an ASX equity research assistant. You are conversational and helpful.\n"
            "\n"
            "Communication style:\n"
            "- Be natural and conversational. Respond like a knowledgeable colleague, not a report generator.\n"
            "- Answer the user's actual question directly before expanding with analysis.\n"
            "- Use plain language. Mention metrics only when they answer or support the question.\n"
            "- If the user asks a simple question, give a concise answer. Don't dump every metric you have.\n"
            "- If the user asks for deep analysis, then provide structured detail with evidence.\n"
            "\n"
            "Domain context:\n"
            "- Exchange: Australian Securities Exchange (ASX), Sydney AEST/AEDT timezone\n"
            "- Reporting: Semi-annual (interim + full-year), calendar year-end typical for resources,"
            " June 30 FY for most corporates\n"
            "- Key metrics you may reference: Revenue, EBIT, NPAT, operating CF, FCF, net debt\n"
            "- You have access to price data, financial statements, announcements, and news when provided\n"
            "\n"
            "Analyst standards:\n"
            "- Lead with the most material facts. Flag data limitations explicitly.\n"
            "- Distinguish between confirmed financial data and qualitative inference.\n"
            "- When financials_narrative is provided, use it as your starting point for trend commentary.\n"
            "- When valuation_multiples are provided, anchor your valuation assessment to them.\n"
            "- Never fabricate metrics not present in the evidence payload.\n"
            "- If data is absent, say so plainly rather than speculating.\n"
            "- Every factual claim must be grounded in the current response payload. Prior session context is background only.\n"
            "- If a statement cannot be verified from the current payload, say that you cannot verify it yet.\n"
            "- Only make claims that can be backed by user-visible sources in the current turn.\n"
            "- You are in direct-answer mode for this response: no tools can be called from here.\n"
            "- Do not emit tool-call JSON, planner arguments, or schema-shaped payloads. Return plain text only.\n"
            "\n"
            f"Current mode: {mode}\n"
            f"Current date (AEST): {date_str}\n"
        )

        prefs: dict[str, str] = {}
        if self._state_store is not None:
            try:
                prefs = self._state_store.get_preferences()
            except Exception:
                pass

        if prefs:
            pref_lines = [f"  {k}: {v}" for k, v in prefs.items()]
            instruction += "\nUser preferences:\n" + "\n".join(pref_lines) + "\n"

        if not local_payload.get("financials"):
            instruction += (
                "\nFinancial truth guard:\n"
                "- Canonical financial metrics are not available for this ticker in the current payload.\n"
                "- Do not state exact revenue, profit, EBIT, NPAT, margin, dividend, balance-sheet, or YoY figures unless they are quoted verbatim in the provided document excerpts.\n"
                "- Do not fabricate financial tables or comparative period values.\n"
                "- For generic company overviews, stay qualitative and say that detailed extracted financials are currently unavailable.\n"
            )

        # Cross-session episodic memory
        if self._state_store:
            try:
                recent_sessions = self._state_store.get_recent_session_summaries(
                    limit=2
                )
                if recent_sessions:
                    session_lines = []
                    for s in recent_sessions:
                        tickers_str = ", ".join(s.get("tickers", [])[:5])
                        session_lines.append(
                            f"  {s['date']}: {s['summary']}"
                            + (f" [tickers: {tickers_str}]" if tickers_str else "")
                        )
                    instruction += (
                        "\nPrior session context:\n" + "\n".join(session_lines) + "\n"
                    )
            except Exception:
                pass

        return instruction

    # ------------------------------------------------------------------ #
    # Agent loop dispatch (Phase 1 — structured mode)                      #
    # ------------------------------------------------------------------ #

    def _run_agent_loop(
        self,
        message: str,
        enable_web: bool,
        prior_ticker: str | None,
        on_chunk,
        on_status,
        analysis_mode: str | None,
        on_thinking=None,
        attached_bundle: _AttachedSourceBundle | None = None,
        request_standard_guidance: str = "",
        force_backend: str | None = None,
    ) -> ChatResponse:
        """Run the agentic tool-calling loop and convert the result to a ChatResponse."""
        parsed_force_backend, base_message = parse_backend_prefix(message)
        turn_force_backend = force_backend or parsed_force_backend

        # Reuse existing ticker detection logic
        ticker, explicit_ticker = self._resolve_ticker_context(
            base_message, prior_ticker=prior_ticker
        )
        if ticker:
            self.last_ticker = ticker

        conversation_history = self._recent_conversation_history()

        # Inject strategy criteria context into message if available
        strategy_block = ""
        if self._strategy_service and ticker:
            try:
                strategy_block = self._strategy_service.build_context_block(ticker)
            except Exception:
                pass  # strategy injection is best-effort

        # OpenViking: fetch semantically relevant prior turns for agent mode.
        # Context source hierarchy: OpenViking (semantic) > StateStore (recency) > Memory (research).
        ov_agent_block = ""
        prior_ov_turns = get_session_context(
            self._ov_session_id,
            base_message,
            semantic_limit=3,
        )
        if prior_ov_turns:
            lines = ["Prior session context:"]
            for t in prior_ov_turns:
                q = str(t.get("query") or "")[:150]
                a = str(t.get("answer") or "")[:250]
                tkr = str(t.get("ticker") or "").strip()
                note = f" [{tkr}]" if tkr else ""
                if q:
                    lines.append(f"  Q{note}: {q}")
                if a:
                    lines.append(f"  A: {a}")
            ov_agent_block = "\n".join(lines)

        # Inject research memory context into message if available
        augmented_message = base_message
        if ov_agent_block:
            augmented_message = ov_agent_block + "\n\n" + augmented_message
        if strategy_block:
            augmented_message = augmented_message + "\n\n" + strategy_block
        if attached_bundle is not None and attached_bundle.context.strip():
            augmented_message = augmented_message + "\n\n" + attached_bundle.context.strip()
        if request_standard_guidance.strip():
            augmented_message = (
                "Request-standard guidance for this turn:\n"
                + request_standard_guidance.strip()
                + "\n\n"
                + augmented_message
            )
        if self._memory and ticker:
            try:
                research = self._memory.read_research(ticker)
                if research:
                    extra_context = (
                        f"\n\n## Prior Research for {ticker}\n{research[:4000]}"
                    )
                    augmented_message = augmented_message + extra_context
            except Exception:
                pass  # memory injection is best-effort

        # Run the agent loop
        from cockpit.core.agent_loop import (
            AgentResult,
        )  # guaranteed available if _agent_loop is set

        agent_message = _apply_backend_prefix(augmented_message, turn_force_backend)
        result: AgentResult = self._agent_loop.run(
            message=agent_message,
            ticker=ticker,
            conversation_history=conversation_history,
            on_chunk=on_chunk,
            on_status=on_status,
            on_thinking=on_thinking,
        )

        # Capture routing metadata from HybridRouter's cost log.
        if self._hybrid_router is not None:
            cost_entries = self._hybrid_router.cost_log()
            if cost_entries:
                last = cost_entries[-1]
                result.routing_metadata = {
                    "source": last["source"],
                    "model": last["model"],
                    "latency_ms": last["latency_ms"],
                    "cost_usd": last["cost_usd"],
                    "routing_reason": last.get("routing_reason"),
                    "total_session_cost_usd": self._hybrid_router.total_cost_usd(),
                }

        self._record_answer_side_effects(
            query=base_message,
            answer=result.text.strip(),
            ticker=ticker,
        )
        combined_evidence = list(attached_bundle.evidence) if attached_bundle else []
        combined_evidence.extend(list(getattr(result, "evidence", None) or []))
        self._remember_youtube_video_options_from_evidence(combined_evidence)
        self._set_latest_sources_payloads(combined_evidence)

        return ChatResponse(
            text=result.text.strip(),
            evidence=combined_evidence,
            action_preview=result.action_preview,
            mode=result.mode,
            routing_metadata=result.routing_metadata,
            tool_traces=getattr(result, "tool_traces", None) or [],
        )

    def _recent_youtube_channel_from_context(self) -> str | None:
        """Best-effort channel carryover from prior structured chat text."""
        patterns = (
            re.compile(r"Recent videos from\s+(.+?)(?:\s+\(|:)", re.IGNORECASE),
            re.compile(
                r"(?:Added|Already watching)\s+YouTube channel\s+(.+?)(?:\s+\(|\.|$)",
                re.IGNORECASE,
            ),
        )
        for item in reversed(self._recent_conversation_history()):
            content = str(item.get("content") or "").strip()
            if not content:
                continue
            for pattern in patterns:
                match = pattern.search(content)
                if match:
                    channel = re.sub(r"\s+", " ", match.group(1)).strip(" .:")
                    if channel:
                        return channel
        return None

    @staticmethod
    def _parse_youtube_video_options_from_text(content: str) -> list[dict[str, Any]]:
        if "Recent videos from" not in content:
            return []
        youtube_url_re = re.compile(
            r"https?://(?:www\.)?(?:youtube\.com/watch\?[^\s]*v=|youtu\.be/)"
            r"[A-Za-z0-9_\-]{6,}[^\s]*",
            re.IGNORECASE,
        )
        option_re = re.compile(r"^\s*(\d+)\.\s+(.+?)(?:\s+\||$)")
        options: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        for line in str(content or "").splitlines():
            option_match = option_re.match(line)
            if option_match:
                current = {
                    "position": int(option_match.group(1)),
                    "title": re.sub(r"\s+", " ", option_match.group(2)).strip(),
                    "webpage_url": "",
                }
                inline_url = youtube_url_re.search(line)
                if inline_url:
                    current["webpage_url"] = inline_url.group(0).rstrip(".,)")
                options.append(current)
                continue
            if current is None:
                continue
            url_match = youtube_url_re.search(line)
            if url_match:
                current["webpage_url"] = url_match.group(0).rstrip(".,)")
        return [row for row in options if row.get("webpage_url")]

    def _remember_youtube_video_options(self, result: dict[str, Any]) -> None:
        videos = result.get("videos") if isinstance(result, dict) else None
        if not isinstance(videos, list):
            return
        options: list[dict[str, Any]] = []
        for index, video in enumerate(videos, start=1):
            if not isinstance(video, dict):
                continue
            url = str(video.get("webpage_url") or video.get("url") or "").strip()
            if not url:
                continue
            options.append(
                {
                    "position": video.get("position") or index,
                    "title": str(video.get("title") or video.get("video_id") or "Untitled").strip(),
                    "webpage_url": url,
                    "video_id": video.get("video_id"),
                    "scores": video.get("scores") if isinstance(video.get("scores"), dict) else {},
                }
            )
        if options:
            self._recent_youtube_video_options = options[:20]

    def _remember_youtube_video_options_from_evidence(
        self,
        evidence: list[dict[str, Any]],
    ) -> None:
        for item in reversed(evidence or []):
            if not isinstance(item, dict):
                continue
            if item.get("tool") != "check_youtube_channel_recent_videos":
                continue
            result = item.get("result")
            if isinstance(result, dict):
                self._remember_youtube_video_options(result)
                if self._recent_youtube_video_options:
                    return

    def _recent_youtube_video_options_from_context(self) -> list[dict[str, Any]]:
        if self._recent_youtube_video_options:
            return list(self._recent_youtube_video_options)
        if self._state_store is None:
            return []
        try:
            history_msgs = self._state_store.get_chat_messages(self._thread_id, limit=12)
        except Exception:
            return []
        for item in reversed(history_msgs or []):
            if item.get("role") != "assistant":
                continue
            options = self._parse_youtube_video_options_from_text(
                str(item.get("content") or "")
            )
            if options:
                self._recent_youtube_video_options = options[:20]
                return list(self._recent_youtube_video_options)
        return []

    def _build_command_route_response(self, route: CommandRoute) -> ChatResponse | None:
        if not route.matched:
            return None
        if not route.tool:
            return ChatResponse(
                text=route.explanation or "I need one more detail to run that command.",
                evidence=[],
                mode=ResponseMode.FAST,
            )

        from cockpit.core.tool_executor import ToolExecutor

        executor = ToolExecutor(self.tool_router, self.action_registry)
        arguments = dict(route.arguments or {})

        if route.action_type == "direct_tool":
            raw_result = executor.execute(route.tool, arguments)
            result = raw_result if isinstance(raw_result, dict) else {"result": raw_result}
            from cockpit.core.agent_loop import AgentLoop

            evidence = [
                {
                    "tool": route.tool,
                    "arguments": arguments,
                    "result": result,
                }
            ]
            if route.tool == "check_youtube_channel_recent_videos":
                self._remember_youtube_video_options(result)
            self._set_latest_sources_payloads(evidence)
            return ChatResponse(
                text=AgentLoop._format_direct_command_tool_result(route, result),
                evidence=evidence,
                mode="command",
            )

        proposal = executor.execute(route.tool, arguments)
        if isinstance(proposal, dict) and (
            proposal.get("ok") is False or proposal.get("error")
        ):
            return ChatResponse(
                text=f"Could not prepare {route.tool}: {proposal.get('error') or 'proposal failed'}",
                evidence=[],
                mode=ResponseMode.FAST,
            )
        preview = normalize_action_preview(
            proposal
            if isinstance(proposal, dict)
            else {
                "tool": route.tool,
                "arguments": arguments,
                "explanation": route.explanation or "",
                "requires_confirmation": True,
            }
        )
        text = route.explanation or f"Ready to execute: {route.tool}"
        if preview.get("requires_confirmation", True) and "/confirm" not in text:
            text = f"{text} Use /confirm to execute."
        return ChatResponse(
            text=text,
            evidence=[],
            action_preview=preview,
            mode=ResponseMode.ACTION,
        )

    def _recent_conversation_history(self) -> list[dict[str, str]]:
        conversation_history: list[dict[str, str]] = []
        if self._state_store is not None:
            try:
                history_msgs = self._state_store.get_chat_messages(
                    self._thread_id, limit=12
                )
                prior_turns = history_msgs[:-1] if history_msgs else []
                conversation_history = [
                    {
                        "role": m.get("role", "user"),
                        "content": str(m.get("content", ""))[:400],
                    }
                    for m in prior_turns[-6:]
                ]
            except Exception:
                pass
        return conversation_history

    def _record_answer_side_effects(
        self,
        *,
        query: str,
        answer: str,
        ticker: str | None,
    ) -> None:
        record_turn(
            self._ov_session_id,
            build_turn_payload(
                session_id=self._ov_session_id,
                thread_id=self._thread_id,
                query=query,
                answer=answer.strip(),
                ticker=ticker,
            ),
        )

        if self._memory:
            try:
                self._memory.append_session_turn("user", query)
                self._memory.append_session_turn("assistant", answer.strip())
            except Exception:
                pass

        if self._state_store is not None and ticker:
            try:
                obs_list = ChatController._extract_ticker_observations(ticker, answer)
                for obs in obs_list:
                    self._state_store.add_entity_observation(
                        ticker=ticker,
                        observation_type=obs["type"],
                        content=obs["content"],
                        source="chat",
                    )
            except Exception:
                pass

    def _build_orchestrated_response(
        self,
        *,
        orchestration_result,
        message: str,
        ticker: str | None,
        force_backend: str | None = None,
        on_chunk=None,
        on_status=None,
        attached_bundle: _AttachedSourceBundle | None = None,
        request_standard_guidance: str = "",
    ) -> ChatResponse | None:
        if orchestration_result is None:
            return None

        primary_ticker = (
            str(orchestration_result.entities.get("primary_ticker") or ticker or "")
            .strip()
            .upper()
        )
        if not self._orchestration_has_substantive_evidence(orchestration_result):
            return None

        evidence = [
            {
                "type": "orchestrator",
                "tool": "orchestrator",
                "details": {
                    "intent": orchestration_result.intent,
                    "source_plan": list(orchestration_result.source_plan),
                    "entities": orchestration_result.entities,
                    "source_status": orchestration_result.answer.get("source_status")
                    or {},
                    "missing_data_recovery": getattr(
                        orchestration_result, "missing_data_recovery", {}
                    ),
                    "missing_categories_before_recovery": list(
                        getattr(
                            orchestration_result,
                            "missing_categories_before_recovery",
                            (),
                        )
                    ),
                    "missing_categories_after_recovery": list(
                        getattr(
                            orchestration_result,
                            "missing_categories_after_recovery",
                            (),
                        )
                    ),
                    "sufficient_for_analysis": bool(
                        getattr(orchestration_result, "sufficient_for_analysis", True)
                    ),
                },
                "result": {
                    "intent": orchestration_result.intent,
                    "source_plan": list(orchestration_result.source_plan),
                    "entities": orchestration_result.entities,
                    "source_status": orchestration_result.answer.get("source_status")
                    or {},
                    "missing_data_recovery": getattr(
                        orchestration_result, "missing_data_recovery", {}
                    ),
                    "sufficient_for_analysis": bool(
                        getattr(orchestration_result, "sufficient_for_analysis", True)
                    ),
                },
            }
        ]
        for source_name in orchestration_result.source_plan:
            payload = (
                orchestration_result.raw_supporting_evidence.get(source_name) or {}
            )
            evidence.append(
                {
                    "type": source_name,
                    "tool": source_name,
                    "details": payload,
                    "result": payload,
                }
            )
        if attached_bundle is not None and attached_bundle.evidence:
            evidence.extend(attached_bundle.evidence)

        if on_status:
            on_status("Routing query through orchestrator")

        coverage_disclosures = self._collect_orchestration_coverage_disclosures(
            orchestration_result
        )
        final_text = orchestration_result.answer_input
        if self._agent_loop is not None:
            conversation_history = self._recent_conversation_history()
            synthesis_question = message
            if request_standard_guidance.strip():
                synthesis_question = (
                    f"{message}\n\nRequest-standard guidance for this turn:\n"
                    f"{request_standard_guidance.strip()}"
                )
            if on_status:
                on_status("Streaming final synthesis")
            previous_force_backend = getattr(
                self._agent_loop, "_turn_force_backend", None
            )
            setattr(self._agent_loop, "_turn_force_backend", force_backend)
            try:
                if on_chunk is not None:
                    final_text = self._agent_loop.synthesize_final_answer_stream(
                        evidence,
                        on_chunk,
                        question=synthesis_question,
                        ticker=primary_ticker or ticker,
                        conversation_history=conversation_history,
                        draft_answer=orchestration_result.answer_input,
                        on_status=on_status,
                    )
                else:
                    final_text = self._agent_loop.synthesize_final_answer(
                        evidence,
                        question=synthesis_question,
                        ticker=primary_ticker or ticker,
                        conversation_history=conversation_history,
                        draft_answer=orchestration_result.answer_input,
                        on_status=on_status,
                    )
            finally:
                setattr(
                    self._agent_loop,
                    "_turn_force_backend",
                    previous_force_backend,
                )
        elif on_chunk is not None and final_text:
            self._stream_plain_text(final_text, on_chunk)

        final_text = self._append_orchestration_disclosures(
            final_text,
            disclosures=coverage_disclosures,
        )

        self._record_answer_side_effects(
            query=message,
            answer=final_text,
            ticker=primary_ticker or ticker,
        )
        self._set_latest_sources_payloads(evidence)
        routing_metadata: dict[str, Any] = {
            "source": "orchestrator",
            "intent": orchestration_result.intent,
            "sources": list(orchestration_result.source_plan),
        }
        if self._hybrid_router is not None:
            cost_entries = self._hybrid_router.cost_log()
            if cost_entries:
                last = cost_entries[-1]
                routing_metadata["routing_reason"] = last.get("routing_reason")

        return ChatResponse(
            text=final_text.strip(),
            evidence=evidence,
            mode=ResponseMode.FAST,
            routing_metadata=routing_metadata,
        )

    @staticmethod
    def _collect_orchestration_coverage_disclosures(orchestration_result) -> list[str]:
        disclosures: list[str] = []
        seen: set[str] = set()

        def _add(message: str) -> None:
            cleaned = str(message or "").strip()
            if not cleaned:
                return
            key = cleaned.lower()
            if key in seen:
                return
            seen.add(key)
            disclosures.append(cleaned)

        missing_categories = [
            str(category)
            for category in list(
                getattr(orchestration_result, "missing_categories_after_recovery", ())
                or []
            )
            if str(category).strip()
        ]
        if missing_categories:
            _add("Unresolved evidence gaps: " + ", ".join(missing_categories))

        source_status = {}
        answer = getattr(orchestration_result, "answer", None)
        if isinstance(answer, dict):
            source_status = answer.get("source_status") or {}
        if isinstance(source_status, dict):
            for source_name, raw_status in source_status.items():
                source_label = str(source_name or "").strip() or "unknown_source"
                if isinstance(raw_status, str):
                    normalized = raw_status.strip().lower()
                    if normalized and normalized != "ok":
                        _add(f"{source_label} retrieval status: {raw_status}")
                    continue
                if isinstance(raw_status, dict):
                    status_value = str(raw_status.get("status") or "").strip()
                    ok_value = raw_status.get("ok")
                    if status_value and status_value.lower() != "ok":
                        _add(f"{source_label} retrieval status: {status_value}")
                    elif ok_value is False:
                        _add(f"{source_label} retrieval status: not_ok")

        raw_supporting = getattr(orchestration_result, "raw_supporting_evidence", None)
        if isinstance(raw_supporting, dict):
            for source_name, payload in raw_supporting.items():
                if not isinstance(payload, dict):
                    continue
                source_label = str(source_name or "").strip() or "unknown_source"
                errors = payload.get("errors")
                if isinstance(errors, list) and errors:
                    _add(
                        f"{source_label} retrieval errors: "
                        + "; ".join(str(err) for err in errors[:3])
                    )
                error_text = str(payload.get("error") or "").strip()
                if error_text:
                    _add(f"{source_label} retrieval error: {error_text}")

        return disclosures

    @staticmethod
    def _append_orchestration_disclosures(
        text: str,
        *,
        disclosures: list[str],
    ) -> str:
        base = str(text or "").strip()
        if not disclosures:
            return base

        lowered = base.lower()
        missing = [item for item in disclosures if item.lower() not in lowered]
        if not missing:
            return base

        suffix_lines = ["", "Coverage and Failure Signals:"]
        suffix_lines.extend(f"- {item}" for item in missing)
        return base + "\n" + "\n".join(suffix_lines)

    @staticmethod
    def _stream_plain_text(text: str, on_chunk) -> None:
        for index, token in enumerate(text.split()):
            suffix = " " if index < len(text.split()) - 1 else ""
            on_chunk(token + suffix)

    # Mapping from web UI mode strings to ResponseMode values used as
    # soft fallback when keyword classification returns FAST.
    _UI_MODE_MAP: dict[str, ResponseMode] = {
        "strategy": ResponseMode.DEEP_ANALYSIS,
        "deep_analysis": ResponseMode.DEEP_ANALYSIS,
        "verification": ResponseMode.VERIFICATION,
    }

    def _run_marketplace_chat_mode(
        self,
        message: str,
        *,
        force_backend: str | None,
        on_chunk,
        on_status,
        attached_bundle: _AttachedSourceBundle | None = None,
    ) -> ChatResponse:
        """Run Marketplace assistant turns without the ASX/ticker short-circuits.

        The Marketplace UI already constructs a strict instruction packet. This
        mode treats that packet as authoritative and routes it straight through
        the chat backend instead of letting ticker heuristics reinterpret it as
        an ASX finance query.
        """

        if on_status is not None:
            on_status("Marketplace assistant mode")

        system_instruction = (
            "You are Tenn in Marketplace assistant mode.\n"
            "- Treat the user message as an application instruction packet for Marketplace mission drafting.\n"
            "- Do not interpret uppercase words as ASX tickers, company identifiers, or command aliases.\n"
            "- Do not trigger finance/news/announcement/backfill workflows unless the user explicitly requests those workflows.\n"
            "- If the user message requests strict JSON only, return strict JSON only.\n"
            "- Return plain text otherwise.\n"
        )

        user_message = message
        if attached_bundle is not None and attached_bundle.context.strip():
            user_message = f"{user_message}\n\n{attached_bundle.context.strip()}"

        prior_messages = [{"role": "system", "content": system_instruction}]
        prompt_fallback = f"{system_instruction}\n\n{user_message}"

        answer: str
        routing_metadata: dict[str, Any] | None = None
        if self._hybrid_router is not None:
            answer = self._hybrid_router.chat(
                user_message,
                timeout=self.llm_timeout_seconds,
                on_chunk=on_chunk,
                prior_messages=prior_messages,
                force_backend=force_backend,
                on_status=on_status,
            )
            last_attempt = self._hybrid_router.last_attempt_metadata()
            if last_attempt:
                routing_metadata = dict(last_attempt)
                routing_metadata["total_session_cost_usd"] = self._hybrid_router.total_cost_usd()
        elif on_chunk is not None:
            try:
                answer = self.ollama_client.chat(
                    user_message,
                    timeout=self.llm_timeout_seconds,
                    on_chunk=on_chunk,
                    prior_messages=prior_messages,
                )
            except TypeError as exc:
                if "on_chunk" not in str(exc) and "prior_messages" not in str(exc):
                    raise
                logger.info("marketplace ollama_client.chat fallback (unsupported kwarg): %s", exc)
                answer = self.ollama_client.chat(
                    prompt_fallback,
                    timeout=self.llm_timeout_seconds,
                )
        else:
            try:
                answer = self.ollama_client.chat(
                    user_message,
                    timeout=self.llm_timeout_seconds,
                    prior_messages=prior_messages,
                )
            except TypeError as exc:
                if "prior_messages" not in str(exc):
                    raise
                logger.info(
                    "marketplace ollama_client.chat fallback (no prior_messages support): %s",
                    exc,
                )
                answer = self.ollama_client.chat(
                    prompt_fallback,
                    timeout=self.llm_timeout_seconds,
                )

        evidence = list(attached_bundle.evidence) if attached_bundle is not None else []
        routing_metadata = dict(routing_metadata or {})
        routing_metadata["ui_mode"] = "marketplace"
        self._record_answer_side_effects(query=message, answer=answer.strip(), ticker=None)
        self._set_latest_sources_payloads(evidence)
        return ChatResponse(
            text=answer.strip(),
            evidence=evidence,
            mode=ResponseMode.FAST,
            routing_metadata=routing_metadata,
        )

    def build_chat_response(
        self,
        message: str,
        enable_web: bool = False,
        enable_rag: bool = True,
        enable_db_diagnostics: bool = False,
        prior_ticker: str | None = None,
        on_chunk=None,
        on_status=None,
        on_thinking=None,
        analysis_mode: str | None = None,
        context_profile: str | None = None,
        ui_mode: str | None = None,
        attached_sources: list[dict[str, Any]] | None = None,
    ) -> ChatResponse:
        article_text_request = self._try_article_text_request(message)
        if article_text_request is not None:
            return article_text_request

        summary_followup = self._try_summary_offer_followup(message, prior_ticker)
        if summary_followup is not None:
            return summary_followup

        rewritten_confirmation = self._rewrite_confirmation_followup(
            message, prior_ticker
        )
        effective_message = rewritten_confirmation or message
        forced_backend, effective_message = parse_backend_prefix(effective_message)
        attached_bundle = _build_attached_source_bundle(attached_sources)

        # Web chat path parity with Textual UI: map recognised natural-language
        # control phrases to deterministic slash commands.
        if not effective_message.strip().startswith("/"):
            derived_cmd = derive_conversational_command(effective_message.strip())
            if derived_cmd:
                effective_message = derived_cmd

        # Slash commands should be deterministic in all UI modes, including
        # marketplace. Dispatch them before mode-specific chat paths.
        if effective_message.strip().startswith("/"):
            cmd_response = self._handle_slash_command(effective_message.strip())
            if cmd_response is not None:
                return cmd_response

        if ui_mode == "marketplace":
            return self._run_marketplace_chat_mode(
                effective_message,
                force_backend=forced_backend,
                on_chunk=on_chunk,
                on_status=on_status,
                attached_bundle=attached_bundle,
            )

        command_route = (
            CommandRoute(matched=False)
            if forced_backend
            else route_command(
                effective_message,
                active_ticker=prior_ticker or self.last_ticker,
                recent_youtube_channel=self._recent_youtube_channel_from_context(),
                recent_youtube_videos=self._recent_youtube_video_options_from_context(),
            )
        )
        command_response = self._build_command_route_response(command_route)
        command_is_analysis_fallback = (
            self._query_orchestrator is not None and command_route.tool == "run_analysis"
        )
        if command_response is not None and not command_is_analysis_fallback:
            return command_response

        market_update_followup = self._try_market_update_followup(effective_message)
        if market_update_followup is not None:
            return market_update_followup

        # --- Greeting short-circuit: don't invoke the full analyst pipeline ---
        if self._GREETING_RE.match(effective_message):
            greeting = (
                "Hey! I'm Tenn — your ASX research assistant. "
                'Ask me about a company (e.g. "tell me about CSL") or run an action from the panel.'
            )
            return ChatResponse(text=greeting, evidence=[], mode=ResponseMode.FAST)

        # --- Runtime clock short-circuit: answer local date/time/day directly ---
        runtime_clock_result = self._try_runtime_clock_shortcircuit(effective_message)
        if runtime_clock_result is not None:
            return runtime_clock_result

        # ------------------------------------------------------------------ #
        # Deterministic fast-paths — fire BEFORE agent loop or keyword LLM.   #
        # These are pure regex/keyword matches that don't need LLM inference. #
        # ------------------------------------------------------------------ #

        # --- Direct company data dump short-circuit ---
        filestats_result = self._try_filestats_shortcircuit(effective_message)
        if filestats_result is not None:
            return filestats_result

        # Ticker detection (shared by both agent and keyword paths).
        ticker, explicit_ticker = self._resolve_ticker_context(
            effective_message, prior_ticker=prior_ticker
        )
        if ticker:
            self.last_ticker = ticker
        standards_mode_hint = self.classify_request(
            effective_message, enable_web=enable_web
        )
        if str(analysis_mode or "").strip().lower() == "deep":
            standards_mode_hint = ResponseMode.DEEP_ANALYSIS
        elif standards_mode_hint == ResponseMode.FAST and ui_mode:
            standards_mode_hint = self._UI_MODE_MAP.get(ui_mode, standards_mode_hint)
        pre_routing_standards_guidance = build_request_standard_prompt_guidance(
            message=effective_message,
            mode=standards_mode_hint.value,
            ticker=ticker,
        )
        pre_routing_standard_type = select_request_standard_type(
            message=effective_message,
            mode=standards_mode_hint.value,
            ticker=ticker,
        )

        clarification_result = self._try_fast_clarification_shortcircuit(
            effective_message,
            ticker=ticker,
            attached_bundle=attached_bundle,
        )
        if clarification_result is not None:
            return clarification_result

        msg_lower = effective_message.lower()
        recent_update_query = bool(ticker) and self._query_requests_recent_update(
            effective_message
        )

        # --- Conversational update shortcut: "update <ticker> announcements" ---
        explicit_ticker_in_message = ticker if explicit_ticker else None
        if (
            "update" in msg_lower
            and "announcement" in msg_lower
            and explicit_ticker_in_message
        ):
            args: dict[str, Any] = {
                "ticker": explicit_ticker_in_message,
                "years": 1,
                "process_documents": True,
            }
            action_preview: dict[str, Any] = {
                "action_id": "update_ticker_financials",
                "args": args,
            }
            if self.action_registry:
                try:
                    preview = self.action_registry.preview(
                        "update_ticker_financials", args
                    )
                    action_preview["command"] = preview.command
                    action_preview["impact"] = preview.estimated_impact
                    action_preview["timeout_seconds"] = preview.timeout_seconds
                except Exception:
                    pass
            return ChatResponse(
                text=f"Preparing to update announcements for {explicit_ticker_in_message}. Use /confirm to execute.",
                evidence=[],
                action_preview=action_preview,
                mode=ResponseMode.ACTION,
            )

        # --- Conversational ingest shortcut: "ingest <ticker>" or bare "ingest" with session ticker ---
        ingest_ticker_match = re.fullmatch(
            r"\s*ingest\s+([A-Za-z]{2,5})\s*[?!.]*\s*", effective_message
        )
        ingest_ticker: str | None = None
        if ingest_ticker_match:
            ingest_ticker = ingest_ticker_match.group(1).upper()
            if ingest_ticker in self.TICKER_STOPWORDS:
                ingest_ticker = None
        elif re.fullmatch(r"\s*ingest\s*[?!.]*\s*", effective_message):
            # Bare "ingest" — inherit active session ticker
            ingest_ticker = ticker or self.last_ticker
            if not ingest_ticker:
                return ChatResponse(
                    text='Which ticker do you want to ingest? e.g. "ingest BHP"',
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
        if ingest_ticker:
            args = {
                "ticker": ingest_ticker,
                "years": 3,
                "process_documents": True,
            }
            action_preview: dict[str, Any] = {
                "action_id": "single_ticker_announcement_backfill",
                "args": args,
            }
            if self.action_registry:
                try:
                    preview = self.action_registry.preview(
                        "single_ticker_announcement_backfill", args
                    )
                    action_preview["command"] = preview.command
                    action_preview["impact"] = preview.estimated_impact
                    action_preview["timeout_seconds"] = preview.timeout_seconds
                except Exception:
                    pass
            return ChatResponse(
                text=(
                    f"Preparing to ingest announcements for {ingest_ticker}. "
                    "Use /confirm to execute."
                ),
                evidence=[],
                action_preview=action_preview,
                mode=ResponseMode.ACTION,
            )

        # --- Explicit web-search shortcut: "search web for ..." ---
        explicit_web_query = self._extract_explicit_web_search_query(effective_message)
        if explicit_web_query is not None:
            if not explicit_web_query:
                return ChatResponse(
                    text='Tell me what to search for, e.g. "search web for BHP latest announcement".',
                    evidence=[],
                    mode=ResponseMode.WEB,
                )
            if not enable_web:
                return ChatResponse(
                    text="Web access is required for web search. Enable web and try again.",
                    evidence=[],
                    action_preview=build_backend_access_proposal_request(
                        "web",
                        enable=True,
                        resume_message=effective_message,
                    ),
                    mode=ResponseMode.FAST,
                )
            try:
                web_result = self.tool_router.web_enrich(
                    explicit_web_query, enabled=True
                )
            except Exception as exc:
                return ChatResponse(
                    text=f"Web search failed: {exc}",
                    evidence=[],
                    mode=ResponseMode.WEB,
                )

            payload = (
                web_result.payload
                if isinstance(getattr(web_result, "payload", None), dict)
                else {}
            )
            evidence: list[dict[str, Any]] = [{"type": "web", "details": payload}]
            if attached_bundle.evidence:
                evidence.extend(attached_bundle.evidence)

            urls = payload.get("urls") if isinstance(payload.get("urls"), list) else []
            lines = [f"Web search results for: {explicit_web_query}"]
            if urls:
                for idx, url in enumerate(urls[:5], start=1):
                    lines.append(f"{idx}. {url}")
            else:
                lines.append("No web results were returned.")

            facts_count = payload.get("facts_count")
            if isinstance(facts_count, int) and facts_count > 0:
                lines.append(f"Extracted {facts_count} numeric web fact(s).")

            return ChatResponse(
                text="\n".join(lines),
                evidence=evidence,
                mode=ResponseMode.WEB,
            )

        # --- Chart intent short-circuit (before general action detection) ---
        if self.detect_chart_intent(effective_message):
            from cockpit.core.chart_args import prepare_chart_action_args

            if not ticker:
                return ChatResponse(
                    text='Which ticker do you want to chart? e.g. "chart CSL" or "candlestick BHP"',
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            chart_ticker = ticker
            out_dir = Path("reports") / "candles"

            def _default_parse_kv(raw: str) -> dict:
                out: dict = {}
                for tok in str(raw or "").split():
                    if "=" not in tok:
                        continue
                    k, v = tok.split("=", 1)
                    out[k] = v
                return out

            _parse_kv = getattr(
                self.action_registry, "parse_kv_args", _default_parse_kv
            )
            chart_args, chart_err = prepare_chart_action_args(
                chart_ticker,
                parse_kv_args=_parse_kv,
                tool_router=self.tool_router,
                out_dir=out_dir,
            )
            if chart_err:
                return ChatResponse(
                    text=f"/chart failed: {chart_err}",
                    evidence=[
                        {
                            "type": "chart_error",
                            "details": {"error": chart_err, "ticker": chart_ticker},
                        }
                    ],
                    action_preview=None,
                    mode=ResponseMode.ACTION,
                )
            if chart_args is None:
                return ChatResponse(
                    text=f"/chart failed: no chart args returned for {chart_ticker}",
                    evidence=[
                        {"type": "chart_error", "details": {"ticker": chart_ticker}}
                    ],
                    action_preview=None,
                    mode=ResponseMode.ACTION,
                )
            chart_args["ticker"] = chart_ticker
            preview = self.action_registry.preview("show_candlestick", chart_args)
            return ChatResponse(
                text=f"Running candlestick chart for {chart_ticker}...",
                evidence=[
                    {
                        "type": "chart_action",
                        "details": {"ticker": chart_ticker, **chart_args},
                    }
                ],
                action_preview={
                    "action_id": "show_candlestick",
                    "args": chart_args,
                    "command": preview.command,
                    "impact": preview.estimated_impact,
                    "timeout_seconds": preview.timeout_seconds,
                },
                mode=ResponseMode.ACTION,
            )

        # --- Price history short-circuit ---
        price_history_result = self._try_price_history_shortcircuit(
            effective_message, ticker
        )
        if price_history_result is not None:
            return price_history_result

        # --- Direct ticker news short-circuit ---
        news_shortcircuit_result = self._try_news_shortcircuit(
            effective_message, ticker
        )
        if news_shortcircuit_result is not None:
            return news_shortcircuit_result

        # --- Action keyword detection (deterministic, no LLM) ---
        action_id = self.detect_action_intent(effective_message)
        if action_id:
            # Action fast-paths need the keyword mode's ActionRegistry.preview()
            # flow, which is handled below in the keyword router section.
            # If we're in agent mode, the agent loop also handles actions via
            # ToolExecutor, but explicit keyword matches are faster and more
            # predictable — so we let them fall through to the keyword action
            # handler below rather than routing through the LLM.
            pass
        else:
            orchestrated_response = None
            prefer_local_context = False
            if self._query_orchestrator is not None:
                try:
                    orchestration_result = (
                        self._query_orchestrator.orchestrate_query_with_context(
                            effective_message,
                            context={
                                "prior_ticker": ticker,
                                "analysis_mode": analysis_mode,
                                "request_standard": pre_routing_standard_type,
                            },
                        )
                    )
                    has_orchestrated_evidence = (
                        self._orchestration_has_substantive_evidence(
                            orchestration_result
                        )
                    )
                    prefer_local_context = bool(ticker) and (
                        self._query_requires_document_grounding(effective_message)
                        or recent_update_query
                        or not has_orchestrated_evidence
                    )
                    if not prefer_local_context:
                        orchestrated_response = self._build_orchestrated_response(
                            orchestration_result=orchestration_result,
                            message=effective_message,
                            ticker=ticker,
                            force_backend=forced_backend,
                            on_chunk=on_chunk,
                            on_status=on_status,
                            attached_bundle=attached_bundle,
                            request_standard_guidance=pre_routing_standards_guidance,
                        )
                except Exception as exc:
                    logger.warning(
                        "Query orchestrator failed; falling back to agent loop: %s",
                        exc,
                    )
            if orchestrated_response is not None:
                return orchestrated_response

            # ------------------------------------------------------------------ #
            # Agent mode dispatch — routes general queries through HybridRouter.  #
            # Only fires for non-action, non-shortcircuited queries.              #
            # ------------------------------------------------------------------ #
            agent_mode = os.environ.get("COCKPIT_AGENT_MODE", "structured")
            if (
                (forced_backend == "api" or not prefer_local_context)
                and agent_mode == "structured"
                and self._agent_loop is not None
            ):
                return self._run_agent_loop(
                    effective_message,
                    enable_web,
                    prior_ticker,
                    on_chunk,
                    on_status,
                    analysis_mode,
                    on_thinking=on_thinking,
                    attached_bundle=attached_bundle,
                    request_standard_guidance=pre_routing_standards_guidance,
                    force_backend=forced_backend,
                )

        # ------------------------------------------------------------------ #
        # Keyword router (legacy path — explicit opt-in or action fallthrough) #
        # ------------------------------------------------------------------ #

        if action_id:
            mode = ResponseMode.ACTION
        else:
            mode = self.classify_request(effective_message, enable_web=enable_web)
            # Soft fallback: when keywords are ambiguous (FAST), honour
            # the UI-selected mode if it maps to a known ResponseMode.
            if mode == ResponseMode.FAST and ui_mode:
                mode = self._UI_MODE_MAP.get(ui_mode, mode)

        effective_profile = context_profile or os.environ.get(
            "COCKPIT_CONTEXT_PROFILE", "balanced"
        )

        # --- Access request: URL in message but web is disabled ---
        if (
            any(p in effective_message for p in ("http://", "https://"))
            and not enable_web
        ):
            return ChatResponse(
                text="Web access is required to fetch that URL. Enable web and try again.",
                evidence=[],
                action_preview=build_backend_access_proposal_request(
                    "web",
                    enable=True,
                    resume_message=effective_message,
                ),
                mode=ResponseMode.FAST,
            )

        # --- Access request: max-depth profile requires web enrichment ---
        if effective_profile == "max-depth" and not enable_web:
            return ChatResponse(
                text="Max-depth analysis requires web enrichment. Enable web and try again.",
                evidence=[],
                action_preview=build_backend_access_proposal_request(
                    "web",
                    enable=True,
                    resume_message=effective_message,
                ),
                mode=ResponseMode.FAST,
            )

        # --- Access request: deep analysis requires RAG but it's disabled ---
        rag_available = bool(getattr(self.tool_router, "qual_context_reader", None))
        rag_enabled = (
            bool(getattr(self.tool_router, "qual_context_enabled", False))
            and enable_rag
        )
        if analysis_mode == "deep" and rag_available and not rag_enabled:
            return ChatResponse(
                text="Deep analysis requires RAG context. Enable RAG and try again.",
                evidence=[],
                action_preview=build_backend_access_proposal_request(
                    "rag",
                    enable=True,
                    resume_message=effective_message,
                ),
                mode=ResponseMode.FAST,
            )

        deep_mode = mode in {ResponseMode.DEEP_ANALYSIS, ResponseMode.VERIFICATION}
        local_context = self.tool_router.gather_local_context(
            ticker=ticker, query=effective_message, deep_mode=deep_mode
        )

        evidence = [
            {"type": "local_context", "details": local_context.payload},
        ]
        if attached_bundle.evidence:
            evidence.extend(attached_bundle.evidence)

        _MARKET_WIDE_ACTIONS = {
            "daily_news_ingest",
            "historical_news_ingest",
            "daily_announcement_ingest",
            "load_news_to_qdrant",
            "universe_announcement_enrichment_backfill",
        }
        if action_id:
            if not ticker and action_id not in _MARKET_WIDE_ACTIONS:
                return ChatResponse(
                    text=f'Action **{action_id}** needs a ticker. e.g. "{action_id} CSL"',
                    evidence=[],
                    mode=ResponseMode.FAST,
                )
            args = {"ticker": ticker or ""}
            try:
                preview = self.action_registry.preview(action_id, args)
            except ValueError as exc:
                remediation = build_backend_runtime_remediation_request(
                    getattr(self.tool_router, "backend_api_client", None),
                    action_id=action_id,
                    args=args,
                    error_message=str(exc),
                )
                if remediation is not None:
                    return ChatResponse(
                        text=(
                            "This action is blocked because the backend reported that the extraction runtime is unavailable. "
                            "Approve the backend remediation to recover and then resume the action."
                        ),
                        evidence=evidence,
                        action_preview=remediation,
                        mode=ResponseMode.ACTION,
                    )
                raise
            return ChatResponse(
                text=(
                    f"Action candidate detected: {action_id}. "
                    f"Use /confirm to execute or /cancel to skip.\n"
                    f"Command: {' '.join(preview.command)}"
                ),
                evidence=evidence,
                action_preview={
                    "action_id": action_id,
                    "args": args,
                    "command": preview.command,
                    "impact": preview.estimated_impact,
                    "timeout_seconds": preview.timeout_seconds,
                },
                mode=mode,
            )

        if mode == ResponseMode.WEB:
            maybe_url = re.search(r"https?://\S+", effective_message)
            if maybe_url:
                web = self.tool_router.fetch_web(maybe_url.group(0), enabled=True)
                evidence.append({"type": "web", "details": web.payload})

        # --- Web enrichment for deep mode, max-depth profile, or freshness intent ---
        should_auto_web_enrich = (
            enable_web
            and hasattr(self.tool_router, "web_enrich")
            and (
                analysis_mode == "deep"
                or effective_profile == "max-depth"
                or recent_update_query
                or (
                    mode in {ResponseMode.DEEP_ANALYSIS, ResponseMode.VERIFICATION}
                    and self._query_signals_fresh_web_context(effective_message)
                )
            )
        )
        if should_auto_web_enrich:
            web_query = f"{ticker}: {effective_message}" if ticker else effective_message
            web_result = self.tool_router.web_enrich(web_query, enabled=True)
            evidence.append({"type": "web", "details": web_result.payload})

        # --- Announcement sync check ---
        if "announcement" in msg_lower and ticker:
            local_docs = (
                (local_context.payload or {}).get("docs", [])
                if isinstance(local_context.payload, dict)
                else []
            )
            sync = self._compute_announcement_sync_status(
                ticker, docs=local_docs, message=effective_message
            )
            offer = self._build_ticker_update_offer(ticker, sync)
            return ChatResponse(
                text=offer.get("note", ""),
                evidence=evidence,
                action_preview=offer.get("action_preview"),
                mode=ResponseMode.FAST,
            )

        local_payload = (
            dict(local_context.payload)
            if isinstance(local_context.payload, dict)
            else {}
        )
        if mode == ResponseMode.WEB:
            local_payload["web_requested"] = True
        local_payload["response_mode"] = mode.value

        # --- Empty / thin context short-circuits ---
        # When the ticker is known but there's no DB data at all, skip the LLM and
        # give the user a direct actionable response with a backfill offer.
        has_docs = bool(local_payload.get("docs"))
        has_financials = bool(local_payload.get("financials"))
        qual_payload = local_payload.get("qual_context")
        if isinstance(qual_payload, dict):
            has_qual = bool(qual_payload.get("hits"))
        else:
            has_qual = bool(qual_payload)
        has_price = self._local_payload_has_price_evidence(local_payload)

        if (
            ticker
            and mode not in {ResponseMode.ACTION, ResponseMode.WEB}
            and not has_docs
            and not has_financials
            and not has_qual
            and not (recent_update_query and has_price)
            and not local_payload.get("db_error")  # don't mask DB errors
        ):
            _backfill_args: dict[str, Any] = {"ticker": ticker, "years": 3}
            _action_preview: dict[str, Any] = {
                "action_id": "single_ticker_announcement_backfill",
                "args": _backfill_args,
            }
            if self.action_registry:
                try:
                    _bp = self.action_registry.preview(
                        "single_ticker_announcement_backfill", _backfill_args
                    )
                    _action_preview["command"] = _bp.command
                    _action_preview["impact"] = _bp.estimated_impact
                    _action_preview["timeout_seconds"] = _bp.timeout_seconds
                except Exception:
                    pass
            return ChatResponse(
                text=(
                    f"No data found for **{ticker}** in the local database. "
                    f"The ingestion pipeline hasn't been run for this ticker yet.\n\n"
                    f"Run a backfill to fetch ASX announcements and extract financials (3 years). "
                    f"Type **/confirm** to start, or click **Single Ticker Backfill** in the actions panel."
                ),
                evidence=evidence,
                action_preview=_action_preview,
                mode=ResponseMode.ACTION,
            )

        # Docs exist but no extracted financials — warn the user before hitting the LLM,
        # so the response is grounded rather than speculative.
        if (
            ticker
            and has_docs
            and not has_financials
            and mode not in {ResponseMode.ACTION, ResponseMode.WEB}
        ):
            n_docs = len(local_payload["docs"])
            local_payload["_missing_financials_warning"] = (
                f"Note: {n_docs} document(s) found for {ticker} but no extracted financial metrics. "
                f"Analysis will be limited to announcements and qualitative context. "
                f"Run **Metric Extraction** to process financials from existing documents."
            )

        system_instruction = self._build_system_instruction(
            mode=mode.value, ticker=ticker, local_payload=local_payload
        )
        if mode == ResponseMode.DEEP_ANALYSIS:
            system_instruction += (
                "This is a deep analysis request. Synthesize the evidence, call out risks, "
                "and be explicit about uncertainty and missing support.\n"
            )
        elif mode == ResponseMode.VERIFICATION:
            system_instruction += (
                "This is a verification request. Focus on current state, failures, and what is "
                "confirmed versus inferred.\n"
            )
        elif mode == ResponseMode.WEB:
            system_instruction += "The user supplied a URL. Incorporate any fetched web evidence if it is available.\n"
        standards_guidance = build_request_standard_prompt_guidance(
            message=effective_message,
            mode=mode.value,
            ticker=ticker,
        )
        if standards_guidance:
            system_instruction += standards_guidance

        # OpenViking: fetch semantically relevant prior turns for this query
        ov_context_block = ""
        prior_ov_turns = get_session_context(
            self._ov_session_id,
            effective_message,
            semantic_limit=3,
        )
        if prior_ov_turns:
            lines = ["Relevant prior session context:"]
            for t in prior_ov_turns:
                q = str(t.get("query") or "")[:150]
                a = str(t.get("answer") or "")[:250]
                tkr = str(t.get("ticker") or "").strip()
                note = f" [{tkr}]" if tkr else ""
                if q:
                    lines.append(f"  Q{note}: {q}")
                if a:
                    lines.append(f"  A: {a}")
            ov_context_block = "\n".join(lines) + "\n\n"

        # Inject recent conversation history for context continuity.
        # Context source hierarchy (keyword mode):
        #   1. OpenViking prior turns (ov_context_block) — semantic relevance, PRIMARY session context
        #   2. StateStore history (history_block)        — last 2 turns only, immediate recency
        #   3. StateStore entity observations            — structured facts, different purpose
        # Using only 2 StateStore turns because OpenViking already covers broader session history.
        history_block = ""
        if self._state_store is not None:
            try:
                history_msgs = self._state_store.get_chat_messages(
                    self._thread_id, limit=4
                )
                # Exclude the most recent message (current turn, just stored)
                prior_turns = history_msgs[:-1] if history_msgs else []
                if prior_turns:
                    lines = []
                    for m in prior_turns[
                        -2:
                    ]:  # last 2 turns for immediate recency only
                        role = m.get("role", "user")
                        content = str(m.get("content", ""))[:400]  # cap per message
                        lines.append(f"{role}: {content}")
                    history_block = "Recent conversation:\n" + "\n".join(lines)
            except Exception:
                pass  # history is best-effort, never fail the main response

        # Prepend strategy criteria before financial context
        context_sections = []
        if self._strategy_service and ticker:
            try:
                _strategy_block = self._strategy_service.build_context_block(ticker)
                if _strategy_block:
                    context_sections.append(_strategy_block)
                    # Update sources metadata with strategy criteria count
                    _src = local_payload.get("sources")
                    if isinstance(_src, dict):
                        g_count = len(self._strategy_service.get_global(limit=10))
                        t_count = len(
                            self._strategy_service.get_ticker(ticker, limit=10)
                        )
                        _src["strategy_criteria_count"] = g_count + t_count
            except Exception:
                pass  # strategy injection is best-effort

        if local_payload.get("financials_narrative"):
            context_sections.append(
                "Financial Trend Summary:\n" + local_payload["financials_narrative"]
            )

        if local_payload.get("valuation_multiples"):
            vm = local_payload["valuation_multiples"]
            mv_lines = []
            for k, v in vm.items():
                if v is not None:
                    mv_lines.append(f"  {k}: {v}")
            if mv_lines:
                context_sections.append("Valuation Multiples:\n" + "\n".join(mv_lines))

        if local_payload.get("agent_memory"):
            mem_lines = []
            for obs in local_payload["agent_memory"]:
                mem_lines.append(
                    f"  [{obs.get('type', 'note')}] {obs.get('content', '')}"
                )
            if mem_lines:
                context_sections.append(
                    "Prior agent observations about this ticker:\n"
                    + "\n".join(mem_lines[:6])
                )

        if local_payload.get("prior_export"):
            pe = local_payload["prior_export"]
            prior_ticker = ticker or str(local_payload.get("ticker") or "")
            context_sections.append(
                f"Most recent prior analysis for {prior_ticker}:\n"
                f"  Question: {pe.get('question', '')}\n"
                f"  (Run on {pe.get('date', 'unknown')})"
            )

        # Build a human-readable evidence section instead of dumping raw JSON.
        # The LLM produces better conversational output when context is readable text,
        # not a 7KB JSON blob with internal fields like pdf_path and document_id.
        evidence_parts: list[str] = []

        if context_sections:
            evidence_parts.extend(context_sections)

        # Summarise docs as readable text
        docs = local_payload.get("docs")
        if isinstance(docs, list) and docs:
            doc_lines = [f"Recent documents for {ticker or 'query'}:"]
            for d in docs[:8]:
                title = str(d.get("title") or "").strip()
                pub = str(d.get("published_at") or "").strip()[:10]
                doc_class = str(d.get("doc_class") or "").strip()
                if title:
                    doc_lines.append(
                        f"  - {title} ({doc_class}, {pub})"
                        if pub
                        else f"  - {title} ({doc_class})"
                    )
            evidence_parts.append("\n".join(doc_lines))
        elif recent_update_query and ticker:
            evidence_parts.append(
                "Recent ASX announcement context:\n"
                f"  - No local ASX announcement documents are currently indexed for {ticker}."
            )

        # Summarise doc snippets as readable excerpts
        snippets = local_payload.get("doc_snippets")
        if isinstance(snippets, list) and snippets:
            snippet_lines = ["Document excerpts:"]
            for s in snippets[:5]:
                title = str(s.get("title") or "").strip()
                excerpt = str(s.get("excerpt") or s.get("text") or "").strip()[:800]
                if excerpt:
                    snippet_lines.append(f"  [{title}]: {excerpt}")
            evidence_parts.append("\n".join(snippet_lines))

        # Render financial metric rows so the LLM can cite specific numbers
        financials = local_payload.get("financials")
        if isinstance(financials, list) and financials:
            fin_lines = [f"Financial metrics for {ticker or 'query'}:"]
            for row in financials[:6]:
                period = str(
                    row.get("period_end") or row.get("period") or row.get("year") or ""
                ).strip()
                period_type = str(row.get("period_type") or "").strip()
                label = f"{period} ({period_type})" if period_type else period
                metrics_found = []
                for metric in (
                    "revenue",
                    "ebit",
                    "npat",
                    "operating_cash_flow",
                    "free_cash_flow",
                    "net_debt",
                    "total_assets",
                    "total_equity",
                    "shares_on_issue",
                ):
                    val = row.get(metric)
                    if val is not None:
                        metrics_found.append(f"    {metric}: {val}")
                if metrics_found:
                    fin_lines.append(f"  {label}:")
                    fin_lines.extend(metrics_found)
            if len(fin_lines) > 1:
                evidence_parts.append("\n".join(fin_lines))

        # Include price context as readable text
        price = local_payload.get("price")
        if isinstance(price, dict) and price.get("symbol"):
            price_lines = [f"Price data for {price.get('symbol')}:"]
            for key in ("last_close", "previous_close", "change_pct", "volume"):
                val = price.get(key)
                if val is not None:
                    price_lines.append(f"  {key}: {val}")
            evidence_parts.append("\n".join(price_lines))

        price_state = local_payload.get("price_state")
        if isinstance(price_state, dict) and price_state:
            state_lines = ["Price state:"]
            for key in (
                "trend_regime",
                "momentum_1d",
                "momentum_20d",
                "annualised_vol",
                "drawdown_from_high",
            ):
                val = price_state.get(key)
                if val is not None:
                    state_lines.append(f"  {key}: {val}")
            if len(state_lines) > 1:
                evidence_parts.append("\n".join(state_lines))

        if recent_update_query:
            recent_price_block = self._build_recent_price_summary_block(local_payload)
            if recent_price_block:
                evidence_parts.append(recent_price_block)
            evidence_parts.append(self._build_recent_news_summary_block(local_payload))

        # Include news/qual context if present
        qual = local_payload.get("qual_context")
        if isinstance(qual, list) and qual:
            qual_lines = ["Qualitative context:"]
            for q in qual[:5]:
                text = str(q.get("text") or q.get("content") or "").strip()[:400]
                source = str(q.get("source_name") or q.get("source") or "").strip()
                if text:
                    qual_lines.append(f"  [{source}]: {text}")
            evidence_parts.append("\n".join(qual_lines))

        # Data quality issues worth surfacing
        dq = local_payload.get("data_quality")
        if isinstance(dq, dict):
            issues = []
            if dq.get("extraction_failures"):
                issues.append(f"{len(dq['extraction_failures'])} extraction failure(s)")
            if dq.get("low_confidence_rows"):
                issues.append(
                    f"{len(dq['low_confidence_rows'])} low-confidence metric(s)"
                )
            if issues:
                evidence_parts.append("Data quality notes: " + "; ".join(issues))

        # Surface missing-financials warning so the LLM knows the gap
        missing_warn = local_payload.get("_missing_financials_warning")
        if missing_warn:
            evidence_parts.insert(0, str(missing_warn))

        evidence_section = "\n\n".join(evidence_parts) if evidence_parts else ""

        # Build the user message separately from the system instruction so the
        # LLM can distinguish its role from the user's question.
        user_parts = []
        if ov_context_block:
            user_parts.append(ov_context_block.strip())
        if history_block:
            user_parts.append(history_block.strip())
        user_parts.append(effective_message)
        if attached_bundle.context.strip():
            user_parts.append(attached_bundle.context.strip())
        if evidence_section.strip():
            user_parts.append(evidence_section.strip())
        user_message = "\n\n".join(user_parts)

        prior_messages = [{"role": "system", "content": system_instruction}]

        # Try with proper system/user message separation first.
        # Fall back to concatenated prompt for clients that don't support prior_messages.
        prompt_fallback = system_instruction + "\n\n" + user_message

        if on_chunk is not None:
            try:
                answer = self.ollama_client.chat(
                    user_message,
                    timeout=self.llm_timeout_seconds,
                    on_chunk=on_chunk,
                    prior_messages=prior_messages,
                )
            except TypeError as exc:
                if "on_chunk" not in str(exc) and "prior_messages" not in str(exc):
                    raise
                logger.info("ollama_client.chat fallback (unsupported kwarg): %s", exc)
                answer = self.ollama_client.chat(
                    prompt_fallback, timeout=self.llm_timeout_seconds
                )
        else:
            try:
                answer = self.ollama_client.chat(
                    user_message,
                    timeout=self.llm_timeout_seconds,
                    prior_messages=prior_messages,
                )
            except TypeError as exc:
                if "prior_messages" not in str(exc):
                    raise
                logger.info(
                    "ollama_client.chat fallback (no prior_messages support): %s", exc
                )
                answer = self.ollama_client.chat(
                    prompt_fallback, timeout=self.llm_timeout_seconds
                )

        if analysis_mode == "deep" and (
            self._looks_like_framework_only_analysis(
                answer=answer, ticker=ticker or "", local_payload=local_payload
            )
            or self._violates_deep_output_contract(answer)
        ):
            answer = self._build_grounded_deep_analysis_brief(
                ticker=ticker or str(local_payload.get("ticker") or ""),
                message=message,
                local_payload=local_payload,
            )
        elif self._violates_missing_financials_contract(answer, local_payload):
            if recent_update_query:
                answer = self._build_grounded_recent_update_brief(
                    ticker=ticker or str(local_payload.get("ticker") or ""),
                    local_payload=local_payload,
                )
            else:
                answer = self._build_grounded_overview_brief(
                    ticker=ticker or str(local_payload.get("ticker") or ""),
                    local_payload=local_payload,
                )

        followup_action_preview: dict[str, Any] | None = None
        if recent_update_query and ticker:
            sync = self._compute_announcement_sync_status(
                ticker,
                docs=local_payload.get("docs") or [],
                message=effective_message,
            )
            offer = self._build_ticker_update_offer(ticker, sync)
            action_preview = offer.get("action_preview")
            if isinstance(action_preview, dict):
                followup_action_preview = action_preview
                answer = answer.rstrip() + self._recent_update_offer_suffix(
                    action_preview,
                    ticker=ticker,
                )

        self._record_answer_side_effects(query=message, answer=answer, ticker=ticker)
        self._set_latest_sources_payloads(evidence)

        return ChatResponse(
            text=answer.strip(),
            evidence=evidence,
            action_preview=followup_action_preview,
            mode=mode,
            prompt=prompt_fallback,
        )

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    _DEEP_REQUIRED_HEADERS = (
        "Verdict:",
        "Evidence:",
        "Risks:",
        "Counterpoints:",
        "Unknowns:",
    )
    _MISSING_FINANCIALS_FORBIDDEN = re.compile(
        r"\b(revenue|profit|npat|ebit|ebitda|dividend|net tangible assets|margin|yoy)\b",
        re.IGNORECASE,
    )

    def _violates_deep_output_contract(self, text: str) -> bool:
        """Return True if text is missing required deep-analysis headers or source anchors."""
        for header in self._DEEP_REQUIRED_HEADERS:
            if header not in text:
                return True
        return "[source:" not in text.lower()

    def _looks_like_framework_only_analysis(
        self,
        *,
        answer: str,
        ticker: str,
        local_payload: dict[str, Any],  # noqa: ARG002
    ) -> bool:
        """Return True if the answer looks like an empty outline with no grounded evidence."""
        # Must have numbered markdown section headers (### N. ...) to be a framework answer.
        if not re.search(r"^###\s+\d+\.", answer, re.MULTILINE):
            return False
        # If the answer contains date anchors or score values, it has some grounding.
        if re.search(r"\d{4}-\d{2}-\d{2}", answer):
            return False
        if re.search(r"\bscore\b\s+\d+\.\d|\b0\.\d{3,}\b", answer, re.IGNORECASE):
            return False
        return True

    def _violates_missing_financials_contract(
        self,
        answer: str,
        local_payload: dict[str, Any],
    ) -> bool:
        if local_payload.get("financials"):
            return False
        text = str(answer or "")
        if not text.strip():
            return False
        if not self._MISSING_FINANCIALS_FORBIDDEN.search(text):
            return False
        has_table = "|" in text
        has_money = bool(re.search(r"\b(?:US\$|A\$|AUD|USD)\s*\d", text))
        has_percent = bool(re.search(r"\b\d+(?:\.\d+)?\s*%", text))
        return has_table or has_money or has_percent

    def _build_grounded_recent_update_brief(
        self,
        *,
        ticker: str,
        local_payload: dict[str, Any],
    ) -> str:
        label = ticker or str(local_payload.get("ticker") or "This ticker").upper()
        lines: list[str] = [f"**{label} recent update**", ""]

        price_block = self._build_recent_price_summary_block(local_payload)
        if price_block:
            lines.append(price_block)
            lines.append("")

        docs = local_payload.get("docs") if isinstance(local_payload.get("docs"), list) else []
        if docs:
            lines.append("Recent filings available:")
            for row in docs[:4]:
                if not isinstance(row, dict):
                    continue
                title = str(row.get("title") or "Untitled filing").strip()
                published_at = str(row.get("published_at") or "").strip()[:10]
                prefix = f"- {published_at}: " if published_at else "- "
                lines.append(f"{prefix}{title}")
            lines.append("")

        news_block = self._build_recent_news_summary_block(local_payload)
        if news_block:
            lines.append(news_block)
            lines.append("")

        if not local_payload.get("financials"):
            lines.append(
                "Canonical financial rows are unavailable in this turn, so this "
                "is a recent-event summary from price, filing, and news evidence "
                "rather than a financial-statement analysis."
            )

        return "\n".join(lines).strip()

    def _build_grounded_overview_brief(
        self,
        *,
        ticker: str,
        local_payload: dict[str, Any],
    ) -> str:
        lines: list[str] = []
        label = ticker or "This company"
        lines.append(f"**{label}**")
        lines.append("")
        docs = [d for d in (local_payload.get("docs") or []) if isinstance(d, dict)]
        if docs:
            lines.append("Recent filings available:")
            for doc in docs[:3]:
                title = str(doc.get("title") or "Untitled filing").strip()
                date = str(doc.get("published_at") or "").strip()[:10]
                if date:
                    lines.append(f"- {date}: {title}")
                else:
                    lines.append(f"- {title}")
            lines.append("")
        price_state = local_payload.get("price_state") or {}
        trend = str(price_state.get("trend_regime") or "").strip()
        if trend:
            lines.append(f"Current price trend: {trend}.")
            lines.append("")
        lines.append(
            "Detailed extracted financial metrics are not currently available in the canonical data for this ticker."
        )
        lines.append(
            "I can still help with a document-grounded summary, recent filings, or price context, but I should not state exact revenue, profit, or margin figures until those metrics are extracted or directly quoted from the documents."
        )
        return "\n".join(lines)

    def _build_grounded_deep_analysis_brief(
        self,
        *,
        ticker: str,
        message: str,
        local_payload: dict[str, Any],  # noqa: ARG002
    ) -> str:
        """Build a structured evidence brief directly from local_payload, bypassing the LLM."""
        lines: list[str] = []
        evidence_lines: list[str] = []

        # --- Qual context hits (deduped by file, path-cleaned) ---
        qual = local_payload.get("qual_context") or {}
        hits = [h for h in (qual.get("hits") or []) if isinstance(h, dict)]
        seen_files: dict[str, float] = {}
        unique_hits: list[dict[str, Any]] = []
        for hit in sorted(
            hits,
            key=lambda h: float(h.get("score") or h.get("final_score") or 0.0),
            reverse=True,
        ):
            file_key = str(hit.get("file") or hit.get("title") or "")
            score = float(hit.get("score") or hit.get("final_score") or 0.0)
            if file_key and file_key in seen_files:
                continue
            if file_key:
                seen_files[file_key] = score
            unique_hits.append(hit)
        for hit in unique_hits:
            score = float(hit.get("score") or hit.get("final_score") or 0.0)
            date = str(hit.get("published_at") or "")[:10]
            raw_file = str(hit.get("file") or "")
            title = str(hit.get("title") or "")
            # Clean absolute paths — use basename only.
            src_label = Path(raw_file).name if raw_file else title
            evidence_lines.append(
                f"- score {score:.3f} | {date} | {title or src_label} [source: {src_label}]"
            )

        # --- Doc snippets — signal extraction for liquidity/refinancing terms ---
        _SIGNAL_TERMS = re.compile(
            r"liquidity|refinanc|cash\s+runway|undrawn|debt\s+facilit|maturity|covenant",
            re.IGNORECASE,
        )
        snippets = [
            s for s in (local_payload.get("doc_snippets") or []) if isinstance(s, dict)
        ]
        signal_snippets: list[str] = []
        for snippet in snippets:
            excerpt = str(snippet.get("excerpt") or "")
            if _SIGNAL_TERMS.search(excerpt):
                src = str(snippet.get("title") or "document")
                excerpt_short = excerpt[:200]
                signal_snippets.append(f'- "{excerpt_short}" [source: {src}]')
        if signal_snippets:
            evidence_lines.append(
                "Signal extraction identified concrete liquidity/refinancing snippets:"
            )
            evidence_lines.extend(signal_snippets)

        # --- Data quality signals ---
        dq = local_payload.get("data_quality") or {}
        for failure in dq.get("recent_failures") or []:
            if isinstance(failure, dict):
                evidence_lines.append(
                    f"- Extraction failed for {failure.get('title', 'unknown')} [source: extraction_runs/documents]"
                )
        for row in dq.get("recent_low_conf_rows") or []:
            if isinstance(row, dict):
                conf = float(row.get("confidence_metrics") or 0.0)
                period = str(row.get("period_type") or "")
                period_end = str(row.get("period_end") or "")
                evidence_lines.append(
                    f"- Low-confidence financials: {period} {period_end} conf={conf:.2f} [source: asx_periodic_financials]"
                )

        # --- Price horizons ---
        for period, ph in (local_payload.get("price_horizons") or {}).items():
            if isinstance(ph, dict) and ph.get("ok"):
                tr = float(ph.get("total_return_pct") or 0.0)
                md = float(ph.get("max_drawdown_pct") or 0.0)
                vol = float(ph.get("volatility_ann_pct") or 0.0)
                evidence_lines.append(
                    f"- total_return={tr:.2f}% max_drawdown={md:.2f}% volatility={vol:.2f}% over {period} "
                    f"[source: price_horizon_{period}]"
                )

        # --- Web facts ---
        for fact in local_payload.get("web_facts") or []:
            if isinstance(fact, dict):
                claim = str(fact.get("claim") or "")
                url = str(fact.get("url") or "")
                evidence_lines.append(f"- Web fact: {claim} [source: {url}]")

        # Assemble structured brief.
        n_sources = len(evidence_lines)
        lines.append("Verdict:")
        lines.append(
            f"{ticker}: Grounded analysis based on {n_sources} evidence item(s) from local context."
        )
        lines.append("")
        lines.append("Evidence:")
        lines.extend(
            evidence_lines if evidence_lines else ["- No local evidence available."]
        )
        lines.append("")
        lines.append("Risks:")
        lines.append("- Dependent on availability and recency of evidence above.")
        lines.append("")
        lines.append("Counterpoints:")
        lines.append(
            "- Data coverage may be partial; full picture requires additional sources."
        )
        lines.append("")
        lines.append("Unknowns:")
        lines.append("- Items not yet disclosed or unavailable in local evidence.")

        return "\n".join(lines)
