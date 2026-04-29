from __future__ import annotations

from typing import Any

import httpx

from app.providers.market_price_provider import MarketPriceProvider


class _FakeClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def __enter__(self) -> "_FakeClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def get(self, *args, **kwargs) -> httpx.Response:
        request = httpx.Request("GET", "https://example.test/chart")
        return httpx.Response(200, json=self._payload, request=request)


def _chart_payload(*, previous_close: float | None) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "currency": "AUD",
        "exchangeName": "ASX",
        "exchangeTimezoneName": "Australia/Sydney",
        "regularMarketPrice": 5.945,
        "chartPreviousClose": 1.54,
    }
    if previous_close is not None:
        meta["previousClose"] = previous_close
    return {
        "chart": {
            "result": [
                {
                    "meta": meta,
                    "timestamp": [1_776_974_400, 1_777_060_800, 1_777_147_200],
                    "indicators": {
                        "quote": [
                            {
                                "open": [5.75, 5.99, 5.99],
                                "high": [6.04, 6.17, 6.05],
                                "low": [5.73, 5.96, 5.885],
                                "close": [5.93, 6.11, 5.945],
                                "volume": [15_991_329, 24_718_110, 17_294_353],
                            }
                        ]
                    },
                }
            ],
            "error": None,
        }
    }


def test_fetch_prefers_yahoo_previous_close_over_range_anchor(monkeypatch) -> None:
    payload = _chart_payload(previous_close=6.11)
    monkeypatch.setattr(httpx, "Client", lambda *args, **kwargs: _FakeClient(payload))

    result = MarketPriceProvider().fetch("PLS", exchange="ASX", range_="1y", interval="1d")

    assert result["current"]["previous_close"] == 6.11


def test_fetch_derives_previous_close_from_history_when_meta_missing(monkeypatch) -> None:
    payload = _chart_payload(previous_close=None)
    monkeypatch.setattr(httpx, "Client", lambda *args, **kwargs: _FakeClient(payload))

    result = MarketPriceProvider().fetch("PLS", exchange="ASX", range_="1y", interval="1d")

    assert result["current"]["previous_close"] == 6.11
