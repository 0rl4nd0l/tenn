#!/usr/bin/env python3
import os
import sys
import unittest
import unittest.mock
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.integrations.backend_api import BackendApiClient  # noqa: E402


def _mock_response(body: dict) -> unittest.mock.Mock:
    import json as _json

    m = unittest.mock.Mock()
    m.content = _json.dumps(body).encode()
    m.json.return_value = body
    m.raise_for_status = unittest.mock.Mock()
    return m


class BackendApiClientApiKeyTests(unittest.TestCase):
    def test_api_key_stored_when_provided(self):
        client = BackendApiClient("http://localhost:8000", api_key="my-secret-key")
        self.assertEqual(client.api_key, "my-secret-key")

    def test_api_key_defaults_to_empty_string(self):
        client = BackendApiClient("http://localhost:8000")
        self.assertEqual(client.api_key, "")

    def test_rag_query_sends_api_key_header_when_key_is_set(self):
        client = BackendApiClient("http://localhost:8000", api_key="test-key")
        resp = _mock_response({"results": []})
        with unittest.mock.patch.object(httpx.Client, "get", return_value=resp) as mock_get:
            client.rag_query("BHP earnings")
        call_kwargs = mock_get.call_args.kwargs
        headers = call_kwargs.get("headers") or {}
        self.assertEqual(headers.get("X-API-Key"), "test-key")

    def test_rag_query_omits_api_key_header_when_no_key_configured(self):
        client = BackendApiClient("http://localhost:8000")
        resp = _mock_response({"results": []})
        with unittest.mock.patch.object(httpx.Client, "get", return_value=resp) as mock_get:
            client.rag_query("BHP earnings")
        call_kwargs = mock_get.call_args.kwargs
        headers = call_kwargs.get("headers") or {}
        self.assertNotIn("X-API-Key", headers)


if __name__ == "__main__":
    unittest.main()
