#!/usr/bin/env python3
import os
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.storage.artifacts import ArtifactStore  # noqa: E402


class CockpitArtifactPriceStateMarkdownTests(unittest.TestCase):
    def _store(self, repo_root: Path) -> ArtifactStore:
        return ArtifactStore(repo_root=repo_root, exports_dir="reports/analysis", reports_dir="reports")

    def test_markdown_includes_compact_price_state_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            store = self._store(repo_root)
            payload = {
                "evidence": [
                    {
                        "type": "local_context",
                        "details": {
                            "price_state": {
                                "ok": True,
                                "ticker": "BHP",
                                "symbol": "BHP.AX",
                                "currency": "AUD",
                                "last_close": 53.33,
                                "previous_close_effective": 52.10,
                                "trend_regime": "bull",
                                "ret_1d": 1.2,
                                "ret_20d": 4.8,
                                "vol_20d_ann": 24.1,
                                "drawdown_from_63d_high": -2.6,
                                "market_time_utc": "2026-02-21T00:00:00+00:00",
                                "data_age_hours": 2.4,
                                "stale_data": False,
                                "history_points": 120,
                                "insufficient_history": False,
                                "error": None,
                            }
                        },
                    }
                ]
            }
            md_path, _ = store.write_analysis("thread-a", "price bhp", "test answer", payload)
            text = Path(md_path).read_text(encoding="utf-8")

            self.assertIn("## Price State", text)
            self.assertIn("ticker `BHP`", text)
            self.assertIn("Last close: 53.33 AUD", text)
            self.assertIn("Returns: 1D +1.20%, 20D +4.80%", text)
            self.assertIn("Trend: regime `bull`, vol(20D ann) 24.10%, drawdown(63D high) -2.60%", text)
            self.assertIn("Freshness: fresh, market_time=2026-02-21T00:00:00+00:00, age=2.4h, history_points=120", text)

    def test_markdown_renders_error_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            store = self._store(repo_root)
            payload = {
                "evidence": [
                    {
                        "type": "local_context",
                        "details": {
                            "price_state": {
                                "ok": False,
                                "ticker": "BHP",
                                "symbol": "BHP.AX",
                                "currency": "AUD",
                                "error": "market price provider returned HTTP 404",
                            }
                        },
                    }
                ]
            }
            md_path, _ = store.write_analysis("thread-b", "bhp price", "cannot verify", payload)
            text = Path(md_path).read_text(encoding="utf-8")

            self.assertIn("## Price State", text)
            self.assertIn("Status: unavailable", text)
            self.assertIn("Error: market price provider returned HTTP 404", text)

    def test_markdown_skips_price_state_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            store = self._store(repo_root)
            payload = {"evidence": [{"type": "local_context", "details": {"ticker": "BHP"}}]}
            md_path, _ = store.write_analysis("thread-c", "analyse bhp", "analysis answer", payload)
            text = Path(md_path).read_text(encoding="utf-8")

            self.assertNotIn("## Price State", text)


if __name__ == "__main__":
    unittest.main()
