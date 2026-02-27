from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        try:
            parsed = float(value)
        except Exception:
            return None
        if not math.isfinite(parsed):
            return None
        return parsed

    @classmethod
    def _fmt_number(cls, value: Any, *, decimals: int = 2) -> str | None:
        parsed = cls._safe_float(value)
        if parsed is None:
            return None
        return f"{parsed:.{decimals}f}"

    @classmethod
    def _fmt_pct(cls, value: Any, *, signed: bool = True) -> str | None:
        parsed = cls._safe_float(value)
        if parsed is None:
            return None
        if signed:
            return f"{parsed:+.2f}%"
        return f"{parsed:.2f}%"

    @staticmethod
    def _extract_price_state(payload: dict[str, Any]) -> dict[str, Any] | None:
        direct = payload.get("price_state")
        if isinstance(direct, dict):
            return direct
        evidence = payload.get("evidence")
        if not isinstance(evidence, list):
            return None
        for item in evidence:
            if not isinstance(item, dict):
                continue
            details = item.get("details")
            if not isinstance(details, dict):
                continue
            state = details.get("price_state")
            if isinstance(state, dict):
                return state
        return None

    @classmethod
    def _render_price_state_section(cls, payload: dict[str, Any]) -> str:
        state = cls._extract_price_state(payload)
        if not isinstance(state, dict):
            return ""

        ticker = str(state.get("ticker") or "").strip().upper()
        symbol = str(state.get("symbol") or "").strip().upper()
        currency = str(state.get("currency") or "").strip().upper()

        lines: list[str] = ["## Price State"]
        identity: list[str] = []
        if ticker:
            identity.append(f"ticker `{ticker}`")
        if symbol:
            identity.append(f"symbol `{symbol}`")
        if currency:
            identity.append(f"currency `{currency}`")
        if identity:
            lines.append(f"- Instrument: {', '.join(identity)}")

        if not bool(state.get("ok")):
            lines.append("- Status: unavailable")
            error = str(state.get("error") or "price lookup failed")
            lines.append(f"- Error: {error}")
            return "\n".join(lines) + "\n"

        last_close = cls._fmt_number(state.get("last_close"))
        previous_close = cls._fmt_number(state.get("previous_close_effective"))
        if last_close:
            suffix = f" {currency}" if currency else ""
            lines.append(f"- Last close: {last_close}{suffix}")
        if previous_close:
            suffix = f" {currency}" if currency else ""
            lines.append(f"- Previous close: {previous_close}{suffix}")

        ret_1d = cls._fmt_pct(state.get("ret_1d"))
        ret_20d = cls._fmt_pct(state.get("ret_20d"))
        if ret_1d or ret_20d:
            returns_parts = []
            if ret_1d:
                returns_parts.append(f"1D {ret_1d}")
            if ret_20d:
                returns_parts.append(f"20D {ret_20d}")
            lines.append(f"- Returns: {', '.join(returns_parts)}")

        trend = str(state.get("trend_regime") or "neutral").strip().lower() or "neutral"
        vol = cls._fmt_pct(state.get("vol_20d_ann"), signed=False)
        drawdown = cls._fmt_pct(state.get("drawdown_from_63d_high"))
        trend_parts = [f"regime `{trend}`"]
        if vol:
            trend_parts.append(f"vol(20D ann) {vol}")
        if drawdown:
            trend_parts.append(f"drawdown(63D high) {drawdown}")
        lines.append(f"- Trend: {', '.join(trend_parts)}")

        stale = state.get("stale_data")
        freshness = "stale" if stale is True else "fresh" if stale is False else "unknown"
        market_time = str(state.get("market_time_utc") or "").strip()
        age_hours = cls._fmt_number(state.get("data_age_hours"), decimals=1)
        history_points = state.get("history_points")
        points_txt = None
        parsed_points = cls._safe_float(history_points)
        if parsed_points is not None:
            points_txt = str(int(parsed_points))
        freshness_parts = [freshness]
        if market_time:
            freshness_parts.append(f"market_time={market_time}")
        if age_hours:
            freshness_parts.append(f"age={age_hours}h")
        if points_txt:
            freshness_parts.append(f"history_points={points_txt}")
        lines.append(f"- Freshness: {', '.join(freshness_parts)}")

        if bool(state.get("insufficient_history")):
            lines.append("- History note: insufficient data for all long-window metrics.")

        return "\n".join(lines) + "\n"

    def write_analysis(self, thread_id: str, question: str, answer: str, payload: dict[str, Any]) -> tuple[str, str]:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = self.exports_dir / thread_id
        base.mkdir(parents=True, exist_ok=True)

        md_path = base / f"{ts}.md"
        json_path = base / f"{ts}.json"

        md_body = f"# Analysis\n\n## Question\n{question}\n\n## Answer\n{answer}\n"
        price_state_section = self._render_price_state_section(payload)
        if price_state_section:
            md_body += "\n" + price_state_section
        md_path.write_text(md_body, encoding="utf-8")
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(md_path), str(json_path)
