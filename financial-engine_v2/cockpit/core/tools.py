from __future__ import annotations

import logging
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from cockpit.core.types import ToolResult

logger = logging.getLogger(__name__)


class ToolRouter:
    def __init__(
        self,
        db_reader,
        file_indexer,
        web_fetcher,
        repo_root: Path,
        web_default_enabled: bool,
        backend_api_client=None,
        qual_context_reader=None,
        qual_context_company_reader=None,
        qual_context_news_reader=None,
        news_context_db_path: str = "",
        news_context_corpus_filter: str = "news",
        state_store=None,
        brave_search_client=None,
        hn_search_client=None,
    ) -> None:
        self.db_reader = db_reader
        self.file_indexer = file_indexer
        self.web_fetcher = web_fetcher
        self.backend_api_client = backend_api_client
        self.brave_search_client = brave_search_client
        self.hn_search_client = hn_search_client
        self.qual_context_company_reader = (
            qual_context_company_reader if qual_context_company_reader is not None else qual_context_reader
        )
        self.qual_context_news_reader = qual_context_news_reader
        # Backward-compatible alias for existing call sites/tests.
        self.qual_context_reader = self.qual_context_company_reader
        self.repo_root = Path(repo_root).resolve()
        self.web_default_enabled = web_default_enabled
        self.news_context_db_path = str(news_context_db_path or "").strip()
        self.news_context_corpus_filter = str(news_context_corpus_filter or "news").strip()
        self._state_store = state_store
        self.qual_context_enabled = (
            any(
                reader is not None
                for reader in (self.qual_context_company_reader, self.qual_context_news_reader)
            )
            or bool(self.news_context_db_path)
        )
        self.dossier_service = None
        self._ticker_cache_ttl_seconds = 120.0
        self._ticker_cache: dict[tuple[Any, ...], tuple[float, dict[str, Any]]] = {}
        self._price_cache_ttl_seconds = 20.0
        self._price_cache: dict[tuple[str, str, str, int], tuple[float, dict[str, Any]]] = {}
        self._excerpt_cache: dict[str, tuple[float, str]] = {}

    def _resolve_doc_path(self, path_value: str | None) -> Path | None:
        if not path_value:
            return None
        path = Path(path_value)
        if not path.is_absolute():
            path = self.repo_root / path
        return path.resolve()

    def _extract_pdf_excerpt(self, pdf_path: Path, max_chars: int = 1500) -> str:
        cache_key = str(pdf_path)
        try:
            mtime = pdf_path.stat().st_mtime
        except Exception:
            return ""

        cached = self._excerpt_cache.get(cache_key)
        if cached and cached[0] == mtime:
            return cached[1]

        try:
            import fitz  # type: ignore
        except Exception:
            return ""
        if not pdf_path.exists() or not pdf_path.is_file():
            return ""
        try:
            with fitz.open(pdf_path) as pdf:
                if pdf.page_count < 1:
                    return ""
                text = pdf[0].get_text() or ""
        except Exception:
            return ""
        excerpt = " ".join(text.split())[:max_chars]
        if len(self._excerpt_cache) >= 256:
            oldest = min(self._excerpt_cache.items(), key=lambda item: item[1][0])[0]
            self._excerpt_cache.pop(oldest, None)
        self._excerpt_cache[cache_key] = (mtime, excerpt)
        return excerpt

    def _load_ticker_context(
        self,
        ticker: str,
        docs_limit: int = 10,
        context_limit: int = 10,
        financials_limit: int = 5,
        extraction_failures_limit: int = 8,
        low_confidence_limit: int = 8,
        low_confidence_threshold: float = 0.4,
    ) -> dict[str, Any]:
        ticker_key = ticker.upper()
        cache_key = (
            ticker_key,
            docs_limit,
            context_limit,
            financials_limit,
            extraction_failures_limit,
            low_confidence_limit,
            float(low_confidence_threshold),
        )
        now = time.monotonic()
        cached = self._ticker_cache.get(cache_key)
        if cached and now - cached[0] <= self._ticker_cache_ttl_seconds:
            return cached[1]

        docs = self.db_reader.get_docs(ticker_key, limit=docs_limit)
        context_rows = self.db_reader.get_announcement_context(ticker_key, limit=context_limit)
        financials = self.db_reader.get_financials(ticker_key, limit=financials_limit)
        extraction_failures = self.db_reader.get_extraction_failures(
            limit=extraction_failures_limit,
            ticker=ticker_key,
        )
        low_confidence_financials = self.db_reader.get_low_confidence_financials(
            threshold=low_confidence_threshold,
            limit=low_confidence_limit,
            ticker=ticker_key,
        )
        db_error = self.db_reader.last_error

        payload = {
            "docs": docs,
            "context_rows": context_rows,
            "financials": financials,
            "extraction_failures": extraction_failures,
            "low_confidence_financials": low_confidence_financials,
            "low_confidence_threshold": float(low_confidence_threshold),
            "db_error": db_error,
        }
        self._ticker_cache[cache_key] = (now, payload)
        return payload

    @staticmethod
    def _compact_price_payload(price_payload: dict[str, Any], max_history_rows: int) -> dict[str, Any]:
        current = price_payload.get("current", {}) if isinstance(price_payload, dict) else {}
        history = price_payload.get("history", []) if isinstance(price_payload, dict) else []
        if not isinstance(history, list):
            history = []
        recent = [row for row in history if isinstance(row, dict)][-max_history_rows:]

        price = current.get("price")
        previous_close = current.get("previous_close")
        change = None
        change_percent = None
        try:
            if price is not None and previous_close not in (None, 0):
                change = float(price) - float(previous_close)
                change_percent = (change / float(previous_close)) * 100.0
        except Exception:
            change = None
            change_percent = None

        return {
            "ok": True,
            "provider": price_payload.get("provider"),
            "ticker": price_payload.get("ticker"),
            "symbol": price_payload.get("symbol"),
            "exchange": price_payload.get("exchange"),
            "currency": price_payload.get("currency"),
            "timezone": price_payload.get("timezone"),
            "exchange_name": price_payload.get("exchange_name"),
            "range": price_payload.get("range"),
            "interval": price_payload.get("interval"),
            "current": {
                "price": price,
                "previous_close": previous_close,
                "change": change,
                "change_percent": change_percent,
                "open": current.get("open"),
                "day_high": current.get("day_high"),
                "day_low": current.get("day_low"),
                "volume": current.get("volume"),
                "market_time": current.get("market_time"),
            },
            "recent_history": [
                {
                    "timestamp": row.get("timestamp"),
                    "open": row.get("open"),
                    "high": row.get("high"),
                    "low": row.get("low"),
                    "close": row.get("close"),
                    "volume": row.get("volume"),
                }
                for row in recent
            ],
        }

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        try:
            parsed = float(value)
        except Exception:
            return None
        if not math.isfinite(parsed):
            return None
        return parsed

    @staticmethod
    def _parse_timestamp_utc(value: Any) -> datetime | None:
        text = str(value or "").strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except Exception:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @classmethod
    def _compute_price_state(cls, price_payload: dict[str, Any]) -> dict[str, Any]:
        ticker = str((price_payload or {}).get("ticker") or "").strip().upper() or None
        symbol = str((price_payload or {}).get("symbol") or "").strip().upper() or ticker
        currency = (price_payload or {}).get("currency")
        history_rows = []
        if isinstance(price_payload, dict):
            if isinstance(price_payload.get("history"), list):
                history_rows = price_payload.get("history") or []
            elif isinstance(price_payload.get("recent_history"), list):
                history_rows = price_payload.get("recent_history") or []

        if not isinstance(price_payload, dict) or price_payload.get("ok") is False:
            return {
                "ok": False,
                "ticker": ticker,
                "symbol": symbol,
                "currency": currency,
                "last_close": None,
                "previous_close_effective": None,
                "trend_regime": "neutral",
                "ret_1d": None,
                "ret_5d": None,
                "ret_20d": None,
                "ret_63d": None,
                "sma20": None,
                "sma50": None,
                "rsi_14": None,
                "vol_20d_ann": None,
                "drawdown_from_63d_high": None,
                "market_time_utc": None,
                "data_age_hours": None,
                "stale_data": True,
                "history_points": 0,
                "insufficient_history": True,
                "error": str((price_payload or {}).get("error") or "price lookup failed"),
            }

        deduped: dict[str, tuple[datetime | None, float]] = {}
        for row in history_rows:
            if not isinstance(row, dict):
                continue
            close = cls._safe_float(row.get("close"))
            if close is None:
                continue
            timestamp = row.get("timestamp")
            dt = cls._parse_timestamp_utc(timestamp)
            key = dt.isoformat() if dt is not None else str(timestamp or "").strip()
            if not key:
                continue
            deduped[key] = (dt, close)

        ordered = list(deduped.items())
        ordered.sort(key=lambda item: ((item[1][0].timestamp() if item[1][0] else float("inf")), item[0]))
        closes = [item[1][1] for item in ordered]
        history_points = len(closes)

        current = price_payload.get("current", {}) if isinstance(price_payload.get("current"), dict) else {}
        last_close = closes[-1] if closes else cls._safe_float(current.get("price"))
        previous_close_effective = (
            closes[-2]
            if len(closes) >= 2
            else cls._safe_float(current.get("previous_close"))
        )

        def _ret(days: int) -> float | None:
            if len(closes) <= days:
                return None
            base = closes[-(days + 1)]
            if base == 0:
                return None
            return ((closes[-1] / base) - 1.0) * 100.0

        def _sma(window: int) -> float | None:
            if len(closes) < window:
                return None
            values = closes[-window:]
            return sum(values) / float(window)

        ret_1d = _ret(1)
        ret_5d = _ret(5)
        ret_20d = _ret(20)
        ret_63d = _ret(63)
        sma20 = _sma(20)
        sma50 = _sma(50)

        # RSI-14 (Wilder smoothing, requires >= 14 bars)
        rsi_14: float | None = None
        if len(closes) >= 14:
            deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
            gains = [d if d > 0 else 0.0 for d in deltas]
            losses = [-d if d < 0 else 0.0 for d in deltas]

            # Initial averages over first 14 periods
            avg_gain = sum(gains[:14]) / 14
            avg_loss = sum(losses[:14]) / 14

            # Wilder smoothing for remaining periods
            for i in range(14, len(gains)):
                avg_gain = (avg_gain * 13 + gains[i]) / 14
                avg_loss = (avg_loss * 13 + losses[i]) / 14

            if avg_loss == 0:
                rsi_14 = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi_14 = 100.0 - (100.0 / (1.0 + rs))

            rsi_14 = round(rsi_14, 1)

        vol_20d_ann = None
        if len(closes) >= 21:
            window = closes[-21:]
            log_returns: list[float] = []
            for prev, nxt in zip(window[:-1], window[1:]):
                if prev <= 0 or nxt <= 0:
                    continue
                value = math.log(nxt / prev)
                if math.isfinite(value):
                    log_returns.append(value)
            if len(log_returns) >= 2:
                mean = sum(log_returns) / len(log_returns)
                var = sum((x - mean) ** 2 for x in log_returns) / (len(log_returns) - 1)
                vol_20d_ann = math.sqrt(var) * math.sqrt(252.0) * 100.0

        drawdown_from_63d_high = None
        if last_close is not None and closes:
            window = closes[-63:]
            peak = max(window) if window else None
            if peak and peak > 0:
                drawdown_from_63d_high = ((last_close / peak) - 1.0) * 100.0

        trend_regime = "neutral"
        if last_close is not None and sma20 is not None and sma50 is not None:
            if last_close > sma20 and sma20 > sma50:
                trend_regime = "bull"
            elif last_close < sma20 and sma20 < sma50:
                trend_regime = "bear"
        elif last_close is not None and sma20 is not None:
            if last_close > sma20:
                trend_regime = "bull"
            elif last_close < sma20:
                trend_regime = "bear"

        market_time_utc = current.get("market_time")
        market_dt = cls._parse_timestamp_utc(market_time_utc)
        data_age_hours = None
        stale_data = True
        if market_dt is not None:
            age = (datetime.now(timezone.utc) - market_dt).total_seconds() / 3600.0
            data_age_hours = max(0.0, age)
            stale_data = data_age_hours > 96.0
            market_time_utc = market_dt.isoformat()

        return {
            "ok": True,
            "ticker": ticker,
            "symbol": symbol,
            "currency": currency,
            "last_close": last_close,
            "previous_close_effective": previous_close_effective,
            "trend_regime": trend_regime,
            "ret_1d": ret_1d,
            "ret_5d": ret_5d,
            "ret_20d": ret_20d,
            "ret_63d": ret_63d,
            "sma20": sma20,
            "sma50": sma50,
            "rsi_14": rsi_14,
            "vol_20d_ann": vol_20d_ann,
            "drawdown_from_63d_high": drawdown_from_63d_high,
            "market_time_utc": market_time_utc,
            "data_age_hours": data_age_hours,
            "stale_data": stale_data,
            "history_points": history_points,
            "insufficient_history": history_points < 63,
            "error": None,
        }

    def _load_price_context_for_window(
        self,
        ticker: str,
        *,
        range_: str,
        interval: str = "1d",
        max_history_rows: int = 260,
    ) -> dict[str, Any]:
        ticker_key = str(ticker or "").strip().upper()
        if not ticker_key:
            error_payload = {"ok": False, "error": "ticker is required"}
            return {
                "price": error_payload,
                "price_state": self._compute_price_state(error_payload),
            }
        if self.backend_api_client is None:
            error_payload = {"ok": False, "ticker": ticker_key, "error": "backend_api_client is not configured"}
            return {
                "price": error_payload,
                "price_state": self._compute_price_state(error_payload),
            }

        range_value = str(range_ or "").strip() or "3mo"
        interval_value = str(interval or "").strip() or "1d"
        max_rows = int(max(1, max_history_rows))
        cache_key = (ticker_key, range_value, interval_value, max_rows)
        now = time.monotonic()
        cached = self._price_cache.get(cache_key)
        if cached and now - cached[0] <= self._price_cache_ttl_seconds:
            return cached[1]

        result = self.backend_api_client.get_price(
            ticker=ticker_key,
            exchange="ASX",
            range_=range_value,
            interval=interval_value,
            timeout=12.0,
        )
        if result.get("ok"):
            payload = result.get("payload", {})
            compact = self._compact_price_payload(
                payload if isinstance(payload, dict) else {},
                max_history_rows=max_rows,
            )
            price_state = self._compute_price_state(payload if isinstance(payload, dict) else compact)
            cached_payload = {"price": compact, "price_state": price_state}
            self._price_cache[cache_key] = (now, cached_payload)
            return cached_payload

        error_payload = {
            "ok": False,
            "ticker": ticker_key,
            "range": range_value,
            "interval": interval_value,
            "error": str(result.get("error") or "price lookup failed"),
            "status_code": result.get("status_code"),
        }
        cached_payload = {
            "price": error_payload,
            "price_state": self._compute_price_state(error_payload),
        }
        self._price_cache[cache_key] = (now, cached_payload)
        return cached_payload

    def _load_price_context(self, ticker: str, *, deep_mode: bool) -> dict[str, Any]:
        return self._load_price_context_for_window(
            ticker=ticker,
            range_="1y" if deep_mode else "3mo",
            interval="1d",
            max_history_rows=260 if deep_mode else 120,
        )

    def get_price_context_for_window(
        self,
        ticker: str,
        *,
        range_: str = "10y",
        interval: str = "1d",
        max_history_rows: int = 3000,
    ) -> dict[str, Any]:
        return self._load_price_context_for_window(
            ticker=ticker,
            range_=range_,
            interval=interval,
            max_history_rows=max_history_rows,
        )

    def build_candlestick_ohlc_lines(
        self,
        ticker: str,
        *,
        range_: str = "1y",
        interval: str = "1d",
        max_history_rows: int = 260,
    ) -> list[dict]:
        """Extract OHLCV rows for candlestick chart.

        Returns list of dicts with keys: timestamp, open, high, low, close, volume.
        Returns empty list if no price data available.
        """
        try:
            bundle = self.get_price_context_for_window(
                ticker,
                range_=range_,
                interval=interval,
                max_history_rows=max_history_rows,
            )
            price = bundle.get("price") if isinstance(bundle, dict) else {}
            price = price if isinstance(price, dict) else {}
            if price.get("ok") is False:
                raise RuntimeError(str(price.get("error") or "price lookup failed"))
            history = price.get("recent_history")
            if not isinstance(history, list) or not history:
                return []
            rows: list[dict] = []
            for row in history:
                if not isinstance(row, dict):
                    continue
                rows.append(
                    {
                        "timestamp": row.get("timestamp"),
                        "open": row.get("open"),
                        "high": row.get("high"),
                        "low": row.get("low"),
                        "close": row.get("close"),
                        "volume": row.get("volume"),
                    }
                )
            return rows
        except RuntimeError:
            raise
        except Exception:
            return []

    def get_price_state(self, ticker: str, *, deep_mode: bool = False) -> dict[str, Any]:
        bundle = self._load_price_context(ticker=ticker, deep_mode=deep_mode)
        state = bundle.get("price_state")
        if isinstance(state, dict):
            return state
        return self._compute_price_state(bundle.get("price", {}))

    @staticmethod
    def _normalize_domain(value: str | None) -> str:
        raw = str(value or "").strip().lower()
        if not raw:
            return ""
        parsed = urlparse(raw if "://" in raw else f"https://{raw}")
        domain = str(parsed.netloc or parsed.path or "").strip().lower()
        if ":" in domain:
            domain = domain.split(":", 1)[0]
        if domain.startswith("www."):
            domain = domain[4:]
        return domain

    def get_preferred_web_domains(
        self,
        *,
        ticker: str | None = None,
        docs: list[dict[str, Any]] | None = None,
    ) -> list[str]:
        selected_docs = docs if isinstance(docs, list) else []
        if not selected_docs and ticker:
            ticker_key = str(ticker or "").strip().upper()
            if ticker_key:
                selected_docs = self.db_reader.get_docs(ticker_key, limit=30)

        out: list[str] = ["asx.com.au"]
        seen = {"asx.com.au"}
        for row in selected_docs:
            if not isinstance(row, dict):
                continue
            domain = self._normalize_domain(str(row.get("source_url") or ""))
            if not domain or domain in seen:
                continue
            seen.add(domain)
            out.append(domain)
        return out

    @staticmethod
    def _build_financials_narrative(financials: list[dict]) -> str:
        """Build a human-readable financial trend summary for LLM context."""
        if not financials or len(financials) < 1:
            return ""

        latest = financials[0]
        prior = financials[1] if len(financials) > 1 else {}

        parts = []

        # Revenue trend
        rev = latest.get("revenue")
        rev_prior = prior.get("revenue")
        if rev is not None:
            if rev_prior and rev_prior != 0:
                rev_yoy = (rev - rev_prior) / abs(rev_prior) * 100
                direction = "grew" if rev_yoy > 0 else "declined"
                parts.append(f"Revenue {direction} {abs(rev_yoy):.1f}% YoY to ${rev:,.0f}.")
            else:
                parts.append(f"Latest revenue: ${rev:,.0f}.")

        # EBIT margin
        ebit = latest.get("ebit")
        if ebit is not None and rev and rev != 0:
            margin = ebit / rev * 100
            parts.append(f"EBIT margin: {margin:.1f}%.")

        # FCF signal
        ocf = latest.get("operating_cf")
        capex = latest.get("capex")
        if ocf is not None and capex is not None:
            fcf = ocf - abs(capex)
            signal = "positive" if fcf > 0 else "negative"
            parts.append(f"Free cash flow is {signal} at ${fcf:,.0f}.")

        # Net debt
        net_debt = latest.get("net_debt")
        if net_debt is not None:
            if net_debt < 0:
                parts.append(f"Balance sheet is net cash (${abs(net_debt):,.0f}).")
            elif net_debt > 0:
                parts.append(f"Net debt: ${net_debt:,.0f}.")

        # EBIT trend
        ebit_prior = prior.get("ebit")
        if ebit is not None and ebit_prior is not None and ebit_prior != 0:
            ebit_yoy = (ebit - ebit_prior) / abs(ebit_prior) * 100
            direction = "improved" if ebit_yoy > 0 else "deteriorated"
            parts.append(f"EBIT {direction} {abs(ebit_yoy):.1f}% YoY.")

        return " ".join(parts) if parts else ""

    @staticmethod
    def _build_data_quality_payload(
        *,
        extraction_failures: list[dict[str, Any]],
        low_conf_rows: list[dict[str, Any]],
        confidence_threshold: float,
        deep_mode: bool,
    ) -> dict[str, Any]:
        fail_limit = 8 if deep_mode else 4
        low_conf_limit = 8 if deep_mode else 4
        trimmed_failures: list[dict[str, Any]] = []
        for row in extraction_failures[:fail_limit]:
            if not isinstance(row, dict):
                continue
            trimmed_failures.append(
                {
                    "ticker": row.get("ticker"),
                    "published_at": row.get("published_at"),
                    "title": row.get("title"),
                    "status": row.get("status"),
                    "error": row.get("error"),
                    "created_at": row.get("created_at"),
                    "document_id": row.get("document_id"),
                }
            )

        trimmed_low_conf: list[dict[str, Any]] = []
        for row in low_conf_rows[:low_conf_limit]:
            if not isinstance(row, dict):
                continue
            trimmed_low_conf.append(
                {
                    "ticker": row.get("ticker"),
                    "period_end": row.get("period_end"),
                    "period_type": row.get("period_type"),
                    "confidence_metrics": row.get("confidence_metrics"),
                    "source_document_id": row.get("source_document_id"),
                }
            )

        return {
            "extraction_failed_count_recent": len([row for row in extraction_failures if isinstance(row, dict)]),
            "low_conf_financial_count_recent": len([row for row in low_conf_rows if isinstance(row, dict)]),
            "confidence_threshold": float(confidence_threshold),
            "recent_failures": trimmed_failures,
            "recent_low_conf_rows": trimmed_low_conf,
        }

    def _query_news_sqlite_context(
        self,
        ticker: str,
        corpus_filter: str,
        top_k: int = 10,
    ) -> dict[str, Any]:
        """Read pre-ranked news chunks from context_chunks SQLite table."""
        import json as _json
        import sqlite3 as _sqlite3

        db = Path(self.news_context_db_path).expanduser().resolve()
        if not db.exists():
            return {"ok": False, "hits": [], "source": "news_sqlite_context", "error": "db not found"}

        ticker_upper = str(ticker or "").strip().upper()
        conn = _sqlite3.connect(str(db))
        conn.row_factory = _sqlite3.Row
        try:
            col_cursor = conn.execute("PRAGMA table_info(context_chunks)")
            columns = {row[1] for row in col_cursor.fetchall()}
            has_relevance = "ticker_relevance_json" in columns

            rows = conn.execute(
                "SELECT * FROM context_chunks WHERE ticker LIKE ? ORDER BY published_at DESC",
                (f"%|{ticker_upper}|%",),
            ).fetchall()
        finally:
            conn.close()

        # Apply corpus prefix filter.
        def _matches(corpus: str) -> bool:
            return not corpus_filter or str(corpus or "").startswith(corpus_filter)

        filtered = [r for r in rows if _matches(str(r["corpus"] or ""))]

        # Build hits, parse relevance, dedupe by URL (keep best score).
        hits_by_url: dict[str, dict[str, Any]] = {}
        for row in filtered:
            url = str(row["url"] or "")
            final_score = 0.5
            ticker_relation_type = "mention"
            if has_relevance:
                try:
                    rel = _json.loads(str(row["ticker_relevance_json"] or "{}") or "{}")
                    td = rel.get(ticker_upper) if isinstance(rel, dict) else None
                    if isinstance(td, dict):
                        final_score = float(td.get("score") or 0.5)
                        ticker_relation_type = str(td.get("label") or "mention")
                except Exception:
                    pass
            hit: dict[str, Any] = {
                "chunk_id": str(row["chunk_id"] or ""),
                "corpus": str(row["corpus"] or ""),
                "title": str(row["title"] or ""),
                "text": str(row["text"] or ""),
                "source": str(row["source"] or ""),
                "url": url,
                "published_at": str(row["published_at"] or ""),
                "ticker": str(row["ticker"] or ""),
                "company": str(row["company"] or ""),
                "final_score": final_score,
                "ticker_relation_type": ticker_relation_type,
                "source_corpus": str(row["corpus"] or ""),
            }
            if url not in hits_by_url or final_score > hits_by_url[url]["final_score"]:
                hits_by_url[url] = hit

        hits = sorted(hits_by_url.values(), key=lambda h: h["final_score"], reverse=True)[:top_k]
        return {
            "ok": True,
            "hits": hits,
            "source": "news_sqlite_context",
            "candidate_count": len(filtered),
            "filtered_count": len(hits),
        }

    def _query_qual_context_reader(
        self,
        reader,
        *,
        query: str,
        ticker: str,
        deep_mode: bool,
        top_k: int,
        company_filter: str | None = None,
        ticker_filter: str = "",
        source_filter: str = "",
    ) -> dict[str, Any]:
        if reader is None:
            return {"ok": False, "hits": [], "error": "reader not configured"}
        company_value = str(company_filter if company_filter is not None else ticker).strip().upper()
        ticker_value = str(ticker_filter or "").strip().upper()
        source_value = str(source_filter or "").strip()
        try:
            payload = reader.query(
                query=query,
                company=company_value,
                deep_mode=deep_mode,
                top_k=top_k,
                ticker_filter=ticker_value,
                source_filter=source_value,
            )
        except Exception as exc:
            return {"ok": False, "hits": [], "error": str(exc)[:400]}
        if not isinstance(payload, dict):
            return {"ok": False, "hits": [], "error": "invalid RAG payload"}
        hits = payload.get("hits")
        payload["hits"] = hits if isinstance(hits, list) else []
        payload.setdefault("ok", False)
        return payload

    @staticmethod
    def _merge_qual_context_hits(
        *,
        company_payload: dict[str, Any] | None,
        news_payload: dict[str, Any] | None,
        deep_mode: bool,
    ) -> dict[str, Any]:
        company_quota = 8 if deep_mode else 4
        news_quota = 4 if deep_mode else 2

        MIN_RAG_SCORE = 0.35

        company_hits_raw = (company_payload or {}).get("hits")
        news_hits_raw = (news_payload or {}).get("hits")
        company_hits = [row for row in company_hits_raw if isinstance(row, dict)] if isinstance(company_hits_raw, list) else []
        news_hits = [row for row in news_hits_raw if isinstance(row, dict)] if isinstance(news_hits_raw, list) else []

        # Filter by minimum RAG score
        company_hits = [h for h in company_hits if h.get("final_score", h.get("semantic_score", 1.0)) >= MIN_RAG_SCORE]
        news_hits = [h for h in news_hits if h.get("final_score", h.get("semantic_score", 1.0)) >= MIN_RAG_SCORE]

        # Enforce max 2 chunks per source document
        def _dedup_by_doc(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
            doc_chunk_counts: dict[str, int] = {}
            deduped_hits: list[dict[str, Any]] = []
            for h in hits:
                chunk_id = h.get("chunk_id", "")
                doc_id = chunk_id.rsplit(":", 1)[0] if ":" in chunk_id else chunk_id
                if doc_chunk_counts.get(doc_id, 0) < 2:
                    deduped_hits.append(h)
                    doc_chunk_counts[doc_id] = doc_chunk_counts.get(doc_id, 0) + 1
            return deduped_hits

        company_hits = _dedup_by_doc(company_hits)
        news_hits = _dedup_by_doc(news_hits)

        selected_company = company_hits[:company_quota]
        selected_news = news_hits[:news_quota]

        merged: list[dict[str, Any]] = []
        i = 0
        j = 0
        while i < len(selected_company) or j < len(selected_news):
            if i < len(selected_company):
                row = dict(selected_company[i])
                row.setdefault("source_corpus", str(row.get("corpus") or "company"))
                merged.append(row)
                i += 1
            if j < len(selected_news):
                row = dict(selected_news[j])
                row.setdefault("source_corpus", str(row.get("corpus") or "news"))
                merged.append(row)
                j += 1

        return {
            "ok": bool(merged) or bool((company_payload or {}).get("ok")) or bool((news_payload or {}).get("ok")),
            "hits": merged,
            "merge_policy": "quota_interleave",
            "company_quota": company_quota,
            "news_quota": news_quota,
            "company_hit_count": len(selected_company),
            "news_hit_count": len(selected_news),
            "company_error": (company_payload or {}).get("error"),
            "news_error": (news_payload or {}).get("error"),
        }

    @classmethod
    def _build_price_horizon_metrics(cls, horizon: str, bundle: dict[str, Any]) -> dict[str, Any]:
        price = bundle.get("price") if isinstance(bundle, dict) else {}
        price = price if isinstance(price, dict) else {}
        state = bundle.get("price_state") if isinstance(bundle, dict) else {}
        state = state if isinstance(state, dict) else {}
        history_rows = price.get("recent_history")
        history_rows = history_rows if isinstance(history_rows, list) else []

        series: list[tuple[datetime | None, float]] = []
        for row in history_rows:
            if not isinstance(row, dict):
                continue
            close = cls._safe_float(row.get("close"))
            if close is None:
                continue
            dt = cls._parse_timestamp_utc(row.get("timestamp"))
            series.append((dt, close))

        series.sort(key=lambda item: item[0].timestamp() if item[0] is not None else float("inf"))
        closes = [item[1] for item in series]

        total_return_pct = None
        if len(closes) >= 2 and closes[0] > 0:
            total_return_pct = ((closes[-1] / closes[0]) - 1.0) * 100.0

        volatility_ann_pct = None
        if len(closes) >= 3:
            returns: list[float] = []
            for prev, nxt in zip(closes[:-1], closes[1:]):
                if prev <= 0 or nxt <= 0:
                    continue
                value = math.log(nxt / prev)
                if math.isfinite(value):
                    returns.append(value)
            if len(returns) >= 2:
                mean = sum(returns) / float(len(returns))
                variance = sum((x - mean) ** 2 for x in returns) / float(len(returns) - 1)
                volatility_ann_pct = math.sqrt(variance) * math.sqrt(252.0) * 100.0

        max_drawdown_pct = None
        if closes:
            peak = closes[0]
            drawdowns: list[float] = []
            for close in closes:
                peak = max(peak, close)
                if peak > 0:
                    drawdowns.append(((close / peak) - 1.0) * 100.0)
            if drawdowns:
                max_drawdown_pct = min(drawdowns)

        return {
            "ok": bool(state.get("ok")),
            "horizon": horizon,
            "total_return_pct": total_return_pct,
            "max_drawdown_pct": max_drawdown_pct,
            "volatility_ann_pct": volatility_ann_pct,
            "history_points": len(closes),
            "coverage_start_utc": series[0][0].isoformat() if series and series[0][0] else None,
            "coverage_end_utc": series[-1][0].isoformat() if series and series[-1][0] else None,
            "data_age_hours": state.get("data_age_hours"),
            "stale_data": state.get("stale_data"),
            "error": state.get("error"),
        }

    def get_news_context(
        self,
        query: str,
        *,
        top_k: int = 10,
        ticker: str | None = None,
        provider: str | None = None,
        language: str = "en",
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict[str, Any]:
        """Retrieve news context, preferring Qdrant via backend API with SQLite fallback.

        Returns a dict with keys:
          - ok: bool
          - hits: list of result dicts
          - _source: "qdrant" or "sqlite_fallback"
          - error: str or None
        """
        # Attempt Qdrant-first via backend API.
        if self.backend_api_client is not None:
            try:
                result = self.backend_api_client.rag_query(
                    q=query,
                    top_k=top_k,
                    ticker=ticker,
                    provider=provider,
                    language=language,
                    date_from=date_from,
                    date_to=date_to,
                )
                raw_results = result.get("results") if isinstance(result, dict) else None
                if isinstance(raw_results, list) and raw_results:
                    logger.info("news_context: source=qdrant results=%d", len(raw_results))
                    hits = [
                        {
                            "score": float(item.get("score", 0.0)) if isinstance(item, dict) else 0.0,
                            **({k: v for k, v in (item.get("payload") or {}).items()} if isinstance(item, dict) else {}),
                        }
                        for item in raw_results
                        if isinstance(item, dict)
                    ]
                    return {"ok": True, "hits": hits, "_source": "qdrant", "error": None}
            except Exception as exc:
                logger.info("news_context: qdrant unavailable (%s), falling back to sqlite", exc)

        # Fallback to SQLite via qual_context_news_reader.
        if self.qual_context_news_reader is not None:
            try:
                payload = self.qual_context_news_reader.query(
                    query=query,
                    company="",
                    deep_mode=False,
                    top_k=top_k,
                    ticker_filter=ticker or "",
                    date_from=date_from or "",
                    date_to=date_to or "",
                )
                if not isinstance(payload, dict):
                    payload = {}
                hits = payload.get("hits")
                hits = hits if isinstance(hits, list) else []
                logger.info("news_context: source=sqlite_fallback results=%d", len(hits))
                return {
                    "ok": bool(payload.get("ok")),
                    "hits": hits,
                    "_source": "sqlite_fallback",
                    "error": payload.get("error"),
                }
            except Exception as exc:
                logger.info("news_context: sqlite fallback failed: %s", exc)
                return {"ok": False, "hits": [], "_source": "sqlite_fallback", "error": str(exc)[:400]}

        logger.info("news_context: no backend or reader configured")
        return {"ok": False, "hits": [], "_source": "sqlite_fallback", "error": "no news source configured"}

    _FILE_SEARCH_KEYWORDS = (
        "report", "file", "document", "log", "output", "export", "read",
        "list", "show", "find", "search", "recent", "latest", "what's in",
    )

    @classmethod
    def _query_wants_file_search(cls, query: str) -> bool:
        lower = query.lower()
        return any(kw in lower for kw in cls._FILE_SEARCH_KEYWORDS)

    def gather_local_context(self, ticker: str | None, query: str, deep_mode: bool = False) -> ToolResult:
        reports_limit = 25 if deep_mode else 10
        matches_limit = 80 if deep_mode else 20
        docs_limit = 30 if deep_mode else 10
        context_limit = 30 if deep_mode else 10
        financials_limit = 15 if deep_mode else 5
        extraction_failures_limit = 12 if deep_mode else 6
        low_confidence_limit = 12 if deep_mode else 6
        low_confidence_threshold = 0.4
        snippets_limit = 15 if deep_mode else 5
        excerpt_chars = 3500 if deep_mode else 1500
        rag_company_limit = 8 if deep_mode else 4
        rag_news_limit = 4 if deep_mode else 2
        payload: dict[str, Any] = {
            "query": query,
            "ticker": ticker,
        }
        if deep_mode or self._query_wants_file_search(query):
            payload["reports"] = self.file_indexer.list_recent_reports(limit=reports_limit)
            payload["matches"] = self.file_indexer.search_text(pattern=query, limit=matches_limit)
        if ticker:
            ticker_payload = self._load_ticker_context(
                ticker,
                docs_limit=docs_limit,
                context_limit=context_limit,
                financials_limit=financials_limit,
                extraction_failures_limit=extraction_failures_limit,
                low_confidence_limit=low_confidence_limit,
                low_confidence_threshold=low_confidence_threshold,
            )
            docs = ticker_payload.get("docs", [])
            context_rows = ticker_payload.get("context_rows", [])
            db_error = ticker_payload.get("db_error")
            extraction_failures = ticker_payload.get("extraction_failures", [])
            extraction_failures = extraction_failures if isinstance(extraction_failures, list) else []
            low_conf_rows = ticker_payload.get("low_confidence_financials", [])
            low_conf_rows = low_conf_rows if isinstance(low_conf_rows, list) else []
            payload["docs"] = docs
            payload["web_preferred_domains"] = self.get_preferred_web_domains(ticker=ticker, docs=docs)
            payload["doc_snippets_source"] = "cockpit_announcement_context" if context_rows else "live_pdf_fallback"
            if context_rows:
                payload["doc_snippets"] = context_rows[:snippets_limit]
            else:
                payload["doc_snippets"] = []
                for row in docs[:snippets_limit]:
                    resolved = self._resolve_doc_path(str(row.get("pdf_path", "")))
                    excerpt = self._extract_pdf_excerpt(resolved, max_chars=excerpt_chars) if resolved else ""
                    payload["doc_snippets"].append(
                        {
                            "document_id": row.get("document_id"),
                            "title": row.get("title"),
                            "published_at": row.get("published_at"),
                            "pdf_path": row.get("pdf_path"),
                            "doc_class": row.get("doc_class"),
                            "excerpt": excerpt,
                        }
                    )
            financials = ticker_payload.get("financials", [])
            payload["financials"] = financials
            if financials:
                narrative = ToolRouter._build_financials_narrative(financials)
                if narrative:
                    payload["financials_narrative"] = narrative
            payload["data_quality"] = self._build_data_quality_payload(
                extraction_failures=[row for row in extraction_failures if isinstance(row, dict)],
                low_conf_rows=[row for row in low_conf_rows if isinstance(row, dict)],
                confidence_threshold=float(ticker_payload.get("low_confidence_threshold", low_confidence_threshold)),
                deep_mode=deep_mode,
            )
            price_bundle = self._load_price_context(ticker=ticker, deep_mode=deep_mode)
            payload["price"] = price_bundle.get("price", {})
            price_state = price_bundle.get("price_state", self._compute_price_state(payload["price"]))
            payload["price_state"] = price_state
            try:
                from backend.app.services.analysis.financial_metrics import compute_valuation_multiples  # type: ignore
                if price_state and price_state.get("last_close") and financials:
                    vm = compute_valuation_multiples(
                        price_last_close=price_state["last_close"],
                        financials_row=financials[0],
                    )
                    if vm:
                        payload["valuation_multiples"] = vm
            except ImportError:
                pass  # valuation multiples are best-effort
            except Exception:
                pass
            if deep_mode:
                horizons: dict[str, Any] = {}
                for horizon, max_rows in (
                    ("1y", 300),
                    ("3y", 900),
                    ("5y", 1500),
                    ("10y", 3000),
                ):
                    bundle = self.get_price_context_for_window(
                        ticker=ticker,
                        range_=horizon,
                        interval="1d",
                        max_history_rows=max_rows,
                    )
                    horizons[horizon] = self._build_price_horizon_metrics(horizon, bundle)
                payload["price_horizons"] = horizons
                # Attach price reaction to each doc snippet in deep mode
                doc_snippets = payload.get("doc_snippets", [])
                if doc_snippets:
                    try:
                        from cockpit.core.update_delta import build_close_series, compute_reaction_for_time
                        close_series = build_close_series(price_bundle.get("price", {}))
                        if close_series:
                            for snippet in doc_snippets:
                                published_at_raw = snippet.get("published_at")
                                if published_at_raw:
                                    pub_dt = self._parse_timestamp_utc(published_at_raw)
                                    if pub_dt is not None:
                                        reaction = compute_reaction_for_time(close_series, published_at=pub_dt)
                                        if reaction:
                                            snippet["price_reaction"] = reaction
                    except Exception:
                        pass  # best-effort
            if db_error:
                payload["db_warning"] = (
                    "Database unavailable or schema not initialized for cockpit reads. "
                    f"db_url={getattr(self.db_reader, 'database_url', 'unknown')}"
                )
                payload["db_error"] = str(db_error)[:400]
            if self.qual_context_enabled and (
                self.qual_context_company_reader is not None
                or self.qual_context_news_reader is not None
                or bool(self.news_context_db_path)
            ):
                company_payload = None
                news_payload = None
                if self.qual_context_company_reader is not None:
                    company_payload = self._query_qual_context_reader(
                        self.qual_context_company_reader,
                        query=query,
                        ticker=ticker,
                        deep_mode=deep_mode,
                        top_k=rag_company_limit,
                        company_filter=ticker,
                        ticker_filter="",
                    )
                    payload["qual_context_company"] = company_payload
                if self.qual_context_news_reader is not None:
                    news_payload = self._query_qual_context_reader(
                        self.qual_context_news_reader,
                        query=query,
                        ticker=ticker,
                        deep_mode=deep_mode,
                        top_k=rag_news_limit,
                        company_filter="",
                        ticker_filter=ticker,
                    )
                    payload["qual_context_news"] = news_payload
                elif self.news_context_db_path and ticker:
                    news_payload = self._query_news_sqlite_context(
                        ticker=ticker,
                        corpus_filter=self.news_context_corpus_filter,
                        top_k=rag_news_limit,
                    )
                    payload["qual_context_news"] = news_payload
                payload["qual_context"] = self._merge_qual_context_hits(
                    company_payload=company_payload,
                    news_payload=news_payload,
                    deep_mode=deep_mode,
                )
            # Inject watchlist history if ticker is being watched
            if ticker and self._state_store is not None:
                try:
                    watchlist = self._state_store.list_watch_tickers() if hasattr(self._state_store, "list_watch_tickers") else []
                    watched_tickers = [t["ticker"].upper() if isinstance(t, dict) else str(t).upper() for t in watchlist]
                    if ticker.upper() in watched_tickers:
                        update_events = (
                            self._state_store.list_update_events(
                                "", ticker=ticker, limit=5
                            )
                            if hasattr(self._state_store, "list_update_events")
                            else []
                        )
                        if update_events:
                            payload["watchlist_history"] = [
                                {
                                    "action": e.get("action_id"),
                                    "status": e.get("status"),
                                    "date": e.get("created_at", "")[:10],
                                    "summary": e.get("summary", e.get("summary_json", {})),
                                }
                                for e in update_events
                            ]
                except Exception:
                    pass
            # Inject agent memory: accumulated observations about this ticker
            if self._state_store is not None and ticker:
                try:
                    observations = self._state_store.get_entity_observations(ticker, limit=8)
                    if observations:
                        payload["agent_memory"] = observations
                except Exception:
                    pass
            # Inject dossier findings: prior research conclusions about this ticker
            if self.dossier_service is not None and ticker:
                try:
                    dossier_result = self.dossier_service.recall(ticker, limit=5)
                    findings = dossier_result.get("findings", []) if dossier_result.get("ok") else []
                    if findings:
                        payload["dossier_findings"] = [
                            {
                                "finding": f.get("finding", ""),
                                "category": f.get("category", ""),
                                "confidence": f.get("confidence", 0.0),
                                "source": f.get("source", ""),
                                "date": (f.get("ts") or "")[:10],
                            }
                            for f in findings
                        ]
                        payload["has_dossier_context"] = True
                except Exception:
                    pass
            # Inject most recent prior analysis export for this ticker (best-effort)
            if self._state_store is not None and ticker:
                try:
                    if hasattr(self._state_store, "list_exports"):
                        recent_exports = self._state_store.list_exports(limit=20)
                        ticker_upper = ticker.upper()
                        for exp in recent_exports:
                            question = str(exp.get("question") or "")
                            if ticker_upper in question.upper():
                                payload["prior_export"] = {
                                    "question": question[:200],
                                    "date": str(exp.get("created_at") or "")[:10],
                                }
                                break
                except Exception:
                    pass
        # Collect sources metadata for evidence footer
        sources: dict[str, Any] = {}
        qual = payload.get("qual_context") or {}
        merged_hits = qual.get("hits") or []
        if merged_hits:
            sources["rag_hits"] = [
                {
                    "title": str(h.get("title") or h.get("source_name") or "untitled"),
                    "score": float(h.get("final_score", h.get("semantic_score", 0.0))),
                    "doc_type": str(h.get("source_corpus") or h.get("corpus") or ""),
                }
                for h in merged_hits[:3]
            ]
        fins = payload.get("financials") or []
        if fins:
            sources["financial_periods"] = [
                (
                    str(f.get("ticker") or ticker or ""),
                    str(f.get("period_end") or f.get("period") or ""),
                    str(f.get("period_type") or ""),
                )
                for f in fins[:3]
            ]
        dossier_findings = payload.get("dossier_findings") or []
        sources["dossier_count"] = len(dossier_findings)
        sources["strategy_criteria_count"] = 0  # set by caller if strategy injected
        payload["sources"] = sources

        return ToolResult(ok=True, title="local_context", payload=payload)

    def fetch_web(self, url: str, enabled: bool, max_chars: int | None = 8000) -> ToolResult:
        if not enabled:
            return ToolResult(ok=False, title="web_disabled", payload={"error": "Web fetch is disabled"})
        try:
            body = self.web_fetcher.fetch_text(url, max_chars=max_chars)
            return ToolResult(ok=True, title="web_fetch", payload={"url": url, "content": body})
        except Exception as exc:
            return ToolResult(ok=False, title="web_fetch", payload={"url": url, "error": str(exc)})

    def web_enrich(
        self,
        query: str,
        *,
        enabled: bool,
        max_results: int = 3,
        max_chars_per_page: int = 3000,
        preferred_domains: list[str] | None = None,
        strict_official: bool = False,
    ) -> ToolResult:
        if not enabled:
            return ToolResult(ok=False, title="web_disabled", payload={"error": "Web fetch is disabled"})
        try:
            payload = self.web_fetcher.search_and_fetch(
                query=query,
                max_results=max_results,
                max_chars_per_page=max_chars_per_page,
                preferred_domains=preferred_domains,
                strict_official=bool(strict_official),
            )
            return ToolResult(ok=bool(payload.get("ok")), title="web_enrich", payload=payload)
        except Exception as exc:
            return ToolResult(
                ok=False,
                title="web_enrich",
                payload={"query": query, "error": str(exc)},
            )
