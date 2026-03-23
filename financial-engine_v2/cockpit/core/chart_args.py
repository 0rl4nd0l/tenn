from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Callable

# Well-known crypto base tickers — shorthand mode bypasses backend OHLC.
_CRYPTO_BASES = frozenset({
    "BTC", "ETH", "SOL", "DOGE", "XRP", "ADA", "DOT", "AVAX", "MATIC",
    "LINK", "UNI", "AAVE", "ATOM", "NEAR", "APT", "ARB", "OP", "LTC",
    "BNB", "FIL", "TRX", "SHIB", "PEPE",
})


def _parse_ticker_and_timeframe(raw: str) -> tuple[str, str]:
    """Split *raw* into (ticker, timeframe).

    Examples
    --------
    >>> _parse_ticker_and_timeframe("BHP")
    ('BHP', '1d')
    >>> _parse_ticker_and_timeframe("BTC 4h")
    ('BTC', '4h')
    """
    parts = raw.strip().split()
    ticker = parts[0].upper() if parts else ""
    timeframe = "1d"
    if len(parts) >= 2:
        candidate = parts[1].lower()
        if candidate in {"1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"}:
            timeframe = candidate
    return ticker, timeframe


def prepare_chart_action_args(
    raw_ticker: str,
    *,
    parse_kv_args: Callable[[str], dict[str, Any]],
    tool_router: Any,
    out_dir: Path,
) -> tuple[dict[str, Any] | None, str | None]:
    """Build arguments for the ``show_candlestick`` action.

    Returns ``(args_dict, None)`` on success or ``(None, error_string)`` on
    failure.

    For crypto tickers the function returns shorthand mode (``-s``) without
    touching the backend.  For equity tickers it fetches OHLCV via
    *tool_router* and writes a CSV file, returning file mode (``-f``).
    """
    ticker, timeframe = _parse_ticker_and_timeframe(raw_ticker)
    if not ticker:
        return None, "no ticker provided"

    # Crypto shorthand — skip backend OHLC.
    if ticker in _CRYPTO_BASES:
        return {
            "mode_flag": "-s",
            "mode_value": f"{ticker}/USDT",
            "timeframe": timeframe,
        }, None

    # Equity path — fetch OHLCV rows and write a CSV.
    try:
        rows = tool_router.build_candlestick_ohlc_lines(
            ticker,
            range_="1y",
            interval=timeframe,
            max_history_rows=260,
        )
    except Exception as exc:
        return None, f"no OHLC data for {ticker}: {exc}"

    if not rows:
        return None, f"no OHLC data for {ticker}"

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_name = f"{ticker}_candles_{timeframe}.csv"
    csv_path = out_dir / csv_name

    fieldnames = ["timestamp", "open", "high", "low", "close", "volume"]
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fieldnames})

    return {
        "mode_flag": "-f",
        "mode_value": str(csv_path),
        "timeframe": timeframe,
    }, None
