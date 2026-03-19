#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
FINANCIAL_ENGINE_ROOT = REPO_ROOT / "financial-engine_v2"
BACKEND_ROOT = FINANCIAL_ENGINE_ROOT / "backend"
DEFAULT_OUTPUT = REPO_ROOT / "reports" / "pdf_extraction_benchmark" / "benchmark_report.json"
DEFAULT_RUN_ROOT = REPO_ROOT / "reports" / "pdf_extraction_benchmark" / "runs"
DEFAULT_GROUND_TRUTH = REPO_ROOT / "data" / "ground_truth"
DOC_ID_SUFFIX_RE = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$", re.IGNORECASE)
DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
METRIC_ALIAS = {
    "npat": "net_income",
    "np_attributable": "net_income",
    "capex": "capital_expenditure",
    "operating_cf": "operating_cash_flow",
    "investing_cf": "investing_cash_flow",
    "financing_cf": "financing_cash_flow",
    "cash_end": "cash_and_equivalents_closing",
}

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.evaluation.ground_truth_loader import DEFAULT_GROUND_TRUTH_DIR, load_ground_truth_index, lookup_ground_truth_metrics  # noqa: E402
from services.evaluation.normalizer import canonical_metric_keys, metric_coverage_rate, rows_to_canonical_metrics  # noqa: E402
from services.evaluation.scorer import score_metric_maps  # noqa: E402
from services.extraction.docling_runner import ensure_docling_venv, run_docling_subprocess  # noqa: E402


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _normalize_metric(value: Any) -> str:
    metric = str(value or "").strip().lower()
    return METRIC_ALIAS.get(metric, metric)


