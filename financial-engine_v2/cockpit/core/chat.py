from __future__ import annotations

import json
import logging
import os
import re
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse

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
    get_relevant_session_context,
    record_turn,
)
from cockpit.core.backend_proposals import (
    build_backend_access_proposal_request,
    build_backend_runtime_remediation_request,
)
from cockpit.core.sources import SourcesFormatter


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

                # Import extraction-state checker so HybridRouter can route
                # chat to the cloud API while GPU extraction is running.
                extraction_checker = None
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

    TICKER_STOPWORDS = {
        "A",
        "AN",
        "AND",
        "AS",
        "ASK",
        "ANALYSE",
        "ANALYZE",
        "ABOUT",
        "CANDLE",
        "CHART",
        "CHECK",
        "FOR",
        "FROM",
        "GIVE",
        "HAVE",
        "HI",
        "HOW",
        "I",
        "IN",
        "IS",
        "IT",
        "LATEST",
        "MANY",
        "ME",
        "MOST",
        "NEWS",
        "OF",
        "ON",
        "ONE",
        "SHOW",
        "PLEASE",
        "PLOT",
        "PRICE",
        "RECENT",
        "SUMMARISE",
        "SUMMARIZE",
        "TELL",
        "THAT",
        "THE",
        "THIS",
        "TO",
        "TODAY",
        "UPDATE",
        "WE",
        "WHAT",
        "WHATS",
        "WITH",
        "YOU",
        "YOUR",
        "DO",
        "DOES",
        "DID",
        "ANY",
        "ALL",
        "COUNT",
        "NUMBER",
        "ANNOUNCEMENT",
        "ANNOUNCEMENTS",
        # Market/exchange scope words — not company tickers.
        "ASX",
        # Common English words that happen to be 2-5 chars.
        "RUN",
        "SOME",
        "SURE",
        "OKAY",
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
        "INTO",
        "AFTER",
        "BEFORE",
        "COULD",
        "WOULD",
        "SHOULD",
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
        "LAST",
        "NEXT",
        "LONG",
        "BIG",
        "OLD",
        "NEW",
        "OWN",
        "OUR",
        # Pronouns used in follow-up questions — not tickers.
        "ITS",
        "THEY",
        "THEM",
        "THEIR",
        "SAME",
        "RIGHT",
        # Verbs and question words commonly seen in conversational messages.
        "WHY",
        "ARE",
        "WAS",
        "HAS",
        "HAD",
        "GOT",
        "GET",
        "LET",
        "SAY",
        "TRY",
        "WAY",
        "END",
        "WHO",
        "FAIL",
        "DONE",
        "WENT",
        "GOES",
        "GOING",
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

    @staticmethod
    def _extract_alpha_tokens(message: str) -> list[tuple[str, str]]:
        # Match ASX-style tickers: letter-started 2-5 alphanumeric chars (e.g. MP1, A200)
        # OR digit-started tickers that contain at least one letter (e.g. 29M, 4DS, 5GN).
        return [
            (m.group(0), m.group(0).upper())
            for m in re.finditer(
                r"\b(?:[A-Za-z][A-Za-z0-9]{1,4}|[0-9]+[A-Za-z][A-Za-z0-9]{0,3})\b",
                message,
            )
        ]

    def _detect_ticker(
        self, message: str, prior_ticker: str | None = None
    ) -> str | None:
        # Prefer explicit ticker-like mentions first, e.g. "$BHP", "ASX:BHP", or "BHP.AX" / "29M.AX".
        explicit = re.search(
            r"(?:\bASX:|\$)([A-Za-z]{2,5})\b|([A-Za-z0-9]{2,5})\.AX\b",
            message,
            re.IGNORECASE,
        )
        if explicit:
            token = (explicit.group(1) or explicit.group(2)).upper()
            if token not in self.TICKER_STOPWORDS:
                return token

        tokens = self._extract_alpha_tokens(message)
        if not tokens:
            return prior_ticker

        # Prefer explicit uppercase ticker-like tokens first.
        for original, upper in tokens:
            if original.isupper() and upper not in self.TICKER_STOPWORDS:
                return upper

        stripped = str(message or "").strip()
        whole_message_token = re.fullmatch(
            r"([A-Za-z0-9]{2,5})(?:\s+(?:1m|5m|15m|30m|1h|4h|1d|1w|1M))?",
            stripped,
            re.IGNORECASE,
        )
        if whole_message_token:
            token = whole_message_token.group(1).upper()
            if token not in self.TICKER_STOPWORDS:
                return token

        ticker_cue_patterns = (
            r"\b(?:about|on|for|vs|versus|compare|chart|price|financials?|announcements?|news|"
            r"analyse|analyze|analysis|ticker|stock|company|research|show|plot|candlestick|candle|"
            r"was|history)\s+{token}\b",
            r"\bprice\s+history\s+{token}\b",
            r"\b{token}\s+(?:vs|versus|chart|price|financials?|announcements?|news|on|between|"
            r"close|closing|summary|performance)\b",
        )
        for original, upper in tokens:
            if upper in self.TICKER_STOPWORDS:
                continue
            token_pattern = re.escape(original)
            if any(
                re.search(pattern.format(token=token_pattern), message, re.IGNORECASE)
                for pattern in ticker_cue_patterns
            ):
                return upper
        return prior_ticker

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

    def _is_global_news_request(self, message: str) -> bool:
        """Return True when the message targets market-wide news rather than a specific company."""
        return bool(self._GLOBAL_NEWS_RE.search(message))

    def _is_global_announcement_request(self, message: str) -> bool:
        """Return True when the message targets market-wide ASX announcements."""
        return bool(self._GLOBAL_ANNOUNCEMENT_RE.search(message))

    def _query_requires_document_grounding(self, message: str) -> bool:
        return bool(self._DOCUMENT_GROUNDING_RE.search(str(message or "")))

    @staticmethod
    def _orchestration_has_substantive_evidence(orchestration_result) -> bool:
        if orchestration_result is None:
            return False
        return bool(
            orchestration_result.financial_truth_results.get("items")
            or orchestration_result.financial_truth_results.get(
                "latest_financial_snapshot"
            )
            or orchestration_result.company_memory_results.get("items")
            or orchestration_result.market_memory_results.get("items")
        )

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
    _DIRECT_NEWS_RE = re.compile(
        r"^\s*(?:latest\s+)?(?:news(?:\s+for)?\s+(?P<prefix>[A-Za-z0-9]{2,5})|(?P<suffix>[A-Za-z0-9]{2,5})\s+news)\s*[?!.]*\s*$",
        re.IGNORECASE,
    )
    _DIRECT_FILESTATS_RE = re.compile(
        r"^\s*(?:(?P<ticker_prefix>[A-Za-z0-9]{1,10})\s+filestats?|filestats?\s+(?P<ticker_suffix>[A-Za-z0-9]{1,10}))\s*[?!.]*\s*$",
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
            return ChatResponse(
                text=f"I couldn't find recent indexed news for {ticker}.",
                evidence=[
                    {
                        "type": "news_search",
                        "details": {"ticker": ticker, "hits": []},
                    }
                ],
                mode=ResponseMode.FAST,
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
        args: dict[str, Any] = {"ticker": ticker, "years": 1, "process_documents": True}
        action_preview: dict[str, Any] = {
            "action_id": "update_ticker_financials",
            "args": args,
        }
        if self.action_registry:
            try:
                preview = self.action_registry.preview("update_ticker_financials", args)
                action_preview["command"] = preview.command
                action_preview["impact"] = preview.estimated_impact
                action_preview["timeout_seconds"] = preview.timeout_seconds
            except Exception:
                pass
        status = sync.get("status", "unknown")
        note = (
            f"Announcement sync check for {ticker}: {status}. "
            f"Use /confirm to update or /cancel to skip."
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
                    "", ticker=ticker, limit=100
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
        "/watch": _slash_watch,
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
    ) -> ChatResponse:
        """Run the agentic tool-calling loop and convert the result to a ChatResponse."""
        # Reuse existing ticker detection logic
        ticker, explicit_ticker = self._resolve_ticker_context(
            message, prior_ticker=prior_ticker
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
        prior_ov_turns = get_relevant_session_context(
            self._ov_session_id, message, limit=3
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
        augmented_message = message
        if ov_agent_block:
            augmented_message = ov_agent_block + "\n\n" + augmented_message
        if strategy_block:
            augmented_message = augmented_message + "\n\n" + strategy_block
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

        result: AgentResult = self._agent_loop.run(
            message=augmented_message,
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
            query=message,
            answer=result.text.strip(),
            ticker=ticker,
        )
        self._set_latest_sources_payloads(result.evidence)

        return ChatResponse(
            text=result.text.strip(),
            evidence=result.evidence,
            action_preview=result.action_preview,
            mode=result.mode,
            routing_metadata=result.routing_metadata,
            tool_traces=getattr(result, "tool_traces", None) or [],
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
        on_chunk=None,
        on_status=None,
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
                },
                "result": {
                    "intent": orchestration_result.intent,
                    "source_plan": list(orchestration_result.source_plan),
                    "entities": orchestration_result.entities,
                    "source_status": orchestration_result.answer.get("source_status")
                    or {},
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

        if on_status:
            on_status("Routing query through orchestrator")

        final_text = orchestration_result.answer_input
        if self._agent_loop is not None:
            conversation_history = self._recent_conversation_history()
            if on_status:
                on_status("Streaming final synthesis")
            if on_chunk is not None:
                final_text = self._agent_loop.synthesize_final_answer_stream(
                    evidence,
                    on_chunk,
                    question=message,
                    ticker=primary_ticker or ticker,
                    conversation_history=conversation_history,
                    draft_answer=orchestration_result.answer_input,
                    on_status=on_status,
                )
            else:
                final_text = self._agent_loop.synthesize_final_answer(
                    evidence,
                    question=message,
                    ticker=primary_ticker or ticker,
                    conversation_history=conversation_history,
                    draft_answer=orchestration_result.answer_input,
                    on_status=on_status,
                )
        elif on_chunk is not None and final_text:
            self._stream_plain_text(final_text, on_chunk)

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
    def _stream_plain_text(text: str, on_chunk) -> None:
        for index, token in enumerate(text.split()):
            suffix = " " if index < len(text.split()) - 1 else ""
            on_chunk(token + suffix)

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

        # --- Greeting short-circuit: don't invoke the full analyst pipeline ---
        if self._GREETING_RE.match(effective_message):
            greeting = (
                "Hey! I'm Tenn — your ASX research assistant. "
                'Ask me about a company (e.g. "tell me about CSL") or run an action from the panel.'
            )
            return ChatResponse(text=greeting, evidence=[], mode=ResponseMode.FAST)

        # --- Slash command dispatch: deterministic, no LLM needed ---
        if effective_message.strip().startswith("/"):
            cmd_response = self._handle_slash_command(effective_message.strip())
            if cmd_response is not None:
                return cmd_response

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

        msg_lower = effective_message.lower()

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

        # --- Conversational ingest shortcut: "ingest <ticker>" means ticker backfill ---
        ingest_ticker_match = re.fullmatch(
            r"\s*ingest\s+([A-Za-z]{2,5})\s*[?!.]*\s*", effective_message
        )
        if ingest_ticker_match:
            ingest_ticker = ingest_ticker_match.group(1).upper()
            if ingest_ticker in self.TICKER_STOPWORDS:
                ingest_ticker_match = None
        if ingest_ticker_match:
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
                            context={"prior_ticker": ticker},
                        )
                    )
                    has_orchestrated_evidence = (
                        self._orchestration_has_substantive_evidence(
                            orchestration_result
                        )
                    )
                    prefer_local_context = bool(ticker) and (
                        self._query_requires_document_grounding(effective_message)
                        or not has_orchestrated_evidence
                    )
                    if not prefer_local_context:
                        orchestrated_response = self._build_orchestrated_response(
                            orchestration_result=orchestration_result,
                            message=effective_message,
                            ticker=ticker,
                            on_chunk=on_chunk,
                            on_status=on_status,
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
                not prefer_local_context
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
                )

        # ------------------------------------------------------------------ #
        # Keyword router (legacy path — explicit opt-in or action fallthrough) #
        # ------------------------------------------------------------------ #

        if action_id:
            mode = ResponseMode.ACTION
        else:
            mode = self.classify_request(effective_message, enable_web=enable_web)

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

        # --- Web enrichment for deep mode or max-depth profile ---
        if (analysis_mode == "deep" or effective_profile == "max-depth") and enable_web:
            if hasattr(self.tool_router, "web_enrich"):
                web_query = (
                    f"{ticker}: {effective_message}" if ticker else effective_message
                )
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
        has_qual = bool(local_payload.get("qual_context"))

        if (
            ticker
            and mode not in {ResponseMode.ACTION, ResponseMode.WEB}
            and not has_docs
            and not has_financials
            and not has_qual
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

        # OpenViking: fetch semantically relevant prior turns for this query
        ov_context_block = ""
        prior_ov_turns = get_relevant_session_context(
            self._ov_session_id, effective_message, limit=3
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
            answer = self._build_grounded_overview_brief(
                ticker=ticker or str(local_payload.get("ticker") or ""),
                local_payload=local_payload,
            )

        self._record_answer_side_effects(query=message, answer=answer, ticker=ticker)
        self._set_latest_sources_payloads(evidence)

        return ChatResponse(
            text=answer.strip(), evidence=evidence, mode=mode, prompt=prompt_fallback
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
