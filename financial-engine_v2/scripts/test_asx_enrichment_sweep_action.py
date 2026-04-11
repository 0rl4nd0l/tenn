from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from app.providers.asx_provider import DiscoveredDoc
from cockpit.core.actions import ActionRegistry
from scripts.asx_enrichment_sweep_action import _discover_historical_by_ticker


class _FakeProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[str, datetime, datetime]] = []

    def discover(self, ticker: str, start: datetime, end: datetime):
        self.calls.append((ticker, start, end))
        return [
            DiscoveredDoc(
                ticker=ticker,
                exchange="ASX",
                doc_class="quarterly",
                doc_subtype="4C",
                title="Quarterly update",
                source_url=f"https://example.com/{ticker}/2026-04-10.pdf",
                published_at=datetime(2026, 4, 10, 2, 0, tzinfo=timezone.utc),
            ),
            DiscoveredDoc(
                ticker=ticker,
                exchange="ASX",
                doc_class="quarterly",
                doc_subtype="4C",
                title="Quarterly update 2",
                source_url=f"https://example.com/{ticker}/2026-04-09.pdf",
                published_at=datetime(2026, 4, 9, 2, 0, tzinfo=timezone.utc),
            ),
        ]


def test_historical_discovery_reuses_year_cache_across_days() -> None:
    provider = _FakeProvider()
    cache: dict[tuple[str, int], list] = {}

    rows_day_one, attempted_one, failed_one, skipped_one = _discover_historical_by_ticker(
        provider,
        tickers=["BHP"],
        target_day=datetime(2026, 4, 10, tzinfo=timezone.utc),
        year_cache=cache,
    )
    rows_day_two, attempted_two, failed_two, skipped_two = _discover_historical_by_ticker(
        provider,
        tickers=["BHP"],
        target_day=datetime(2026, 4, 9, tzinfo=timezone.utc),
        year_cache=cache,
    )

    assert attempted_one == 1
    assert attempted_two == 1
    assert failed_one == 0
    assert failed_two == 0
    assert skipped_one == 0
    assert skipped_two == 0
    assert len(provider.calls) == 1
    assert [row.source_url for row in rows_day_one] == ["https://example.com/BHP/2026-04-10.pdf"]
    assert [row.source_url for row in rows_day_two] == ["https://example.com/BHP/2026-04-09.pdf"]


def test_universe_backfill_defaults_to_year_sized_chunks() -> None:
    reg = ActionRegistry(repo_root=REPO_ROOT, confirm_required=True)
    cmd = reg.build_command(
        "universe_announcement_enrichment_backfill",
        {"total_days_back": 1825},
    )

    idx = cmd.index("--chunk-days")
    assert cmd[idx + 1] == "365"


def test_universe_backfill_defaults_to_selective_narrative_policy() -> None:
    reg = ActionRegistry(repo_root=REPO_ROOT, confirm_required=True)
    cmd = reg.build_command(
        "universe_announcement_enrichment_backfill",
        {"total_days_back": 1825},
    )

    idx = cmd.index("--narrative-policy")
    assert cmd[idx + 1] == "selective"
