"""types.py — Frozen dataclasses for portfolio definitions.

All types are immutable (frozen=True). PortfolioDefinition is the canonical
input format; holdings are loaded from JSON via reader.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class Holding:
    """A single portfolio position.

    Only ticker is required. All other fields are optional and used
    for weight computation, sector exposure, and geographic breakdown.
    """

    ticker: str
    shares: float | None = None
    weight_override: float | None = None
    cost_basis: float | None = None
    sector: str | None = None
    geography: str | None = None


@dataclass(frozen=True)
class PortfolioDefinition:
    """A named portfolio with a list of holdings.

    Created/loaded via reader.py. The portfolio_id is used as the
    artifact filename stem.
    """

    portfolio_id: str
    name: str
    holdings: tuple[Holding, ...] = ()
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if not self.created_at:
            object.__setattr__(self, "created_at", now)
        if not self.updated_at:
            object.__setattr__(self, "updated_at", now)

    @property
    def tickers(self) -> tuple[str, ...]:
        """All tickers in the portfolio, preserving order."""
        return tuple(h.ticker for h in self.holdings)
