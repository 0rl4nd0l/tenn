from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Callable


DATA_MISSING_MESSAGE = "This cannot be verified based on available data."
PriceReplyBuilder = Callable[[dict[str, Any], dict[str, Any] | None], str]


class AnswerReadiness:
    PROMPT_ECHO_MARKERS = (
        "final context prompt for custom gpt",
        "custom gpt:",
        "as of my last update",
        "i am unable to directly access real-time",
        "you've provided",
        "user question regarding",
        "trading thesis.docx",
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
        "here\u2019s a structured approach",
        "here's a structured approach",
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
    def looks_like_prompt_echo(cls, answer: str) -> bool:
        text = (answer or "").strip().lower()
        if not text:
            return False
        if text.startswith("final context prompt for custom gpt"):
            return True
        marker_hits = sum(1 for marker in cls.PROMPT_ECHO_MARKERS if marker in text)
        return marker_hits >= 2

    @staticmethod
    def build_ticker_docs_reply(ticker: str, docs: list[dict[str, Any]]) -> str:
        if not docs:
            return f"{DATA_MISSING_MESSAGE}. No indexed announcements were found for {ticker}."

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
    def parse_timestamp_utc(value: Any) -> datetime | None:
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
    def is_announcement_recency_request(message: str) -> bool:
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
    def compute_announcement_sync_status(
        cls,
        ticker: str,
        docs: list[dict[str, Any]],
        message: str,
    ) -> dict[str, Any]:
        now_utc = datetime.now(timezone.utc)
        threshold = (
            cls.ANNOUNCEMENT_STALE_HOURS_RECENCY
            if cls.is_announcement_recency_request(message)
            else cls.ANNOUNCEMENT_STALE_HOURS_DEFAULT
        )
        latest_dt: datetime | None = None
        for row in docs:
            if not isinstance(row, dict):
                continue
            dt = cls.parse_timestamp_utc(row.get("published_at"))
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
                "reason": f"latest indexed announcement is {age_hours:.1f}h old (threshold {threshold:.0f}h)",
            }
        )
        return result

    @classmethod
    def looks_like_fabricated_letter(cls, answer: str) -> bool:
        text = (answer or "").strip().lower()
        if not text:
            return False
        return sum(1 for marker in cls.FABRICATED_LETTER_MARKERS if marker in text) >= 2

    @staticmethod
    def has_verification_disclaimer(answer: str) -> bool:
        return DATA_MISSING_MESSAGE.lower() in str(answer or "").strip().lower()

    @staticmethod
    def has_verifiable_local_evidence(local_payload: dict[str, Any]) -> bool:
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
    def looks_like_off_topic_analysis(
        cls,
        answer: str,
        ticker: str | None,
        docs: list[dict[str, Any]],
    ) -> bool:
        text = (answer or "").strip().lower()
        if not text:
            return True

        if cls.has_verification_disclaimer(text):
            return False

        if any(marker in text for marker in cls.OFF_TOPIC_ANALYSIS_MARKERS):
            return True

        ticker_token_present = False
        if ticker:
            t = re.escape(str(ticker).strip().lower())
            if t:
                ticker_token_present = (
                    re.search(rf"\b{t}\b", text) is not None or re.search(rf"\b{t}\.ax\b", text) is not None
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

        if len(text) >= 70 and not ticker_token_present and not title_token_present:
            return True
        if len(text) >= 500 and not ticker_token_present and not title_token_present:
            return True
        if len(text) >= 1200 and not title_token_present:
            return True

        return False

    @classmethod
    def looks_like_framework_only_analysis(
        cls,
        answer: str,
        ticker: str | None,
        local_payload: dict[str, Any],
    ) -> bool:
        text = str(answer or "").strip().lower()
        if not text:
            return True
        if cls.has_verification_disclaimer(text):
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
    def find_deep_section_spans(cls, answer: str) -> dict[str, tuple[int, int]]:
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
    def missing_deep_required_headers(cls, answer: str) -> list[str]:
        spans = cls.find_deep_section_spans(answer)
        missing = [header for header in cls.DEEP_REQUIRED_HEADERS if header not in spans]
        if missing:
            return missing
        starts = [spans[header][0] for header in cls.DEEP_REQUIRED_HEADERS]
        if starts != sorted(starts):
            return ["SectionOrder"]
        return []

    @classmethod
    def extract_deep_section_body(
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
    def violates_deep_output_contract(cls, answer: str) -> bool:
        text = str(answer or "").strip()
        if not text:
            return True
        missing = cls.missing_deep_required_headers(text)
        if missing:
            return True

        spans = cls.find_deep_section_spans(text)
        for header in cls.DEEP_REQUIRED_HEADERS:
            body = cls.extract_deep_section_body(text, spans, header)
            if not body:
                return True

        evidence_body = cls.extract_deep_section_body(text, spans, "Evidence")
        if DATA_MISSING_MESSAGE.lower() in evidence_body.lower():
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
            line for line in evidence_bullets if DATA_MISSING_MESSAGE.lower() not in line.lower()
        ]
        if non_disclaimer_bullets and any(source_anchor_pattern.search(line) is None for line in non_disclaimer_bullets):
            return True
        return False

    @staticmethod
    def build_global_docs_reply(rows: list[dict[str, Any]]) -> str:
        if not rows:
            return f"{DATA_MISSING_MESSAGE}."

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

    @classmethod
    def build_grounded_analysis_fallback(
        cls,
        ticker: str,
        local_payload: dict[str, Any],
        build_price_reply: PriceReplyBuilder,
    ) -> str:
        docs = local_payload.get("docs") if isinstance(local_payload, dict) else []
        docs = docs if isinstance(docs, list) else []
        lines = [
            f"{DATA_MISSING_MESSAGE}. The generated analysis was not sufficiently grounded to {ticker}."
        ]
        lines.append("Returning verified local context instead:")
        lines.append(cls.build_ticker_docs_reply(ticker=ticker, docs=docs))

        price_payload = local_payload.get("price") if isinstance(local_payload, dict) else {}
        price_state = local_payload.get("price_state") if isinstance(local_payload, dict) else {}
        if isinstance(price_state, dict) and price_state.get("ok"):
            price_line = build_price_reply(
                price_payload if isinstance(price_payload, dict) else {},
                price_state if isinstance(price_state, dict) else {},
            ).splitlines()
            if price_line:
                lines.append(f"Latest price context: {price_line[0]}")
        return "\n".join(lines)

    @staticmethod
    def clean_qual_anchor_label(row: dict[str, Any]) -> str:
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
    def clean_signal_text(text: str, max_chars: int = 220) -> str:
        normalized = re.sub(r"\s+", " ", str(text or "")).strip(" \t\r\n-:;,.")
        if len(normalized) <= max_chars:
            return normalized
        return normalized[:max_chars].rstrip(" ,;:.") + "..."

    @classmethod
    def extract_signal_fragments(cls, text: str, *, max_fragments: int = 2) -> list[str]:
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
            frag = cls.clean_signal_text(content[start:end], max_chars=220)
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

    @classmethod
    def collect_liquidity_signal_rows(
        cls,
        *,
        qual_hits: list[dict[str, Any]],
        doc_snippets: list[dict[str, Any]],
        max_rows: int = 4,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        seen_keys: set[str] = set()

        def _row_source_label(row: dict[str, Any]) -> str:
            if "file" in row or "doc_date" in row:
                return cls.clean_qual_anchor_label(row)
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
            fragments = cls.extract_signal_fragments(str(row.get("text") or ""), max_fragments=2)
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
    def build_data_quality_evidence_bullets(data_quality: dict[str, Any], *, limit: int = 2) -> list[str]:
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
            out.append(f"- {day_prefix}Extraction failed for {title}.{suffix} [source: extraction_runs/documents]")
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
    def build_price_horizon_evidence_bullets(price_horizons: dict[str, Any], *, limit: int = 2) -> list[str]:
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
    def build_web_fact_evidence_bullets(web_facts: list[dict[str, Any]], *, limit: int = 2) -> list[str]:
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

    @classmethod
    def build_grounded_deep_analysis_brief(
        cls,
        ticker: str,
        message: str,
        local_payload: dict[str, Any],
        build_price_reply: PriceReplyBuilder,
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

        evidence_bullets.extend(cls.build_data_quality_evidence_bullets(data_quality=data_quality, limit=2))

        signal_rows = cls.collect_liquidity_signal_rows(
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
                title = cls.clean_qual_anchor_label(row)
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
        price_text = build_price_reply(
            price_payload if isinstance(price_payload, dict) else {},
            price_state if isinstance(price_state, dict) else {},
        )
        price_lines = [row for row in str(price_text).splitlines() if row.strip()]
        price_ok = isinstance(price_state, dict) and bool(price_state.get("ok"))
        if price_ok and price_lines and len(evidence_bullets) < 8:
            evidence_bullets.append(f"- Market context: {price_lines[0]} [source: price_state]")

        if len(evidence_bullets) < 8:
            for bullet in cls.build_price_horizon_evidence_bullets(price_horizons=price_horizons, limit=2):
                evidence_bullets.append(bullet)
                if len(evidence_bullets) >= 8:
                    break

        if len(evidence_bullets) < 8:
            for bullet in cls.build_web_fact_evidence_bullets(web_facts=web_facts, limit=2):
                evidence_bullets.append(bullet)
                if len(evidence_bullets) >= 8:
                    break

        if not evidence_bullets:
            evidence_bullets = [f"- {DATA_MISSING_MESSAGE}."]
        elif len(evidence_bullets) < 4:
            evidence_bullets.extend([f"- {DATA_MISSING_MESSAGE}."] * (4 - len(evidence_bullets)))

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
            risks.append(f"- {DATA_MISSING_MESSAGE}. Key current financial metrics were not present in extracted financial rows.")
        if not docs:
            risks.append(f"- {DATA_MISSING_MESSAGE}. No indexed filing anchors were available.")
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
            counterpoints.append(f"- {DATA_MISSING_MESSAGE}.")

        unknowns: list[str] = [
            "- Liquidity runway, debt maturity ladder, and covenant headroom are unknown unless explicitly disclosed in the retrieved excerpts.",
            f"- {DATA_MISSING_MESSAGE}.",
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

    @classmethod
    def build_operational_analysis_brief(
        cls,
        ticker: str,
        local_payload: dict[str, Any],
        build_price_reply: PriceReplyBuilder,
    ) -> str:
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
            lines.append(f"{DATA_MISSING_MESSAGE}. No indexed announcements were found.")

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
            lines.append(f"Financial snapshot: {DATA_MISSING_MESSAGE}.")

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
        price_text = build_price_reply(
            price_payload if isinstance(price_payload, dict) else {},
            price_state if isinstance(price_state, dict) else {},
        )
        lines.append("Price context:")
        for row in str(price_text).splitlines()[:4]:
            lines.append(f"- {row}")

        lines.append(f"Use `deep analysis analyse {ticker}` for full 9-section LLM analysis.")
        return "\n".join(lines)
