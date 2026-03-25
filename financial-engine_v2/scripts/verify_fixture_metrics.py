#!/usr/bin/env python3
"""
Verify financial metrics from ASX PDFs using Claude API (PDF vision).

Sends the PDF to Claude with a structured extraction prompt,
then outputs a fixture-ready JSON with hand-verified metrics.

Usage:
    python scripts/verify_fixture_metrics.py <pdf_path> <ticker> <period_type> <period_end>

Example:
    python scripts/verify_fixture_metrics.py data/asx/docs/CBA/financial_performance/2025-08-13_2025-annual-report_d3ff8317.pdf CBA A 2025-06-30
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path

# Load .env if ANTHROPIC_API_KEY not in environment
env_path = Path(__file__).parent.parent / ".env"
if "ANTHROPIC_API_KEY" not in os.environ and env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line.startswith("ANTHROPIC_API_KEY=") and not line.startswith("#"):
            key = line.split("=", 1)[1].strip().strip('"').strip("'")
            os.environ["ANTHROPIC_API_KEY"] = key
            break

import anthropic


METRIC_FIELDS = [
    "revenue", "ebit", "np_attributable",
    "operating_cf", "investing_cf", "financing_cf",
    "capex", "cash_end", "net_debt", "shares_outstanding",
]

EXTRACTION_PROMPT = """You are a financial data extraction expert. Extract the following metrics from this ASX financial report PDF.

TICKER: {ticker}
PERIOD TYPE: {period_type} (A=Annual, H=Half-year, Q=Quarterly)
EXPECTED PERIOD END: {period_end}

Extract these metrics (use the CURRENT period column, not prior period):

1. **revenue** — Total revenue/sales from ordinary activities. For banks: Net interest income + Non-interest income = Total income.
2. **ebit** — Earnings Before Interest and Tax. Use "Profit from operations" or "Operating profit" (BEFORE finance costs). NOT "Profit before tax" if it's after finance costs. For banks: use "Cash profit before tax" or "Statutory profit before income tax" — bank EBIT is typically reported pre-tax since interest IS the business.
3. **np_attributable** — Net profit/loss after tax ATTRIBUTABLE TO EQUITY HOLDERS OF THE PARENT. Not total group profit. Look for the line that says "attributable to owners/members/equity holders of the parent".
4. **operating_cf** — Net cash from operating activities.
5. **investing_cf** — Net cash used in investing activities (usually negative).
6. **financing_cf** — Net cash from/used in financing activities.
7. **capex** — Payments for property, plant and equipment only. NOT acquisitions. For banks: this is usually very small.
8. **cash_end** — Cash and cash equivalents at end of period. For banks: use "Cash and liquid assets" or balance sheet cash.
9. **net_debt** — Total borrowings minus cash. If not directly stated, derive from: total current borrowings + total non-current borrowings - cash_end. For banks: this metric is usually NOT applicable (set to null) because their balance sheet IS debt.
10. **shares_outstanding** — Total ordinary shares on issue minus treasury shares. Use the ABSOLUTE number (not in thousands or millions).

RULES:
- Report values in the document's stated scale (e.g., if "$M" then report in millions).
- State the scale clearly (thousands, millions, billions).
- Report the currency (AUD, USD, etc.).
- For negative values, use negative numbers (not parentheses).
- If a metric is genuinely not available or not applicable, set it to null.
- For each metric, cite the exact page, table/section, and row label.
- Verify period_end matches the document's reporting period.

