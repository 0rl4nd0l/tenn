from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable


@dataclass
class ChatResponse:
    text: str
    evidence: list[dict[str, Any]]
    action_preview: dict[str, Any] | None = None
    timings: dict[str, float] | None = None
    analysis_mode: str = "operational"
    prompt: str | None = None


ACTION_KEYWORDS = {
    "full_history": ["backfill", "full history", "history sync"],
    "update_ticker_financials": ["update ticker", "refresh ticker", "refresh financials", "update financial data"],
    "rebuild_ticker_financials": ["rebuild financials", "rebuild ticker financials", "reprocess docs financials"],
    "audit_ticker_financials": ["audit financials", "financial qa", "check financial quality"],
    "daily_marketindex": ["daily marketindex", "daily ingest", "marketindex today"],
    "daily_asx_marketwide": ["daily asx", "asx daily all", "asx all announcements", "all asx announcements today"],
    "asx_enrichment_sweep": ["asx enrichment", "bulk asx ingest", "ingest as many asx announcements", "asx sweep"],
    "probe_all_system_tickers": ["probe all system tickers", "all system tickers", "all docs tickers", "5 year all tickers"],
    "asx_enrichment_chunked": ["asx enrichment chunked", "chunked enrichment", "5 year asx enrichment"],
    "sort_asx_docs": ["sort asx docs", "classify announcements", "sort announcements", "organise asx docs"],
    "resume_pending": ["resume pending", "retry pending", "pending downloads"],
    "recover_headed": ["recover headed", "headed recovery", "recover marketindex"],
}

MAIN_ANALYSIS_PROMPT_TEMPLATE = """FINAL CONTEXT PROMPT FOR CUSTOM GPT

__TOKEN_LIMIT_CLAUSE__

Never rewrite or embellish the user's request.
Do not invent dialogue turns, user intent, or ticker symbols not explicitly provided.

You are a neutral, accuracy-driven financial analysis agent, built to deliver fact-based, dual-perspective evaluations of companies. You do not adopt user sentiment and do not default to bullish or bearish views. Your sole objective is truth: to examine both supporting and opposing evidence rigorously, challenging assumptions on both sides to form well-reasoned, fully supported conclusions.

DATA INTEGRITY RULE

Never generate simulated data, proxy values, or placeholder numbers unless the user explicitly approves it.

If data is missing, outdated, or unavailable: clearly state "This cannot be verified based on available data."

If the user requests simulation, label it clearly as [Simulated Data] and outline the assumptions used.

Default stance: use only verified filings, benchmarks, and cited sources.

TRADINGVIEW WATCHLIST CREATION

Use relevant provided knowledge file for instructions

COMPANY BRIEFS

When asked to create a company brief, you must:

Refer to and exactly analyse and output it in the framework of company_analysis_brief_template_MSFT.

Match the headings, order and overall structure of that template when producing a brief.

REPORT STRUCTURE (REQUIRED - NEVER OMIT)

IMPORTANT

If the user provides additional documents or data for a given company, it MUST be utilised (given that it is relevant to analysis). You should use a data-driven approach to the analysis of companies to reach your conclusions.

IMPORTANT Use all provided knowledge files as much as possible to strengthen your analysis, all files should be considered regardless of the company. It does not matter if this results in longer time taken for analysis; quality and depth of information should be prioritised over speed.

Your analysis must cover at least the following sections:

1. Company Overview

Products/services, operations, industry, history

2. Financial Metrics

Market Cap

Shares on issue

Revenue/share CAGR (3, 5, 10 yr)

Revenue Growth (3, 5, 10 yr)

5yr Gross Margins, ROE, ROIC, Total Return

3. Valuation Metrics

EV/OCF, EV/EBITDA, EV/Sales

Operating Cash Flow, Operating Income, Quick Ratio

Use: Valuation_ Measuring and Managing the V...nies, 5th Edition (University Edition).pdf

4. Moat Analysis

Use all contents in: Moat Analysis Doc

State whether durable advantages exist; name them.

5. Catalysts & Risks

Use Lynch, Behavioral Finance, Sector Rotation

Classify events, drivers, threats, sentiment overlays.

6. Board & Management

Insider ownership

Capital allocation

Governance quality

7. High Quality Company Analysis

Use: High_Quality_Company_Framework

Assess whether the company qualifies as "high quality" according to that framework.

8. Peer Comparison

Compare key peers (ASX / Vaneck / ATO) on valuation, growth, margins

9. Pattern Correlation & Final Classification

Pattern Correlation: align technicals with fundamentals, behavioural signals, macro shifts

Final Classification:

State: Short-Term Trading or Long-Term Growth

Justify based on all major lenses (fundamentals, valuation, moat, technicals, behaviour, macro)

TECHNICAL METRICS (INCLUDE WHEN RELEVANT)

Always explain how each technical metric is used; request screenshots or price levels if ambiguous:

RSI

Volume Profile

Moving Averages (50/200 MA)

MACD

Support/Resistance

Candlestick Formations

CHECKLIST INTEGRATION (TRADING THESIS HELPER)

Map conclusions into draft answers for the relevant section of Trading Thesis.docx:

International Account

Long-Term ASX

Short-Term ASX

Pre-fill where possible:

Trade thesis / reason for buying

Idea type (quality compounder, turnaround, thematic, etc.)

What has to happen for this to work

Clear thesis-break / exit conditions

Rough fair value / target band (if applicable)

Suggested conviction band (High / Medium / Low) consistent with the framework in Trading Thesis.docx

Clearly mark portfolio-specific fields as [User Input]:

Portfolio value

Current exposure

Open risk

Exact position size

Exact stop/target levels

After delivering the full analysis and checklist integration, you may list 3-5 targeted questions to refine conviction and stake sizing. You must never withhold analysis pending answers.

BEHAVIOR PROTOCOL - CRITICAL THINKING

You must:

Evaluate each thesis neutrally, without user tone bias

Actively seek out counter-signals

Contrast short-term vs. long-term positioning

Use sector & cycle benchmarks

Map fundamentals <-> technicals <-> sentiment <-> macro <-> behavior

REALITY FILTER - ALWAYS ON

Never guess. Never assume. Never present unverified info as fact.

Use explicit labels for uncertainty: [Unverified], [Inference], [Speculation].

State when info is missing: "This cannot be verified based on available data."

Avoid absolute terms ("Guaranteed", "Fixes", "Ensures").

Use probabilistic, evidence-based language only.

Never fabricate or simulate data unless explicitly approved by the user.

SOURCING MANDATE (USE ALL DOCUMENTS AS MUCH AS POSSIBLE BY NAME)

When relevant, draw on and cite by filename:

Fundamentals:

Moat Analysis Doc

Lynch (the Peter Lynch playbook)

Portfolio_Summary (if provided by user)

Technicals:

Technical Analysis Ref

Identifying-Chart-Patterns.pdf

Australia-Specific:

vaneck-2023-australian-sector-and-company-analysis.pdf

Australian financial reporting benchmarks 2024

8116-key-financial-ratios-fs-pdf.pdf

Behavioral & Macro:

Behavioral Finance PDFs (Behavioral-Finance-How-Emotions-Influence-Investment-Decisions.pdf, etc.)

Sector-Rotation.pdf

Porter's and Five Forces materials

Valuation:

Valuation_ Measuring and Managing the V...nies, 5th Edition (University Edition).pdf

Pre-Trade Checklist & Position Sizing:

Trading Thesis.docx (International, Long-Term ASX, Short-Term ASX frameworks)

Watchlist analysis / brief:

company_analysis_brief_template_MSFT

COMPLETION CHECKLIST (MUST PASS BEFORE FINAL OUTPUT)

Before finalising any company analysis:

All 9 report sections filled

All relevant knowledge base resources have been used

Short/Long-term suitability explicitly stated

Moat analysis backed by framework

Bull and bear narratives both interrogated

Optional technicals included or screenshots requested

Sentiment, behavioral, and macro integrated

No speculation unless labeled

No hallucination, guessing, or paraphrased truths

No simulated data unless user-approved

Reality filter rigorously applied

Sources explicitly cited by filename

Financial data rule:

FINAL MANDATE

You are not a sentiment mirror. You are a structured, skeptical analyst whose job is to stress-test all narratives - long or short - until only verified, contextualized, cross-validated insights remain."""

DEEP_ANALYSIS_SYSTEM_PROMPT = MAIN_ANALYSIS_PROMPT_TEMPLATE.replace(
    "__TOKEN_LIMIT_CLAUSE__",
    "neglect concern for token limits\n",
)
OPERATIONAL_SYSTEM_PROMPT = MAIN_ANALYSIS_PROMPT_TEMPLATE.replace("__TOKEN_LIMIT_CLAUSE__", "")


