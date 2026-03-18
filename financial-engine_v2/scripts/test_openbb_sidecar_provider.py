#!/usr/bin/env python3
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.providers.openbb_sidecar_provider import (  # noqa: E402
    OpenBBSidecarProvider,
    OpenBBSidecarProviderError,
)


class _FakeResponse:
    def __init__(self, payload=None, status_code=200, detail=None):
        self._payload = payload
        self.status_code = status_code
        self.detail = detail
        self.content = b"{}"

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "http://localhost")
            response = httpx.Response(
                self.status_code,
                request=request,
                json={"detail": self.detail or "error"},
            )
            raise httpx.HTTPStatusError("http error", request=request, response=response)
        return None

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, response, sink):
        self._response = response
        self._sink = sink

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url, params=None):
        self._sink["url"] = url
        self._sink["params"] = params
        return self._response


class OpenBBSidecarProviderTests(unittest.TestCase):
    def test_fetch_price_success(self):
        sink = {}
        payload = {"provider": "openbb_sidecar", "ticker": "BHP", "history": []}
        fake_response = _FakeResponse(payload=payload, status_code=200)

        def _client_factory(*args, **kwargs):  # noqa: ARG001
            return _FakeClient(fake_response, sink)

        with patch("app.providers.openbb_sidecar_provider.httpx.Client", side_effect=_client_factory):
            provider = OpenBBSidecarProvider(base_url="http://localhost:8081", timeout=5)
            result = provider.fetch_price(ticker="BHP", exchange="ASX", range_="1mo", interval="1d")

        self.assertEqual(result["provider"], "openbb_sidecar")
        self.assertEqual(sink["url"], "http://localhost:8081/v1/price")
        self.assertEqual(sink["params"]["ticker"], "BHP")
        self.assertEqual(sink["params"]["exchange"], "ASX")
        self.assertEqual(sink["params"]["range"], "1mo")
        self.assertEqual(sink["params"]["interval"], "1d")

    def test_fetch_price_http_error_raises_provider_error(self):
        sink = {}
        fake_response = _FakeResponse(payload={"detail": "upstream unavailable"}, status_code=502, detail="upstream unavailable")

        def _client_factory(*args, **kwargs):  # noqa: ARG001
            return _FakeClient(fake_response, sink)

        with patch("app.providers.openbb_sidecar_provider.httpx.Client", side_effect=_client_factory):
            provider = OpenBBSidecarProvider(base_url="http://localhost:8081", timeout=5)
            with self.assertRaises(OpenBBSidecarProviderError) as ctx:
                provider.fetch_price(ticker="BHP", exchange="ASX", range_="1mo", interval="1d")
        self.assertIn("upstream unavailable", str(ctx.exception))

    def test_fetch_fundamentals_statements_validates_statement_type(self):
        provider = OpenBBSidecarProvider(base_url="http://localhost:8081", timeout=5)
        with self.assertRaises(ValueError):
            provider.fetch_fundamentals_statements(
                ticker="BHP",
                exchange="ASX",
                statement_type="invalid",
                period="annual",
                limit=8,
            )


if __name__ == "__main__":
    unittest.main()
