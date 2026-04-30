from __future__ import annotations

from app.services.analysis.sector_comparison import get_sector_for_ticker

SECTOR_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Materials": ("iron ore", "lithium", "copper", "gold", "bulk commodity"),
    "Energy": ("oil", "gas", "lng", "coal", "hydrogen", "green hydrogen"),
    "Financials": ("bank", "banks", "lender", "credit"),
    "Healthcare": ("healthcare", "medtech", "hospital", "biotech"),
    "Technology": ("software", "cloud", "data centre", "semiconductor"),
}
_MARKET_FRAME_KEYWORDS = ("sector", "industry", "market", "commodity")


def infer_sector(statement: str, tickers: list[str] | None = None) -> str | None:
    lowered = str(statement or "").lower()
    normalized_tickers = [
        str(ticker or "").strip().upper() for ticker in list(tickers or []) if str(ticker or "").strip()
    ]
    has_market_frame = any(token in lowered for token in _MARKET_FRAME_KEYWORDS)

    for sector, keywords in SECTOR_KEYWORDS.items():
        sector_terms = tuple(keywords) + (sector.lower(),)
        if any(keyword in lowered for keyword in sector_terms) and (
            not normalized_tickers or has_market_frame
        ):
            return sector

    if normalized_tickers and has_market_frame:
        sectors = {get_sector_for_ticker(ticker) for ticker in normalized_tickers}
        sectors.discard(None)
        if len(sectors) == 1:
            return next(iter(sectors))
    return None
