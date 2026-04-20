from __future__ import annotations

import json
from html import escape
from typing import Any


PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js"


def _json_compact(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), default=str)


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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
    confidence_summary = (
        payload.get("confidence_summary")
        if isinstance(payload.get("confidence_summary"), dict)
        else {}
    )
    verification_summary = (
        payload.get("verification_summary")
        if isinstance(payload.get("verification_summary"), dict)
        else {}
    )
    verification_checks = (
        verification_summary.get("checks")
        if isinstance(verification_summary.get("checks"), dict)
        else {}
    )
    metrics_diff = (
        payload.get("metrics_diff")
        if isinstance(payload.get("metrics_diff"), list)
        else []
    )

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
        (
            "Verification Flags",
            str(sum(int(v or 0) for v in verification_checks.values()))
            if verification_checks
            else "0",
        ),
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
    price_state = (
        payload.get("price_state")
        if isinstance(payload.get("price_state"), dict)
        else {}
    )
    current = (
        price_state.get("current")
        if isinstance(price_state.get("current"), dict)
        else {}
    )
    metrics = (
        price_state.get("metrics")
        if isinstance(price_state.get("metrics"), dict)
        else {}
    )
    recent_history = (
        payload.get("recent_history")
        if isinstance(payload.get("recent_history"), list)
        else []
    )

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
        (
            "Current Close",
            f"{current_close:.4f}"
            if isinstance(current_close, (int, float))
            else "n/a",
        ),
        (
            "YTD Return",
            f"{ytd_return:.2f}%" if isinstance(ytd_return, (int, float)) else "n/a",
        ),
        (
            "Volatility 30d",
            f"{vol_30d:.2f}%" if isinstance(vol_30d, (int, float)) else "n/a",
        ),
        (
            "Max Drawdown",
            f"{max_drawdown:.2f}%" if isinstance(max_drawdown, (int, float)) else "n/a",
        ),
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
    price_state = (
        payload.get("price_state")
        if isinstance(payload.get("price_state"), dict)
        else {}
    )
    current = (
        price_state.get("current")
        if isinstance(price_state.get("current"), dict)
        else {}
    )
    metrics = (
        price_state.get("metrics")
        if isinstance(price_state.get("metrics"), dict)
        else {}
    )
    recent_history = (
        payload.get("recent_history")
        if isinstance(payload.get("recent_history"), list)
        else []
    )

    ohlcv: list[dict[str, Any]] = []
    volume_data: list[dict[str, Any]] = []
    daily_returns: list[dict[str, Any]] = []
    prev_close: float | None = None

    for row in recent_history:
        if not isinstance(row, dict):
            continue
        ts = str(row.get("timestamp") or "")
        if not ts:
            continue
        o = _to_float(row.get("open"))
        h = _to_float(row.get("high"))
        lo = _to_float(row.get("low"))
        c = _to_float(row.get("close"))
        v = row.get("volume")
        if o is None or h is None or lo is None or c is None:
            continue
        ohlcv.append({"time": ts[:10], "open": o, "high": h, "low": lo, "close": c})
        volume_data.append(
            {
                "time": ts[:10],
                "value": int(v) if v is not None else 0,
                "color": "#3fb950" if c >= o else "#f85149",
            }
        )
        if prev_close is not None and prev_close != 0:
            daily_returns.append(
                {
                    "time": ts[:10],
                    "value": round(((c - prev_close) / prev_close) * 100.0, 4),
                }
            )
        prev_close = c

    current_close = current.get("close")
    ytd_return = metrics.get("ytd_return")
    vol_30d = metrics.get("vol_30d")
    max_drawdown = metrics.get("max_drawdown")
    sample_count = metrics.get("sample_count", len(ohlcv))

    cards = [
        ("Ticker", ticker),
        (
            "Current Close",
            f"{current_close:.4f}"
            if isinstance(current_close, (int, float))
            else "n/a",
        ),
        (
            "YTD Return",
            f"{ytd_return:.2f}%" if isinstance(ytd_return, (int, float)) else "n/a",
        ),
        (
            "Volatility 30d",
            f"{vol_30d:.2f}%" if isinstance(vol_30d, (int, float)) else "n/a",
        ),
        (
            "Max Drawdown",
            f"{max_drawdown:.2f}%"
            if isinstance(max_drawdown, (int, float))
            else "n/a",
        ),
        ("Sample Count", str(sample_count)),
    ]
    cards_html = "".join(
        f'<div class="card"><div class="label">{escape(label)}</div><div class="value mono">{escape(value)}</div></div>'
        for label, value in cards
    )
    generated_at = str(payload.get("generated_at") or "")
    safe_ticker = escape(ticker)
    safe_window = escape(window)
    safe_samples = escape(str(sample_count))
    safe_generated = escape(generated_at)

    lc_cdn = "https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_ticker} Candlestick Dashboard</title>
  <script src="{lc_cdn}"></script>
  <style>
    :root {{
      --bg: #0d1117; --panel: #161b22; --border: #30363d; --text: #e6edf3;
      --muted: #8b949e; --accent: #58a6ff; --good: #3fb950; --warn: #d29922; --bad: #f85149;
    }}
    body {{ margin: 0; background: linear-gradient(180deg,#0d1117 0%,#111827 100%); color: var(--text); font-family: "IBM Plex Sans","Segoe UI",sans-serif; }}
    .wrap {{ max-width: 1280px; margin: 0 auto; padding: 24px; }}
    .hero, .panel, .card {{ background: rgba(22,27,34,.94); border: 1px solid var(--border); border-radius: 16px; }}
    .hero {{ padding: 20px 24px; margin-bottom: 18px; }}
    .hero h1 {{ margin: 0 0 8px; font-size: 28px; }}
    .hero p, .meta {{ margin: 0; color: var(--muted); }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(220px,1fr)); gap: 14px; margin-bottom: 18px; }}
    .card {{ padding: 14px 16px; }}
    .label {{ color: var(--muted); font-size: 12px; letter-spacing: .08em; text-transform: uppercase; }}
    .value {{ margin-top: 6px; font-size: 24px; font-weight: 600; }}
    .panel {{ padding: 12px; margin-bottom: 18px; }}
    .panel h2 {{ margin: 6px 8px 2px; color: var(--muted); font-size: 14px; letter-spacing: .08em; text-transform: uppercase; }}
    .chart-box {{ height: 360px; }}
    .mono {{ font-family: "IBM Plex Mono","SFMono-Regular",monospace; }}
  </style>
</head>
<body>
<div class="wrap">
  <section class="hero">
    <h1>{safe_ticker} Candlestick Dashboard</h1>
    <p>OHLCV candlestick chart with volume and returns for window={safe_window}.</p>
    <p class="meta mono">window={safe_window} | samples={safe_samples} | generated={safe_generated}</p>
  </section>
  <section class="grid">{cards_html}</section>
  <section class="panel"><h2>Candlestick</h2><div id="candle-chart" class="chart-box"></div></section>
  <section class="panel"><h2>Volume</h2><div id="volume-chart" class="chart-box" style="height:200px"></div></section>
  <section class="panel"><h2>Daily Returns (%)</h2><div id="returns-chart" class="chart-box" style="height:200px"></div></section>
</div>
<script>
const ohlcv = {_json_compact(ohlcv)};
const volumeData = {_json_compact(volume_data)};
const dailyReturns = {_json_compact(daily_returns)};

const chartOpts = {{
  layout: {{ background: {{ color: 'transparent' }}, textColor: '#e6edf3' }},
  grid: {{ vertLines: {{ color: '#21262d' }}, horzLines: {{ color: '#21262d' }} }},
  timeScale: {{ borderColor: '#30363d', timeVisible: true }},
  rightPriceScale: {{ borderColor: '#30363d' }},
}};

function makeChart(id, height) {{
  const el = document.getElementById(id);
  return LightweightCharts.createChart(el, {{ ...chartOpts, width: el.offsetWidth, height }});
}}

// Candlestick
const candleChart = makeChart('candle-chart', 360);
const candleSeries = candleChart.addCandlestickSeries({{
  upColor: '#3fb950', downColor: '#f85149',
  borderUpColor: '#3fb950', borderDownColor: '#f85149',
  wickUpColor: '#3fb950', wickDownColor: '#f85149',
}});
candleSeries.setData(ohlcv);
candleChart.timeScale().fitContent();

// Volume
const volChart = makeChart('volume-chart', 200);
const volSeries = volChart.addHistogramSeries({{ priceFormat: {{ type: 'volume' }} }});
volSeries.setData(volumeData);
volChart.timeScale().fitContent();

// Returns
const retChart = makeChart('returns-chart', 200);
const retSeries = retChart.addLineSeries({{ color: '#d29922', lineWidth: 1 }});
retSeries.setData(dailyReturns);
retChart.timeScale().fitContent();

// Sync time scales
candleChart.timeScale().subscribeVisibleLogicalRangeChange(range => {{
  if (range) {{ volChart.timeScale().setVisibleLogicalRange(range); retChart.timeScale().setVisibleLogicalRange(range); }}
}});

// Responsive resize
window.addEventListener('resize', () => {{
  ['candle-chart','volume-chart','returns-chart'].forEach(id => {{
    const el = document.getElementById(id);
    const chart = id === 'candle-chart' ? candleChart : id === 'volume-chart' ? volChart : retChart;
    chart.applyOptions({{ width: el.offsetWidth }});
  }});
}});
</script>
</body>
</html>"""


def build_filestats_dashboard_html(payload: dict[str, Any]) -> str:
    ticker = str(payload.get("ticker") or "UNKNOWN")
    generated_at = str(payload.get("generated_at") or "")
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}

    docs = payload.get("docs") if isinstance(payload.get("docs"), list) else []
    financials = (
        payload.get("financials") if isinstance(payload.get("financials"), list) else []
    )
    risk_notes = (
        payload.get("risk_notes") if isinstance(payload.get("risk_notes"), list) else []
    )
    price_history = (
        payload.get("price_history_1y")
        if isinstance(payload.get("price_history_1y"), list)
        else []
    )
    extraction_failures = (
        payload.get("extraction_failures")
        if isinstance(payload.get("extraction_failures"), list)
        else []
    )
    low_conf = (
        payload.get("low_confidence_financials")
        if isinstance(payload.get("low_confidence_financials"), list)
        else []
    )
    company_memory = (
        payload.get("company_memory")
        if isinstance(payload.get("company_memory"), dict)
        else {}
    )
    market_memory = (
        payload.get("market_memory")
        if isinstance(payload.get("market_memory"), dict)
        else {}
    )
    cockpit_local = (
        payload.get("cockpit_local_memory")
        if isinstance(payload.get("cockpit_local_memory"), dict)
        else {}
    )

    timestamps: list[str] = []
    closes: list[float] = []
    for row in price_history:
        if not isinstance(row, dict):
            continue
        close = _to_float(row.get("close"))
        ts = str(row.get("timestamp") or "")
        if close is None or not ts:
            continue
        timestamps.append(ts)
        closes.append(close)

    doc_class_counts: dict[str, int] = {}
    recent_docs: list[dict[str, str]] = []
    for row in docs:
        if not isinstance(row, dict):
            continue
        doc_class = str(row.get("doc_class") or "other").strip() or "other"
        doc_class_counts[doc_class] = int(doc_class_counts.get(doc_class, 0)) + 1
        recent_docs.append(
            {
                "published": str(row.get("published_at") or "")[:10],
                "doc_class": doc_class,
                "title": str(row.get("title") or ""),
                "document_id": str(row.get("document_id") or ""),
            }
        )

    financial_rows: list[dict[str, Any]] = []
    for row in financials[:20]:
        if not isinstance(row, dict):
            continue
        financial_rows.append(
            {
                "period_end": str(row.get("period_end") or ""),
                "period_type": str(row.get("period_type") or ""),
                "revenue": row.get("revenue"),
                "ebit": row.get("ebit"),
                "npat": row.get("np_attributable"),
                "operating_cf": row.get("operating_cf"),
                "capex": row.get("capex"),
            }
        )

    risk_rows: list[dict[str, str]] = []
    for row in risk_notes[:20]:
        if not isinstance(row, dict):
            continue
        risk_rows.append(
            {
                "published": str(row.get("published_at") or "")[:10],
                "title": str(row.get("title") or ""),
                "risk_summary": str(row.get("risk_summary") or ""),
                "guidance": str(row.get("guidance_summary") or ""),
            }
        )

    quality_counts = {
        "extraction_failures": len(
            [r for r in extraction_failures if isinstance(r, dict)]
        ),
        "low_conf_financials": len([r for r in low_conf if isinstance(r, dict)]),
        "risk_notes": len([r for r in risk_notes if isinstance(r, dict)]),
    }

    memory_counts = {
        "backend_company_entries": len(
            [r for r in (company_memory.get("entries") or []) if isinstance(r, dict)]
        ),
        "backend_market_items": len(
            [r for r in (market_memory.get("items") or []) if isinstance(r, dict)]
        ),
        "cockpit_agent_memory": len(
            [
                r
                for r in (cockpit_local.get("agent_memory") or [])
                if isinstance(r, dict)
            ]
        ),
        "cockpit_dossier_findings": len(
            [
                r
                for r in (cockpit_local.get("dossier_findings") or [])
                if isinstance(r, dict)
            ]
        ),
        "cockpit_watchlist_history": len(
            [
                r
                for r in (cockpit_local.get("watchlist_history") or [])
                if isinstance(r, dict)
            ]
        ),
        "cockpit_strategy_criteria": len(
            [
                r
                for r in (cockpit_local.get("strategy_criteria") or [])
                if isinstance(r, dict)
            ]
        ),
    }

    cards = [
        ("Ticker", ticker),
        ("Docs", str(summary.get("doc_count", len(docs)))),
        (
            "Financial Periods",
            str(summary.get("financial_period_count", len(financials))),
        ),
        ("1Y Points", str(summary.get("price_points_1y", len(timestamps)))),
        (
            "Last Close",
            (
                f"{float(summary.get('last_close')):,.4f}"
                if _to_float(summary.get("last_close")) is not None
                else "n/a"
            ),
        ),
        (
            "1Y Return",
            (
                f"{float(summary.get('one_year_return_pct')):+.2f}%"
                if _to_float(summary.get("one_year_return_pct")) is not None
                else "n/a"
            ),
        ),
        ("Risk Notes", str(summary.get("risk_note_count", len(risk_notes)))),
        (
            "Extraction Failures",
            str(
                summary.get(
                    "extraction_failure_count", quality_counts["extraction_failures"]
                )
            ),
        ),
    ]
    cards_html = "".join(
        f'<div class="card"><div class="label">{escape(label)}</div><div class="value mono">{escape(value)}</div></div>'
        for label, value in cards
    )

    body = f"""
    <section class="hero">
      <h1>{escape(ticker)} Filestats Dashboard</h1>
      <p>Visual company data dump with price, filing, financial, quality, and memory context.</p>
      <p class="meta mono">generated={escape(generated_at)} | price_window=1y daily</p>
    </section>
    <section class="grid">{cards_html}</section>
    <section class="panel"><h2>Price (1Y Daily Close)</h2><div id="fs-price" class="plot"></div></section>
    <section class="panel"><h2>Document Classes</h2><div id="fs-doc-class" class="plot"></div></section>
    <section class="panel"><h2>Latest Financial Snapshot</h2><div id="fs-financial-bars" class="plot"></div></section>
    <section class="panel"><h2>Data Quality</h2><div id="fs-quality" class="plot"></div></section>
    <section class="panel"><h2>Memory Surface Counts</h2><div id="fs-memory" class="plot"></div></section>
    <section class="panel"><h2>Recent Documents</h2><div id="fs-docs-table" class="plot"></div></section>
    <section class="panel"><h2>Narrative / Risk Notes</h2><div id="fs-risk-table" class="plot"></div></section>
    """

    latest_fin = financial_rows[0] if financial_rows else {}
    fin_labels = ["Revenue", "EBIT", "NPAT", "Operating CF", "Capex"]
    fin_values = [
        _to_float(latest_fin.get("revenue")),
        _to_float(latest_fin.get("ebit")),
        _to_float(latest_fin.get("npat")),
        _to_float(latest_fin.get("operating_cf")),
        _to_float(latest_fin.get("capex")),
    ]

    doc_classes_sorted = sorted(
        doc_class_counts.items(), key=lambda item: item[1], reverse=True
    )
    doc_class_names = [name for name, _ in doc_classes_sorted]
    doc_class_values = [count for _, count in doc_classes_sorted]

    docs_table = recent_docs[:30]
    risks_table = risk_rows[:20]

    script = f"""
    const timestamps = {_json_compact(timestamps)};
    const closes = {_json_compact(closes)};
    const docClassNames = {_json_compact(doc_class_names)};
    const docClassValues = {_json_compact(doc_class_values)};
    const finLabels = {_json_compact(fin_labels)};
    const finValues = {_json_compact(fin_values)};
    const qualityCounts = {_json_compact(quality_counts)};
    const memoryCounts = {_json_compact(memory_counts)};
    const docsTable = {_json_compact(docs_table)};
    const risksTable = {_json_compact(risks_table)};
    const finPeriodLabel = {_json_compact(str(latest_fin.get("period_end") or ""))};

    const baseLayout = {{
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: {{color: '#e6edf3'}},
      margin: {{l: 60, r: 20, t: 30, b: 90}}
    }};

    Plotly.newPlot('fs-price', [
      {{type: 'scatter', mode: 'lines', x: timestamps, y: closes, line: {{color: '#58a6ff', width: 2}}, name: 'Close'}}
    ], {{...baseLayout, xaxis: {{type: 'date'}}}}, {{displayModeBar: false, responsive: true}});

    Plotly.newPlot('fs-doc-class', [
      {{type: 'bar', x: docClassNames, y: docClassValues, marker: {{color: '#3fb950'}}}}
    ], baseLayout, {{displayModeBar: false, responsive: true}});

    Plotly.newPlot('fs-financial-bars', [
      {{type: 'bar', x: finLabels, y: finValues, marker: {{color: ['#58a6ff','#3fb950','#d29922','#2f81f7','#f85149']}}}}
    ], {{...baseLayout, title: {{text: finPeriodLabel ? `Period: ${{finPeriodLabel}}` : 'No financial rows'}}}}, {{displayModeBar: false, responsive: true}});

    Plotly.newPlot('fs-quality', [
      {{type: 'bar', x: Object.keys(qualityCounts), y: Object.values(qualityCounts), marker: {{color: ['#f85149','#d29922','#58a6ff']}}}}
    ], baseLayout, {{displayModeBar: false, responsive: true}});

    Plotly.newPlot('fs-memory', [
      {{type: 'bar', x: Object.keys(memoryCounts), y: Object.values(memoryCounts), marker: {{color: '#7ee787'}}}}
    ], {{...baseLayout, margin: {{l: 80, r: 20, t: 20, b: 140}}}}, {{displayModeBar: false, responsive: true}});

    Plotly.newPlot('fs-docs-table', [{{
      type: 'table',
      header: {{
        values: ['Published', 'Class', 'Title', 'Document ID'],
        fill: {{color: '#1f2937'}},
        font: {{color: '#e6edf3'}},
        align: 'left'
      }},
      cells: {{
        values: [
          docsTable.map(r => r.published || ''),
          docsTable.map(r => r.doc_class || ''),
          docsTable.map(r => r.title || ''),
          docsTable.map(r => r.document_id || ''),
        ],
        fill: {{color: '#161b22'}},
        font: {{color: '#e6edf3'}},
        align: 'left'
      }}
    }}], {{paper_bgcolor:'rgba(0,0,0,0)', margin: {{l: 10, r: 10, t: 10, b: 10}}}}, {{displayModeBar: false, responsive: true}});

    Plotly.newPlot('fs-risk-table', [{{
      type: 'table',
      header: {{
        values: ['Published', 'Title', 'Risk Summary', 'Guidance'],
        fill: {{color: '#1f2937'}},
        font: {{color: '#e6edf3'}},
        align: 'left'
      }},
      cells: {{
        values: [
          risksTable.map(r => r.published || ''),
          risksTable.map(r => r.title || ''),
          risksTable.map(r => r.risk_summary || ''),
          risksTable.map(r => r.guidance || ''),
        ],
        fill: {{color: '#161b22'}},
        font: {{color: '#e6edf3'}},
        align: 'left'
      }}
    }}], {{paper_bgcolor:'rgba(0,0,0,0)', margin: {{l: 10, r: 10, t: 10, b: 10}}}}, {{displayModeBar: false, responsive: true}});
    """

    return _build_document(f"{ticker} Filestats Dashboard", body, script)


def build_verification_dashboard_html(payload: dict[str, Any]) -> str:
    ticker = str(payload.get("ticker") or "ALL")
    checks = payload.get("checks") if isinstance(payload.get("checks"), dict) else {}
    remediation = (
        payload.get("remediation")
        if isinstance(payload.get("remediation"), list)
        else []
    )
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
                    "title": str(
                        row.get("title")
                        or row.get("document_id")
                        or row.get("source_document_id")
                        or ""
                    ),
                    "detail": str(
                        row.get("error")
                        or row.get("status")
                        or row.get("period_end")
                        or ""
                    ),
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
