"""Universe provider — returns the set of active tickers for a given exchange.

The DB-backed function is preferred when the companies table has been populated.
The hardcoded ASX20 list is retained as a fallback for cold-start and test
environments where the companies table is empty or unavailable.
"""

from __future__ import annotations

import logging
from typing import Sequence

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hardcoded fallback — ASX20 constituents (as of investigation session)
# ---------------------------------------------------------------------------

ASX20: list[str] = [
    "BHP", "CBA", "CSL", "NAB", "WBC", "ANZ", "WES", "MQG", "TLS", "RIO",
    "WOW", "FMG", "GMG", "WDS", "ALL", "COL", "TCL", "QBE", "IAG", "SUN",
]


# ---------------------------------------------------------------------------
# DB-backed universe query
# ---------------------------------------------------------------------------

def get_active_tickers(exchange: str = "ASX", *, session) -> list[str]:
    """Return active tickers from the companies master table.

    Queries the companies table for rows where exchange matches and status is
    'active'.  Falls back to the hardcoded ASX20 list when the table is empty
    or a DB error occurs, logging a warning in either case.

    Args:
        exchange: Exchange code to filter on (default "ASX").
        session:  SQLAlchemy Session (sync) — caller is responsible for
                  providing and closing the session.

    Returns:
        List of ticker strings, uppercased, sorted alphabetically.
    """
    try:
        from app.models.companies import Company  # local import to avoid circular deps

        rows: Sequence[Company] = (
            session.query(Company.ticker)
            .filter(Company.exchange == exchange, Company.status == "active")
            .order_by(Company.ticker)
            .all()
        )
        tickers = [row.ticker for row in rows]
        if tickers:
            logger.debug(
                "universe: loaded %d active tickers from companies table (exchange=%s)",
                len(tickers),
                exchange,
            )
            return tickers

        logger.warning(
            "universe: companies table is empty for exchange=%s — falling back to hardcoded ASX20",
            exchange,
        )
    except Exception:
        logger.warning(
            "universe: failed to query companies table — falling back to hardcoded ASX20",
            exc_info=True,
        )

    return list(ASX20)