Respond with ONLY valid JSON in this exact format:
{{
    "verified_period_end": "YYYY-MM-DD",
    "currency": "AUD",
    "scale": "millions",
    "metrics": {{
        "revenue": {{"value": 12345, "page": 10, "source": "Income Statement, 'Revenue from ordinary activities'"}},
        "ebit": {{"value": 5678, "page": 10, "source": "Income Statement, 'Profit from operations'"}},
        ...for each of the 10 metrics...
    }}
}}
"""


def extract_metrics(pdf_path: str, ticker: str, period_type: str, period_end: str) -> dict:
    """Send PDF to Claude and extract financial metrics."""
    client = anthropic.Anthropic()

    pdf_bytes = Path(pdf_path).read_bytes()
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    # Check file size - Claude has a ~32MB limit for PDFs
    size_mb = len(pdf_bytes) / (1024 * 1024)
    if size_mb > 30:
        print(f"WARNING: PDF is {size_mb:.1f}MB — may exceed Claude's limit. Consider using a smaller filing.", file=sys.stderr)

    prompt = EXTRACTION_PROMPT.format(
        ticker=ticker,
        period_type=period_type,
        period_end=period_end,
    )

    print(f"Sending {ticker} ({size_mb:.1f}MB) to Claude...", file=sys.stderr)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ],
    )

    # Extract JSON from response
    text = response.content[0].text
    # Try to find JSON block
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    return json.loads(text)


def build_fixture(result: dict, ticker: str, period_type: str, period_end: str, pdf_path: str) -> dict:
    """Convert Claude extraction result into eval fixture format."""
    scale_multipliers = {
        "thousands": 1_000,
        "millions": 1_000_000,
        "billions": 1_000_000_000,
        "units": 1,
    }

    scale = result.get("scale", "millions")
    multiplier = scale_multipliers.get(scale, 1_000_000)
    currency = result.get("currency", "AUD")

    metrics = {}
    expected_nulls = []
    tolerances = {}
    source_notes = []

    # Default tolerances per metric
    default_tol = {
        "revenue": 0.005, "ebit": 0.02, "np_attributable": 0.02,
        "operating_cf": 0.01, "investing_cf": 0.01, "financing_cf": 0.01,
        "capex": 0.02, "cash_end": 0.001, "net_debt": 0.05,
        "shares_outstanding": 0.01,
    }

    for metric in METRIC_FIELDS:
        entry = result.get("metrics", {}).get(metric, {})
        value = entry.get("value") if isinstance(entry, dict) else entry

        if value is None:
            expected_nulls.append(metric)
            continue

        # shares_outstanding is absolute count, not scaled
        if metric == "shares_outstanding":
            metrics[metric] = float(value)
        else:
            metrics[metric] = float(value) * multiplier

        tolerances[metric] = default_tol.get(metric, 0.02)

        if isinstance(entry, dict):
            source_notes.append(
                f"{metric}: page {entry.get('page', '?')}, {entry.get('source', 'unknown')}"
            )

    # Build source description
    source_desc = (
        f"Claude API verified from {Path(pdf_path).name} "
        f"({ticker}, {period_type}, {period_end}). "
        f"Currency={currency}, scale={scale}. "
        + "; ".join(source_notes)
    )

    fixture = {
        "_source": source_desc,
        "_verification": "claude-api-sonnet",
        "ticker": ticker,
        "pdf_path": pdf_path,
        "document_id": f"{ticker.lower()}_{period_end.replace('-', '')}_{period_type.lower()}",
        "period_type": period_type,
        "period_end": result.get("verified_period_end", period_end),
        "currency": currency,
        "scale": scale,
        "metrics": metrics,
        "expected_nulls": expected_nulls,
        "tolerances": tolerances,
        "config": {
            "min_accuracy_overall": 0.80,
        },
    }

    return fixture


def main():
    parser = argparse.ArgumentParser(description="Verify fixture metrics via Claude API")
    parser.add_argument("pdf_path", help="Path to PDF (relative to financial-engine_v2/)")
    parser.add_argument("ticker", help="ASX ticker")
    parser.add_argument("period_type", choices=["A", "H", "Q"], help="A=Annual, H=Half, Q=Quarterly")
    parser.add_argument("period_end", help="Period end date YYYY-MM-DD")
    parser.add_argument("--raw", action="store_true", help="Output raw Claude response instead of fixture")
    args = parser.parse_args()

    result = extract_metrics(args.pdf_path, args.ticker, args.period_type, args.period_end)

    if args.raw:
        print(json.dumps(result, indent=2))
    else:
        fixture = build_fixture(result, args.ticker, args.period_type, args.period_end, args.pdf_path)
        print(json.dumps(fixture, indent=2))


if __name__ == "__main__":
    main()
