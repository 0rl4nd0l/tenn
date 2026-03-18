from __future__ import annotations

from typing import Any

import httpx


DEFAULT_BASE_URL = "http://localhost:8081"
DEFAULT_TIMEOUT_SECONDS = 20.0


class OpenBBSidecarProviderError(RuntimeError):
    pass


class OpenBBSidecarProvider:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = DEFAULT_TIMEOUT_SECONDS):
        self.base_url = str(base_url or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = float(timeout)

    def _request(self, path: str, *, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            try:
                response = client.get(url, params=params)
                response.raise_for_status()
                payload = response.json() if response.content else {}
            except httpx.HTTPStatusError as exc:
                detail = None
                code = exc.response.status_code if exc.response is not None else "unknown"
                try:
                    body = exc.response.json() if exc.response is not None else {}
                    detail = body.get("detail") if isinstance(body, dict) else None
                except Exception:
                    detail = None
                message = str(detail or f"openbb sidecar returned HTTP {code}")
                raise OpenBBSidecarProviderError(message) from exc
            except Exception as exc:
                raise OpenBBSidecarProviderError(f"openbb sidecar request failed: {exc}") from exc
        if not isinstance(payload, dict):
            raise OpenBBSidecarProviderError("openbb sidecar returned invalid JSON payload")
        if not payload:
            raise OpenBBSidecarProviderError("openbb sidecar returned empty response")
        return payload

    @staticmethod
    def _normalize_ticker(value: str) -> str:
        ticker = str(value or "").strip().upper()
        if not ticker:
            raise ValueError("ticker is required")
        return ticker

    @staticmethod
    def _normalize_exchange(value: str) -> str:
        exchange = str(value or "").strip().upper()
        return exchange or "ASX"

    def fetch_price(
        self,
        *,
        ticker: str,
        exchange: str = "ASX",
        range_: str = "1mo",
        interval: str = "1d",
    ) -> dict[str, Any]:
        range_value = str(range_ or "").strip()
        interval_value = str(interval or "").strip()
        if not range_value:
            raise ValueError("range is required")
        if not interval_value:
            raise ValueError("interval is required")
        return self._request(
            "/v1/price",
            params={
                "ticker": self._normalize_ticker(ticker),
                "exchange": self._normalize_exchange(exchange),
                "range": range_value,
                "interval": interval_value,
            },
        )

    def fetch_fundamentals_profile(self, *, ticker: str, exchange: str = "ASX") -> dict[str, Any]:
        return self._request(
            "/v1/fundamentals/profile",
            params={
                "ticker": self._normalize_ticker(ticker),
                "exchange": self._normalize_exchange(exchange),
            },
        )

    def fetch_fundamentals_summary(self, *, ticker: str, exchange: str = "ASX") -> dict[str, Any]:
        return self._request(
            "/v1/fundamentals/summary",
            params={
                "ticker": self._normalize_ticker(ticker),
                "exchange": self._normalize_exchange(exchange),
            },
        )

    def fetch_fundamentals_statements(
        self,
        *,
        ticker: str,
        exchange: str = "ASX",
        statement_type: str = "income",
        period: str = "annual",
        limit: int = 8,
    ) -> dict[str, Any]:
        statement_value = str(statement_type or "").strip().lower()
        period_value = str(period or "").strip().lower()
        if statement_value not in {"income", "balance", "cashflow"}:
            raise ValueError("statement_type must be one of: income, balance, cashflow")
        if period_value not in {"annual", "quarter"}:
            raise ValueError("period must be one of: annual, quarter")
        if int(limit) < 1:
            raise ValueError("limit must be >= 1")
        return self._request(
            "/v1/fundamentals/statements",
            params={
                "ticker": self._normalize_ticker(ticker),
                "exchange": self._normalize_exchange(exchange),
                "statement_type": statement_value,
                "period": period_value,
                "limit": int(limit),
            },
        )
