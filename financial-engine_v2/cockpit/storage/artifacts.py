from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _render_price_state_md(ps: dict) -> str:
    """Render a ## Price State markdown section from a price_state dict."""
    lines = ["## Price State", ""]
    if not ps.get("ok"):
        lines.append("Status: unavailable")
        if ps.get("error"):
            lines.append(f"Error: {ps['error']}")
        return "\n".join(lines)

    ticker = ps.get("ticker", "")
    currency = ps.get("currency", "")
    last_close = ps.get("last_close")
    ret_1d = ps.get("ret_1d")
    ret_20d = ps.get("ret_20d")
    trend_regime = ps.get("trend_regime", "")
    vol_20d_ann = ps.get("vol_20d_ann")
    drawdown = ps.get("drawdown_from_63d_high")
    market_time = ps.get("market_time_utc", "")
    data_age_hours = ps.get("data_age_hours")
    stale_data = ps.get("stale_data", False)
    history_points = ps.get("history_points")

    lines.append(f"ticker `{ticker}`")
    lines.append(f"Last close: {last_close} {currency}")

    ret_parts = []
    if ret_1d is not None:
        ret_parts.append(f"1D {ret_1d:+.2f}%")
    if ret_20d is not None:
        ret_parts.append(f"20D {ret_20d:+.2f}%")
    if ret_parts:
        lines.append(f"Returns: {', '.join(ret_parts)}")

    trend_parts = []
    if trend_regime:
        trend_parts.append(f"regime `{trend_regime}`")
    if vol_20d_ann is not None:
        trend_parts.append(f"vol(20D ann) {vol_20d_ann:.2f}%")
    if drawdown is not None:
        trend_parts.append(f"drawdown(63D high) {drawdown:.2f}%")
    if trend_parts:
        lines.append(f"Trend: {', '.join(trend_parts)}")

    freshness_parts = ["stale" if stale_data else "fresh"]
    if market_time:
        freshness_parts.append(f"market_time={market_time}")
    if data_age_hours is not None:
        freshness_parts.append(f"age={data_age_hours}h")
    if history_points is not None:
        freshness_parts.append(f"history_points={history_points}")
    lines.append(f"Freshness: {', '.join(freshness_parts)}")

    return "\n".join(lines)


class ArtifactStore:
    def __init__(self, repo_root: Path, exports_dir: str, reports_dir: str) -> None:
        self.repo_root = repo_root
        self.exports_dir = (repo_root / exports_dir).resolve()
        self.reports_dir = (repo_root / reports_dir).resolve()
        self.logs_dir = (self.reports_dir / "cockpit" / "logs").resolve()
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def write_json(self, rel_path: str, payload: dict[str, Any]) -> str:
        path = (self.repo_root / rel_path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(path)

    def write_text(self, rel_path: str, content: str) -> str:
        path = (self.repo_root / rel_path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return str(path)

    def write_analysis(self, thread_id: str, question: str, answer: str, payload: dict[str, Any]) -> tuple[str, str]:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        base = self.exports_dir / thread_id
        base.mkdir(parents=True, exist_ok=True)

        md_path = base / f"{ts}.md"
        json_path = base / f"{ts}.json"

        # Find price_state in payload evidence.
        price_state: dict | None = None
        for ev in (payload.get("evidence") or []):
            ps = (ev.get("details") or {}).get("price_state")
            if isinstance(ps, dict):
                price_state = ps
                break

        md = f"# Analysis\n\n## Question\n{question}\n\n## Answer\n{answer}\n"
        if price_state is not None:
            md += "\n" + _render_price_state_md(price_state) + "\n"

        md_path.write_text(md, encoding="utf-8")
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(md_path), str(json_path)
