from __future__ import annotations

import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from cockpit.core.types import ToolResult


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
    ) -> None:
        self.db_reader = db_reader
        self.file_indexer = file_indexer
        self.web_fetcher = web_fetcher
        self.backend_api_client = backend_api_client
        self.qual_context_company_reader = (
            qual_context_company_reader if qual_context_company_reader is not None else qual_context_reader
        )
        self.qual_context_news_reader = qual_context_news_reader
        # Backward-compatible alias for existing call sites/tests.
        self.qual_context_reader = self.qual_context_company_reader
        self.repo_root = Path(repo_root).resolve()
        self.web_default_enabled = web_default_enabled
        self.qual_context_enabled = any(
            reader is not None
            for reader in (self.qual_context_company_reader, self.qual_context_news_reader)
        )
        self._ticker_cache_ttl_seconds = 15.0
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

    def _query_qual_context_reader(
        self,
        reader,
        *,
        query: str,
        ticker: str,
        deep_mode: bool,
        top_k: int,
    ) -> dict[str, Any]:
        if reader is None:
            return {"ok": False, "hits": [], "error": "reader not configured"}
        try:
            payload = reader.query(
                query=query,
                company=ticker,
                deep_mode=deep_mode,
                top_k=top_k,
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

        company_hits_raw = (company_payload or {}).get("hits")
        news_hits_raw = (news_payload or {}).get("hits")
        company_hits = [row for row in company_hits_raw if isinstance(row, dict)] if isinstance(company_hits_raw, list) else []
        news_hits = [row for row in news_hits_raw if isinstance(row, dict)] if isinstance(news_hits_raw, list) else []

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
            "reports": self.file_indexer.list_recent_reports(limit=reports_limit),
            "matches": self.file_indexer.search_text(pattern=query, limit=matches_limit),
        }
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
                            "excerpt": excerpt,
                        }
                    )
            payload["financials"] = ticker_payload.get("financials", [])
            payload["data_quality"] = self._build_data_quality_payload(
                extraction_failures=[row for row in extraction_failures if isinstance(row, dict)],
                low_conf_rows=[row for row in low_conf_rows if isinstance(row, dict)],
                confidence_threshold=float(ticker_payload.get("low_confidence_threshold", low_confidence_threshold)),
                deep_mode=deep_mode,
            )
            price_bundle = self._load_price_context(ticker=ticker, deep_mode=deep_mode)
            payload["price"] = price_bundle.get("price", {})
            payload["price_state"] = price_bundle.get("price_state", self._compute_price_state(payload["price"]))
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
            if db_error:
                payload["db_warning"] = (
                    "Database unavailable or schema not initialized for cockpit reads. "
                    f"db_url={getattr(self.db_reader, 'database_url', 'unknown')}"
                )
                payload["db_error"] = str(db_error)[:400]
            if self.qual_context_enabled and (
                self.qual_context_company_reader is not None or self.qual_context_news_reader is not None
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
                    )
                    payload["qual_context_company"] = company_payload
                if self.qual_context_news_reader is not None:
                    news_payload = self._query_qual_context_reader(
                        self.qual_context_news_reader,
                        query=query,
                        ticker=ticker,
                        deep_mode=deep_mode,
                        top_k=rag_news_limit,
                    )
                    payload["qual_context_news"] = news_payload
                payload["qual_context"] = self._merge_qual_context_hits(
                    company_payload=company_payload,
                    news_payload=news_payload,
                    deep_mode=deep_mode,
                )
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