def _normalize_period(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    match = DATE_RE.search(text)
    if match:
        return str(match.group(1))
    return text


def _normalize_scope(value: Any) -> str:
    scope = str(value or "").strip().lower()
    aliases = {
        "consolidated_statement": "group",
        "consolidated": "group",
        "group": "group",
        "appendix_statement": "group",
        "parent": "parent",
        "any": "any",
    }
    return aliases.get(scope, scope or "unknown")


def _doc_id_from_path(pdf_path: Path) -> str:
    stem = pdf_path.stem
    match = DOC_ID_SUFFIX_RE.search(stem)
    if match:
        return str(match.group(1)).lower()
    return stem.lower()


def _iter_pdfs(pdf_dir: Path) -> list[Path]:
    return sorted(path for path in pdf_dir.rglob("*.pdf") if path.is_file())


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _text_completeness(text: str) -> dict[str, Any]:
    lines = [line for line in str(text or "").splitlines() if line.strip()]
    words = re.findall(r"[A-Za-z0-9_]+", str(text or ""))
    return {
        "text_chars": len(str(text or "")),
        "non_empty_lines": len(lines),
        "token_count_est": len(words),
    }


def _rows_completeness(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    metrics = {
        _normalize_metric(row.get("metric_base") or row.get("metric"))
        for row in rows
        if _normalize_metric(row.get("metric_base") or row.get("metric"))
    }
    populated_periods = sum(1 for row in rows if _normalize_period(row.get("statement_period_end") or row.get("period_end")))
    populated_values = sum(1 for row in rows if _safe_float(row.get("value")) is not None)
    return {
        "row_count": len(rows),
        "unique_metrics": len(metrics),
        "rows_with_period_end": populated_periods,
        "rows_with_numeric_value": populated_values,
    }


def _backend_json_completeness(payload: Mapping[str, Any]) -> dict[str, Any]:
    metrics = dict(payload.get("metrics") or {})
    populated_metrics = sum(1 for value in metrics.values() if _safe_float(value) is not None)
    narrative_keys = ("risk_summary", "guidance_summary", "material_changes")
    populated_narrative = sum(1 for key in narrative_keys if str(payload.get(key) or "").strip())
    return {
        "metric_field_count": len(metrics),
        "metric_field_populated": populated_metrics,
        "narrative_field_populated": populated_narrative,
    }


def _normalize_backend_json_metrics(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    metrics = dict(payload.get("metrics") or {})
    period_end = _normalize_period(payload.get("period_end"))
    period_type = str(payload.get("period_type") or "").strip()
    rows: list[dict[str, Any]] = []
    for metric_name, raw_value in metrics.items():
        value = _safe_float(raw_value)
        if value is None:
            continue
        rows.append(
            {
                "metric": _normalize_metric(metric_name),
                "period_end": period_end,
                "period_type": period_type,
                "scope": "group",
                "currency": "UNKNOWN",
                "value": value,
                "source_mode": "llm_json",
            }
        )
    return rows


def _normalize_canonical_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        metric = _normalize_metric(row.get("metric_base") or row.get("metric"))
        if not metric:
            continue
        value = _safe_float(row.get("value"))
        if value is None:
            value = _safe_float(row.get("raw_value"))
        if value is None:
            continue
        normalized.append(
            {
                "metric": metric,
                "period_end": _normalize_period(row.get("statement_period_end") or row.get("period_end")),
                "period_type": str(row.get("statement_period") or row.get("period_type") or "").strip(),
                "scope": _normalize_scope(row.get("statement_scope")),
                "currency": str(row.get("currency") or "UNKNOWN").strip().upper() or "UNKNOWN",
                "value": value,
                "source_mode": str(row.get("source_mode") or "").strip(),
            }
        )
    return normalized


def _normalize_ocr_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        value = _safe_float(row.get("value"))
        if value is None:
            continue
        normalized.append(
            {
                "metric": _normalize_metric(row.get("metric")),
                "period_end": _normalize_period(row.get("statement_period_end")),
                "period_type": str(row.get("statement_period") or "").strip(),
                "scope": _normalize_scope(row.get("statement_scope")),
                "currency": str(row.get("currency") or "UNKNOWN").strip().upper() or "UNKNOWN",
                "value": value,
                "source_mode": "ocr",
            }
        )
    return normalized


def _metric_key(row: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        _normalize_metric(row.get("metric")),
        _normalize_period(row.get("period_end")),
        _normalize_scope(row.get("scope")),
    )


def _tolerance_for_value(metric: str, gold_value: float, period_type: str) -> float:
    metric_name = str(metric or "").lower()
    period = str(period_type or "").lower()
    if "pct" in metric_name or "percent" in period:
        return 0.05
    if "ratio" in metric_name or "_to_" in metric_name:
        return 0.002
    return max(2.0, 0.0001 * abs(float(gold_value)))


def _ground_truth_status(metrics: Mapping[str, Any]) -> str:
    return "SUCCESS" if bool(metrics) else "DATA_MISSING"


def _detect_environment_state(docling_venv_path: str | Path | None) -> dict[str, Any]:
    current_virtual_env = str(os.environ.get("VIRTUAL_ENV") or "").strip() or None
    if current_virtual_env is None and getattr(sys, "base_prefix", sys.prefix) != sys.prefix:
        current_virtual_env = sys.prefix
    backend_requirements = FINANCIAL_ENGINE_ROOT / "backend" / "requirements.txt"
    backend_requirements_text = backend_requirements.read_text(encoding="utf-8") if backend_requirements.exists() else ""
    runtime_python_path = REPO_ROOT / "scripts" / "runtime_python.py"
    runtime_python_text = runtime_python_path.read_text(encoding="utf-8") if runtime_python_path.exists() else ""
    docling_state = asdict(
        ensure_docling_venv(
            venv_path=docling_venv_path,
            create_if_missing=False,
        )
    )
    return {
        "current_python": sys.executable,
        "current_virtual_env": current_virtual_env,
        "project_root": str(REPO_ROOT),
        "requirements_files": [
            str(REPO_ROOT / "requirements.txt"),
            str(FINANCIAL_ENGINE_ROOT / "backend" / "requirements.txt"),
            str(FINANCIAL_ENGINE_ROOT / "worker" / "requirements.txt"),
        ],
        "venvs_detected": {
            "financial_engine_dot_venv": str(FINANCIAL_ENGINE_ROOT / ".venv") if (FINANCIAL_ENGINE_ROOT / ".venv").exists() else None,
            "financial_engine_venv": str(FINANCIAL_ENGINE_ROOT / "venv") if (FINANCIAL_ENGINE_ROOT / "venv").exists() else None,
            "docling_gpu_venv": str(REPO_ROOT / ".venv-docling-gpu") if (REPO_ROOT / ".venv-docling-gpu").exists() else None,
            "docling_gpu_repair_venv": str(REPO_ROOT / ".venv-docling-gpu-repair") if (REPO_ROOT / ".venv-docling-gpu-repair").exists() else None,
            "docling_wrapper_target": docling_state["venv_path"],
        },
        "poetry_detected": any(
            candidate.exists()
            for candidate in (
                REPO_ROOT / "poetry.lock",
                REPO_ROOT / "pyproject.toml",
                FINANCIAL_ENGINE_ROOT / "poetry.lock",
                FINANCIAL_ENGINE_ROOT / "pyproject.toml",
            )
        ),
        "conda_detected": bool(os.environ.get("CONDA_PREFIX")),
        "docling_runtime": docling_state,
        "global_dependency_leakage": {
            "current_interpreter_outside_venv": current_virtual_env is None,
            "backend_requirements_include_docling": "docling" in backend_requirements_text.lower(),
            "runtime_python_falls_back_to_python3": "python3" in runtime_python_text,
        },
    }


@dataclass(frozen=True)
class MethodSpec:
    name: str
    category: str
    output_type: str
    benchmarkable: bool
    environment: str
    cpu_gpu_path: str
    dependencies: tuple[str, ...]
    document_types: tuple[str, ...]
    invocation_paths: tuple[str, ...]
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    runner: Callable[..., dict[str, Any]]


def _run_backend_pymupdf_text(
    pdf_path: Path,
    *,
    run_dir: Path,
    docling_venv_path: str | Path | None = None,
    docling_create_venv: bool = False,
    docling_cpu: bool = False,
    subprocess_timeout_sec: float | None = None,
) -> dict[str, Any]:
    module = _load_module(
        FINANCIAL_ENGINE_ROOT / "backend" / "app" / "services" / "text_extract.py",
        "benchmark_backend_text_extract",
    )
    text = module.extract_text_from_pdf(str(pdf_path))
    return {
        "status": "ok",
        "output_type": "text",
        "text": text,
        "text_stats": _text_completeness(text),
        "completeness": _text_completeness(text),
        "normalized_metrics": [],
        "artifacts": {},
    }


def _run_preprocess_pymupdf_text(
    pdf_path: Path,
    *,
    run_dir: Path,
    docling_venv_path: str | Path | None = None,
    docling_create_venv: bool = False,
    docling_cpu: bool = False,
    subprocess_timeout_sec: float | None = None,
) -> dict[str, Any]:
    module = _load_module(
        FINANCIAL_ENGINE_ROOT / "scripts" / "preprocess_investment_pdfs.py",
        "benchmark_preprocess_investment_pdfs",
    )
    text, page_count = module.extract_pdf_text_pymupdf(pdf_path)
    return {
        "status": "ok",
        "output_type": "text",
        "text": text,
        "text_stats": {
            **_text_completeness(text),
            "page_count": int(page_count),
        },
        "completeness": _text_completeness(text),
        "normalized_metrics": [],
        "artifacts": {},
    }


def _run_preprocess_pdftotext(
    pdf_path: Path,
    *,
    run_dir: Path,
    docling_venv_path: str | Path | None = None,
    docling_create_venv: bool = False,
    docling_cpu: bool = False,
    subprocess_timeout_sec: float | None = None,
) -> dict[str, Any]:
    module = _load_module(
        FINANCIAL_ENGINE_ROOT / "scripts" / "preprocess_investment_pdfs.py",
        "benchmark_preprocess_investment_pdfs_pdftotext",
    )
    if shutil.which("pdftotext") is None:
        raise RuntimeError("pdftotext_not_available")
    text = module.extract_pdf_text_pdftotext(pdf_path)
    return {
        "status": "ok",
        "output_type": "text",
        "text": text,
        "text_stats": _text_completeness(text),
        "completeness": _text_completeness(text),
        "normalized_metrics": [],
        "artifacts": {},
    }


def _run_backend_llm_json(
    pdf_path: Path,
    *,
    run_dir: Path,
    docling_venv_path: str | Path | None = None,
    docling_create_venv: bool = False,
    docling_cpu: bool = False,
    subprocess_timeout_sec: float | None = None,
) -> dict[str, Any]:
    text_extract_module = _load_module(
        FINANCIAL_ENGINE_ROOT / "backend" / "app" / "services" / "text_extract.py",
        "benchmark_backend_text_extract_llm",
    )
    extraction_module = _load_module(
        FINANCIAL_ENGINE_ROOT / "backend" / "app" / "services" / "extraction.py",
        "benchmark_backend_prompt_builder",
    )
    from app.services.llm import generate_json

    text = text_extract_module.extract_text_from_pdf(str(pdf_path))
    payload = generate_json(
        extraction_module.build_prompt(text),
        metadata={
            "task_type": "reasoning",
            "component": "benchmark_pdf_extraction",
            "operation": "backend_llm_json",
            "source_pdf": str(pdf_path),
        },
    )
    return {
        "status": "ok",
        "output_type": "json",
        "structured_json": payload,
        "text_stats": _text_completeness(text),
        "completeness": _backend_json_completeness(payload),
        "normalized_metrics": _normalize_backend_json_metrics(payload),
        "artifacts": {},
    }


def _extract_financial_metrics_command(pdf_path: Path, out_dir: Path, extractor: str, *, docling_cpu: bool) -> list[str]:
    canonical_json = out_dir / "canonical.json"
    canonical_csv = out_dir / "canonical.csv"
    primary_csv = out_dir / "primary.csv"
    primary_json = out_dir / "primary.json"
    all_variants_json = out_dir / "all_variants.json"
    all_datapoints_json = out_dir / "all_datapoints.json"
    coverage_enhanced_json = out_dir / "coverage_enhanced.json"
    coverage_backfill_audit_json = out_dir / "coverage_backfill_audit.json"
    context_csv = out_dir / "context.csv"
    context_json = out_dir / "context.json"
    rejected_json = out_dir / "rejected.json"
    blocks_json = out_dir / "blocks.json"
    high_csv = out_dir / "high.csv"
    high_json = out_dir / "high.json"
    diagnostics_json = out_dir / "document_diagnostics.json"
    financial_gates_json = out_dir / "financial_gates.json"
    coverage_gates_json = out_dir / "coverage_gates.json"
    coverage_enhanced_gates_json = out_dir / "coverage_enhanced_gates.json"

    command = [
        str(REPO_ROOT / "scripts" / "extract_financial_metrics.py"),
        "--pdf",
        str(pdf_path),
        "--out-csv",
        str(canonical_csv),
        "--out-json",
        str(canonical_json),
        "--out-primary-csv",
        str(primary_csv),
        "--out-primary-json",
        str(primary_json),
        "--out-all-variants-json",
        str(all_variants_json),
        "--out-all-datapoints-json",
        str(all_datapoints_json),
        "--out-coverage-enhanced-json",
        str(coverage_enhanced_json),
        "--out-coverage-backfill-audit-json",
        str(coverage_backfill_audit_json),
        "--out-context-csv",
        str(context_csv),
        "--out-context-json",
        str(context_json),
        "--out-rejected-json",
        str(rejected_json),
        "--out-blocks-json",
        str(blocks_json),
        "--out-document-diagnostics-json",
        str(diagnostics_json),
        "--out-high-csv",
        str(high_csv),
        "--out-high-json",
        str(high_json),
        "--financial-gates-report",
        str(financial_gates_json),
        "--coverage-gates-report",
        str(coverage_gates_json),
        "--coverage-enhanced-gates-report",
        str(coverage_enhanced_gates_json),
        "--no-sqlite",
        "--no-enforce-financial-gates",
        "--no-enforce-coverage-gates",
        "--no-quarantine-rules",
        "--extractor",
        extractor,
    ]
    if extractor == "docling" and docling_cpu:
        command.append("--cpu")
    return command


def _load_financial_metrics_artifacts(out_dir: Path) -> dict[str, Any]:
    canonical_rows = _read_json(out_dir / "canonical.json", [])
    diagnostics = _read_json(out_dir / "document_diagnostics.json", [])
    return {
        "canonical_rows": canonical_rows if isinstance(canonical_rows, list) else [],
        "document_diagnostics": diagnostics if isinstance(diagnostics, list) else [],
        "artifacts": {
            "canonical_json": str(out_dir / "canonical.json"),
            "canonical_csv": str(out_dir / "canonical.csv"),
            "document_diagnostics_json": str(out_dir / "document_diagnostics.json"),
        },
    }


def _run_financial_metrics_pdftotext(
    pdf_path: Path,
    *,
    run_dir: Path,
    docling_venv_path: str | Path | None = None,
    docling_create_venv: bool = False,
    docling_cpu: bool = False,
    subprocess_timeout_sec: float | None = None,
) -> dict[str, Any]:
    if shutil.which("pdftotext") is None:
        raise RuntimeError("pdftotext_not_available")
    out_dir = run_dir / "financial_metrics_pdftotext"
    out_dir.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, *_extract_financial_metrics_command(pdf_path, out_dir, "pdftotext", docling_cpu=docling_cpu)]

    result = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        timeout=subprocess_timeout_sec,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    loaded = _load_financial_metrics_artifacts(out_dir)
    return {
        "status": "ok" if result.returncode == 0 else "failed",
        "output_type": "canonical_rows",
        "canonical_rows": loaded["canonical_rows"],
        "document_diagnostics": loaded["document_diagnostics"],
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
        "completeness": _rows_completeness(loaded["canonical_rows"]),
        "normalized_metrics": _normalize_canonical_rows(loaded["canonical_rows"]),
        "artifacts": loaded["artifacts"],
    }


def _run_financial_metrics_docling(
    pdf_path: Path,
    *,
    run_dir: Path,
    docling_venv_path: str | Path | None = None,
    docling_create_venv: bool = False,
    docling_cpu: bool = False,
    subprocess_timeout_sec: float | None = None,
) -> dict[str, Any]:
    out_dir = run_dir / "financial_metrics_docling"
    out_dir.mkdir(parents=True, exist_ok=True)
    command = _extract_financial_metrics_command(pdf_path, out_dir, "docling", docling_cpu=docling_cpu)
    subprocess_result = run_docling_subprocess(
        command,
        cwd=REPO_ROOT,
        timeout_sec=subprocess_timeout_sec,
        venv_path=docling_venv_path,
        create_venv_if_missing=docling_create_venv,
    )
    loaded = _load_financial_metrics_artifacts(out_dir)
    status = "ok"
    if not subprocess_result.get("ok", False):
        status = "failed" if subprocess_result.get("returncode") is not None else "unavailable"
    return {
        "status": status,
        "output_type": "canonical_rows",
        "canonical_rows": loaded["canonical_rows"],
        "document_diagnostics": loaded["document_diagnostics"],
        "stdout": str(subprocess_result.get("stdout") or ""),
        "stderr": str(subprocess_result.get("stderr") or ""),
        "returncode": subprocess_result.get("returncode"),
        "docling_runtime": subprocess_result.get("state"),
        "completeness": _rows_completeness(loaded["canonical_rows"]),
        "normalized_metrics": _normalize_canonical_rows(loaded["canonical_rows"]),
        "artifacts": loaded["artifacts"],
    }


def _run_ocr_last_resort(
    pdf_path: Path,
    *,
    run_dir: Path,
    docling_venv_path: str | Path | None = None,
    docling_create_venv: bool = False,
    docling_cpu: bool = False,
    subprocess_timeout_sec: float | None = None,
) -> dict[str, Any]:
    ocr_module = _load_module(
        REPO_ROOT / "scripts" / "ocr_last_resort.py",
        "benchmark_ocr_last_resort",
    )
    extract_module = _load_module(
        REPO_ROOT / "scripts" / "extract_financial_metrics.py",
        "benchmark_extract_financial_metrics_for_ocr",
    )
    prepared_pages = extract_module._prepare_bbox_pages(pdf_path, timeout_sec=180.0)
    pages = sorted(int(page) for page in prepared_pages.keys())
    rows, stats = ocr_module.collect_ocr_candidates_for_pdf(
        pdf_path,
        pages=pages,
        prepared_pages=prepared_pages,
        source_kind="benchmark",
    )
    return {
        "status": "ok",
        "output_type": "ocr_candidates",
        "ocr_rows": rows,
        "ocr_stats": stats,
        "completeness": {
            **stats,
            "row_count": len(rows),
        },
        "normalized_metrics": _normalize_ocr_rows(rows),
        "artifacts": {},
    }


METHOD_SPECS: tuple[MethodSpec, ...] = (
    MethodSpec(
        name="backend_pymupdf_text",
        category="text_extractor",
        output_type="text",
        benchmarkable=True,
        environment="financial-engine_v2 main runtime (.venv/current interpreter)",
        cpu_gpu_path="CPU",
        dependencies=("pymupdf",),
        document_types=("ASX announcement PDFs", "periodic reports"),
        invocation_paths=(
            "financial-engine_v2/backend/app/services/text_extract.py:extract_text_from_pdf",
            "financial-engine_v2/backend/app/services/pipeline.py:process_document",
            "financial-engine_v2/backend/app/worker_tasks.py:process_document",
            "financial-engine_v2/worker/app/tasks.py:process_document",
        ),
        strengths=("shared production path", "direct page text extraction"),
        weaknesses=("no OCR fallback", "text-only output"),
        runner=_run_backend_pymupdf_text,
    ),
    MethodSpec(
        name="preprocess_pymupdf_text",
        category="text_extractor",
        output_type="text",
        benchmarkable=True,
        environment="financial-engine_v2 script runtime (.venv/current interpreter)",
        cpu_gpu_path="CPU",
        dependencies=("pymupdf",),
        document_types=("local investment PDF corpora",),
        invocation_paths=(
            "financial-engine_v2/scripts/preprocess_investment_pdfs.py:extract_pdf_text_pymupdf",
            "financial-engine_v2/scripts/preprocess_investment_pdfs.py:run",
        ),
        strengths=("lightweight", "deterministic"),
        weaknesses=("text-only output", "not metric-specific"),
        runner=_run_preprocess_pymupdf_text,
    ),
    MethodSpec(
        name="preprocess_pdftotext_text",
        category="text_extractor",
        output_type="text",
        benchmarkable=True,
        environment="financial-engine_v2 script runtime + system pdftotext binary",
        cpu_gpu_path="CPU",
        dependencies=("pdftotext",),
        document_types=("local investment PDF corpora",),
        invocation_paths=(
            "financial-engine_v2/scripts/preprocess_investment_pdfs.py:extract_pdf_text_pdftotext",
            "financial-engine_v2/scripts/preprocess_investment_pdfs.py:compare_extraction_accuracy_for_pdf",
        ),
        strengths=("external parser comparison path", "existing token-overlap audit"),
        weaknesses=("text-only output", "depends on poppler-utils"),
        runner=_run_preprocess_pdftotext,
    ),
    MethodSpec(
        name="backend_llm_json",
        category="llm_extractor",
        output_type="json",
        benchmarkable=True,
        environment="financial-engine_v2 backend runtime + configured LLM endpoint",
        cpu_gpu_path="llm_cpu/llm_gpu routing",
        dependencies=("pymupdf", "httpx", "configured LLM runtime"),
        document_types=("ASX periodic financial PDFs",),
        invocation_paths=(
            "financial-engine_v2/backend/app/services/extraction.py:build_prompt",
            "financial-engine_v2/backend/app/services/pipeline.py:process_document",
            "financial-engine_v2/backend/app/services/llm.py:generate_json",
        ),
        strengths=("production structured JSON output", "direct downstream schema match"),
        weaknesses=("no checked-in ground-truth wiring", "depends on live LLM runtime"),
        runner=_run_backend_llm_json,
    ),
    MethodSpec(
        name="financial_metrics_pdftotext",
        category="financial_metrics_extractor",
        output_type="canonical_rows",
        benchmarkable=True,
        environment="repo root runtime + system pdftotext binary",
        cpu_gpu_path="CPU",
        dependencies=("pdftotext",),
        document_types=("annual reports", "half-year reports", "quarterly appendices"),
        invocation_paths=(
            "scripts/extract_financial_metrics.py --extractor pdftotext",
            "scripts/run_extraction_quality_cycle.sh",
            "scripts/compare_docling_accuracy.py",
        ),
        strengths=("canonical row normalization", "existing coverage/audit tooling"),
        weaknesses=("depends on poppler-utils", "no OCR integration in main flow"),
        runner=_run_financial_metrics_pdftotext,
    ),
    MethodSpec(
        name="financial_metrics_docling",
        category="financial_metrics_extractor",
        output_type="canonical_rows",
        benchmarkable=True,
        environment="dedicated Docling venv via services/extraction/docling_runner.py",
        cpu_gpu_path="GPU-capable with CPU fallback",
        dependencies=("docling", "torch/runtime-specific accelerator stack"),
        document_types=("annual reports", "half-year reports", "quarterly appendices"),
        invocation_paths=(
            "scripts/extract_financial_metrics.py --extractor docling",
            "scripts/docling_export_tables.py",
            "scripts/compare_docling_accuracy.py",
            "services/extraction/docling_runner.py",
        ),
        strengths=("table-structure-aware extraction", "existing fallback diagnostics"),
        weaknesses=("heavy dependency stack", "requires isolated venv"),
        runner=_run_financial_metrics_docling,
    ),
    MethodSpec(
        name="ocr_last_resort",
        category="ocr_candidate_extractor",
        output_type="ocr_candidates",
        benchmarkable=True,
        environment="repo root runtime + system tesseract/pdftoppm binaries",
        cpu_gpu_path="CPU",
        dependencies=("tesseract", "pdftoppm"),
        document_types=("scanned or near-empty text-layer PDFs",),
        invocation_paths=(
            "scripts/ocr_last_resort.py:collect_ocr_candidates_for_pdf",
            "scripts/ocr_last_resort.py:extract_ocr_candidates_for_page",
        ),
        strengths=("fail-closed OCR helper", "explicit dependency checks"),
        weaknesses=("not wired into primary financial extraction flow", "metric labels usually blank"),
        runner=_run_ocr_last_resort,
    ),
)


def _registry_payload() -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for spec in METHOD_SPECS:
        payload.append(
            {
                "name": spec.name,
                "category": spec.category,
                "output_type": spec.output_type,
                "benchmarkable": spec.benchmarkable,
                "environment": spec.environment,
                "cpu_gpu_path": spec.cpu_gpu_path,
                "dependencies": list(spec.dependencies),
                "document_types": list(spec.document_types),
                "invocation_paths": list(spec.invocation_paths),
                "strengths": list(spec.strengths),
                "weaknesses": list(spec.weaknesses),
            }
        )
    return payload


def _method_map() -> dict[str, MethodSpec]:
    return {spec.name: spec for spec in METHOD_SPECS}


def _run_method(
    spec: MethodSpec,
    pdf_path: Path,
    *,
    run_root: Path,
    ground_truth_metrics: Mapping[str, Any],
    docling_venv_path: str | Path | None,
    docling_create_venv: bool,
    docling_cpu: bool,
    subprocess_timeout_sec: float | None,
) -> dict[str, Any]:
    method_dir = run_root / spec.name
    method_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    try:
        payload = spec.runner(
            pdf_path,
            run_dir=method_dir,
            docling_venv_path=docling_venv_path,
            docling_create_venv=docling_create_venv,
            docling_cpu=docling_cpu,
            subprocess_timeout_sec=subprocess_timeout_sec,
        )
    except subprocess.TimeoutExpired as exc:
        payload = {
            "status": "failed",
            "output_type": spec.output_type,
            "error": f"timeout_after_{exc.timeout}_seconds",
            "normalized_metrics": [],
            "completeness": {},
            "artifacts": {},
        }
    except Exception as exc:
        payload = {
            "status": "failed",
            "output_type": spec.output_type,
            "error": str(exc),
            "normalized_metrics": [],
            "completeness": {},
            "artifacts": {},
        }
    runtime_seconds = round(time.perf_counter() - started, 6)
    normalized_metrics = list(payload.get("normalized_metrics") or [])
    canonical_metrics = rows_to_canonical_metrics(normalized_metrics)
    score = score_metric_maps(canonical_metrics, ground_truth_metrics, tolerance_pct=0.02)
    verification_ratio = _safe_float(payload.get("verification_ratio"))
    if verification_ratio is None:
        verification_ratio = 1.0
    return {
        "status": str(payload.get("status") or "failed"),
        "runtime_seconds": runtime_seconds,
        "output_type": spec.output_type,
        "completeness": dict(payload.get("completeness") or {}),
        "score": score,
        "artifacts": dict(payload.get("artifacts") or {}),
        "normalized_metrics": normalized_metrics,
        "canonical_metrics": canonical_metrics,
        "metric_coverage_rate": round(metric_coverage_rate(canonical_metrics), 6),
        "verification_ratio": round(float(verification_ratio), 6),
        "text_stats": dict(payload.get("text_stats") or {}),
        "document_diagnostics": list(payload.get("document_diagnostics") or []),
        "structured_json": payload.get("structured_json"),
        "ocr_stats": dict(payload.get("ocr_stats") or {}),
        "stderr": str(payload.get("stderr") or ""),
        "stdout": str(payload.get("stdout") or ""),
        "error": str(payload.get("error") or ""),
        "returncode": payload.get("returncode"),
        "docling_runtime": payload.get("docling_runtime"),
    }


def _summarize_documents(documents: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    per_method: dict[str, dict[str, Any]] = {}
    for document in documents:
        methods = dict(document.get("methods") or {})
        for method_name, payload in methods.items():
            entry = per_method.setdefault(
                method_name,
                {
                    "documents": 0,
                    "failed": 0,
                    "runtime_seconds_total": 0.0,
                    "scored_documents": 0,
                    "accuracy_total": 0.0,
                    "completeness_total": 0.0,
                    "exact_match_rate_total": 0.0,
                    "tolerance_match_rate_total": 0.0,
                    "metric_coverage_rate_total": 0.0,
                },
            )
            entry["documents"] += 1
            if payload.get("status") not in {"ok", "success"}:
                entry["failed"] += 1
            entry["runtime_seconds_total"] += float(payload.get("runtime_seconds") or 0.0)
            entry["metric_coverage_rate_total"] += float(payload.get("metric_coverage_rate") or 0.0)
            score = dict(payload.get("score") or {})
            if str(score.get("status") or "") == "SUCCESS":
                aggregate = dict(score.get("aggregate") or {})
                entry["scored_documents"] += 1
                entry["accuracy_total"] += float(aggregate.get("accuracy") or 0.0)
                entry["completeness_total"] += float(aggregate.get("completeness") or 0.0)
                entry["exact_match_rate_total"] += float(aggregate.get("exact_match_rate") or 0.0)
                entry["tolerance_match_rate_total"] += float(aggregate.get("tolerance_match_rate") or 0.0)

    for payload in per_method.values():
        documents_count = max(1, int(payload["documents"]))
        scored_documents = int(payload["scored_documents"])
        payload["failure_rate"] = round(float(payload["failed"]) / float(documents_count), 6)
        payload["runtime_seconds_total"] = round(float(payload["runtime_seconds_total"]), 6)
        payload["runtime_seconds_average"] = round(float(payload["runtime_seconds_total"]) / float(documents_count), 6)
        payload["metric_coverage_rate_average"] = round(float(payload["metric_coverage_rate_total"]) / float(documents_count), 6)
        if scored_documents > 0:
            payload["accuracy_average"] = round(float(payload["accuracy_total"]) / float(scored_documents), 6)
            payload["completeness_average"] = round(float(payload["completeness_total"]) / float(scored_documents), 6)
            payload["exact_match_rate_average"] = round(float(payload["exact_match_rate_total"]) / float(scored_documents), 6)
            payload["tolerance_match_rate_average"] = round(float(payload["tolerance_match_rate_total"]) / float(scored_documents), 6)
        else:
            payload["accuracy_average"] = 0.0
            payload["completeness_average"] = 0.0
            payload["exact_match_rate_average"] = 0.0
            payload["tolerance_match_rate_average"] = 0.0
    return per_method


def _build_method_comparison(per_method: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    methods: list[dict[str, Any]] = []
    for method_name, payload in per_method.items():
        scored_documents = int(payload.get("scored_documents") or 0)
        completeness_for_ranking = float(payload.get("completeness_average") or 0.0)
        if scored_documents == 0:
            completeness_for_ranking = float(payload.get("metric_coverage_rate_average") or 0.0)
        methods.append(
            {
                "name": method_name,
                "accuracy": round(float(payload.get("accuracy_average") or 0.0), 6),
                "completeness": round(completeness_for_ranking, 6),
                "latency": round(float(payload.get("runtime_seconds_average") or 0.0), 6),
            }
        )

    ranked = sorted(
        methods,
        key=lambda item: (
            -float(item.get("accuracy") or 0.0),
            -float(item.get("completeness") or 0.0),
            float(item.get("latency") or 0.0),
            str(item.get("name") or ""),
        ),
    )
    ranking = [str(item["name"]) for item in ranked] if len(ranked) >= 2 else []
    return {
        "methods": ranked,
        "ranking": ranking,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit and benchmark current PDF extraction methods.")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--pdf", action="append", help="PDF file to benchmark. May be repeated.")
    input_group.add_argument("--pdf-dir", help="Directory of PDFs to benchmark.")
    parser.add_argument(
        "--methods",
        default="all",
        help="Comma-separated method names, or 'all'.",
    )
    parser.add_argument(
        "--out-json",
        default=str(DEFAULT_OUTPUT),
        help="Structured benchmark report output path.",
    )
    parser.add_argument(
        "--run-root",
        default=str(DEFAULT_RUN_ROOT),
        help="Directory for per-method benchmark artifacts.",
    )
    parser.add_argument(
        "--ground-truth",
        default=str(DEFAULT_GROUND_TRUTH),
        help="Ground-truth JSON file or directory. Defaults to data/ground_truth.",
    )
    parser.add_argument(
        "--gold-dir",
        default="",
        help="Legacy alias for --ground-truth. When set, it overrides --ground-truth.",
    )
    parser.add_argument(
        "--docling-venv",
        default=str(REPO_ROOT / ".venv_docling"),
        help="Docling venv path. Defaults to .venv_docling at repo root.",
    )
    parser.add_argument(
        "--create-docling-venv",
        action="store_true",
        help="Create the Docling venv if missing.",
    )
    parser.add_argument(
        "--docling-cpu",
        action="store_true",
        help="Force CPU mode for Docling extraction.",
    )
    parser.add_argument(
        "--subprocess-timeout-sec",
        type=float,
        default=0.0,
        help="Optional timeout for subprocess-backed extraction methods.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    selected_methods = _method_map()
    if str(args.methods).strip().lower() != "all":
        requested = {name.strip() for name in str(args.methods).split(",") if name.strip()}
        selected_methods = {name: spec for name, spec in selected_methods.items() if name in requested}
        if not selected_methods:
            raise SystemExit("No valid benchmark methods selected.")

    if args.pdf:
        pdfs = [Path(value).expanduser().resolve() for value in args.pdf]
    else:
        pdfs = _iter_pdfs(Path(args.pdf_dir).expanduser().resolve())
    if not pdfs:
        raise SystemExit("No PDF files found for benchmarking.")
    for pdf in pdfs:
        if not pdf.exists() or not pdf.is_file():
            raise SystemExit(f"Invalid PDF path: {pdf}")

    ground_truth_path = str(args.gold_dir).strip() or str(args.ground_truth).strip() or str(DEFAULT_GROUND_TRUTH_DIR)
    ground_truth_index = load_ground_truth_index(ground_truth_path)
    ground_truth_status = "SUCCESS" if ground_truth_index else "DATA_MISSING"

    out_json = Path(args.out_json).expanduser().resolve()
    run_root = Path(args.run_root).expanduser().resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    run_root.mkdir(parents=True, exist_ok=True)

    documents: list[dict[str, Any]] = []
    for pdf in pdfs:
        doc_id = _doc_id_from_path(pdf)
        ground_truth_metrics = lookup_ground_truth_metrics(pdf, ground_truth_index)
        doc_run_root = run_root / doc_id
        doc_run_root.mkdir(parents=True, exist_ok=True)
        method_results: dict[str, Any] = {}
        for name, spec in selected_methods.items():
            method_results[name] = _run_method(
                spec,
                pdf,
                run_root=doc_run_root,
                ground_truth_metrics=ground_truth_metrics,
                docling_venv_path=args.docling_venv,
                docling_create_venv=bool(args.create_docling_venv),
                docling_cpu=bool(args.docling_cpu),
                subprocess_timeout_sec=float(args.subprocess_timeout_sec or 0.0) or None,
            )
        documents.append(
            {
                "pdf": str(pdf),
                "doc_id": doc_id,
                "ground_truth_metrics": ground_truth_metrics,
                "ground_truth_metric_count": len(ground_truth_metrics),
                "ground_truth_status": _ground_truth_status(ground_truth_metrics),
                "methods": method_results,
            }
        )

    summary_per_method = _summarize_documents(documents)
    method_comparison = _build_method_comparison(summary_per_method)

    report = {
        "status": "SUCCESS",
        "generated_at_utc": utc_now(),
        "ground_truth_status": ground_truth_status,
        "inputs": {
            "pdf_count": len(pdfs),
            "pdfs": [str(pdf) for pdf in pdfs],
            "methods": sorted(selected_methods.keys()),
            "ground_truth": ground_truth_path,
            "gold_dir": str(args.gold_dir or ""),
            "canonical_metric_keys": list(canonical_metric_keys()),
        },
        "environment": _detect_environment_state(args.docling_venv),
        "extraction_registry": _registry_payload(),
        "documents": documents,
        "method_comparison": method_comparison,
        "summary": {
            "per_method": summary_per_method,
        },
    }
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": "SUCCESS", "out_json": str(out_json), "documents": len(documents)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
