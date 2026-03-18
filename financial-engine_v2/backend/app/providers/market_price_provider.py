from datetime import datetime, timezone

import httpx


YAHOO_CHART_PATH = "/v8/finance/chart"
DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_BASE_URL = "https://query1.finance.yahoo.com"

EXCHANGE_SUFFIX = {
    "ASX": "AX",
    "LSE": "L",
    "TSX": "TO",
    "HKEX": "HK",
    "NYSE": "",
    "NASDAQ": "",
}


class MarketPriceProviderError(RuntimeError):
    pass


def _as_iso(ts):
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
    except Exception:
        return None


def _at(values, idx):
    if not isinstance(values, list):
        return None
    if idx < 0 or idx >= len(values):
        return None
    value = values[idx]
    return value if value is not None else None


class MarketPriceProvider:
    def __init__(self, base_url=DEFAULT_BASE_URL, timeout=DEFAULT_TIMEOUT_SECONDS):
        self.base_url = str(base_url).rstrip("/")
        self.timeout = float(timeout)

    def _candidate_base_urls(self) -> list[str]:
        primary = str(self.base_url).rstrip("/")
        candidates = [primary]
        lower = primary.lower()
        if "query1.finance.yahoo.com" in lower:
            candidates.append(primary.replace("query1.finance.yahoo.com", "query2.finance.yahoo.com"))
        elif "query2.finance.yahoo.com" in lower:
            candidates.append(primary.replace("query2.finance.yahoo.com", "query1.finance.yahoo.com"))
        deduped: list[str] = []
        seen: set[str] = set()
        for item in candidates:
            if item in seen:
                continue
            seen.add(item)
            deduped.append(item)
        return deduped

    def _normalize_symbol(self, ticker, exchange):
        symbol = str(ticker or "").strip().upper()
        if not symbol:
            raise ValueError("ticker is required")
        if "." in symbol:
            return symbol
        suffix = EXCHANGE_SUFFIX.get(str(exchange or "ASX").strip().upper(), "")
        return f"{symbol}.{suffix}" if suffix else symbol

    def fetch(self, ticker, exchange="ASX", range_="1mo", interval="1d"):
        if not str(range_ or "").strip():
            raise ValueError("range is required")
        if not str(interval or "").strip():
            raise ValueError("interval is required")

        symbol = self._normalize_symbol(ticker=ticker, exchange=exchange)
        params = {
            "range": str(range_).strip(),
            "interval": str(interval).strip(),
            "includePrePost": "false",
            "events": "div,splits",
        }

        payload = None
        last_http_error: httpx.HTTPStatusError | None = None
        last_error: Exception | None = None
        for base_url in self._candidate_base_urls():
            url = f"{base_url}{YAHOO_CHART_PATH}/{symbol}"
            try:
                with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                    response = client.get(
                        url,
                        params=params,
                        headers={"User-Agent": "Mozilla/5.0"},
                    )
                    response.raise_for_status()
                    payload = response.json()
                break
            except httpx.HTTPStatusError as exc:
                last_http_error = exc
                code = exc.response.status_code if exc.response is not None else None
                # Yahoo sometimes rate-limits one edge host; try alternate host before failing.
                if code == 429:
                    continue
                last_error = exc
                continue
            except Exception as exc:
                last_error = exc
                continue

        if payload is None:
            if last_http_error is not None:
                code = last_http_error.response.status_code if last_http_error.response is not None else "unknown"
                if code == 429:
                    raise MarketPriceProviderError(
                        "market price provider rate limited (HTTP 429); retry shortly"
                    ) from last_http_error
                raise MarketPriceProviderError(f"market price provider returned HTTP {code}") from last_http_error
            if last_error is not None:
                raise MarketPriceProviderError(f"market price request failed: {last_error}") from last_error
            raise MarketPriceProviderError("market price request failed: unknown error")

        chart = payload.get("chart") or {}
        provider_error = chart.get("error")
        if provider_error:
            detail = provider_error.get("description") if isinstance(provider_error, dict) else str(provider_error)
            raise MarketPriceProviderError(detail or "market price provider returned an error")

        results = chart.get("result") or []
        if not results:
            raise MarketPriceProviderError("market price provider returned no result")

        result = results[0] or {}
        meta = result.get("meta") or {}
        quote = ((result.get("indicators") or {}).get("quote") or [{}])[0] or {}
        timestamps = result.get("timestamp") or []

        history = []
        for i, ts in enumerate(timestamps):
            history.append(
                {
                    "timestamp": _as_iso(ts),
                    "open": _at(quote.get("open"), i),
                    "high": _at(quote.get("high"), i),
                    "low": _at(quote.get("low"), i),
                    "close": _at(quote.get("close"), i),
                    "volume": _at(quote.get("volume"), i),
                }
            )

        return {
            "provider": "yahoo_finance",
            "ticker": str(ticker or "").strip().upper(),
            "symbol": symbol,
            "exchange": str(exchange or "").strip().upper() or None,
            "currency": meta.get("currency"),
            "timezone": meta.get("exchangeTimezoneName"),
            "exchange_name": meta.get("exchangeName"),
            "range": params["range"],
            "interval": params["interval"],
            "current": {
                "price": meta.get("regularMarketPrice"),
                "previous_close": meta.get("chartPreviousClose") or meta.get("previousClose"),
                "open": meta.get("regularMarketOpen"),
                "day_high": meta.get("regularMarketDayHigh"),
                "day_low": meta.get("regularMarketDayLow"),
                "volume": meta.get("regularMarketVolume"),
                "market_time": _as_iso(meta.get("regularMarketTime")),
            },
            "history": history,
        }
