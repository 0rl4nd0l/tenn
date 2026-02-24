#!/usr/bin/env python3
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.providers.market_price_provider import MarketPriceProvider  # noqa: E402


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, payload, sink):
        self._payload = payload
        self._sink = sink

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url, params=None, headers=None):
        self._sink["url"] = url
        self._sink["params"] = params
        self._sink["headers"] = headers
        return _FakeResponse(self._payload)


class MarketPriceProviderTests(unittest.TestCase):
    def test_normalizes_asx_symbol(self):
        provider = MarketPriceProvider()
        self.assertEqual(provider._normalize_symbol("bhp", "ASX"), "BHP.AX")

    def test_keeps_explicit_symbol_suffix(self):
        provider = MarketPriceProvider()
        self.assertEqual(provider._normalize_symbol("TENN", "NYSE"), "TENN")
        self.assertEqual(provider._normalize_symbol("BHP.AX", "NYSE"), "BHP.AX")

    def test_fetch_parses_current_and_history(self):
        payload = {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "currency": "AUD",
                            "exchangeTimezoneName": "Australia/Sydney",
                            "exchangeName": "ASX",
                            "regularMarketPrice": 40.1,
                            "regularMarketTime": 1735423200,
                            "regularMarketOpen": 39.8,
                            "regularMarketDayHigh": 40.2,
                            "regularMarketDayLow": 39.5,
                            "regularMarketVolume": 12345,
                            "chartPreviousClose": 39.7,
                        },
                        "timestamp": [1735336800, 1735423200],
                        "indicators": {
                            "quote": [
                                {
                                    "open": [39.2, 39.8],
                                    "high": [39.9, 40.2],
                                    "low": [39.0, 39.5],
                                    "close": [39.7, 40.1],
                                    "volume": [10000, 12345],
                                }
                            ]
                        },
                    }
                ],
                "error": None,
            }
        }
        sink = {}

        def _client_factory(*args, **kwargs):
            return _FakeClient(payload=payload, sink=sink)

        with patch("app.providers.market_price_provider.httpx.Client", side_effect=_client_factory):
            provider = MarketPriceProvider(base_url="https://query1.finance.yahoo.com", timeout=5)
            result = provider.fetch(ticker="BHP", exchange="ASX", range_="1mo", interval="1d")

        self.assertEqual(result["symbol"], "BHP.AX")
        self.assertEqual(result["current"]["price"], 40.1)
        self.assertEqual(len(result["history"]), 2)
        self.assertEqual(result["history"][1]["close"], 40.1)
        self.assertEqual(sink["params"]["range"], "1mo")
        self.assertEqual(sink["params"]["interval"], "1d")


if __name__ == "__main__":
    unittest.main()
