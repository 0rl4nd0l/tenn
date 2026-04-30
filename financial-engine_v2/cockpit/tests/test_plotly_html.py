from __future__ import annotations

from cockpit.core.plotly_html import build_candlestick_dashboard_html


def test_candlestick_dashboard_surfaces_latest_open_and_close() -> None:
    html = build_candlestick_dashboard_html(
        {
            "ticker": "EOS",
            "window": "1d",
            "recent_history": [
                {
                    "timestamp": "2026-04-30T00:00:00Z",
                    "open": 8.95,
                    "high": 9.20,
                    "low": 8.80,
                    "close": 9.06,
                    "volume": 123456,
                }
            ],
            "price_state": {
                "current": {"close": 9.06},
                "metrics": {"sample_count": 1},
            },
            "generated_at": "2026-04-30T07:55:00Z",
        }
    )

    assert "Latest Date" in html
    assert "2026-04-30" in html
    assert "Latest Open" in html
    assert "8.9500" in html
    assert "Latest Close" in html
    assert "9.0600" in html

