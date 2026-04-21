"""analyser.py — Portfolio analysis orchestrator.

Calls each sub-module, assembles the full portfolio artifact, and writes
the result to reports/portfolio/{portfolio_id}_summary.json.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.modules.portfolio.catalyst_calendar import compute_catalyst_calendar
from app.modules.portfolio.moat_quality import compute_moat_quality
from app.modules.portfolio.position_sizing import compute_position_sizing
from app.modules.portfolio.reader import load_portfolio
from app.modules.portfolio.risk_aggregation import compute_risk_aggregation
from app.modules.portfolio.types import PortfolioDefinition
from app.modules.portfolio.valuation_summary import compute_valuation_summary
from app.modules.portfolio.weights import compute_weights

logger = logging.getLogger(__name__)


def _default_reports_root() -> Path:
    """Derive reports root from canonical settings with a writable fallback."""
    backend_root = Path(__file__).resolve().parents[3]
    candidates = [
        Path(getattr(settings, "data_root", "/data")).expanduser().resolve() / "reports",
        backend_root / "reports",
    ]
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            if os.access(candidate, os.W_OK | os.X_OK):
                return candidate
        except OSError:
            continue
    return candidates[0]


class PortfolioAnalyser:
    """Orchestrates portfolio-level analysis across all sub-modules."""

    def run(
        self,
        definition: PortfolioDefinition,
        reports_root: str | None = None,
        prices: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Run full portfolio analysis and write the summary artifact.

        Args:
            definition: The portfolio definition with holdings.
            reports_root: Override for artifact read/write root.
            prices: Optional current prices per ticker for weight computation.

        Returns:
            The full portfolio summary dict (also written to disk).
        """
        root = reports_root or str(_default_reports_root())
        tickers = definition.tickers

        # Compute weights
        weights = compute_weights(definition.holdings, prices)

        logger.info(
            "Running portfolio analysis for %s (%d holdings)",
            definition.portfolio_id, len(tickers),
        )

        # Run each sub-module
        valuation = compute_valuation_summary(tickers, weights, root)
        moat = compute_moat_quality(tickers, weights, root)
        catalysts = compute_catalyst_calendar(tickers, root)
        risk = compute_risk_aggregation(tickers, weights, root)
        sizing = compute_position_sizing(tickers, weights, root)

        # Collect all missing tickers
        all_missing = sorted(set(
            valuation.get("holdings_missing", [])
            + moat.get("holdings_missing", [])
            + catalysts.get("holdings_missing", [])
            + risk.get("holdings_missing", [])
            + sizing.get("holdings_missing", [])
        ))

        # Assemble summary
        summary: dict[str, Any] = {
            "schema_version": "1.0",
            "portfolio_id": definition.portfolio_id,
            "portfolio_name": definition.name,
            "holdings_count": len(tickers),
            "generated_at": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ",
            ),
            "weights": {
                t: round(w, 4) for t, w in weights.items()
            },
            "valuation": valuation,
            "moat_quality": moat,
            "catalyst_calendar": catalysts,
            "risk_aggregation": risk,
            "position_sizing": sizing,
            "holdings_missing_any_artifact": all_missing,
        }

        # Write artifact
        out_path = self._write_summary(definition.portfolio_id, summary, root)
        summary["artifact_path"] = str(out_path)
        logger.info("Portfolio summary written to %s", out_path)

        return summary

    def _write_summary(
        self,
        portfolio_id: str,
        summary: dict[str, Any],
        reports_root: str,
    ) -> Path:
        """Atomic write of portfolio summary JSON."""
        out_dir = Path(reports_root) / "portfolio"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{portfolio_id}_summary.json"

        fd, tmp_path = tempfile.mkstemp(dir=str(out_dir), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, default=str, ensure_ascii=False)
                f.write("\n")
            os.replace(tmp_path, str(path))
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        return path


def analyse_portfolio(
    portfolio_path: str,
    reports_root: str | None = None,
    prices: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Convenience entry point: load portfolio and run analysis.

    Args:
        portfolio_path: Path to portfolio JSON file.
        reports_root: Override for artifact read/write root.
        prices: Optional current prices per ticker.

    Returns:
        The full portfolio summary dict.
    """
    definition = load_portfolio(portfolio_path)
    analyser = PortfolioAnalyser()
    return analyser.run(definition, reports_root, prices)
