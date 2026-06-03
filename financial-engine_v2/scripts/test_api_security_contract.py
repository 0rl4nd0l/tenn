import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402


class ApiSecurityContractTests(unittest.TestCase):
    def setUp(self):
        self._old_api_key = getattr(settings, "api_key", "")
        settings.api_key = "test-key"
        self.client = TestClient(app)

    def tearDown(self):
        settings.api_key = self._old_api_key

    def test_non_health_requires_api_key(self):
        response = self.client.get("/api/docs?ticker=BHP")
        self.assertEqual(response.status_code, 401)

    def test_health_remains_public(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)

    def test_backfill_years_are_bounded_at_route(self):
        response = self.client.post(
            "/api/backfill/ticker/BHP?years=999&process_documents=false",
            headers={"X-API-Key": "test-key"},
        )
        self.assertEqual(response.status_code, 422)

    def test_ticker_path_is_validated_at_route(self):
        response = self.client.post(
            "/api/backfill/ticker/not-a-ticker?years=1&process_documents=false",
            headers={"X-API-Key": "test-key"},
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
