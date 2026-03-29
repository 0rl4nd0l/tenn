"""reader.py — Load and save portfolio definitions from/to JSON.

Handles deserialization of holdings into frozen dataclasses and
serialization back to portable JSON.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.modules.portfolio.types import Holding, PortfolioDefinition


def load_portfolio(path: str | Path) -> PortfolioDefinition:
    """Read a portfolio JSON file and return a frozen PortfolioDefinition."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    holdings = tuple(
        Holding(
            ticker=h["ticker"],
            shares=h.get("shares"),
            weight_override=h.get("weight_override"),
            cost_basis=h.get("cost_basis"),
            sector=h.get("sector"),
            geography=h.get("geography"),
        )
        for h in raw.get("holdings", [])
    )
    return PortfolioDefinition(
        portfolio_id=raw["portfolio_id"],
        name=raw["name"],
        holdings=holdings,
        created_at=raw.get("created_at", ""),
        updated_at=raw.get("updated_at", ""),
    )


def save_portfolio(portfolio: PortfolioDefinition, path: str | Path) -> None:
    """Write a PortfolioDefinition to JSON."""
    payload = {
        "portfolio_id": portfolio.portfolio_id,
        "name": portfolio.name,
        "holdings": [
            {k: v for k, v in {
                "ticker": h.ticker,
                "shares": h.shares,
                "weight_override": h.weight_override,
                "cost_basis": h.cost_basis,
                "sector": h.sector,
                "geography": h.geography,
            }.items() if v is not None}
            for h in portfolio.holdings
        ],
        "created_at": portfolio.created_at,
        "updated_at": portfolio.updated_at,
    }
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
