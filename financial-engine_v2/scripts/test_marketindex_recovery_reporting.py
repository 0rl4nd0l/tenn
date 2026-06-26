#!/usr/bin/env python3
import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


def _load_module():
    path = SCRIPTS_ROOT / "marketindex_recovery_reporting.py"
    spec = importlib.util.spec_from_file_location("marketindex_recovery_reporting", str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class MarketIndexRecoveryReportingTests(unittest.TestCase):
    def test_summary_counts_blockers_and_names_recovery_command(self) -> None:
        mod = _load_module()

        summary = mod.build_marketindex_recovery_summary(tickers=["BHP", "RIO", "BHP"])
        mod.add_marketindex_recovery_blocker(
            summary,
            ticker="BHP",
            marker="blocked_marketindex_headed_required",
            document_id="doc-1",
            source_url="https://www.marketindex.com.au/asx/bhp/announcements/example-2A0000001",
            stage="download",
        )
        mod.add_marketindex_recovery_blocker(
            summary,
            ticker="RIO",
            marker="blocked_marketindex_403",
            document_id="doc-2",
            source_url="https://www.marketindex.com.au/asx/rio/announcements/example-2A0000002",
            stage="download",
        )

        self.assertEqual(summary["requires_headed_recovery_count"], 2)
        self.assertEqual(summary["counts_by_marker"]["blocked_marketindex_403"], 1)
        self.assertEqual(summary["counts_by_ticker"]["BHP"], 1)
        self.assertEqual(summary["counts_by_ticker"]["RIO"], 1)
        self.assertEqual(
            summary["recommended_command"],
            "python3 scripts/recover_marketindex_headed.py --ticker BHP,RIO",
        )
        self.assertEqual(summary["samples"][0]["stage"], "download")


if __name__ == "__main__":
    unittest.main()
