#!/usr/bin/env python3
from __future__ import annotations

import itertools
import json
import os
import subprocess
from pathlib import Path
from typing import Any


FLAG_NAMES = (
    "ENABLE_STRICT_PERIOD_FILTER",
    "ENABLE_STRICT_SCOPE_FILTER",
    "ENABLE_STRICT_EVIDENCE",
    "ENABLE_ANOMALY_FILTER",
)


def _flag_env(flags: dict[str, bool]) -> dict[str, str]:
    out: dict[str, str] = {}
    for name in FLAG_NAMES:
        out[name] = "1" if bool(flags.get(name, True)) else "0"
    return out


def run_flag_experiments(
    *,
    python_bin: str,
    routed_script: str,
    pdfs: list[str],
    docling_venv: str,
    out_dir: str,
    strict_truth_mode: bool = True,
) -> dict[str, Any]:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    experiments: list[dict[str, Any]] = []
    for combo in itertools.product([True, False], repeat=len(FLAG_NAMES)):
        flags = dict(zip(FLAG_NAMES, combo))
        combo_id = "".join("1" if v else "0" for v in combo)
        out_json = str(Path(out_dir) / f"routed_flags_{combo_id}.json")
        run_root = str(Path(out_dir) / f"runs_{combo_id}")
        cmd = [python_bin, routed_script]
        for pdf in pdfs:
            cmd += ["--pdf", pdf]
        cmd += [
            "--docling-venv",
            docling_venv,
            "--docling-cpu",
            "--subprocess-timeout-sec",
            "30",
            "--out-json",
            out_json,
            "--run-root",
            run_root,
        ]
        if strict_truth_mode:
            cmd.append("--strict-truth-mode")
        env = dict(os.environ)
        env.update(_flag_env(flags))
        proc = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        rec: dict[str, Any] = {"flags": flags, "combo_id": combo_id, "returncode": proc.returncode, "out_json": out_json}
        if proc.returncode == 0 and Path(out_json).exists():
            payload = json.loads(Path(out_json).read_text(encoding="utf-8"))
            docs = list(payload.get("documents") or [])
            metric_counts = [len(dict(d.get("metrics") or {})) for d in docs]
            verification = [float(d.get("verification_ratio") or 0.0) for d in docs]
            rec["metrics_per_doc"] = (sum(metric_counts) / max(1, len(metric_counts)))
            rec["empty_docs"] = sum(1 for c in metric_counts if c == 0)
            rec["verification_ratio_avg"] = (sum(verification) / max(1, len(verification)))
        else:
            rec["stderr"] = (proc.stderr or "")[:300]
        experiments.append(rec)
    return {"experiments": experiments}
