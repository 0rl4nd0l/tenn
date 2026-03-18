#!/usr/bin/env python3
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.api import routes  # noqa: E402


class MarketDataModeRoutingTests(unittest.TestCase):
    def setUp(self):
        self._old_mode = routes.settings.market_data_mode
        self._old_staging = routes.settings.openbb_sidecar_enable_staging_writes

    def tearDown(self):
        routes.settings.market_data_mode = self._old_mode
        routes.settings.openbb_sidecar_enable_staging_writes = self._old_staging

    def test_price_uses_yahoo_mode_by_default(self):
        routes.settings.market_data_mode = "yahoo"
        routes.settings.openbb_sidecar_enable_staging_writes = False

        with patch("app.api.routes.MarketPriceProvider") as yahoo_cls, patch(
            "app.api.routes.OpenBBSidecarProvider"
        ) as openbb_cls:
            yahoo_cls.return_value.fetch.return_value = {"provider": "yahoo_finance", "ticker": "BHP"}
            payload = routes.price(
                ticker="BHP",
                range_="1mo",
                interval="1d",
                exchange="ASX",
            )

        self.assertEqual(payload["provider"], "yahoo_finance")
        self.assertTrue(yahoo_cls.return_value.fetch.called)
        self.assertFalse(openbb_cls.return_value.fetch_price.called)

    def test_price_uses_openbb_sidecar_when_mode_enabled(self):
        routes.settings.market_data_mode = "openbb_sidecar"
        routes.settings.openbb_sidecar_enable_staging_writes = False

        with patch("app.api.routes.MarketPriceProvider") as yahoo_cls, patch(
            "app.api.routes.OpenBBSidecarProvider"
        ) as openbb_cls:
            openbb_cls.return_value.fetch_price.return_value = {"provider": "openbb_sidecar", "ticker": "BHP"}
            payload = routes.price(
                ticker="BHP",
                range_="1mo",
                interval="1d",
                exchange="ASX",
            )

        self.assertEqual(payload["provider"], "openbb_sidecar")
        self.assertTrue(openbb_cls.return_value.fetch_price.called)
        self.assertFalse(yahoo_cls.return_value.fetch.called)


if __name__ == "__main__":
    unittest.main()
