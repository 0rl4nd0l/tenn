#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT = REPO_ROOT.parent


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATION = _load_module(ROOT / "scripts" / "validation_quality_cycle.py", "validation_quality_cycle")
FORENSIC = _load_module(ROOT / "balance_sheet_forensic_analysis.py", "balance_sheet_forensic_analysis")
SCORER = _load_module(ROOT / "scripts" / "score_gold_set.py", "score_gold_set")


def _find_latest_canonical_for_ticker(ticker: str) -> Path | None:
    t = str(ticker or "").strip().upper()
    if not t:
        return None
    base = ROOT / "reports" / f"stress_reference_{t}"
    if not base.exists():
        return None

    candidates = []
    for run_dir in base.glob("run_*"):
        for name in ("canonical_section_capture.csv", "canonical.csv"):
            p = run_dir / name
            if p.exists():
                candidates.append(p)
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _read_optional_csv(path: Path | None) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame()
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate ticker canonical outputs and optional gold score.")
    ap.add_argument("--ticker", default="")
    ap.add_argument("--canonical-csv", default="")
    ap.add_argument("--derived-csv", default="")
    ap.add_argument("--risk-csv", default="")
    ap.add_argument("--with-gold", default="", help="Optional gold dir path (e.g., gold/BHP)")
    ap.add_argument("--out-dir", default="")
    args = ap.parse_args()

    canonical_csv = (
        Path(args.canonical_csv).expanduser().resolve()
        if str(args.canonical_csv).strip()
        else _find_latest_canonical_for_ticker(str(args.ticker))
    )
    if canonical_csv is None or not canonical_csv.exists():
        raise SystemExit("Canonical CSV not found. Provide --canonical-csv or a valid --ticker with prior run artifacts.")

    default_out = ROOT / "reports" / "validate_ticker" / (
        str(args.ticker).strip().upper() or canonical_csv.parent.name
    )
    out_dir = Path(args.out_dir).expanduser().resolve() if str(args.out_dir).strip() else default_out
    out_dir.mkdir(parents=True, exist_ok=True)

    derived_csv = Path(args.derived_csv).expanduser().resolve() if str(args.derived_csv).strip() else (canonical_csv.parent / "derived_metrics.csv")
    risk_csv = Path(args.risk_csv).expanduser().resolve() if str(args.risk_csv).strip() else (canonical_csv.parent / "risk_signals.csv")

    canonical_df = pd.read_csv(canonical_csv)
    derived_df = _read_optional_csv(derived_csv)
    risk_df = _read_optional_csv(risk_csv)

    VALIDATION.run_validation(canonical_df, derived_df, risk_df, out_dir)
    forensic_summary = FORENSIC.run_forensic(canonical_df, out_dir, min_confidence=0)

    summary = {
        "ticker": str(args.ticker).strip().upper(),
        "canonical_csv": str(canonical_csv),
        "derived_csv": str(derived_csv) if derived_csv.exists() else "",
        "risk_csv": str(risk_csv) if risk_csv.exists() else "",
        "out_dir": str(out_dir),
        "forensic_summary": forensic_summary,
        "gold_score": None,
    }

    if str(args.with_gold).strip():
        gold_dir = Path(args.with_gold).expanduser().resolve()
        if not gold_dir.exists():
            raise SystemExit(f"Gold directory not found: {gold_dir}")
        gold_out_dir = out_dir / "gold_score"
        gold_result = SCORER.score_gold_set(
            gold_dir=gold_dir,
            canonical_csv=canonical_csv,
            out_dir=gold_out_dir,
        )
        summary["gold_score"] = {
            "out_dir": str(gold_out_dir),
            "totals": gold_result.get("totals", {}),
        }

    summary_path = out_dir / "validate_ticker_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Validation output: {out_dir}")
    print(f"Summary: {summary_path}")
    if summary.get("gold_score"):
        totals = summary["gold_score"].get("totals", {})
        print(
            "Gold score P/R/F1: "
            f"{totals.get('precision', 0):.6f}/"
            f"{totals.get('recall', 0):.6f}/"
            f"{totals.get('f1', 0):.6f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