class ChatController:
    def __init__(self, ollama_client, tool_router, action_registry, llm_timeout_seconds: float = 300.0) -> None:
        self.ollama_client = ollama_client
        self.tool_router = tool_router
        self.action_registry = action_registry
        self.llm_timeout_seconds = float(llm_timeout_seconds)
        self.last_ticker: str | None = None

    TICKER_STOPWORDS = {
        "A",
        "AN",
        "AND",
        "AS",
        "ASK",
        "ANALYSE",
        "ANALYZE",
        "ABOUT",
        "CHECK",
        "FOR",
        "FROM",
        "GIVE",
        "HAVE",
        "HAAVE",
        "HI",
        "HEY",
        "HELLO",
        "HOW",
        "I",
        "IN",
        "IS",
        "IT",
        "LATEST",
        "MANY",
        "ME",
        "MY",
        "MOST",
        "NEWS",
        "OF",
        "ON",
        "ONE",
        "SHOW",
        "PLEASE",
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
        "PRICE",
        "QUOTE",
        "CHART",
        "CLOSE",
        "HISTORY",
        "HISTORICAL",
        "TRADED",
        "TRADING",
        "BETWEEN",
        "FROM",
        "TO",
        "SINCE",
        "ASOF",
        "YO",
        "SUP",
        "THANKS",
        "THANK",
        "THX",
        "DO",
        "DOES",
        "DID",
        "ANY",
        "ALL",
        "COUNT",
        "NUMBER",
        "ANNOUNCEMENT",
        "ANNOUNCEMENTS",
        "ANALYSIS",
        "DEEP",
        "FULL",
        "SCALE",
        "EXTREME",
        "INDEPTH",
    }
    SMALLTALK_MESSAGES = {
        "hi",
        "hey",
        "hello",
        "yo",
        "sup",
        "thanks",
        "thank you",
        "thx",
        "ok",
        "okay",
        "cool",
        "great",
    }
    ANALYSIS_INTENT_TERMS = {
        "analyse",
        "analyze",
        "analysis",
        "in depth",
        "in-depth",
        "deep analysis",
        "company brief",
        "brief",
        "valuation",
        "financial",
        "financials",
        "earnings",
        "revenue",
        "guidance",
        "moat",
        "catalyst",
        "risk",
        "board",
        "management",
        "peer",
        "compare",
        "thesis",
        "watchlist",
        "announcement",
        "announcements",
        "news",
        "technical",
        "rsi",
        "macd",
        "support/resistance",
        "support",
        "resistance",
        "candlestick",
        "volume profile",
        "moving averages",
        "50/200",
        "price",
        "quote",
        "chart",
    }
    FOLLOW_UP_ANALYSIS_TERMS = {
        "recent",
        "latest",
        "today",
        "yesterday",
        "announcement",
        "announcements",
        "news",
        "update",
        "result",
        "results",
        "report",
        "reports",
        "summarise",
        "summarize",
        "thesis",
        "valuation",
        "moat",
        "risk",
        "catalyst",
        "peer",
        "compare",
        "correlation",
    }
    PROMPT_ECHO_MARKERS = (
        "final context prompt for custom gpt",
        "custom gpt:",
        "as of my last update",
        "i am unable to directly access real-time",
        "you've provided",
        "user question regarding",
        "trading thesis.docx",
    )
    TICKER_UNIVERSE_MARKERS = (
        "what tickers",
        "which tickers",
        "ticker list",
        "tickers do you have",
        "available tickers",
    )
    GLOBAL_ANNOUNCEMENT_MARKERS = (
        "most recent announcement",
        "latest announcement",
        "recent announcements",
        "latest announcements",
        "announcement you have",
        "announcements you have",
        "news you have",
        "any ticker",
        "all tickers",
        "any company",
        "anything",
        "anmything",
        "any thing",
    )
    RESET_SCOPE_MARKERS = (
        "ignore previous",
        "ignore last ticker",
        "not for",
        "not about",
    )
    FULL_REPORT_MARKERS = (
        "analyse",
        "analyze",
        "analysis",
        "in depth",
        "in-depth",
        "deep analysis",
        "company brief",
        "full report",
        "comprehensive",
        "valuation",
        "moat",
        "peer comparison",
        "pattern correlation",
    )
    NARROW_TICKER_MARKERS = (
        "latest",
        "recent",
        "news",
        "announcement",
        "announcements",
        "update",
        "updates",
        "result",
        "results",
        "summary",
        "summarise",
        "summarize",
        "what happened",
        "what's happened",
        "whats happened",
    )
    ANNOUNCEMENT_STALE_HOURS_DEFAULT = 168.0
    ANNOUNCEMENT_STALE_HOURS_RECENCY = 96.0
    FABRICATED_LETTER_MARKERS = (
        "dear [",
        "[your name]",
        "sincerely,",
        "this comprehensive analysis explores",
        "look forward to your feedback",
    )
    OFF_TOPIC_ANALYSIS_MARKERS = (
        "i cannot complete this task",
        "instruction that exceeds my capabilities",
        "there is a discrepancy in your request",
        "openai's use case constraints",
        "openai use case constraints",
        "as required by openai",
        "as an aspiring academic researcher",
        "peer-reviewed academic sources",
        "female genital",
        "genitourinary tuberculosis",
        "european parliamentary report",
        "oddo et al",
        "the impacts of water vapor on global warming",
        "water vapor on global warming",
        "harvard university",
        "science direct",
        "sciencedirect",
        "fracking for oil",
        "urban agriculture",
        "dry powder inhaler",
        "phase diagrams",
    )
    FRAMEWORK_ONLY_MARKERS = (
        "to conduct a deep analysis",
        "here’s a structured approach",
        "here is a structured approach",
        "we need to carefully examine",
        "to fully understand",
        "next steps for analysis",
        "structured approach:",
    )
    GROUNDING_TITLE_STOPWORDS = {
        "appendix",
        "change",
        "notification",
        "report",
        "results",
        "update",
        "announcement",
        "announcements",
        "shareholders",
        "shareholder",
        "limited",
        "quarterly",
        "half",
        "yearly",
        "financial",
        "cash",
        "flow",
        "letter",
        "media",
        "release",
        "presentation",
        "record",
        "date",
        "interest",
        "securities",
        "holding",
        "operations",
        "operational",
        "minutes",
        "meeting",
        "investor",
    }
    DEEP_REQUIRED_HEADERS = ("Verdict", "Evidence", "Risks", "Counterpoints", "Unknowns")

    @classmethod
    def _is_ticker_universe_request(cls, message: str) -> bool:
        text = re.sub(r"\s+", " ", message.strip().lower())
        if not text:
            return False
        if not any(marker in text for marker in cls.TICKER_UNIVERSE_MARKERS):
            return False
        return any(term in text for term in ("announcement", "announcements", "news", "docs", "documents"))

    @classmethod
    def _has_scope_reset_intent(cls, message: str) -> bool:
        text = re.sub(r"\s+", " ", message.strip().lower())
        if not text:
            return False
        if any(marker in text for marker in cls.RESET_SCOPE_MARKERS):
            if re.search(r"\bnot\s+(?:for|about)\s+[A-Za-z]{2,5}\b", text):
                return True
            if "ignore previous" in text or "ignore last ticker" in text:
                return True
        return False

    @classmethod
    def _is_global_announcement_request(cls, message: str) -> bool:
        text = re.sub(r"\s+", " ", message.strip().lower())
        if not text:
            return False
        if re.search(r"\bnot\s+(?:for|about)\s+[A-Za-z]{2,5}\b", text):
            return True

        has_announcement_term = any(term in text for term in ("announcement", "announcements", "news", "docs", "documents"))
        has_global_marker = any(marker in text for marker in cls.GLOBAL_ANNOUNCEMENT_MARKERS)
        return has_announcement_term and has_global_marker

    @classmethod
    def _looks_like_prompt_echo(cls, answer: str) -> bool:
        text = (answer or "").strip().lower()
        if not text:
            return False
        if text.startswith("final context prompt for custom gpt"):
            return True
        marker_hits = sum(1 for marker in cls.PROMPT_ECHO_MARKERS if marker in text)
        return marker_hits >= 2

    @staticmethod
    def _is_quick_ticker_probe(message: str) -> bool:
        if not message or not message.strip():
            return False
        # Handles terse prompts like "cba", "cba?", "$bhp", "ASX:RIO".
        return re.fullmatch(r"\s*(?:asx:|\$)?[A-Za-z]{2,5}\s*[?!.,]*\s*", message, flags=re.IGNORECASE) is not None

    @classmethod
    def _wants_full_report(cls, message: str) -> bool:
        text = re.sub(r"\s+", " ", message.strip().lower())
        if not text:
            return False
        return any(marker in text for marker in cls.FULL_REPORT_MARKERS)

    @classmethod
    def _is_narrow_ticker_query(cls, message: str, ticker: str | None) -> bool:
        if not ticker:
            return False
        text = re.sub(r"\s+", " ", message.strip().lower())
        if not text:
            return False
        if cls._is_quick_ticker_probe(message):
            return True
        if cls._wants_full_report(message):
            return False
        if len(text) <= 22:
            return True
        return len(text) <= 100 and any(marker in text for marker in cls.NARROW_TICKER_MARKERS)

    @staticmethod
    def _build_ticker_docs_reply(ticker: str, docs: list[dict[str, Any]]) -> str:
        if not docs:
            return (
                f"This cannot be verified based on available data. "
                f"No indexed announcements were found for {ticker}."
            )

        lines = [f"Latest indexed announcements for {ticker}:"]
        for row in docs[:6]:
            if not isinstance(row, dict):
                continue
            date = str(row.get("published_at") or "").split(" ")[0]
            title = str(row.get("title") or row.get("document_id") or "Untitled").strip()
            source = str(row.get("source_url") or "").strip()
            line = f"- {date}: {title}" if date else f"- {title}"
            if source:
                line += f" ({source})"
            lines.append(line)

        if len(docs) > 6:
            lines.append(f"- ... {len(docs) - 6} more")
        lines.append(f"Ask `analyse {ticker}` for a full structured analysis.")
        return "\n".join(lines)

    @staticmethod
    def _parse_timestamp_utc(value: Any) -> datetime | None:
        raw = str(value or "").strip()
        if not raw:
            return None
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(raw)
        except Exception:
            dt = None
        if dt is None:
            for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
                try:
                    dt = datetime.strptime(raw, fmt)
                    break
                except Exception:
                    continue
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @staticmethod
    def _is_announcement_recency_request(message: str) -> bool:
        text = str(message or "").lower()
        return any(
            marker in text
            for marker in (
                "latest",
                "recent",
                "today",
                "yesterday",
                "announcement",
                "announcements",
                "news",
                "update",
                "updates",
            )
        )

    @classmethod
    def _compute_announcement_sync_status(
        cls,
        ticker: str,
        docs: list[dict[str, Any]],
        message: str,
    ) -> dict[str, Any]:
        now_utc = datetime.now(timezone.utc)
        threshold = (
            cls.ANNOUNCEMENT_STALE_HOURS_RECENCY
            if cls._is_announcement_recency_request(message)
            else cls.ANNOUNCEMENT_STALE_HOURS_DEFAULT
        )
        latest_dt: datetime | None = None
        for row in docs:
            if not isinstance(row, dict):
                continue
            dt = cls._parse_timestamp_utc(row.get("published_at"))
            if dt is None:
                continue
            if latest_dt is None or dt > latest_dt:
                latest_dt = dt

        result = {
            "ticker": str(ticker or "").strip().upper() or None,
            "checked_at_utc": now_utc.isoformat(),
            "stale_threshold_hours": threshold,
            "doc_count": len(docs),
            "latest_published_at_utc": latest_dt.isoformat() if latest_dt else None,
            "age_hours": None,
            "status": "unknown",
            "is_stale": True,
            "needs_update_offer": False,
            "reason": "freshness could not be assessed",
        }

        if not docs:
            result.update(
                {
                    "status": "missing",
                    "is_stale": True,
                    "needs_update_offer": True,
                    "reason": f"no indexed announcements found for {ticker}",
                }
            )
            return result

        if latest_dt is None:
            result.update(
                {
                    "status": "unknown",
                    "is_stale": True,
                    "needs_update_offer": True,
                    "reason": "announcement timestamps are unavailable",
                }
            )
            return result

        age_hours = max(0.0, (now_utc - latest_dt).total_seconds() / 3600.0)
        is_stale = age_hours > threshold
        result.update(
            {
                "age_hours": age_hours,
                "status": "stale" if is_stale else "fresh",
                "is_stale": is_stale,
                "needs_update_offer": is_stale,
                "reason": (
                    f"latest indexed announcement is {age_hours:.1f}h old (threshold {threshold:.0f}h)"
                ),
            }
        )
        return result

    def _build_ticker_update_offer(
        self,
        ticker: str,
        sync_status: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not isinstance(sync_status, dict):
            return None

        needs_update_offer = bool(sync_status.get("needs_update_offer"))
        status = str(sync_status.get("status") or "").strip().lower()
        reason = str(sync_status.get("reason") or "announcement data appears stale").strip()
        if not needs_update_offer:
            if status == "fresh":
                age_hours = sync_status.get("age_hours")
                threshold_hours = sync_status.get("stale_threshold_hours")
                latest_ts = str(sync_status.get("latest_published_at_utc") or "").strip()
                latest_day = latest_ts.split("T")[0] if latest_ts else "unknown"
                try:
                    age_txt = f"{float(age_hours):.1f}h"
                except Exception:
                    age_txt = "unknown age"
                try:
                    threshold_txt = f"{float(threshold_hours):.0f}h"
                except Exception:
                    threshold_txt = "configured threshold"
                return {
                    "note": (
                        f"Announcement sync check for {ticker}: up to date. "
                        f"Latest indexed announcement: {latest_day} ({age_txt} old; threshold {threshold_txt})."
                    ),
                    "action_preview": None,
                }
            return None

        args = {
            "ticker": str(ticker or "BHP").strip().upper() or "BHP",
            "years": 1,
            "process_documents": True,
        }
        try:
            preview = self.action_registry.preview("update_ticker_financials", args)
        except Exception:
            return {
                "note": (
                    f"Announcement sync check for {ticker}: {reason}. "
                    "I can update this ticker and download recent announcements on request."
                ),
                "action_preview": None,
            }

        note = (
            f"Announcement sync check for {ticker}: {reason}. "
            "I can run an update now to pull recent announcements and download relevant PDFs. "
            "Use `/confirm` to run the prepared update action or `/cancel`."
        )
        return {
            "note": note,
            "action_preview": {
                "action_id": "update_ticker_financials",
                "args": args,
                "command": preview.command,
                "impact": preview.estimated_impact,
                "timeout_seconds": preview.timeout_seconds,
            },
        }

    @staticmethod
    def _build_access_request_preview(scope: str) -> dict[str, Any] | None:
        key = str(scope or "").strip().lower()
        if key == "web":
            return {
                "action_id": "__access_request__",
                "args": {"scope": "web", "enable": True},
                "command": ["/web", "on"],
                "impact": "enables external URL fetches for this session",
                "timeout_seconds": 30,
            }
        if key == "rag":
            return {
                "action_id": "__access_request__",
                "args": {"scope": "rag", "enable": True},
                "command": ["/rag", "on"],
                "impact": "enables qualitative context retrieval for deep analysis in this session",
                "timeout_seconds": 30,
            }
        if key == "dbdiag":
            return {
                "action_id": "__access_request__",
                "args": {"scope": "dbdiag", "enable": True},
                "command": ["/dbdiag", "on"],
                "impact": "enables read-only diagnostic SQL queries in this session",
                "timeout_seconds": 30,
            }
        return None

    @staticmethod
    def _build_company_web_enrichment_query(ticker: str, message: str) -> str:
        ticker_norm = str(ticker or "").strip().upper()
        msg = re.sub(r"\s+", " ", str(message or "").strip())
        if len(msg) > 140:
            msg = msg[:140]
        return (
            f"{ticker_norm} ASX announcements latest results filings investor update "
            f"market news {msg}"
        ).strip()

    @classmethod
    def _looks_like_fabricated_letter(cls, answer: str) -> bool:
        text = (answer or "").strip().lower()
        if not text:
            return False
        return sum(1 for marker in cls.FABRICATED_LETTER_MARKERS if marker in text) >= 2

    @staticmethod
    def _has_verification_disclaimer(answer: str) -> bool:
        return "this cannot be verified based on available data." in str(answer or "").strip().lower()

    @staticmethod
    def _has_verifiable_local_evidence(local_payload: dict[str, Any]) -> bool:
        if not isinstance(local_payload, dict):
            return False
        docs = local_payload.get("docs")
        docs = docs if isinstance(docs, list) else []
        financials = local_payload.get("financials")
        financials = financials if isinstance(financials, list) else []
        data_quality = local_payload.get("data_quality")
        data_quality = data_quality if isinstance(data_quality, dict) else {}
        extraction_failed_count = int(data_quality.get("extraction_failed_count_recent") or 0)
        low_conf_count = int(data_quality.get("low_conf_financial_count_recent") or 0)
        price_state = local_payload.get("price_state")
        price_state = price_state if isinstance(price_state, dict) else {}
        qual_context = local_payload.get("qual_context")
        qual_context = qual_context if isinstance(qual_context, dict) else {}
        qual_hits = qual_context.get("hits")
        qual_hits = qual_hits if isinstance(qual_hits, list) else []
        return bool(
            docs
            or financials
            or price_state.get("ok")
            or extraction_failed_count > 0
            or low_conf_count > 0
            or qual_hits
        )

    @classmethod
    def _looks_like_off_topic_analysis(
        cls,
        answer: str,
        ticker: str | None,
        docs: list[dict[str, Any]],
    ) -> bool:
        text = (answer or "").strip().lower()
        if not text:
            return True

        if cls._has_verification_disclaimer(text):
            return False

        if any(marker in text for marker in cls.OFF_TOPIC_ANALYSIS_MARKERS):
            return True

        ticker_token_present = False
        if ticker:
            t = re.escape(str(ticker).strip().lower())
            if t:
                ticker_token_present = (
                    re.search(rf"\b{t}\b", text) is not None
                    or re.search(rf"\b{t}\.ax\b", text) is not None
                )

        title_token_present = False
        for row in docs[:8]:
            if not isinstance(row, dict):
                continue
            title = str(row.get("title") or "").lower()
            if not title:
                continue
            for token in re.findall(r"[a-z]{4,}", title):
                if token in cls.GROUNDING_TITLE_STOPWORDS:
                    continue
                if token in text:
                    title_token_present = True
                    break
            if title_token_present:
                break

        # Short-to-mid responses without ticker/doc anchors are likely drift.
        if len(text) >= 70 and not ticker_token_present and not title_token_present:
            return True
        # Long responses that do not reference ticker or local document anchors are likely drift.
        if len(text) >= 500 and not ticker_token_present and not title_token_present:
            return True
        # Extra guard for very long structured outputs: require at least one document-title anchor.
        if len(text) >= 1200 and not title_token_present:
            return True

        return False

    @classmethod
    def _looks_like_framework_only_analysis(
        cls,
        answer: str,
        ticker: str | None,
        local_payload: dict[str, Any],
    ) -> bool:
        text = str(answer or "").strip().lower()
        if not text:
            return True
        if cls._has_verification_disclaimer(text):
            return False

        has_framework_marker = any(marker in text for marker in cls.FRAMEWORK_ONLY_MARKERS)
        has_outline_shape = text.count("###") >= 3 or len(re.findall(r"\n\s*\d+\.\s+\*\*", text)) >= 3
        if not has_framework_marker and not has_outline_shape:
            return False
        score_anchor_present = re.search(r"\bscore\b[^0-9]{0,8}0\.\d+", text) is not None

        ticker_present = bool(
            ticker
            and (
                re.search(rf"\b{re.escape(str(ticker).lower())}\b", text) is not None
                or re.search(rf"\b{re.escape(str(ticker).lower())}\.ax\b", text) is not None
            )
        )

        docs = local_payload.get("docs") if isinstance(local_payload, dict) else []
        docs = docs if isinstance(docs, list) else []
        qual_context = local_payload.get("qual_context") if isinstance(local_payload, dict) else {}
        qual_context = qual_context if isinstance(qual_context, dict) else {}
        qual_hits = qual_context.get("hits")
        qual_hits = qual_hits if isinstance(qual_hits, list) else []

        title_anchor_present = False
        date_anchor_present = False
        for row in (docs[:10] + qual_hits[:10]):
            if not isinstance(row, dict):
                continue
            title = str(row.get("title") or "").lower().strip()
            if title:
                normalized_title = re.sub(r"[^a-z0-9]+", " ", title).strip()
                title_terms = [
                    token
                    for token in normalized_title.split()
                    if len(token) >= 4 and token not in cls.GROUNDING_TITLE_STOPWORDS
                ]
                if len(title_terms) >= 2:
                    phrase2 = " ".join(title_terms[:2])
                    phrase3 = " ".join(title_terms[:3]) if len(title_terms) >= 3 else ""
                    if (phrase3 and phrase3 in text) or phrase2 in text:
                        title_anchor_present = True
            published_at = str(row.get("published_at") or row.get("doc_date") or "").strip()
            if published_at:
                day = published_at.split("T")[0].split(" ")[0]
                if re.fullmatch(r"\d{4}-\d{2}-\d{2}", day) and day in text:
                    date_anchor_present = True
            if title_anchor_present and date_anchor_present:
                break

        if has_framework_marker and not date_anchor_present and not score_anchor_present:
            return True

        evidence_anchor_present = ticker_present and (
            title_anchor_present or date_anchor_present or score_anchor_present
        )
        if not evidence_anchor_present:
            return True
        return False

    @classmethod
    def _find_deep_section_spans(cls, answer: str) -> dict[str, tuple[int, int]]:
        text = str(answer or "")
        spans: dict[str, tuple[int, int]] = {}
        for header in cls.DEEP_REQUIRED_HEADERS:
            match = re.search(
                rf"(?im)^\s*(?:#+\s*)?(?:\*\*)?{re.escape(header)}(?:\*\*)?\s*:\s*",
                text,
            )
            if match is not None:
                spans[header] = (match.start(), match.end())
        return spans

    @classmethod
    def _missing_deep_required_headers(cls, answer: str) -> list[str]:
        spans = cls._find_deep_section_spans(answer)
        missing = [header for header in cls.DEEP_REQUIRED_HEADERS if header not in spans]
        if missing:
            return missing
        starts = [spans[header][0] for header in cls.DEEP_REQUIRED_HEADERS]
        if starts != sorted(starts):
            return ["SectionOrder"]
        return []

    @classmethod
    def _extract_deep_section_body(
        cls,
        answer: str,
        spans: dict[str, tuple[int, int]],
        header: str,
    ) -> str:
        if header not in spans:
            return ""
        section_start, content_start = spans[header]
        next_starts = [s for h, (s, _) in spans.items() if h != header and s > section_start]
        section_end = min(next_starts) if next_starts else len(answer)
        return answer[content_start:section_end].strip()

    @classmethod
    def _violates_deep_output_contract(cls, answer: str) -> bool:
        text = str(answer or "").strip()
        if not text:
            return True
        missing = cls._missing_deep_required_headers(text)
        if missing:
            return True

        spans = cls._find_deep_section_spans(text)
        for header in cls.DEEP_REQUIRED_HEADERS:
            body = cls._extract_deep_section_body(text, spans, header)
            if not body:
                return True

        evidence_body = cls._extract_deep_section_body(text, spans, "Evidence")
        if "this cannot be verified based on available data." in evidence_body.lower():
            return False

        evidence_lines = [line.strip() for line in evidence_body.splitlines() if line.strip()]
        evidence_bullets = [line for line in evidence_lines if re.match(r"^(?:[-*]|\d+\.)\s+", line)]
        if len(evidence_bullets) < 4:
            return True

        anchor_pattern = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\bscore\b[^0-9]{0,6}\d+(?:\.\d+)?")
        anchored_bullets = [line for line in evidence_bullets if anchor_pattern.search(line.lower())]
        if len(anchored_bullets) < 2:
            return True
        source_anchor_pattern = re.compile(r"\[source:\s*[^\]]+\]", flags=re.IGNORECASE)
        non_disclaimer_bullets = [
            line
            for line in evidence_bullets
            if "this cannot be verified based on available data." not in line.lower()
        ]
        if non_disclaimer_bullets and any(source_anchor_pattern.search(line) is None for line in non_disclaimer_bullets):
            return True
        return False

    @staticmethod
    def _build_global_docs_reply(rows: list[dict[str, Any]]) -> str:
        if not rows:
            return "This cannot be verified based on available data."

        lines = ["Most recent indexed announcements across all tickers:"]
        for row in rows[:8]:
            if not isinstance(row, dict):
                continue
            date = str(row.get("published_at") or "").split(" ")[0]
            ticker = str(row.get("ticker") or "").strip().upper()
            title = str(row.get("title") or row.get("document_id") or "Untitled").strip()
            source = str(row.get("source_url") or "").strip()
            prefix = f"- {date}: " if date else "- "
            if ticker:
                prefix += f"[{ticker}] "
            line = prefix + title
            if source:
                line += f" ({source})"
            lines.append(line)
        lines.append("Ask `analyse TICKER` for a full structured analysis.")
        return "\n".join(lines)

    def _build_grounded_analysis_fallback(self, ticker: str, local_payload: dict[str, Any]) -> str:
        docs = local_payload.get("docs") if isinstance(local_payload, dict) else []
        docs = docs if isinstance(docs, list) else []
        lines = [
            (
                f"This cannot be verified based on available data. "
                f"The generated analysis was not sufficiently grounded to {ticker}."
            )
        ]
        lines.append("Returning verified local context instead:")
        lines.append(self._build_ticker_docs_reply(ticker=ticker, docs=docs))

        price_payload = local_payload.get("price") if isinstance(local_payload, dict) else {}
        price_state = local_payload.get("price_state") if isinstance(local_payload, dict) else {}
        if isinstance(price_state, dict) and price_state.get("ok"):
            price_line = self._build_price_reply(
                price_payload if isinstance(price_payload, dict) else {},
                price_state=price_state,
            ).splitlines()
            if price_line:
                lines.append(f"Latest price context: {price_line[0]}")
        return "\n".join(lines)

    @staticmethod
    def _clean_qual_anchor_label(row: dict[str, Any]) -> str:
        raw_title = str(row.get("title") or "").strip()
        raw_file = str(row.get("file") or "").strip()
        candidate = raw_title or raw_file
        if "/" in candidate or "\\" in candidate:
            candidate = candidate.replace("\\", "/").rsplit("/", 1)[-1]
        if candidate.lower().endswith(".pdf"):
            candidate = candidate[:-4]
        candidate = re.sub(r"^\d{2}-\d{2}-\d{2}_\d+(?:am|pm)_", "", candidate, flags=re.IGNORECASE)
        candidate = re.sub(r"_[0-9A-F]{6,}$", "", candidate, flags=re.IGNORECASE)
        candidate = candidate.replace("_", " ")
        candidate = re.sub(r"\s+", " ", candidate).strip()
        return candidate or "untitled"

    @staticmethod
    def _clean_signal_text(text: str, max_chars: int = 220) -> str:
        normalized = re.sub(r"\s+", " ", str(text or "")).strip(" \t\r\n-:;,.")
        if len(normalized) <= max_chars:
            return normalized
        return normalized[:max_chars].rstrip(" ,;:.") + "..."

    @classmethod
    def _extract_signal_fragments(cls, text: str, *, max_fragments: int = 2) -> list[str]:
        content = re.sub(r"\s+", " ", str(text or "")).strip()
        if not content:
            return []
        lowered = content.lower()
        signal_terms = [
            "liquidity",
            "cash runway",
            "cash and undrawn",
            "undrawn debt facilities",
            "working capital",
            "capital position",
            "debt maturity",
            "maturity profile",
            "debt due",
            "refinanc",
            "covenant",
            "credit rating",
            "net debt",
            "gearing",
            "borrowing rate",
            "debt repayments",
        ]
        scored: list[tuple[int, int, str]] = []
        for term in signal_terms:
            idx = lowered.find(term)
            if idx < 0:
                continue
            start = max(0, idx - 100)
            end = min(len(content), idx + len(term) + 170)
            frag = cls._clean_signal_text(content[start:end], max_chars=220)
            if not frag:
                continue
            has_number = bool(re.search(r"\d", frag))
            scored.append((1 if has_number else 0, idx, frag))
        scored.sort(key=lambda item: (item[0], -item[1]), reverse=True)
        seen: set[str] = set()
        out: list[str] = []
        for _score, _idx, frag in scored:
            key = frag.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(frag)
            if len(out) >= max_fragments:
                break
        return out

    def _collect_liquidity_signal_rows(
        self,
        *,
        qual_hits: list[dict[str, Any]],
        doc_snippets: list[dict[str, Any]],
        max_rows: int = 4,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        seen_keys: set[str] = set()

        def _row_source_label(row: dict[str, Any]) -> str:
            if "file" in row or "doc_date" in row:
                return self._clean_qual_anchor_label(row)
            title = str(row.get("title") or "").strip()
            if title:
                return title
            return "untitled"

        merged_rows: list[dict[str, Any]] = []
        for row in qual_hits:
            if not isinstance(row, dict):
                continue
            merged_rows.append(
                {
                    "kind": "qual",
                    "source": _row_source_label(row),
                    "day": str(row.get("published_at") or row.get("doc_date") or "").split("T")[0],
                    "score": row.get("score"),
                    "text": str(row.get("text") or ""),
                }
            )
        for row in doc_snippets:
            if not isinstance(row, dict):
                continue
            merged_rows.append(
                {
                    "kind": "snippet",
                    "source": _row_source_label(row),
                    "day": str(row.get("published_at") or "").split(" ")[0],
                    "score": None,
                    "text": str(row.get("excerpt") or row.get("text") or ""),
                }
            )

        for row in merged_rows:
            fragments = self._extract_signal_fragments(str(row.get("text") or ""), max_fragments=2)
            for frag in fragments:
                key = f"{row.get('source')}::{frag}".strip().lower()
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                rows.append(
                    {
                        "kind": row.get("kind"),
                        "source": row.get("source"),
                        "day": row.get("day"),
                        "score": row.get("score"),
                        "fragment": frag,
                    }
                )
                if len(rows) >= max_rows:
                    return rows
        return rows

    @staticmethod
    def _build_data_quality_evidence_bullets(data_quality: dict[str, Any], *, limit: int = 2) -> list[str]:
        if not isinstance(data_quality, dict):
            return []
        out: list[str] = []
        failures = data_quality.get("recent_failures")
        failures = failures if isinstance(failures, list) else []
        low_conf_rows = data_quality.get("recent_low_conf_rows")
        low_conf_rows = low_conf_rows if isinstance(low_conf_rows, list) else []
        threshold = data_quality.get("confidence_threshold")

        for row in failures[: max(0, limit)]:
            if not isinstance(row, dict):
                continue
            day = str(row.get("published_at") or row.get("created_at") or "").split("T")[0].split(" ")[0]
            title = str(row.get("title") or row.get("document_id") or "unknown document").strip()
            error_txt = re.sub(r"\s+", " ", str(row.get("error") or "")).strip()[:140]
            day_prefix = f"{day}: " if day else ""
            suffix = f" error={error_txt}" if error_txt else ""
            out.append(
                f"- {day_prefix}Extraction failed for {title}.{suffix} [source: extraction_runs/documents]"
            )
            if len(out) >= limit:
                return out

        for row in low_conf_rows[: max(0, limit - len(out))]:
            if not isinstance(row, dict):
                continue
            period = str(row.get("period_end") or "unknown period").strip()
            period_type = str(row.get("period_type") or "").strip()
            ticker = str(row.get("ticker") or "").strip().upper()
            confidence = row.get("confidence_metrics")
            confidence_txt = str(confidence)
            if isinstance(confidence, (int, float)):
                confidence_txt = f"{float(confidence):.3f}"
            label_bits = [bit for bit in [ticker, period, period_type] if bit]
            label = " ".join(label_bits).strip() or period
            thresh_txt = f"{float(threshold):.2f}" if isinstance(threshold, (int, float)) else str(threshold or "0.4")
            out.append(
                f"- {period}: Low-confidence financial row ({label}) confidence={confidence_txt} "
                f"threshold={thresh_txt}. [source: asx_periodic_financials]"
            )
            if len(out) >= limit:
                return out
        return out

    @staticmethod
    def _build_price_horizon_evidence_bullets(price_horizons: dict[str, Any], *, limit: int = 2) -> list[str]:
        if not isinstance(price_horizons, dict):
            return []
        out: list[str] = []
        for horizon in ("1y", "3y", "5y", "10y"):
            row = price_horizons.get(horizon)
            if not isinstance(row, dict) or not row.get("ok"):
                continue
            total_return = row.get("total_return_pct")
            drawdown = row.get("max_drawdown_pct")
            volatility = row.get("volatility_ann_pct")
            points = row.get("history_points")

            def _fmt_metric(value: Any) -> str:
                if isinstance(value, (int, float)):
                    return f"{float(value):.2f}%"
                return "n/a"

            out.append(
                f"- {horizon}: total_return={_fmt_metric(total_return)} max_drawdown={_fmt_metric(drawdown)} "
                f"vol_ann={_fmt_metric(volatility)} points={points}. [source: price_horizon_{horizon}]"
            )
            if len(out) >= limit:
                break
        return out

    @staticmethod
    def _build_web_fact_evidence_bullets(web_facts: list[dict[str, Any]], *, limit: int = 2) -> list[str]:
        out: list[str] = []
        for row in web_facts:
            if not isinstance(row, dict):
                continue
            claim = re.sub(r"\s+", " ", str(row.get("claim") or "")).strip()
            if not claim:
                continue
            claim = claim[:220]
            source_url = str(row.get("url") or "").strip()
            source_label = source_url or "web_fact"
            out.append(f"- Web fact: {claim} [source: {source_label}]")
            if len(out) >= max(1, int(limit)):
                break
        return out

    def _build_grounded_deep_analysis_brief(
        self,
        ticker: str,
        message: str,
        local_payload: dict[str, Any],
    ) -> str:
        docs = local_payload.get("docs") if isinstance(local_payload, dict) else []
        docs = docs if isinstance(docs, list) else []
        qual_context = local_payload.get("qual_context") if isinstance(local_payload, dict) else {}
        qual_context = qual_context if isinstance(qual_context, dict) else {}
        qual_context_company = local_payload.get("qual_context_company") if isinstance(local_payload, dict) else {}
        qual_context_company = qual_context_company if isinstance(qual_context_company, dict) else {}
        qual_context_news = local_payload.get("qual_context_news") if isinstance(local_payload, dict) else {}
        qual_context_news = qual_context_news if isinstance(qual_context_news, dict) else {}
        qual_hits = qual_context.get("hits")
        qual_hits = qual_hits if isinstance(qual_hits, list) else []
        if not qual_hits:
            company_hits = qual_context_company.get("hits")
            company_hits = company_hits if isinstance(company_hits, list) else []
            news_hits = qual_context_news.get("hits")
            news_hits = news_hits if isinstance(news_hits, list) else []
            qual_hits = [row for row in company_hits + news_hits if isinstance(row, dict)]
        doc_snippets = local_payload.get("doc_snippets") if isinstance(local_payload, dict) else []
        doc_snippets = doc_snippets if isinstance(doc_snippets, list) else []
        financials = local_payload.get("financials") if isinstance(local_payload, dict) else []
        financials = financials if isinstance(financials, list) else []
        data_quality = local_payload.get("data_quality") if isinstance(local_payload, dict) else {}
        data_quality = data_quality if isinstance(data_quality, dict) else {}
        price_horizons = local_payload.get("price_horizons") if isinstance(local_payload, dict) else {}
        price_horizons = price_horizons if isinstance(price_horizons, dict) else {}
        web_facts = local_payload.get("web_facts") if isinstance(local_payload, dict) else []
        web_facts = web_facts if isinstance(web_facts, list) else []

        sync = local_payload.get("announcement_sync") if isinstance(local_payload, dict) else {}
        sync = sync if isinstance(sync, dict) else {}
        sync_status = str(sync.get("status") or "").strip().lower()
        latest_sync = str(sync.get("latest_published_at_utc") or "").strip()
        latest_day = latest_sync.split("T")[0] if latest_sync else ""
        verdict_bits = [f"Grounded deep analysis for {ticker} using indexed local evidence only."]
        if docs:
            latest_doc_day = str(docs[0].get("published_at") or "").split(" ")[0]
            if latest_doc_day:
                verdict_bits.append(f"Latest filing anchor is {latest_doc_day}.")
        if sync_status:
            freshness_day = latest_day or "unknown"
            verdict_bits.append(f"Announcement sync is {sync_status} (latest indexed {freshness_day}).")
        verdict_text = " ".join(verdict_bits)

        evidence_bullets: list[str] = []
        for row in docs[:2]:
            if not isinstance(row, dict):
                continue
            day = str(row.get("published_at") or "").split(" ")[0]
            title = str(row.get("title") or row.get("document_id") or "Untitled").strip()
            if day and title:
                evidence_bullets.append(f"- {day}: {title} [source: {title}]")
            elif title:
                evidence_bullets.append(f"- {title} [source: {title}]")

        evidence_bullets.extend(self._build_data_quality_evidence_bullets(data_quality=data_quality, limit=2))

        signal_rows = self._collect_liquidity_signal_rows(
            qual_hits=[row for row in qual_hits if isinstance(row, dict)],
            doc_snippets=[row for row in doc_snippets if isinstance(row, dict)],
            max_rows=3,
        )
        for row in signal_rows:
            source = str(row.get("source") or "untitled").strip() or "untitled"
            day = str(row.get("day") or "").strip()
            fragment = str(row.get("fragment") or "").strip()
            if not fragment:
                continue
            score = row.get("score")
            score_txt = ""
            try:
                if score is not None:
                    score_txt = f" score {float(score):.3f} |"
            except (TypeError, ValueError):
                score_txt = ""
            prefix = f"{day}:" if day else "signal:"
            evidence_bullets.append(f"- {prefix}{score_txt} {fragment} [source: {source}]")

        if qual_context.get("ok") and qual_hits and len(evidence_bullets) < 7:
            seen_qual_sources: set[str] = set()
            for row in qual_hits:
                if not isinstance(row, dict):
                    continue
                source_key = str(row.get("file") or row.get("title") or "").strip().lower()
                if not source_key:
                    source_key = str(row.get("text") or "").strip().lower()[:120]
                if source_key and source_key in seen_qual_sources:
                    continue
                if source_key:
                    seen_qual_sources.add(source_key)
                score = row.get("score")
                day = str(row.get("published_at") or row.get("doc_date") or "").strip().split("T")[0]
                title = self._clean_qual_anchor_label(row)
                try:
                    score_txt = f"{float(score):.3f}" if score is not None else "n/a"
                except (TypeError, ValueError):
                    score_txt = "n/a"
                anchor = f"{day} | {title}" if day else title
                evidence_bullets.append(f"- score {score_txt} | {anchor} [source: {title}]")
                if len(evidence_bullets) >= 8 or len(seen_qual_sources) >= 4:
                    break
        if len(evidence_bullets) > 8:
            evidence_bullets = evidence_bullets[:8]

        hit_text = " ".join(str(row.get("text") or "") for row in qual_hits if isinstance(row, dict)).lower()
        snippet_text = " ".join(
            str(row.get("excerpt") or row.get("text") or "") for row in doc_snippets if isinstance(row, dict)
        ).lower()
        signal_text = f"{hit_text} {snippet_text}".strip()
        liquidity_terms = ("liquidity", "cash flow", "cash runway", "working capital", "capital resources")
        refinancing_terms = ("refinanc", "debt maturity", "maturity", "covenant", "facility")
        liq_hits = sum(1 for term in liquidity_terms if term in signal_text)
        refi_hits = sum(1 for term in refinancing_terms if term in signal_text)

        if financials:
            latest_fin = financials[0] if isinstance(financials[0], dict) else {}
            period_end = str(latest_fin.get("period_end") or "").strip() or "unknown period"
            period_type = str(latest_fin.get("period_type") or "").strip()
            revenue = latest_fin.get("revenue")
            ebit = latest_fin.get("ebit")
            npat = latest_fin.get("np_attributable")
            fin_label = f"{period_end}{', ' + period_type if period_type else ''}"
            evidence_bullets.append(
                f"- Financial snapshot {fin_label}: Revenue={revenue}, EBIT={ebit}, NPAT attributable={npat}. "
                "[source: extracted_financials]"
            )

        price_payload = local_payload.get("price") if isinstance(local_payload, dict) else {}
        price_state = local_payload.get("price_state") if isinstance(local_payload, dict) else {}
        price_text = self._build_price_reply(
            price_payload if isinstance(price_payload, dict) else {},
            price_state if isinstance(price_state, dict) else {},
        )
        price_lines = [row for row in str(price_text).splitlines() if row.strip()]
        price_ok = isinstance(price_state, dict) and bool(price_state.get("ok"))
        if price_ok and price_lines and len(evidence_bullets) < 8:
            evidence_bullets.append(f"- Market context: {price_lines[0]} [source: price_state]")

        if len(evidence_bullets) < 8:
            for bullet in self._build_price_horizon_evidence_bullets(price_horizons=price_horizons, limit=2):
                evidence_bullets.append(bullet)
                if len(evidence_bullets) >= 8:
                    break

        if len(evidence_bullets) < 8:
            for bullet in self._build_web_fact_evidence_bullets(web_facts=web_facts, limit=2):
                evidence_bullets.append(bullet)
                if len(evidence_bullets) >= 8:
                    break

        if not evidence_bullets:
            evidence_bullets = ["- This cannot be verified based on available data."]
        elif len(evidence_bullets) < 4:
            evidence_bullets.extend(
                ["- This cannot be verified based on available data."] * (4 - len(evidence_bullets))
            )

        risks: list[str] = []
        extraction_failed_count = int(data_quality.get("extraction_failed_count_recent") or 0)
        low_conf_count = int(data_quality.get("low_conf_financial_count_recent") or 0)
        if liq_hits or refi_hits:
            risks.append(
                "- Retrieved qualitative excerpts include liquidity/refinancing language; monitor covenant and maturity detail in the next filing."
            )
        if extraction_failed_count > 0:
            risks.append(
                f"- Data quality risk: {extraction_failed_count} recent extraction failures reduce confidence in complete filing coverage."
            )
        if low_conf_count > 0:
            risks.append(
                f"- Data quality risk: {low_conf_count} extracted financial rows are below confidence threshold and should be manually verified."
            )
        if signal_rows:
            risks.append(
                "- Signal excerpts are OCR-derived and may omit surrounding context; validate covenant and debt ladder details in primary filings."
            )
        if not financials:
            risks.append("- This cannot be verified based on available data. Key current financial metrics were not present in extracted financial rows.")
        if not docs:
            risks.append("- This cannot be verified based on available data. No indexed filing anchors were available.")
        if not risks:
            risks.append("- No additional risk signal could be verified beyond the indexed evidence set.")

        counterpoints: list[str] = []
        if docs:
            counterpoints.append("- Multiple indexed documents are available, reducing single-document bias in interpretation.")
        if signal_rows:
            counterpoints.append("- Signal extraction identified concrete liquidity/refinancing snippets rather than only retrieval scores.")
        if qual_hits:
            counterpoints.append("- Semantic retrieval returned directly relevant passages, which improves narrative signal coverage.")
        if price_ok and price_lines:
            counterpoints.append(f"- Market context is available: {price_lines[0]}")
        if price_horizons:
            counterpoints.append("- Multi-horizon market context (1Y/3Y/5Y/10Y) is available for trend and drawdown cross-checking.")
        if web_facts:
            counterpoints.append("- Deterministic web fact extraction contributed claim-level external anchors with source URLs.")
        if not counterpoints:
            counterpoints.append("- This cannot be verified based on available data.")

        unknowns: list[str] = [
            "- Liquidity runway, debt maturity ladder, and covenant headroom are unknown unless explicitly disclosed in the retrieved excerpts.",
            "- This cannot be verified based on available data.",
        ]
        if message.strip():
            unknowns.insert(0, f"- Scope requested: {message.strip()}")

        lines = [
            "Verdict:",
            verdict_text,
            "",
            "Evidence:",
            *evidence_bullets[:8],
            "",
            "Risks:",
            *risks[:4],
            "",
            "Counterpoints:",
            *counterpoints[:4],
            "",
            "Unknowns:",
            *unknowns[:4],
        ]
        return "\n".join(lines)

    def _build_operational_analysis_brief(self, ticker: str, local_payload: dict[str, Any]) -> str:
        docs = local_payload.get("docs") if isinstance(local_payload, dict) else []
        docs = docs if isinstance(docs, list) else []
        financials = local_payload.get("financials") if isinstance(local_payload, dict) else []
        financials = financials if isinstance(financials, list) else []

        lines = [f"Grounded operational brief for {ticker} (local indexed evidence):"]
        if docs:
            latest_date = str(docs[0].get("published_at") or "").split(" ")[0]
            if latest_date:
                lines.append(f"Latest indexed announcement date: {latest_date}.")
            lines.append(f"Recent announcements in context: {len(docs)}.")
            lines.append("Key recent filings:")
            for row in docs[:6]:
                if not isinstance(row, dict):
                    continue
                date = str(row.get("published_at") or "").split(" ")[0]
                title = str(row.get("title") or row.get("document_id") or "Untitled").strip()
                source = str(row.get("source_url") or "").strip()
                item = f"- {date}: {title}" if date else f"- {title}"
                if source:
                    item += f" ({source})"
                lines.append(item)
            if len(docs) > 6:
                lines.append(f"- ... {len(docs) - 6} more")
        else:
            lines.append("This cannot be verified based on available data. No indexed announcements were found.")

        if financials:
            latest_fin = financials[0] if isinstance(financials[0], dict) else {}
            period_end = str(latest_fin.get("period_end") or "").strip()
            period_type = str(latest_fin.get("period_type") or "").strip()
            revenue = latest_fin.get("revenue")
            ebit = latest_fin.get("ebit")
            npat = latest_fin.get("np_attributable")
            fin_bits: list[str] = []
            if period_end:
                fin_bits.append(period_end)
            if period_type:
                fin_bits.append(period_type)
            header = "Latest extracted financial snapshot"
            if fin_bits:
                header += f" ({', '.join(fin_bits)})"
            lines.append(header + ":")
            lines.append(f"- Revenue: {revenue}")
            lines.append(f"- EBIT: {ebit}")
            lines.append(f"- NPAT attributable: {npat}")
        else:
            lines.append("Financial snapshot: This cannot be verified based on available data.")

        data_quality = local_payload.get("data_quality") if isinstance(local_payload, dict) else {}
        data_quality = data_quality if isinstance(data_quality, dict) else {}
        if data_quality:
            extraction_failed_count = int(data_quality.get("extraction_failed_count_recent") or 0)
            low_conf_count = int(data_quality.get("low_conf_financial_count_recent") or 0)
            threshold = data_quality.get("confidence_threshold")
            lines.append("Data quality:")
            lines.append(
                f"- Recent extraction failures: {extraction_failed_count}; low-confidence financial rows: {low_conf_count} "
                f"(threshold={threshold})."
            )

        price_horizons = local_payload.get("price_horizons") if isinstance(local_payload, dict) else {}
        price_horizons = price_horizons if isinstance(price_horizons, dict) else {}
        if price_horizons:
            lines.append("Multi-horizon market context:")
            for horizon in ("1y", "3y", "5y", "10y"):
                row = price_horizons.get(horizon)
                if not isinstance(row, dict) or not row.get("ok"):
                    continue
                total_return = row.get("total_return_pct")
                drawdown = row.get("max_drawdown_pct")
                volatility = row.get("volatility_ann_pct")
                lines.append(
                    f"- {horizon}: return={total_return if total_return is not None else 'n/a'} "
                    f"drawdown={drawdown if drawdown is not None else 'n/a'} "
                    f"vol_ann={volatility if volatility is not None else 'n/a'}"
                )

        price_payload = local_payload.get("price") if isinstance(local_payload, dict) else {}
        price_state = local_payload.get("price_state") if isinstance(local_payload, dict) else {}
        price_text = self._build_price_reply(
            price_payload if isinstance(price_payload, dict) else {},
            price_state=price_state if isinstance(price_state, dict) else {},
        )
        lines.append("Price context:")
        for row in str(price_text).splitlines()[:4]:
            lines.append(f"- {row}")

        lines.append(f"Use `deep analysis analyse {ticker}` for full 9-section LLM analysis.")
        return "\n".join(lines)

    @staticmethod
    def _sanitize_prompt_local_payload(payload: dict[str, Any], deep_mode: bool) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {}

        keep_keys = {
            "query",
            "ticker",
            "docs",
            "doc_snippets_source",
            "doc_snippets",
            "qual_context",
            "qual_context_company",
            "qual_context_news",
            "financials",
            "price",
            "price_state",
            "price_horizons",
            "data_quality",
            "web_facts",
            "web_source_quality",
            "web_preferred_domains",
            "announcement_sync",
            "db_warning",
            "db_error",
            "note",
        }
        sanitized: dict[str, Any] = {}
        for key in keep_keys:
            if key in payload:
                sanitized[key] = payload[key]

        docs = sanitized.get("docs")
        if isinstance(docs, list):
            docs_limit = 20 if deep_mode else 10
            trimmed_docs: list[dict[str, Any]] = []
            for row in docs[:docs_limit]:
                if not isinstance(row, dict):
                    continue
                trimmed_docs.append(
                    {
                        "document_id": row.get("document_id"),
                        "ticker": row.get("ticker"),
                        "doc_class": row.get("doc_class"),
                        "doc_subtype": row.get("doc_subtype"),
                        "published_at": row.get("published_at"),
                        "title": row.get("title"),
                        "source_url": row.get("source_url"),
                        "pdf_path": row.get("pdf_path"),
                    }
                )
            sanitized["docs"] = trimmed_docs

        snippets = sanitized.get("doc_snippets")
        if isinstance(snippets, list):
            snippet_limit = 12 if deep_mode else 6
            excerpt_limit = 2800 if deep_mode else 1200
            trimmed_snippets: list[dict[str, Any]] = []
            for row in snippets[:snippet_limit]:
                if not isinstance(row, dict):
                    continue
                excerpt = str(row.get("excerpt") or "")
                trimmed_snippets.append(
                    {
                        "document_id": row.get("document_id"),
                        "ticker": row.get("ticker"),
                        "published_at": row.get("published_at"),
                        "title": row.get("title"),
                        "pdf_path": row.get("pdf_path"),
                        "excerpt": excerpt[:excerpt_limit],
                    }
                )
            sanitized["doc_snippets"] = trimmed_snippets

        qual_context = sanitized.get("qual_context")
        if isinstance(qual_context, dict):
            hits = qual_context.get("hits")
            if isinstance(hits, list):
                hit_limit = 12 if deep_mode else 6
                text_limit = 2800 if deep_mode else 1200
                trimmed_hits: list[dict[str, Any]] = []
                for row in hits[:hit_limit]:
                    if not isinstance(row, dict):
                        continue
                    text = str(row.get("text") or "")
                    trimmed_hits.append(
                        {
                            "score": row.get("score"),
                            "company": row.get("company"),
                            "corpus": row.get("corpus"),
                            "doc_type": row.get("doc_type"),
                            "doc_date": row.get("doc_date"),
                            "file": row.get("file"),
                            "section": row.get("section"),
                            "title": row.get("title"),
                            "published_at": row.get("published_at"),
                            "text": text[:text_limit],
                        }
                    )
                qual_context["hits"] = trimmed_hits

        for key in ("qual_context_company", "qual_context_news"):
            scoped = sanitized.get(key)
            if not isinstance(scoped, dict):
                continue
            hits = scoped.get("hits")
            if not isinstance(hits, list):
                continue
            hit_limit = 12 if deep_mode else 6
            text_limit = 2800 if deep_mode else 1200
            trimmed_hits: list[dict[str, Any]] = []
            for row in hits[:hit_limit]:
                if not isinstance(row, dict):
                    continue
                text = str(row.get("text") or "")
                trimmed_hits.append(
                    {
                        "score": row.get("score"),
                        "company": row.get("company"),
                        "corpus": row.get("corpus"),
                        "source_corpus": row.get("source_corpus"),
                        "doc_type": row.get("doc_type"),
                        "doc_date": row.get("doc_date"),
                        "file": row.get("file"),
                        "section": row.get("section"),
                        "title": row.get("title"),
                        "published_at": row.get("published_at"),
                        "text": text[:text_limit],
                    }
                )
            scoped["hits"] = trimmed_hits

        financials = sanitized.get("financials")
        if isinstance(financials, list):
            fin_limit = 12 if deep_mode else 6
            sanitized["financials"] = financials[:fin_limit]

        price = sanitized.get("price")
        if isinstance(price, dict):
            compact_price = dict(price)
            recent = compact_price.get("recent_history")
            if isinstance(recent, list):
                compact_price["recent_history"] = recent[-(40 if deep_mode else 12) :]
            sanitized["price"] = compact_price

        price_state = sanitized.get("price_state")
        if isinstance(price_state, dict):
            sanitized["price_state"] = {
                "ok": price_state.get("ok"),
                "ticker": price_state.get("ticker"),
                "symbol": price_state.get("symbol"),
                "currency": price_state.get("currency"),
                "last_close": price_state.get("last_close"),
                "previous_close_effective": price_state.get("previous_close_effective"),
                "trend_regime": price_state.get("trend_regime"),
                "ret_1d": price_state.get("ret_1d"),
                "ret_5d": price_state.get("ret_5d"),
                "ret_20d": price_state.get("ret_20d"),
                "ret_63d": price_state.get("ret_63d"),
                "sma20": price_state.get("sma20"),
                "sma50": price_state.get("sma50"),
                "vol_20d_ann": price_state.get("vol_20d_ann"),
                "drawdown_from_63d_high": price_state.get("drawdown_from_63d_high"),
                "market_time_utc": price_state.get("market_time_utc"),
                "data_age_hours": price_state.get("data_age_hours"),
                "stale_data": price_state.get("stale_data"),
                "history_points": price_state.get("history_points"),
                "insufficient_history": price_state.get("insufficient_history"),
                "error": price_state.get("error"),
            }

        data_quality = sanitized.get("data_quality")
        if isinstance(data_quality, dict):
            fail_rows = data_quality.get("recent_failures")
            fail_rows = fail_rows if isinstance(fail_rows, list) else []
            low_rows = data_quality.get("recent_low_conf_rows")
            low_rows = low_rows if isinstance(low_rows, list) else []
            sanitized["data_quality"] = {
                "extraction_failed_count_recent": data_quality.get("extraction_failed_count_recent"),
                "low_conf_financial_count_recent": data_quality.get("low_conf_financial_count_recent"),
                "confidence_threshold": data_quality.get("confidence_threshold"),
                "recent_failures": fail_rows[: (8 if deep_mode else 4)],
                "recent_low_conf_rows": low_rows[: (8 if deep_mode else 4)],
            }

        price_horizons = sanitized.get("price_horizons")
        if isinstance(price_horizons, dict):
            compact_horizons: dict[str, Any] = {}
            for horizon in ("1y", "3y", "5y", "10y"):
                row = price_horizons.get(horizon)
                if not isinstance(row, dict):
                    continue
                compact_horizons[horizon] = {
                    "ok": row.get("ok"),
                    "total_return_pct": row.get("total_return_pct"),
                    "max_drawdown_pct": row.get("max_drawdown_pct"),
                    "volatility_ann_pct": row.get("volatility_ann_pct"),
                    "history_points": row.get("history_points"),
                    "data_age_hours": row.get("data_age_hours"),
                    "stale_data": row.get("stale_data"),
                    "error": row.get("error"),
                }
            sanitized["price_horizons"] = compact_horizons

        web_facts = sanitized.get("web_facts")
        if isinstance(web_facts, list):
            fact_limit = 8 if deep_mode else 3
            compact_facts: list[dict[str, Any]] = []
            for row in web_facts[:fact_limit]:
                if not isinstance(row, dict):
                    continue
                compact_facts.append(
                    {
                        "url": row.get("url"),
                        "claim": str(row.get("claim") or "")[:240],
                        "numbers": row.get("numbers"),
                        "dates": row.get("dates"),
                        "terms": row.get("terms"),
                    }
                )
            sanitized["web_facts"] = compact_facts

        web_quality = sanitized.get("web_source_quality")
        if isinstance(web_quality, dict):
            sanitized["web_source_quality"] = {
                "official_source_required": web_quality.get("official_source_required"),
                "official_source_found": web_quality.get("official_source_found"),
                "official_candidates_found": web_quality.get("official_candidates_found"),
                "facts_count": web_quality.get("facts_count"),
                "preferred_domains": web_quality.get("preferred_domains"),
            }

        return sanitized

    @staticmethod
    def _extract_alpha_tokens(message: str) -> list[tuple[str, str]]:
        return [(m.group(0), m.group(0).upper()) for m in re.finditer(r"\b([A-Za-z]{2,5})\b", message)]

    @classmethod
    def _is_smalltalk_message(cls, message: str) -> bool:
        normalized = re.sub(r"\s+", " ", message.strip().lower())
        return normalized in cls.SMALLTALK_MESSAGES

    def _requests_structured_analysis(
        self,
        message: str,
        ticker: str | None,
        prior_ticker: str | None,
    ) -> bool:
        if self._is_smalltalk_message(message):
            return False

        text = message.lower()
        if "http://" in text or "https://" in text:
            return True
        if any(term in text for term in self.ANALYSIS_INTENT_TERMS):
            return True

        explicit_ticker = self._detect_ticker(message, prior_ticker=None)
        if explicit_ticker is not None:
            return True

        # Follow-up requests may rely on prior ticker context ("what about recent ones").
        if ticker and prior_ticker and ticker == prior_ticker:
            if any(term in text for term in self.FOLLOW_UP_ANALYSIS_TERMS):
                return True
        return False

    def _detect_ticker(self, message: str, prior_ticker: str | None = None) -> str | None:
        if self._is_smalltalk_message(message):
            return None

        # Prefer explicit ticker-like mentions first, e.g. "$BHP" or "ASX:BHP".
        explicit = re.search(r"(?:\bASX:|\$)([A-Za-z]{2,5})\b", message)
        if explicit:
            return explicit.group(1).upper()

        # Analysis-oriented forms should resolve ticker explicitly before generic intent parsing.
        # This prevents phrases like "deep analysis on bhp" from being misread as ticker "DEEP".
        for pattern in (
            r"\b(?:deep|in[- ]depth|full(?:[- ]scale)?|extreme)\s+analysis\s+(?:on|for|of|about|re|regarding)\s+([A-Za-z]{2,5})\b",
            r"\banalysis\s+(?:on|for|of|about|re|regarding)\s+([A-Za-z]{2,5})\b",
            r"\b(?:analyse|analyze)\s+(?:on|for|of|about|re|regarding)?\s*([A-Za-z]{2,5})\b",
        ):
            match = re.search(pattern, message, flags=re.IGNORECASE)
            if not match:
                continue
            token = match.group(1).upper()
            if token not in self.TICKER_STOPWORDS:
                return token

        tokens = self._extract_alpha_tokens(message)
        if not tokens:
            return prior_ticker

        # Natural-language ticker intents, e.g. "analyse bhp", "ticker csl", "about rio".
        intent_pattern = re.compile(
            r"\b(?:ticker|code|symbol|asx|analyse|analyze|analysis|check|show|about|on|for|with|regarding|update|news|announcements?)\s+([A-Za-z]{2,5})\b",
            flags=re.IGNORECASE,
        )
        for intent_match in intent_pattern.finditer(message):
            token = intent_match.group(1).upper()
            if token not in self.TICKER_STOPWORDS:
                return token

        # Reverse form, e.g. "bhp announcements" / "csl news".
        reverse_intent_match = re.search(
            r"\b([A-Za-z]{2,5})\s+(?:announcements?|news|analysis|financials?)\b",
            message,
            flags=re.IGNORECASE,
        )
        if reverse_intent_match:
            token = reverse_intent_match.group(1).upper()
            if token not in self.TICKER_STOPWORDS:
                return token

        # Reverse price-style requests, e.g. "bhp price" / "csl chart".
        reverse_price_intent_match = re.search(
            r"\b([A-Za-z]{2,5})\s+(?:price|quote|chart|close|historical|history)\b",
            message,
            flags=re.IGNORECASE,
        )
        if reverse_price_intent_match:
            token = reverse_price_intent_match.group(1).upper()
            if token not in self.TICKER_STOPWORDS:
                return token

        # Historical range forms, e.g. "bhp between 2025-01-01 and 2025-01-31".
        historical_range_ticker_match = re.search(
            r"\b([A-Za-z]{2,5})\s+(?:between|from|since)\b",
            message,
            flags=re.IGNORECASE,
        )
        if historical_range_ticker_match:
            token = historical_range_ticker_match.group(1).upper()
            if token not in self.TICKER_STOPWORDS:
                return token

        # Historical phrasing, e.g. "what was bhp on 2025-01-15".
        historical_ticker_match = re.search(
            r"\b(?:what\s+was|how\s+did|price\s+of|close\s+of)\s+([A-Za-z]{2,5})\b",
            message,
            flags=re.IGNORECASE,
        )
        if historical_ticker_match:
            token = historical_ticker_match.group(1).upper()
            if token not in self.TICKER_STOPWORDS:
                return token

        # Price-style requests, e.g. "price bhp" / "quote of csl".
        price_intent_match = re.search(
            r"\b(?:price|quote|chart|close|historical|history)\s+(?:(?:of|for)\s+)?([A-Za-z]{2,5})\b",
            message,
            flags=re.IGNORECASE,
        )
        if price_intent_match:
            token = price_intent_match.group(1).upper()
            if token not in self.TICKER_STOPWORDS:
                return token

        # Single-token query fallback, mostly for direct ticker asks like "bhp".
        single = re.fullmatch(r"\s*([A-Za-z]{2,4})\s*[?!.,]*\s*", message)
        if single:
            token = single.group(1).upper()
            if token not in self.TICKER_STOPWORDS:
                return token

        # Prefer explicit uppercase ticker-like tokens first.
        for original, upper in tokens:
            if original.isupper() and upper not in self.TICKER_STOPWORDS:
                return upper

        return prior_ticker

    def detect_action_intent(self, message: str) -> str | None:
        text = message.lower()
        if (
            re.search(
                r"\b(?:update|refresh|sync|download|pull)\b.*\b(?:announcement|announcements|news|docs?|documents?)\b",
                text,
                flags=re.IGNORECASE,
            )
            or re.search(
                r"\b(?:announcement|announcements|news|docs?|documents?)\b.*\b(?:update|refresh|sync|download|pull)\b",
                text,
                flags=re.IGNORECASE,
            )
        ):
            return "update_ticker_financials"
        # Resolve overlapping keywords by selecting the most specific match
        # (longest matched phrase), rather than first dict insertion order.
        matches: list[tuple[int, str]] = []
        for action_id, words in ACTION_KEYWORDS.items():
            best_len = 0
            for w in words:
                phrase = str(w or "").strip().lower()
                if not phrase:
                    continue
                if phrase in text:
                    best_len = max(best_len, len(phrase))
            if best_len > 0:
                matches.append((best_len, action_id))
        if matches:
            matches.sort(key=lambda item: item[0], reverse=True)
            return matches[0][1]
        return None

    @staticmethod
    def _is_price_request(message: str, ticker: str | None) -> bool:
        if not ticker:
            return False
        text = str(message or "").lower()
        if not any(
            marker in text
            for marker in ("price", "quote", "chart", "historical", "history", "close", "traded", "trading")
        ):
            return False
        if any(marker in text for marker in ("full analysis", "deep analysis", "company brief", "valuation", "moat")):
            return False
        return True

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        try:
            return float(value)
        except Exception:
            return None

    @staticmethod
    def _parse_historical_date_token(token: str) -> datetime | None:
        raw = str(token or "").strip().replace(",", "")
        raw = re.sub(r"\s+", " ", raw)
        raw = re.sub(r"\bsept\b", "sep", raw, flags=re.IGNORECASE)
        if not raw:
            return None
        formats = (
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%m/%d/%y",
            "%b %d %Y",
            "%B %d %Y",
            "%d %b %Y",
            "%d %B %Y",
        )
        parsed: datetime | None = None
        for fmt in formats:
            try:
                parsed = datetime.strptime(raw, fmt)
                break
            except Exception:
                continue
        if parsed is None:
            return None
        if parsed.year < 1900 or parsed.year > 2100:
            return None
        return parsed.replace(tzinfo=timezone.utc, hour=0, minute=0, second=0, microsecond=0)

    @classmethod
    def _extract_date_mentions(cls, message: str) -> list[datetime]:
        text = str(message or "")
        if not text:
            return []

        patterns = (
            r"\b\d{4}-\d{2}-\d{2}\b",
            r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
            r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b",
            r"\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+\d{4}\b",
        )

        mentions: list[tuple[int, datetime]] = []
        for pattern in patterns:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                dt = cls._parse_historical_date_token(match.group(0))
                if dt is not None:
                    mentions.append((match.start(), dt))

        lowered = text.lower()
        now_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_idx = lowered.find("today")
        if today_idx >= 0:
            mentions.append((today_idx, now_day))
        yesterday_idx = lowered.find("yesterday")
        if yesterday_idx >= 0:
            mentions.append((yesterday_idx, now_day - timedelta(days=1)))

        mentions.sort(key=lambda item: item[0])
        out: list[datetime] = []
        seen: set[str] = set()
        for _, dt in mentions:
            key = dt.date().isoformat()
            if key in seen:
                continue
            seen.add(key)
            out.append(dt)
        return out

    @classmethod
    def _parse_historical_price_request(
        cls,
        message: str,
        ticker: str | None,
    ) -> dict[str, Any] | None:
        if not ticker:
            return None
        text = re.sub(r"\s+", " ", str(message or "").lower()).strip()
        if not text:
            return None

        if any(
            marker in text
            for marker in (
                "price history",
                "full price history",
                "all price history",
                "entire price history",
                "max price history",
                "historical price history",
            )
        ):
            return {"kind": "full_summary"}

        dates = cls._extract_date_mentions(message)
        if not dates:
            return None

        has_price_language = any(
            marker in text
            for marker in (
                "price",
                "quote",
                "chart",
                "historical",
                "history",
                "close",
                "traded",
                "trading",
                "as of",
                "what was",
                "between",
                "from",
                "since",
            )
        )
        if not has_price_language:
            return None

        if len(dates) >= 2 and any(marker in text for marker in ("between", "from", "to", "and", "through", "until")):
            start_dt = dates[0]
            end_dt = dates[1]
            if end_dt < start_dt:
                start_dt, end_dt = end_dt, start_dt
            return {
                "kind": "range",
                "start_date": start_dt.date().isoformat(),
                "end_date": end_dt.date().isoformat(),
            }

        if "since" in text and dates:
            start_dt = dates[0]
            end_dt = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            if end_dt < start_dt:
                start_dt, end_dt = end_dt, start_dt
            return {
                "kind": "range",
                "start_date": start_dt.date().isoformat(),
                "end_date": end_dt.date().isoformat(),
            }

        return {
            "kind": "on_date",
            "target_date": dates[0].date().isoformat(),
        }

    @classmethod
    def _extract_close_series(cls, price_payload: dict[str, Any]) -> list[tuple[datetime, float]]:
        history = []
        if isinstance(price_payload, dict):
            if isinstance(price_payload.get("history"), list):
                history = price_payload.get("history") or []
            elif isinstance(price_payload.get("recent_history"), list):
                history = price_payload.get("recent_history") or []
        deduped: dict[str, tuple[datetime, float]] = {}
        for row in history:
            if not isinstance(row, dict):
                continue
            ts = cls._parse_timestamp_utc(row.get("timestamp"))
            close = cls._safe_float(row.get("close"))
            if ts is None or close is None:
                continue
            deduped[ts.isoformat()] = (ts, close)
        out = list(deduped.values())
        out.sort(key=lambda item: item[0].timestamp())
        return out

    @classmethod
    def _build_historical_price_reply(
        cls,
        price_payload: dict[str, Any],
        price_state: dict[str, Any],
        query: dict[str, Any],
    ) -> str:
        state = price_state if isinstance(price_state, dict) else {}
        if not state.get("ok"):
            error = str(state.get("error") or (price_payload or {}).get("error") or "price lookup failed")
            return f"This cannot be verified based on available data. Price feed error: {error}"

        series = cls._extract_close_series(price_payload if isinstance(price_payload, dict) else {})
        if not series:
            return "This cannot be verified based on available data. No historical close series was returned."

        symbol = state.get("symbol") or price_payload.get("symbol") or price_payload.get("ticker") or "unknown"
        currency = state.get("currency") or price_payload.get("currency") or ""
        coverage_start = series[0][0].date().isoformat()
        coverage_end = series[-1][0].date().isoformat()

        def _fmt_num(value: Any, decimals: int = 4) -> str:
            parsed = cls._safe_float(value)
            if parsed is None:
                return "n/a"
            return f"{parsed:.{decimals}f}"

        def _fmt_pct(value: Any) -> str:
            parsed = cls._safe_float(value)
            if parsed is None:
                return "n/a"
            return f"{parsed:+.2f}%"

        kind = str(query.get("kind") or "").strip().lower()
        if kind == "full_summary":
            first_ts, first_close = series[0]
            last_ts, last_close = series[-1]
            total_ret = None
            if first_close not in (None, 0):
                total_ret = ((last_close / first_close) - 1.0) * 100.0
            highs = [close for _, close in series]
            high_close = max(highs) if highs else None
            low_close = min(highs) if highs else None
            return (
                f"Full historical summary for {symbol}\n"
                f"Coverage: {coverage_start} to {coverage_end} ({len(series)} points)\n"
                f"Start close: {_fmt_num(first_close)} {currency} | End close: {_fmt_num(last_close)} {currency}\n"
                f"Total return over coverage: {_fmt_pct(total_ret)}\n"
                f"Close high/low over coverage: {_fmt_num(high_close)} / {_fmt_num(low_close)}"
            )

        if kind == "on_date":
            raw = str(query.get("target_date") or "").strip()
            target = cls._parse_historical_date_token(raw)
            if target is None:
                return "This cannot be verified based on available data. The requested date was not parsed."
            target_date = target.date()

            anchor_idx = -1
            for idx, (ts, _) in enumerate(series):
                if ts.date() <= target_date:
                    anchor_idx = idx
                else:
                    break
            if anchor_idx < 0:
                return (
                    "This cannot be verified based on available data. "
                    f"No price history exists on or before {target_date.isoformat()}."
                )

            anchor_ts, anchor_close = series[anchor_idx]
            prev_close = series[anchor_idx - 1][1] if anchor_idx > 0 else None
            ret_1d = None
            if prev_close not in (None, 0):
                ret_1d = ((anchor_close / prev_close) - 1.0) * 100.0
            exact = anchor_ts.date() == target_date
            match_note = "exact" if exact else "nearest prior trading day"

            return (
                f"Historical close for {symbol} on {target_date.isoformat()}: {_fmt_num(anchor_close)} {currency}\n"
                f"Matched candle date: {anchor_ts.date().isoformat()} ({match_note})\n"
                f"1D move into that close: {_fmt_pct(ret_1d)}\n"
                f"History coverage: {coverage_start} to {coverage_end} ({len(series)} points)"
            )

        if kind == "range":
            start_raw = str(query.get("start_date") or "").strip()
            end_raw = str(query.get("end_date") or "").strip()
            start_dt = cls._parse_historical_date_token(start_raw)
            end_dt = cls._parse_historical_date_token(end_raw)
            if start_dt is None or end_dt is None:
                return "This cannot be verified based on available data. One or more requested dates were not parsed."
            start_date = start_dt.date()
            end_date = end_dt.date()
            if end_date < start_date:
                start_date, end_date = end_date, start_date

            window = [(ts, close) for ts, close in series if start_date <= ts.date() <= end_date]
            if not window:
                return (
                    "This cannot be verified based on available data. "
                    f"No price candles were found between {start_date.isoformat()} and {end_date.isoformat()}."
                )

            first_ts, first_close = window[0]
            last_ts, last_close = window[-1]
            period_ret = None
            if first_close not in (None, 0):
                period_ret = ((last_close / first_close) - 1.0) * 100.0
            highs = [close for _, close in window]
            high_close = max(highs) if highs else None
            low_close = min(highs) if highs else None

            return (
                f"Historical range for {symbol}: {start_date.isoformat()} to {end_date.isoformat()}\n"
                f"Start close ({first_ts.date().isoformat()}): {_fmt_num(first_close)} {currency}\n"
                f"End close ({last_ts.date().isoformat()}): {_fmt_num(last_close)} {currency}\n"
                f"Period return (close-to-close): {_fmt_pct(period_ret)} | "
                f"Close high/low: {_fmt_num(high_close)} / {_fmt_num(low_close)}\n"
                f"Trading days in window: {len(window)} | Coverage: {coverage_start} to {coverage_end}"
            )

        return "This cannot be verified based on available data. Unsupported historical price query."

    @staticmethod
    def _build_price_reply(price_payload: dict[str, Any], price_state: dict[str, Any] | None = None) -> str:
        state = price_state if isinstance(price_state, dict) else {}
        if not state.get("ok"):
            error = str(state.get("error") or (price_payload or {}).get("error") or "price lookup failed")
            return f"This cannot be verified based on available data. Price feed error: {error}"

        def _fmt_pct(value: Any) -> str:
            try:
                return f"{float(value):+.2f}%"
            except Exception:
                return "n/a"

        def _fmt_num(value: Any, decimals: int = 4) -> str:
            try:
                return f"{float(value):.{decimals}f}"
            except Exception:
                return "n/a"

        current = price_payload.get("current", {}) if isinstance(price_payload, dict) else {}
        symbol = state.get("symbol") or price_payload.get("symbol") or price_payload.get("ticker") or "unknown"
        currency = state.get("currency") or price_payload.get("currency") or ""
        last_close = state.get("last_close")
        previous_close = state.get("previous_close_effective")
        trend = str(state.get("trend_regime") or "neutral")
        vol_20d_ann = state.get("vol_20d_ann")
        market_time_utc = state.get("market_time_utc") or current.get("market_time")
        stale = bool(state.get("stale_data"))
        age_hours = state.get("data_age_hours")
        ret_1d = state.get("ret_1d")
        ret_20d = state.get("ret_20d")
        high = current.get("day_high")
        low = current.get("day_low")
        volume = current.get("volume")

        freshness = "stale" if stale else "fresh"
        freshness_detail = f"{freshness}"
        try:
            freshness_detail += f", {float(age_hours):.1f}h old"
        except Exception:
            freshness_detail += ", age unknown"

        return (
            f"Price snapshot for {symbol}: {_fmt_num(last_close)} {currency}\n"
            f"Previous close (effective): {_fmt_num(previous_close)}\n"
            f"Returns: 1D {_fmt_pct(ret_1d)} | 20D {_fmt_pct(ret_20d)}\n"
            f"Trend regime: {trend}\n"
            f"Volatility (20d ann): {_fmt_pct(vol_20d_ann)}\n"
            f"Data freshness: {freshness_detail}\n"
            f"Market time (UTC): {market_time_utc}\n"
            f"Day range: {low} - {high} | Volume: {volume}"
        )

    def build_chat_response(
        self,
        message: str,
        enable_web: bool = False,
        prior_ticker: str | None = None,
        analysis_mode: str = "operational",
        on_chunk: Callable[[str], None] | None = None,
    ) -> ChatResponse:
        started_at = time.perf_counter()
        mode = str(analysis_mode or "operational").strip().lower()
        deep_mode = mode in {"deep", "full", "extreme", "in-depth", "in_depth", "full-scale"}
        global_scope_reset = self._has_scope_reset_intent(message)
        global_announcement_scope = self._is_global_announcement_request(message)
        ticker = self._detect_ticker(
            message,
            prior_ticker=None if global_announcement_scope else (prior_ticker or self.last_ticker),
        )
        if global_scope_reset:
            self.last_ticker = None
        else:
            self.last_ticker = ticker or self.last_ticker

        action_id = self.detect_action_intent(message)
        if action_id:
            context_started_at = time.perf_counter()
            local_context = self.tool_router.gather_local_context(ticker=ticker, query=message, deep_mode=deep_mode)
            context_ms = (time.perf_counter() - context_started_at) * 1000.0
            evidence = [
                {"type": "local_context", "details": local_context.payload},
            ]
            args = {"ticker": ticker or "BHP"}
            if action_id == "update_ticker_financials":
                args["years"] = 1
                args["process_documents"] = True
            preview = self.action_registry.preview(action_id, args)
            total_ms = (time.perf_counter() - started_at) * 1000.0
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
                timings={
                    "total_ms": total_ms,
                    "context_ms": context_ms,
                    "web_ms": 0.0,
                    "llm_ms": 0.0,
                },
                analysis_mode="deep" if deep_mode else "operational",
            )

        if self._is_smalltalk_message(message):
            total_ms = (time.perf_counter() - started_at) * 1000.0
            return ChatResponse(
                text=(
                    "Hey. I can help with company analysis or cockpit operations. "
                    "Try `analyse BHP` or ask an operations question."
                ),
                evidence=[
                    {
                        "type": "local_context",
                        "details": {
                            "query": message,
                            "ticker": None,
                            "reports": [],
                            "matches": [],
                            "note": "smalltalk_short_circuit",
                        },
                    }
                ],
                timings={
                    "total_ms": total_ms,
                    "context_ms": 0.0,
                    "web_ms": 0.0,
                    "llm_ms": 0.0,
                },
                analysis_mode="deep" if deep_mode else "operational",
            )

        if self._is_ticker_universe_request(message):
            context_started_at = time.perf_counter()
            rows = self.tool_router.db_reader.list_recent_doc_tickers(limit=40)
            context_ms = (time.perf_counter() - context_started_at) * 1000.0
            if rows:
                symbols = [str(row.get("ticker") or "").strip().upper() for row in rows]
                symbols = [s for s in symbols if s]
                display = symbols[:25]
                text = "I currently have announcement docs indexed for: " + ", ".join(display) + "."
                if len(symbols) > len(display):
                    text += f" (+{len(symbols) - len(display)} more)"
            else:
                text = "This cannot be verified based on available data."
                if self.tool_router.db_reader.last_error:
                    text += " Announcement index is currently unavailable."
            total_ms = (time.perf_counter() - started_at) * 1000.0
            return ChatResponse(
                text=text,
                evidence=[
                    {
                        "type": "local_context",
                        "details": {
                            "query": message,
                            "ticker": None,
                            "ticker_coverage": rows[:40],
                            "note": "ticker_universe_short_circuit",
                        },
                    }
                ],
                timings={
                    "total_ms": total_ms,
                    "context_ms": context_ms,
                    "web_ms": 0.0,
                    "llm_ms": 0.0,
                },
                analysis_mode="deep" if deep_mode else "operational",
            )

        if global_announcement_scope:
            context_started_at = time.perf_counter()
            rows = self.tool_router.db_reader.list_recent_documents(limit=12)
            context_ms = (time.perf_counter() - context_started_at) * 1000.0
            text = self._build_global_docs_reply(rows)
            if not rows and self.tool_router.db_reader.last_error:
                text += " Announcement index is currently unavailable."
            total_ms = (time.perf_counter() - started_at) * 1000.0
            return ChatResponse(
                text=text,
                evidence=[
                    {
                        "type": "local_context",
                        "details": {
                            "query": message,
                            "ticker": None,
                            "docs": rows[:12],
                            "note": "global_announcements_short_circuit",
                        },
                    }
                ],
                timings={
                    "total_ms": total_ms,
                    "context_ms": context_ms,
                    "web_ms": 0.0,
                    "llm_ms": 0.0,
                },
                analysis_mode="deep" if deep_mode else "operational",
            )

        historical_price_query = self._parse_historical_price_request(message, ticker=ticker)
        if historical_price_query:
            context_started_at = time.perf_counter()
            bundle: dict[str, Any] = {}
            window_loader = getattr(self.tool_router, "get_price_context_for_window", None)
            if callable(window_loader):
                bundle = window_loader(
                    ticker=ticker or "",
                    range_="max",
                    interval="1d",
                    max_history_rows=5000 if deep_mode else 3200,
                )
                state = bundle.get("price_state") if isinstance(bundle, dict) else {}
                if not (isinstance(state, dict) and state.get("ok")):
                    bundle = window_loader(
                        ticker=ticker or "",
                        range_="10y",
                        interval="1d",
                        max_history_rows=3200,
                    )

            if not isinstance(bundle, dict) or not bundle:
                local_payload = self.tool_router.gather_local_context(
                    ticker=ticker,
                    query=message,
                    deep_mode=True,
                ).payload
                bundle = {
                    "price": local_payload.get("price", {}) if isinstance(local_payload, dict) else {},
                    "price_state": local_payload.get("price_state", {}) if isinstance(local_payload, dict) else {},
                }

            context_ms = (time.perf_counter() - context_started_at) * 1000.0
            price_payload = bundle.get("price", {}) if isinstance(bundle, dict) else {}
            price_state = bundle.get("price_state", {}) if isinstance(bundle, dict) else {}
            text = self._build_historical_price_reply(
                price_payload if isinstance(price_payload, dict) else {},
                price_state if isinstance(price_state, dict) else {},
                historical_price_query,
            )
            total_ms = (time.perf_counter() - started_at) * 1000.0
            return ChatResponse(
                text=text,
                evidence=[
                    {
                        "type": "local_context",
                        "details": {
                            "query": message,
                            "ticker": ticker,
                            "price_history_query": historical_price_query,
                            "price": price_payload if isinstance(price_payload, dict) else {},
                            "price_state": price_state if isinstance(price_state, dict) else {},
                        },
                    }
                ],
                timings={
                    "total_ms": total_ms,
                    "context_ms": context_ms,
                    "web_ms": 0.0,
                    "llm_ms": 0.0,
                },
                analysis_mode="deep" if deep_mode else "operational",
            )

        if self._is_price_request(message, ticker=ticker):
            context_started_at = time.perf_counter()
            local_payload = self.tool_router.gather_local_context(
                ticker=ticker,
                query=message,
                deep_mode=deep_mode,
            ).payload
            context_ms = (time.perf_counter() - context_started_at) * 1000.0
            text = self._build_price_reply(
                local_payload.get("price", {}),
                local_payload.get("price_state", {}),
            )
            total_ms = (time.perf_counter() - started_at) * 1000.0
            return ChatResponse(
                text=text,
                evidence=[{"type": "local_context", "details": local_payload}],
                timings={
                    "total_ms": total_ms,
                    "context_ms": context_ms,
                    "web_ms": 0.0,
                    "llm_ms": 0.0,
                },
                analysis_mode="deep" if deep_mode else "operational",
            )

        structured_analysis = self._requests_structured_analysis(message, ticker=ticker, prior_ticker=prior_ticker)
        narrow_ticker_query = bool(ticker and self._is_narrow_ticker_query(message, ticker=ticker))
        if structured_analysis and deep_mode and ticker and not enable_web:
            total_ms = (time.perf_counter() - started_at) * 1000.0
            return ChatResponse(
                text=(
                    "Deep mode can auto-run web enrichment for company analysis, but web access is disabled. "
                    "Do you want me to enable web enrichment for this session? "
                    "Use `/confirm` to approve (your previous request will auto-resume) or `/cancel`."
                ),
                evidence=[
                    {
                        "type": "local_context",
                        "details": {
                            "query": message,
                            "ticker": ticker,
                            "note": "deep_mode_web_enrichment_requires_web_access",
                        },
                    }
                ],
                action_preview=self._build_access_request_preview("web"),
                timings={
                    "total_ms": total_ms,
                    "context_ms": 0.0,
                    "web_ms": 0.0,
                    "llm_ms": 0.0,
                },
                analysis_mode="deep",
            )
        if structured_analysis and ("http://" in message.lower() or "https://" in message.lower()) and not enable_web:
            total_ms = (time.perf_counter() - started_at) * 1000.0
            return ChatResponse(
                text=(
                    "This request includes a URL but web fetch is disabled. "
                    "I can request temporary web access for this session. "
                    "Use `/confirm` to approve (your previous request will auto-resume) or `/cancel`."
                ),
                evidence=[
                    {
                        "type": "local_context",
                        "details": {
                            "query": message,
                            "ticker": ticker,
                            "note": "web_access_required_for_url_evidence",
                        },
                    }
                ],
                action_preview=self._build_access_request_preview("web"),
                timings={
                    "total_ms": total_ms,
                    "context_ms": 0.0,
                    "web_ms": 0.0,
                    "llm_ms": 0.0,
                },
                analysis_mode="deep" if deep_mode else "operational",
            )

        qual_reader = (
            getattr(self.tool_router, "qual_context_company_reader", None)
            or getattr(self.tool_router, "qual_context_news_reader", None)
            or getattr(self.tool_router, "qual_context_reader", None)
        )
        qual_enabled = bool(getattr(self.tool_router, "qual_context_enabled", False))
        if structured_analysis and deep_mode and ticker and qual_reader is not None and not qual_enabled:
            total_ms = (time.perf_counter() - started_at) * 1000.0
            return ChatResponse(
                text=(
                    "Deep analysis can use qualitative context, but it is currently disabled. "
                    "I can request enabling RAG context for this session. "
                    "Use `/confirm` to approve (your previous request will auto-resume) or `/cancel`."
                ),
                evidence=[
                    {
                        "type": "local_context",
                        "details": {
                            "query": message,
                            "ticker": ticker,
                            "note": "rag_access_available_but_disabled",
                        },
                    }
                ],
                action_preview=self._build_access_request_preview("rag"),
                timings={
                    "total_ms": total_ms,
                    "context_ms": 0.0,
                    "web_ms": 0.0,
                    "llm_ms": 0.0,
                },
                analysis_mode="deep",
            )

        web_offer_note: str | None = None
        web_offer_preview: dict[str, Any] | None = None
        if structured_analysis and ticker and not deep_mode and not enable_web and self._wants_full_report(message):
            web_offer_note = (
                "Optional: I can also search the web for external context and recent sources. "
                "Use `/confirm` to approve web access for this session, or `/cancel` to keep local-only analysis."
            )
            web_offer_preview = self._build_access_request_preview("web")

        context_started_at = time.perf_counter()
        if structured_analysis or narrow_ticker_query:
            local_payload = self.tool_router.gather_local_context(
                ticker=ticker,
                query=message,
                deep_mode=deep_mode,
            ).payload
        else:
            local_payload = {
                "query": message,
                "ticker": None,
                "reports": [],
                "matches": [],
                "note": "operational_conversation_no_company_analysis",
            }
        update_offer_note: str | None = None
        update_offer_preview: dict[str, Any] | None = None
        if (structured_analysis or narrow_ticker_query) and ticker and isinstance(local_payload, dict):
            docs_for_sync = local_payload.get("docs")
            docs_for_sync = docs_for_sync if isinstance(docs_for_sync, list) else []
            sync_status = self._compute_announcement_sync_status(
                ticker=ticker,
                docs=docs_for_sync,
                message=message,
            )
            local_payload["announcement_sync"] = sync_status
            update_offer = self._build_ticker_update_offer(ticker=ticker, sync_status=sync_status)
            if isinstance(update_offer, dict):
                note = str(update_offer.get("note") or "").strip()
                if note:
                    update_offer_note = note
                preview = update_offer.get("action_preview")
                if isinstance(preview, dict):
                    update_offer_preview = preview
        context_ms = (time.perf_counter() - context_started_at) * 1000.0
        evidence = [{"type": "local_context", "details": local_payload}]

        if narrow_ticker_query:
            docs = local_payload.get("docs") if isinstance(local_payload, dict) else []
            docs = docs if isinstance(docs, list) else []
            text = self._build_ticker_docs_reply(ticker=ticker, docs=docs)
            if update_offer_note:
                text = f"{text}\n\n{update_offer_note}"
            if web_offer_note:
                text = f"{text}\n\n{web_offer_note}"

            total_ms = (time.perf_counter() - started_at) * 1000.0
            return ChatResponse(
                text=text,
                evidence=evidence,
                action_preview=update_offer_preview or web_offer_preview,
                timings={
                    "total_ms": total_ms,
                    "context_ms": context_ms,
                    "web_ms": 0.0,
                    "llm_ms": 0.0,
                },
                analysis_mode="deep" if deep_mode else "operational",
            )

        # In operational mode, keep analysis deterministic and grounded to local evidence.
        # This avoids free-form model drift for generic "analyse <ticker>" requests.
        if structured_analysis and ticker and not deep_mode:
            text = self._build_operational_analysis_brief(ticker=ticker, local_payload=local_payload)
            if update_offer_note:
                text = f"{text}\n\n{update_offer_note}"
            if web_offer_note:
                text = f"{text}\n\n{web_offer_note}"
            total_ms = (time.perf_counter() - started_at) * 1000.0
            return ChatResponse(
                text=text,
                evidence=evidence,
                action_preview=update_offer_preview or web_offer_preview,
                timings={
                    "total_ms": total_ms,
                    "context_ms": context_ms,
                    "web_ms": 0.0,
                    "llm_ms": 0.0,
                },
                analysis_mode="operational",
            )

        # Avoid drifting into made-up company analysis when no company target is provided.
        if structured_analysis and not ticker and "http" not in message.lower():
            text = (
                "Please specify a ticker (for example: `analyse BHP`) so I can anchor the answer to real documents. "
                "If you want the index universe, ask: `what tickers do you have announcements for`."
            )
            total_ms = (time.perf_counter() - started_at) * 1000.0
            return ChatResponse(
                text=text,
                evidence=evidence,
                timings={
                    "total_ms": total_ms,
                    "context_ms": context_ms,
                    "web_ms": 0.0,
                    "llm_ms": 0.0,
                },
                analysis_mode="deep" if deep_mode else "operational",
            )

        web_ms = 0.0
        web_prompt_payload: dict[str, Any] | None = None
        if enable_web and structured_analysis:
            maybe_url = re.search(r"https?://\S+", message)
            web_started_at = time.perf_counter()
            if maybe_url:
                web = self.tool_router.fetch_web(
                    maybe_url.group(0),
                    enabled=True,
                    max_chars=None if deep_mode else 8000,
                )
                web_ms = (time.perf_counter() - web_started_at) * 1000.0
                evidence.append({"type": "web", "details": web.payload})
                if web.ok:
                    web_prompt_payload = {
                        "url": web.payload.get("url"),
                        "content": str(web.payload.get("content") or ""),
                    }
                else:
                    web_prompt_payload = {
                        "url": web.payload.get("url"),
                        "error": web.payload.get("error"),
                    }
            elif deep_mode and ticker:
                web_query = self._build_company_web_enrichment_query(ticker=ticker, message=message)
                preferred_domains = []
                if isinstance(local_payload, dict):
                    domains = local_payload.get("web_preferred_domains")
                    if isinstance(domains, list):
                        preferred_domains = [str(domain).strip() for domain in domains if str(domain).strip()]
                web = self.tool_router.web_enrich(
                    web_query,
                    enabled=True,
                    max_results=4,
                    max_chars_per_page=3500,
                    preferred_domains=preferred_domains,
                    strict_official=True,
                )
                web_ms = (time.perf_counter() - web_started_at) * 1000.0
                evidence.append({"type": "web", "details": web.payload})
                if isinstance(local_payload, dict) and isinstance(web.payload, dict):
                    facts = web.payload.get("facts")
                    local_payload["web_facts"] = facts if isinstance(facts, list) else []
                    local_payload["web_source_quality"] = {
                        "official_source_required": web.payload.get("official_source_required"),
                        "official_source_found": web.payload.get("official_source_found"),
                        "official_candidates_found": web.payload.get("official_candidates_found"),
                        "facts_count": web.payload.get("facts_count"),
                        "preferred_domains": web.payload.get("preferred_domains"),
                    }
                web_prompt_payload = web.payload if isinstance(web.payload, dict) else {"query": web_query}

        has_local_evidence = self._has_verifiable_local_evidence(local_payload)
        has_web_evidence = False
        if isinstance(web_prompt_payload, dict):
            if str(web_prompt_payload.get("content") or "").strip():
                has_web_evidence = True
            pages = web_prompt_payload.get("pages")
            if isinstance(pages, list):
                has_web_evidence = has_web_evidence or any(
                    isinstance(page, dict) and bool(str(page.get("content") or "").strip())
                    for page in pages
                )
        if structured_analysis and ticker and deep_mode and not has_local_evidence and not has_web_evidence:
            answer = "This cannot be verified based on available data."
            if update_offer_note:
                answer = f"{answer}\n\n{update_offer_note}"
            if web_offer_note:
                answer = f"{answer}\n\n{web_offer_note}"
            total_ms = (time.perf_counter() - started_at) * 1000.0
            return ChatResponse(
                text=answer,
                evidence=evidence,
                action_preview=update_offer_preview or web_offer_preview,
                timings={
                    "total_ms": total_ms,
                    "context_ms": context_ms,
                    "web_ms": web_ms,
                    "llm_ms": 0.0,
                },
                analysis_mode="deep",
            )

        system_prompt = DEEP_ANALYSIS_SYSTEM_PROMPT if deep_mode else OPERATIONAL_SYSTEM_PROMPT
        prompt = f"{system_prompt}\n\n"
        if structured_analysis:
            local_payload_for_prompt = self._sanitize_prompt_local_payload(local_payload, deep_mode=deep_mode)
            local_context_json = json.dumps(local_payload_for_prompt)
            if not deep_mode:
                local_context_json = local_context_json[:7000]
            if deep_mode:
                prompt += (
                    "DEEP MODE OUTPUT CONTRACT:\n"
                    "- Do not output a methodology, framework outline, or step-by-step plan.\n"
                    "- Provide direct analysis conclusions grounded only in the evidence JSON.\n"
                    "- Include sections in this exact order and heading text:\n"
                    "  Verdict:\n"
                    "  Evidence:\n"
                    "  Risks:\n"
                    "  Counterpoints:\n"
                    "  Unknowns:\n"
                    "- In Evidence, include 4-8 bullets with concrete anchors (date + title/file and/or qual score).\n"
                    "- Every Evidence bullet must end with: [source: <doc title or file label>].\n"
                    "- If evidence is missing, state exactly: This cannot be verified based on available data.\n\n"
                )
            prompt += (
                f"User question: {message}\n\n"
                "Local evidence JSON:\n"
                f"{local_context_json}\n"
            )
        else:
            prompt += (
                "Operational conversation mode for this message:\n"
                "- The user did not request a company analysis report.\n"
                "- Respond briefly and directly.\n"
                "- Do not output the 9-section company analysis template.\n"
                "- Do not infer a ticker, company, portfolio fields, or data.\n\n"
                f"User question: {message}\n"
            )
        if web_prompt_payload is not None:
            web_json = json.dumps(web_prompt_payload)
            if not deep_mode:
                web_json = web_json[:4500]
            prompt += "\nWeb evidence JSON:\n" + web_json + "\n"

        llm_started_at = time.perf_counter()
        prompt_used = prompt
        answer = self.ollama_client.chat(prompt_used, timeout=self.llm_timeout_seconds, on_chunk=on_chunk)
        # Some small models occasionally echo policy/prompt text instead of answering.
        if self._looks_like_prompt_echo(answer):
            retry_prompt = (
                prompt
                + "\n\nCRITICAL RESPONSE FIX:\n"
                + "- Do not restate system instructions or policy.\n"
                + "- Answer only the user's question directly.\n"
                + "- Max 6 concise lines.\n"
            )
            retry_answer = self.ollama_client.chat(retry_prompt, timeout=self.llm_timeout_seconds, on_chunk=None)
            if self._looks_like_prompt_echo(retry_answer):
                answer = "This cannot be verified based on available data."
            else:
                prompt_used = retry_prompt
                answer = retry_answer
        docs_for_relevance = local_payload.get("docs") if isinstance(local_payload, dict) else []
        docs_for_relevance = docs_for_relevance if isinstance(docs_for_relevance, list) else []
        if structured_analysis and ticker and self._looks_like_off_topic_analysis(
            answer,
            ticker=ticker,
            docs=docs_for_relevance,
        ):
            retry_prompt = (
                prompt
                + "\n\nCRITICAL RELEVANCE FIX:\n"
                + f"- You must analyze only ticker {ticker}.\n"
                + "- Use only the provided local evidence JSON and optional web evidence.\n"
                + "- If evidence is insufficient, respond exactly: This cannot be verified based on available data.\n"
                + "- Never switch to unrelated domains or synthetic documents.\n"
            )
            retry_answer = self.ollama_client.chat(retry_prompt, timeout=self.llm_timeout_seconds, on_chunk=None)
            if self._looks_like_prompt_echo(retry_answer) or self._looks_like_off_topic_analysis(
                retry_answer,
                ticker=ticker,
                docs=docs_for_relevance,
            ):
                answer = self._build_grounded_analysis_fallback(ticker=ticker, local_payload=local_payload)
            else:
                prompt_used = retry_prompt
                answer = retry_answer
        if structured_analysis and deep_mode and ticker and self._looks_like_framework_only_analysis(
            answer,
            ticker=ticker,
            local_payload=local_payload,
        ):
            retry_prompt = (
                prompt
                + "\n\nCRITICAL GROUNDING FIX:\n"
                + f"- Analyze only {ticker} using provided evidence.\n"
                + "- Do not output any framework/methodology language.\n"
                + "- Start with a direct verdict sentence.\n"
                + "- Then provide Evidence bullets with concrete anchors (date + title/file or qual score).\n"
                + "- End every Evidence bullet with [source: <doc title or file label>].\n"
                + "- If required evidence is missing, say: This cannot be verified based on available data.\n"
            )
            retry_answer = self.ollama_client.chat(retry_prompt, timeout=self.llm_timeout_seconds, on_chunk=None)
            if self._looks_like_prompt_echo(retry_answer) or self._looks_like_framework_only_analysis(
                retry_answer,
                ticker=ticker,
                local_payload=local_payload,
            ):
                answer = self._build_grounded_deep_analysis_brief(
                    ticker=ticker,
                    message=message,
                    local_payload=local_payload,
                )
            else:
                prompt_used = retry_prompt
                answer = retry_answer
        if structured_analysis and deep_mode and ticker and self._violates_deep_output_contract(answer):
            retry_prompt = (
                prompt
                + "\n\nCRITICAL STRUCTURE FIX:\n"
                + "- Output only these top-level headers in this exact order: Verdict, Evidence, Risks, Counterpoints, Unknowns.\n"
                + "- Each header must end with a colon.\n"
                + "- Evidence must include 4-8 bullets with concrete anchors (YYYY-MM-DD and/or score 0.xxx).\n"
                + "- Every Evidence bullet must end with [source: <doc title or file label>].\n"
                + "- No methodology text, no framework outline, no process steps.\n"
                + "- If evidence is missing, use exactly: This cannot be verified based on available data.\n"
            )
            retry_answer = self.ollama_client.chat(retry_prompt, timeout=self.llm_timeout_seconds, on_chunk=None)
            if (
                self._looks_like_prompt_echo(retry_answer)
                or self._looks_like_framework_only_analysis(
                    retry_answer,
                    ticker=ticker,
                    local_payload=local_payload,
                )
                or self._violates_deep_output_contract(retry_answer)
            ):
                answer = self._build_grounded_deep_analysis_brief(
                    ticker=ticker,
                    message=message,
                    local_payload=local_payload,
                )
            else:
                prompt_used = retry_prompt
                answer = retry_answer
        if ticker and not deep_mode and self._looks_like_fabricated_letter(answer):
            docs = local_payload.get("docs") if isinstance(local_payload, dict) else []
            docs = docs if isinstance(docs, list) else []
            answer = self._build_ticker_docs_reply(ticker=ticker, docs=docs)
        if structured_analysis and ticker and not has_local_evidence and not has_web_evidence:
            if not self._has_verification_disclaimer(answer):
                answer = "This cannot be verified based on available data."
        if update_offer_note:
            answer = f"{answer.strip()}\n\n{update_offer_note}"
        if web_offer_note:
            answer = f"{answer.strip()}\n\n{web_offer_note}"
        llm_ms = (time.perf_counter() - llm_started_at) * 1000.0
        total_ms = (time.perf_counter() - started_at) * 1000.0

        return ChatResponse(
            text=answer.strip(),
            evidence=evidence,
            action_preview=update_offer_preview or web_offer_preview,
            timings={
                "total_ms": total_ms,
                "context_ms": context_ms,
                "web_ms": web_ms,
                "llm_ms": llm_ms,
            },
            analysis_mode="deep" if deep_mode else "operational",
            prompt=prompt_used,
        )

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
