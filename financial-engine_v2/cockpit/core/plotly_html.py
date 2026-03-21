from __future__ import annotations

import json
from html import escape
from typing import Any


PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js"


def _json_compact(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), default=str)


def _build_document(title: str, body: str, script: str) -> str:
    safe_title = escape(title)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <script src="{PLOTLY_CDN}"></script>
  <style>
    :root {{
      --bg: #0d1117;
      --panel: #161b22;
      --border: #30363d;
      --text: #e6edf3;
      --muted: #8b949e;
      --accent: #58a6ff;
      --good: #3fb950;
      --warn: #d29922;
      --bad: #f85149;
    }}
    body {{
      margin: 0;
      background: linear-gradient(180deg, #0d1117 0%, #111827 100%);
      color: var(--text);
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
    }}
    .wrap {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 24px;
    }}
    .hero, .panel, .card {{
      background: rgba(22, 27, 34, 0.94);
      border: 1px solid var(--border);
      border-radius: 16px;
    }}
    .hero {{
      padding: 20px 24px;
      margin-bottom: 18px;
    }}
    .hero h1 {{
      margin: 0 0 8px;
      font-size: 28px;
    }}
    .hero p, .meta {{
      margin: 0;
      color: var(--muted);
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
      margin-bottom: 18px;
    }}
    .card {{
      padding: 14px 16px;
    }}
    .label {{
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .value {{
      margin-top: 6px;
      font-size: 24px;
      font-weight: 600;
    }}
    .panel {{
      padding: 12px;
      margin-bottom: 18px;
    }}
    .panel h2 {{
      margin: 6px 8px 2px;
      color: var(--muted);
      font-size: 14px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .plot {{
      min-height: 360px;
    }}
    .mono {{
      font-family: "IBM Plex Mono", "SFMono-Regular", monospace;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    {body}
  </div>
  <script>
  {script}
  </script>
</body>
</html>"""


def build_snapshot_dashboard_html(payload: dict[str, Any]) -> str:
    ticker = str(payload.get("ticker") or "UNKNOWN")
    confidence_summary = payload.get("confidence_summary") if isinstance(payload.get("confidence_summary"), dict) else {}
    verification_summary = payload.get("verification_summary") if isinstance(payload.get("verification_summary"), dict) else {}
    verification_checks = verification_summary.get("checks") if isinstance(verification_summary.get("checks"), dict) else {}
    metrics_diff = payload.get("metrics_diff") if isinstance(payload.get("metrics_diff"), list) else []

    metric_fields: list[str] = []
    metric_before: list[float | None] = []
    metric_after: list[float | None] = []
    metric_delta: list[float | None] = []
    for row in metrics_diff:
        if not isinstance(row, dict):
            continue
        field = str(row.get("field") or "").strip()
        if not field:
            continue
        metric_fields.append(field)
        metric_before.append(row.get("before"))
        metric_after.append(row.get("after"))
        metric_delta.append(row.get("delta"))

    cards = [
        ("Ticker", ticker),
        ("Confidence Before", str(confidence_summary.get("before") or "n/a")),
        ("Confidence After", str(confidence_summary.get("after") or "n/a")),
        ("Verification Flags", str(sum(int(v or 0) for v in verification_checks.values())) if verification_checks else "0"),
    ]
    cards_html = "".join(
        f'<div class="card"><div class="label">{escape(label)}</div><div class="value mono">{escape(value)}</div></div>'
        for label, value in cards
    )

    body = f"""
    <section class="hero">
      <h1>{escape(ticker)} Snapshot Dashboard</h1>
      <p>Before/after financial metrics with verification counts.</p>
      <p class="meta mono">created_at={escape(str(payload.get("created_at") or "n/a"))}</p>
    </section>
    <section class="grid">{cards_html}</section>
    <section class="panel"><h2>Metric Comparison</h2><div id="snapshot-comparison" class="plot"></div></section>
    <section class="panel"><h2>Metric Delta</h2><div id="snapshot-delta" class="plot"></div></section>
    <section class="panel"><h2>Verification Counts</h2><div id="snapshot-verification" class="plot"></div></section>
    """

    script = f"""
    const metricFields = {_json_compact(metric_fields)};
    const metricBefore = {_json_compact(metric_before)};
    const metricAfter = {_json_compact(metric_after)};
    const metricDelta = {_json_compact(metric_delta)};
    const verificationChecks = {_json_compact(verification_checks)};

    const baseLayout = {{
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: {{color: '#e6edf3'}},
      margin: {{l: 60, r: 20, t: 20, b: 90}}
    }};

    Plotly.newPlot('snapshot-comparison', [
      {{type: 'bar', name: 'Before', x: metricFields, y: metricBefore, marker: {{color: '#58a6ff'}}}},
      {{type: 'bar', name: 'After', x: metricFields, y: metricAfter, marker: {{color: '#3fb950'}}}}
    ], {{...baseLayout, barmode: 'group'}}, {{displayModeBar: false, responsive: true}});

    Plotly.newPlot('snapshot-delta', [
      {{
        type: 'bar',
        x: metricFields,
        y: metricDelta,
        marker: {{color: metricDelta.map(v => (v || 0) >= 0 ? '#3fb950' : '#f85149')}}
      }}
    ], baseLayout, {{displayModeBar: false, responsive: true}});

    Plotly.newPlot('snapshot-verification', [
      {{type: 'bar', x: Object.keys(verificationChecks), y: Object.values(verificationChecks), marker: {{color: '#d29922'}}}}
    ], {{...baseLayout, margin: {{l: 60, r: 20, t: 20, b: 110}}}}, {{displayModeBar: false, responsive: true}});
    """
    return _build_document(f"{ticker} Snapshot Dashboard", body, script)


def build_price_dashboard_html(payload: dict[str, Any]) -> str:
    ticker = str(payload.get("ticker") or "UNKNOWN")
    window = str(payload.get("window") or "1y")
    price_state = payload.get("price_state") if isinstance(payload.get("price_state"), dict) else {}
    current = price_state.get("current") if isinstance(price_state.get("current"), dict) else {}
    metrics = price_state.get("metrics") if isinstance(price_state.get("metrics"), dict) else {}
    recent_history = payload.get("recent_history") if isinstance(payload.get("recent_history"), list) else []

    timestamps: list[str] = []
    closes: list[float | None] = []
    volumes: list[int | None] = []
    for row in recent_history:
        if not isinstance(row, dict):
            continue
        timestamps.append(str(row.get("timestamp") or ""))
        closes.append(row.get("close"))
        volumes.append(row.get("volume"))

    current_close = current.get("close")
    ytd_return = metrics.get("ytd_return")
    vol_30d = metrics.get("vol_30d")
    max_drawdown = metrics.get("max_drawdown")
    sample_count = metrics.get("sample_count", len(timestamps))

    cards = [
        ("Ticker", ticker),
        ("Current Close", f"{current_close:.4f}" if isinstance(current_close, (int, float)) else "n/a"),
        ("YTD Return", f"{ytd_return:.2f}%" if isinstance(ytd_return, (int, float)) else "n/a"),
        ("Volatility 30d", f"{vol_30d:.2f}%" if isinstance(vol_30d, (int, float)) else "n/a"),
        ("Max Drawdown", f"{max_drawdown:.2f}%" if isinstance(max_drawdown, (int, float)) else "n/a"),
        ("Sample Count", str(sample_count)),
    ]
    cards_html = "".join(
        f'<div class="card"><div class="label">{escape(label)}</div><div class="value mono">{escape(value)}</div></div>'
        for label, value in cards
    )

    generated_at = str(payload.get("generated_at") or "")

    body = f"""
    <section class="hero">
      <h1>{escape(ticker)} Price Dashboard</h1>
      <p>Close price and volume for window={escape(window)}.</p>
      <p class="meta mono">window={escape(window)} | samples={escape(str(sample_count))} | generated={escape(generated_at)}</p>
    </section>
    <section class="grid">{cards_html}</section>
    <section class="panel"><h2>Metadata</h2><div id="price-metadata" class="plot"></div></section>
    <section class="panel"><h2>Close Price</h2><div id="price-close" class="plot"></div></section>
    <section class="panel"><h2>Daily Volume</h2><div id="price-volume" class="plot"></div></section>
    """

    script = f"""
    const timestamps = {_json_compact(timestamps)};
    const closes = {_json_compact(closes)};
    const volumes = {_json_compact(volumes)};
    const metaWindow = {_json_compact(window)};
    const metaSamples = {_json_compact(str(sample_count))};
    const metaGenerated = {_json_compact(generated_at)};

    const baseLayout = {{
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: {{color: '#e6edf3'}},
      margin: {{l: 60, r: 20, t: 20, b: 90}}
    }};

    Plotly.newPlot('price-metadata', [{{
      type: 'table',
      header: {{
        values: ['Window', 'Sample Count', 'Generated'],
        fill: {{color: '#1f2937'}},
        font: {{color: '#e6edf3'}},
        align: 'left'
      }},
      cells: {{
        values: [[metaWindow], [metaSamples], [metaGenerated]],
        fill: {{color: '#161b22'}},
        font: {{color: '#e6edf3'}},
        align: 'left'
      }}
    }}], {{
      paper_bgcolor: 'rgba(0,0,0,0)',
      margin: {{l: 10, r: 10, t: 10, b: 10}}
    }}, {{displayModeBar: false, responsive: true}});

    Plotly.newPlot('price-close', [
      {{type: 'scatter', mode: 'lines', x: timestamps, y: closes, line: {{color: '#58a6ff'}}, name: 'Close'}}
    ], {{...baseLayout, xaxis: {{type: 'date'}}}}, {{displayModeBar: false, responsive: true}});

    Plotly.newPlot('price-volume', [
      {{type: 'bar', x: timestamps, y: volumes, marker: {{color: '#3fb950'}}, name: 'Volume'}}
    ], {{...baseLayout, xaxis: {{type: 'date'}}}}, {{displayModeBar: false, responsive: true}});
    """
    return _build_document(f"{ticker} Price Dashboard", body, script)


def build_candlestick_dashboard_html(payload: dict[str, Any]) -> str:
    ticker = str(payload.get("ticker") or "UNKNOWN")
    window = str(payload.get("window") or "1y")
    price_state = payload.get("price_state") if isinstance(payload.get("price_state"), dict) else {}
    current = price_state.get("current") if isinstance(price_state.get("current"), dict) else {}
    metrics = price_state.get("metrics") if isinstance(price_state.get("metrics"), dict) else {}
    recent_history = payload.get("recent_history") if isinstance(payload.get("recent_history"), list) else []

    timestamps: list[str] = []
    opens: list[float | None] = []
    highs: list[float | None] = []
    lows: list[float | None] = []
    closes: list[float | None] = []
    volumes: list[int | None] = []
    for row in recent_history:
        if not isinstance(row, dict):
            continue
        timestamps.append(str(row.get("timestamp") or ""))
        opens.append(row.get("open"))
        highs.append(row.get("high"))
        lows.append(row.get("low"))
        closes.append(row.get("close"))
        volumes.append(row.get("volume"))

    # Compute daily returns from close prices for chart 3.
    daily_returns: list[float | None] = [None]
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        cur = closes[i]
        if isinstance(prev, (int, float)) and isinstance(cur, (int, float)) and prev != 0:
            daily_returns.append(((cur - prev) / prev) * 100.0)
        else:
            daily_returns.append(None)

    current_close = current.get("close")
    ytd_return = metrics.get("ytd_return")
    vol_30d = metrics.get("vol_30d")
    max_drawdown = metrics.get("max_drawdown")
    sample_count = metrics.get("sample_count", len(timestamps))

    cards = [
        ("Ticker", ticker),
        ("Current Close", f"{current_close:.4f}" if isinstance(current_close, (int, float)) else "n/a"),
        ("YTD Return", f"{ytd_return:.2f}%" if isinstance(ytd_return, (int, float)) else "n/a"),
        ("Volatility 30d", f"{vol_30d:.2f}%" if isinstance(vol_30d, (int, float)) else "n/a"),
        ("Max Drawdown", f"{max_drawdown:.2f}%" if isinstance(max_drawdown, (int, float)) else "n/a"),
        ("Sample Count", str(sample_count)),
    ]
    cards_html = "".join(
        f'<div class="card"><div class="label">{escape(label)}</div><div class="value mono">{escape(value)}</div></div>'
        for label, value in cards
    )

    generated_at = str(payload.get("generated_at") or "")

    body = f"""
    <section class="hero">
      <h1>{escape(ticker)} Candlestick Dashboard</h1>
      <p>OHLCV candlestick chart with volume and returns for window={escape(window)}.</p>
      <p class="meta mono">window={escape(window)} | samples={escape(str(sample_count))} | generated={escape(generated_at)}</p>
    </section>
    <section class="grid">{cards_html}</section>
    <section class="panel"><h2>Candlestick</h2><div id="candle-ohlc" class="plot"></div></section>
    <section class="panel"><h2>Volume</h2><div id="candle-volume" class="plot"></div></section>
    <section class="panel"><h2>Daily Returns (%)</h2><div id="candle-returns" class="plot"></div></section>
    """

    script = f"""
    const timestamps = {_json_compact(timestamps)};
    const opens = {_json_compact(opens)};
    const highs = {_json_compact(highs)};
    const lows = {_json_compact(lows)};
    const closes = {_json_compact(closes)};
    const volumes = {_json_compact(volumes)};
    const dailyReturns = {_json_compact(daily_returns)};

    const baseLayout = {{
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: {{color: '#e6edf3'}},
      margin: {{l: 60, r: 20, t: 20, b: 90}}
    }};

    Plotly.newPlot('candle-ohlc', [{{
      type: 'candlestick',
      x: timestamps,
      open: opens,
      high: highs,
      low: lows,
      close: closes,
      increasing: {{line: {{color: '#3fb950'}}}},
      decreasing: {{line: {{color: '#f85149'}}}}
    }}], {{...baseLayout, xaxis: {{type: 'date', rangeslider: {{visible: false}}}}}}, {{displayModeBar: false, responsive: true}});

    Plotly.newPlot('candle-volume', [
      {{type: 'bar', x: timestamps, y: volumes, marker: {{color: '#58a6ff'}}, name: 'Volume'}}
    ], {{...baseLayout, xaxis: {{type: 'date'}}}}, {{displayModeBar: false, responsive: true}});

    Plotly.newPlot('candle-returns', [
      {{type: 'scatter', mode: 'lines', x: timestamps, y: dailyReturns, line: {{color: '#d29922'}}, name: 'Daily Return %'}}
    ], {{...baseLayout, xaxis: {{type: 'date'}}}}, {{displayModeBar: false, responsive: true}});
    """
    return _build_document(f"{ticker} Candlestick Dashboard", body, script)


def build_verification_dashboard_html(payload: dict[str, Any]) -> str:
    ticker = str(payload.get("ticker") or "ALL")
    checks = payload.get("checks") if isinstance(payload.get("checks"), dict) else {}
    remediation = payload.get("remediation") if isinstance(payload.get("remediation"), list) else []
    samples = payload.get("samples") if isinstance(payload.get("samples"), dict) else {}

    sample_rows: list[dict[str, str]] = []
    for bucket, rows in samples.items():
        if not isinstance(rows, list):
            continue
        for row in rows[:3]:
            if not isinstance(row, dict):
                continue
            sample_rows.append(
                {
                    "bucket": str(bucket),
                    "ticker": str(row.get("ticker") or ""),
                    "title": str(row.get("title") or row.get("document_id") or row.get("source_document_id") or ""),
                    "detail": str(row.get("error") or row.get("status") or row.get("period_end") or ""),
                }
            )

    cards = [
        ("Ticker", ticker),
        ("Missing PDFs", str(checks.get("missing_pdf_files", 0))),
        ("Blocked Docs", str(checks.get("blocked_documents", 0))),
        ("Low Confidence", str(checks.get("low_confidence_financials", 0))),
    ]
    cards_html = "".join(
        f'<div class="card"><div class="label">{escape(label)}</div><div class="value mono">{escape(value)}</div></div>'
        for label, value in cards
    )
    body = f"""
    <section class="hero">
      <h1>{escape(ticker)} Verification Dashboard</h1>
      <p>Operational verification summary and remediation guidance.</p>
    </section>
    <section class="grid">{cards_html}</section>
    <section class="panel"><h2>Verification Counts</h2><div id="verification-counts" class="plot"></div></section>
    <section class="panel"><h2>Sample Issues</h2><div id="verification-samples" class="plot"></div></section>
    <section class="panel"><h2>Remediation</h2><div id="verification-remediation" class="plot"></div></section>
    """
    script = f"""
    const checks = {_json_compact(checks)};
    const sampleRows = {_json_compact(sample_rows)};
    const remediation = {_json_compact(remediation)};
    const layout = {{
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: {{color: '#e6edf3'}},
      margin: {{l: 60, r: 20, t: 20, b: 110}}
    }};

    Plotly.newPlot('verification-counts', [
      {{type: 'bar', x: Object.keys(checks), y: Object.values(checks), marker: {{color: '#58a6ff'}}}}
    ], layout, {{displayModeBar: false, responsive: true}});

    Plotly.newPlot('verification-samples', [{{
      type: 'table',
      header: {{
        values: ['Bucket', 'Ticker', 'Title', 'Detail'],
        fill: {{color: '#1f2937'}},
        font: {{color: '#e6edf3'}},
        align: 'left'
      }},
      cells: {{
        values: [
          sampleRows.map(r => r.bucket),
          sampleRows.map(r => r.ticker),
          sampleRows.map(r => r.title),
          sampleRows.map(r => r.detail)
        ],
        fill: {{color: '#161b22'}},
        font: {{color: '#e6edf3'}},
        align: 'left'
      }}
    }}], {{
      paper_bgcolor: 'rgba(0,0,0,0)',
      margin: {{l: 10, r: 10, t: 10, b: 10}}
    }}, {{displayModeBar: false, responsive: true}});

    Plotly.newPlot('verification-remediation', [{{
      type: 'table',
      header: {{
        values: ['Recommended next step'],
        fill: {{color: '#1f2937'}},
        font: {{color: '#e6edf3'}},
        align: 'left'
      }},
      cells: {{
        values: [remediation.length ? remediation : ['No remediation required']],
        fill: {{color: '#161b22'}},
        font: {{color: '#e6edf3'}},
        align: 'left'
      }}
    }}], {{
      paper_bgcolor: 'rgba(0,0,0,0)',
      margin: {{l: 10, r: 10, t: 10, b: 10}}
    }}, {{displayModeBar: false, responsive: true}});
    """
    return _build_document(f"{ticker} Verification Dashboard", body, script)
