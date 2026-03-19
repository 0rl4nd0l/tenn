#!/usr/bin/env python3
"""
Run financial metrics extraction with both pdftotext and Docling on the same companies,
then compare outputs for accuracy analysis.

Usage:
  python scripts/compare_docling_accuracy.py --max-tickers 5
  python scripts/compare_docling_accuracy.py --tickers 10X 29M A2M
  python scripts/compare_docling_accuracy.py --max-tickers 3          # GPU default
  python scripts/compare_docling_accuracy.py --max-tickers 3 --cpu    # CPU fallback
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
from datetime import date
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.runtime_python import print_runtime_info, resolve_python

DOCS = ROOT / "financial-engine_v2" / "data" / "asx" / "docs"
OUT_DIR = ROOT / "reports" / "docling_accuracy_comparison"
FINANCIAL_SOURCE_KINDS = {"canonical_report", "appendix_report"}
NON_FINANCIAL_SKIP_REASON = "non_financial_document"
EXPENSE_SIGN_METRICS = {
    "depreciation_and_amortisation",
    "finance_costs",
    "income_tax_expense",
    "operating_expenses",
}
_EXTRACT_MODULE = None


def run_extract(
    pdf_path: Path,
    out_prefix: Path,
    extractor: str,
    timeout_sec: int = 600,
    cpu: bool = False,
    enforce_gates: bool = False,
    allow_empty: bool = False,
    python_executable: Optional[str] = None,
) -> dict:
    """Run extraction with given backend. Returns {ok, canonical_rows, path}."""
    if python_executable is None:
        python_executable = resolve_python()
    out_prefix.mkdir(parents=True, exist_ok=True)
    json_path = out_prefix / "canonical.json"
    csv_path = out_prefix / "canonical.csv"
    diagnostics_path = out_prefix / "document_diagnostics.json"
    cmd = [
        python_executable,
        str(ROOT / "scripts" / "extract_financial_metrics.py"),
        "--pdf", str(pdf_path),
        "--out-json", str(json_path),
        "--out-csv", str(csv_path),
        "--out-document-diagnostics-json", str(diagnostics_path),
        "--no-sqlite",
        "--no-quarantine-rules",
        "--extractor", extractor,
    ]
    if not enforce_gates:
        cmd.extend(["--no-enforce-financial-gates", "--no-enforce-coverage-gates"])
    if cpu:
        cmd.append("--cpu")
    try:
        import subprocess
        r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout_sec)
        ok = r.returncode == 0
        rows = []
        document_diagnostics = []
        if json_path.exists():
            with open(json_path) as f:
                rows = json.load(f)
        if diagnostics_path.exists():
            with open(diagnostics_path) as f:
                document_diagnostics = json.load(f)
        failure_type = _failure_type(r.returncode, rows)
        if not ok:
            return {
                "ok": False,
                "canonical_rows": [],
                "document_diagnostics": document_diagnostics,
                "path": str(json_path),
                "returncode": r.returncode,
                "stderr": (r.stderr or "").strip(),
                "error": str(_extract_failure_error(
                    {
                        "stderr": (r.stderr or "").strip(),
                        "returncode": r.returncode,
                    }
                )),
                "failure_type": failure_type,
            }
        if not rows and not allow_empty:
            return {
                "ok": True,
                "canonical_rows": [],
                "document_diagnostics": document_diagnostics,
                "path": str(json_path),
                "returncode": r.returncode,
                "stderr": (r.stderr or "").strip(),
                "failure_type": failure_type,
            }
        return {
            "ok": ok,
            "canonical_rows": rows,
            "document_diagnostics": document_diagnostics,
            "path": str(json_path),
            "returncode": r.returncode,
            "stderr": (r.stderr or "").strip(),
            "failure_type": failure_type,
        }
    except Exception as e:
        return {
            "ok": False,
            "canonical_rows": [],
            "document_diagnostics": [],
            "path": "",
            "failure_type": "hard",
            "error": str(e),
        }


DEFAULT_EXTRACT_RUNNER = run_extract


def _empty_extraction_result() -> Dict[str, Any]:
    return {
        "ok": True,
        "canonical_rows": [],
        "document_diagnostics": [],
        "path": "",
    }


def _append_extraction_result(target: Dict[str, Any], result: Dict[str, Any]) -> None:
    target["canonical_rows"].extend(list(result.get("canonical_rows", []) or []))
    target["document_diagnostics"].extend(list(result.get("document_diagnostics", []) or []))


def _extract_failure_error(result: Dict[str, Any]) -> str:
    return str(result.get("stderr", "")).strip() or str(result.get("error", "")).strip()


def _build_failed_document(
    ticker: str,
    pdf: Path,
    pdf_index: int,
    total_pdfs: int,
    extractor: str,
    result: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "ticker": ticker,
        "document": str(pdf),
        "pdf_index": pdf_index,
        "total_pdfs": total_pdfs,
        "extractor": extractor,
        "returncode": result.get("returncode"),
        "error": _extract_failure_error(result),
    }


def _default_max_workers() -> int:
    return max(1, min(8, os.cpu_count() or 1))


def _log_failed_document(failure: Dict[str, Any]) -> None:
    error = failure.get("error")
    rc_suffix = f" rc={failure['returncode']}" if failure.get("returncode") is not None else ""
    error_suffix = f": {str(error)[:200]}" if error else ""
    print(
        f"      FAILED extractor={failure.get('extractor')} document={Path(str(failure.get('document', ''))).name}"
        f"{rc_suffix}{error_suffix}",
        flush=True,
    )


def _process_benchmark_document(
    ticker: str,
    benchmark_document: Dict[str, Any],
    pdf_index: int,
    total_pdfs: int,
    out_base: Path,
    timeout_sec: int = 600,
    cpu: bool = False,
    enforce_gates: bool = False,
    allow_empty: bool = False,
    python_executable: Optional[str] = None,
    extract_runner: Callable[..., Dict[str, Any]] = DEFAULT_EXTRACT_RUNNER,
) -> Dict[str, Any]:
    original_pdf = Path(str(benchmark_document.get("document", "")).strip())
    result: Dict[str, Any] = {
        "benchmark_document": dict(benchmark_document),
        "document": str(original_pdf),
        "pdf_index": pdf_index,
        "total_pdfs": total_pdfs,
        "pdftotext_result": _empty_extraction_result(),
        "docling_result": _empty_extraction_result(),
        "setup_failure": None,
    }
    if not original_pdf.exists():
        result["setup_failure"] = _build_failed_document(
            ticker,
            original_pdf,
            pdf_index,
            total_pdfs,
            "benchmark_setup",
            {
                "returncode": None,
                "error": f"missing_pdf: {original_pdf}",
            },
        )
        return result

    try:
        result["pdftotext_result"] = extract_runner(
            original_pdf,
            out_base / ticker / "pdftotext" / f"{pdf_index:04d}",
            "pdftotext",
            timeout_sec=timeout_sec,
            enforce_gates=enforce_gates,
            allow_empty=allow_empty,
            python_executable=python_executable,
        )
        result["docling_result"] = extract_runner(
            original_pdf,
            out_base / ticker / "docling" / f"{pdf_index:04d}",
            "docling",
            timeout_sec=timeout_sec,
            cpu=cpu,
            enforce_gates=enforce_gates,
            allow_empty=allow_empty,
            python_executable=python_executable,
        )
    except Exception as e:
        result["setup_failure"] = _build_failed_document(
            ticker,
            original_pdf,
            pdf_index,
            total_pdfs,
            "benchmark_setup",
            {
                "returncode": None,
                "error": str(e),
            },
        )
    return result


def _process_benchmark_document_worker(task: Dict[str, Any]) -> Dict[str, Any]:
    return _process_benchmark_document(
        str(task["ticker"]),
        dict(task["benchmark_document"]),
        int(task["pdf_index"]),
        int(task["total_pdfs"]),
        Path(str(task["out_base"])),
        timeout_sec=int(task["timeout_sec"]),
        cpu=bool(task["cpu"]),
        enforce_gates=bool(task["enforce_gates"]),
        allow_empty=bool(task["allow_empty"]),
        python_executable=str(task["python_executable"]) if task.get("python_executable") else None,
        extract_runner=DEFAULT_EXTRACT_RUNNER,
    )


def benchmark_ticker_documents(
    ticker: str,
    benchmark_documents: List[Dict[str, Any]],
    out_base: Path,
    timeout_sec: int = 600,
    cpu: bool = False,
    enforce_gates: bool = False,
    allow_empty: bool = False,
    python_executable: Optional[str] = None,
    extract_runner: Optional[Callable[..., Dict[str, Any]]] = None,
    max_workers: Optional[int] = None,
) -> Dict[str, Any]:
    if extract_runner is None:
        extract_runner = run_extract
    if max_workers is None:
        max_workers = _default_max_workers()
    else:
        max_workers = max(1, int(max_workers))
    pdftotext_result = _empty_extraction_result()
    docling_result = _empty_extraction_result()
    successful_documents: List[Dict[str, Any]] = []
    failed_documents: List[Dict[str, Any]] = []
    total_pdfs = len(benchmark_documents)

    tasks: List[Dict[str, Any]] = []
    for pdf_index, benchmark_document in enumerate(benchmark_documents, start=1):
        original_pdf = Path(str(benchmark_document.get("document", "")).strip())
        print(
            f"    ticker={ticker} pdf_index={pdf_index} total_pdfs={total_pdfs} document={original_pdf.name}",
            flush=True,
        )
        tasks.append(
            {
                "ticker": ticker,
                "benchmark_document": dict(benchmark_document),
                "pdf_index": pdf_index,
                "total_pdfs": total_pdfs,
                "out_base": str(out_base),
                "timeout_sec": timeout_sec,
                "cpu": cpu,
                "enforce_gates": enforce_gates,
                "allow_empty": allow_empty,
                "python_executable": python_executable,
            }
        )

    can_parallelize = max_workers > 1 and extract_runner is DEFAULT_EXTRACT_RUNNER
    if can_parallelize:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            task_results = list(executor.map(_process_benchmark_document_worker, tasks))
    else:
        task_results = [
            _process_benchmark_document(
                ticker,
                dict(task["benchmark_document"]),
                int(task["pdf_index"]),
                int(task["total_pdfs"]),
                Path(str(task["out_base"])),
                timeout_sec=int(task["timeout_sec"]),
                cpu=bool(task["cpu"]),
                enforce_gates=bool(task["enforce_gates"]),
                allow_empty=bool(task["allow_empty"]),
                python_executable=str(task["python_executable"]) if task.get("python_executable") else None,
                extract_runner=extract_runner,
            )
            for task in tasks
        ]

    for task_result in task_results:
        original_pdf = Path(str(task_result.get("document", "")).strip())
        pdf_index = int(task_result.get("pdf_index", 0) or 0)
        setup_failure = task_result.get("setup_failure")
        if isinstance(setup_failure, dict):
            failed_documents.append(setup_failure)
            _log_failed_document(setup_failure)
            continue

        r_pdf = dict(task_result.get("pdftotext_result", {}) or {})
        r_docling = dict(task_result.get("docling_result", {}) or {})

        pdf_failed = not bool(r_pdf.get("ok"))
        docling_failed = not bool(r_docling.get("ok"))
        if pdf_failed:
            failure = _build_failed_document(ticker, original_pdf, pdf_index, total_pdfs, "pdftotext", r_pdf)
            failed_documents.append(failure)
            _log_failed_document(failure)
        if docling_failed:
            failure = _build_failed_document(ticker, original_pdf, pdf_index, total_pdfs, "docling", r_docling)
            failed_documents.append(failure)
            _log_failed_document(failure)
        if pdf_failed or docling_failed:
            continue

        _append_extraction_result(pdftotext_result, r_pdf)
        _append_extraction_result(docling_result, r_docling)
        successful_documents.append(dict(task_result.get("benchmark_document", {}) or {}))

    return {
        "pdftotext_result": pdftotext_result,
        "docling_result": docling_result,
        "successful_documents": successful_documents,
        "failed_documents": failed_documents,
    }


def _row_key(r: dict) -> tuple:
    """(metric, period_end) for deduping and comparison."""
    return (str(r.get("metric", "")), str(r.get("statement_period_end", "")))


def normalize_metric_name(name: str) -> str:
    if not name:
        return ""

    return (
        name.lower()
        .replace("total ", "")
        .replace("net ", "")
        .replace(" attributable", "")
        .strip()
    )


def _parse_period_end(period_end: object) -> Optional[date]:
    text = str(period_end or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def periods_match(p1: object, p2: object) -> bool:
    d1 = _parse_period_end(p1)
    d2 = _parse_period_end(p2)
    if d1 is None or d2 is None:
        return False

    return d1 == d2 or abs((d1 - d2).days) <= 7


def _failure_type(returncode: object, output: object) -> str:
    rc = _safe_int(returncode)
    return (
        "hard" if rc != 0 else
        "empty_output" if not output else
        "partial"
    )


def parse_accounting_number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        return None
    v = " ".join(str(value).split()).strip()
    if not v:
        return None
    neg_paren = v.startswith("(") and v.endswith(")")
    if neg_paren:
        v = v[1:-1].strip()
    v = v.replace(",", "")
    try:
        parsed = float(v)
    except ValueError:
        return None
    if neg_paren:
        return -abs(parsed)
    return parsed


def normalize_metric_value(metric_name: str, value):
    parsed = parse_accounting_number(value)
    if parsed is None:
        return value
    metric = (metric_name or "").strip().lower()
    if metric in EXPENSE_SIGN_METRICS:
        return -abs(parsed)
    return parsed


def _row_value(r: dict):
    metric = str(r.get("metric", ""))
    return normalize_metric_value(metric, r.get("value"))


def load_rows(path: Path) -> list:
    if not path or not Path(path).exists():
        return []
    with open(path) as f:
        return json.load(f)


def _load_extract_module():
    global _EXTRACT_MODULE
    if _EXTRACT_MODULE is None:
        extract_path = ROOT / "scripts" / "extract_financial_metrics.py"
        scripts_dir = str(extract_path.parent)
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        spec = importlib.util.spec_from_file_location("extract_financial_metrics_for_compare", str(extract_path))
        if spec is None or spec.loader is None:
            raise RuntimeError(f"failed to load module: {extract_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _EXTRACT_MODULE = module
    return _EXTRACT_MODULE


def classify_document_source_kind(pdf: Path) -> str:
    module = _load_extract_module()
    return str(module.classify_pdf_source_kind(pdf))


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _group_rows_by_document(rows: List[dict]) -> Dict[str, List[dict]]:
    grouped: Dict[str, List[dict]] = {}
    for row in rows:
        document = _document_key(str(row.get("file") or row.get("source_file") or "").strip())
        if not document:
            continue
        grouped.setdefault(document, []).append(row)
    return grouped


def _document_key(document: str) -> str:
    return str(Path(document))


def _group_diagnostics_by_document(document_diagnostics: List[dict]) -> Dict[str, dict]:
    grouped: Dict[str, dict] = {}
    for entry in document_diagnostics:
        document = _document_key(str(entry.get("document", "")).strip())
        if not document:
            continue
        grouped[document] = dict(entry)
    return grouped


def _coverage_metric_keys(rows: List[dict]) -> int:
    return len({_row_key(row) for row in rows})


def _matched_comparison_keys(by_pdf: Dict[tuple, List[object]], by_docling: Dict[tuple, List[object]]) -> List[tuple]:
    matched: List[tuple] = []
    used_pdf: Set[tuple] = set()

    for docling_key in by_docling:
        normalized_docling_metric = normalize_metric_name(str(docling_key[0]))
        candidates = [
            pdf_key
            for pdf_key in by_pdf
            if pdf_key not in used_pdf
            and normalize_metric_name(str(pdf_key[0])) == normalized_docling_metric
            and periods_match(pdf_key[1], docling_key[1])
        ]
        if not candidates:
            continue

        docling_period = _parse_period_end(docling_key[1])

        def _candidate_rank(pdf_key: tuple) -> tuple:
            pdf_period = _parse_period_end(pdf_key[1])
            delta = abs((pdf_period - docling_period).days) if pdf_period and docling_period else 999999
            exact_period = 0 if str(pdf_key[1]) == str(docling_key[1]) else 1
            exact_metric = 0 if str(pdf_key[0]) == str(docling_key[0]) else 1
            return (delta, exact_period, exact_metric, str(pdf_key[0]), str(pdf_key[1]))

        matched_pdf_key = min(candidates, key=_candidate_rank)
        used_pdf.add(matched_pdf_key)
        matched.append((matched_pdf_key, docling_key))

    return matched


def _document_ticker(document: str, default: str = "") -> str:
    if default:
        return default
    path = Path(document)
    parts = path.parts
    try:
        docs_idx = parts.index("docs")
    except ValueError:
        return ""
    if docs_idx + 1 < len(parts):
        return parts[docs_idx + 1]
    return ""


def collect_benchmark_corpus(pdf_dir: Path, include_nonfinancial: bool = False) -> Dict[str, Any]:
    documents: List[Dict[str, Any]] = []
    documents_skipped: List[Dict[str, Any]] = []
    financial_documents_processed = 0
    pdf_paths = sorted(pdf_dir.rglob("*.pdf"))
    for pdf in pdf_paths:
        document = str(pdf)
        source_kind = classify_document_source_kind(pdf)
        record = {
            "ticker": _document_ticker(document, default=pdf_dir.name),
            "document": document,
            "source_kind": source_kind,
        }
        if source_kind in FINANCIAL_SOURCE_KINDS:
            financial_documents_processed += 1
        if include_nonfinancial or source_kind in FINANCIAL_SOURCE_KINDS:
            documents.append(record)
            continue
        documents_skipped.append(
            {
                **record,
                "skip_reason": NON_FINANCIAL_SKIP_REASON,
            }
        )
    return {
        "documents": documents,
        "documents_skipped": documents_skipped,
        "financial_documents_processed": financial_documents_processed,
        "nonfinancial_documents_skipped": len(documents_skipped),
        "total_pdf_count": len(pdf_paths),
    }


def _filter_rows_by_documents(rows: List[dict], allowed_documents: Set[str]) -> List[dict]:
    filtered: List[dict] = []
    for row in rows:
        document = _document_key(str(row.get("file") or row.get("source_file") or "").strip())
        if document in allowed_documents:
            filtered.append(dict(row))
    return filtered


def _filter_document_diagnostics_by_documents(
    document_diagnostics: List[dict],
    allowed_documents: Set[str],
) -> List[dict]:
    filtered: List[dict] = []
    for entry in document_diagnostics:
        document = _document_key(str(entry.get("document", "")).strip())
        if document in allowed_documents:
            filtered.append(dict(entry))
    return filtered


def filter_extraction_result_by_documents(
    result: Dict[str, Any],
    allowed_documents: Set[str],
) -> Dict[str, Any]:
    filtered = dict(result)
    filtered["canonical_rows"] = _filter_rows_by_documents(list(result.get("canonical_rows", []) or []), allowed_documents)
    filtered["document_diagnostics"] = _filter_document_diagnostics_by_documents(
        list(result.get("document_diagnostics", []) or []),
        allowed_documents,
    )
    return filtered


def build_pipeline_documents(
    ticker: str,
    pdftotext_result: Dict[str, Any],
    docling_result: Dict[str, Any],
    benchmark_documents: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    pdf_rows_by_document = _group_rows_by_document(list(pdftotext_result.get("canonical_rows", []) or []))
    selected_rows_by_document = _group_rows_by_document(list(docling_result.get("canonical_rows", []) or []))
    docling_diagnostics = _group_diagnostics_by_document(list(docling_result.get("document_diagnostics", []) or []))

    benchmark_documents_by_path: Dict[str, Dict[str, Any]] = {}
    for entry in list(benchmark_documents or []):
        document = _document_key(str(entry.get("document", "")).strip())
        if not document:
            continue
        benchmark_documents_by_path[document] = dict(entry)

    all_documents = sorted(benchmark_documents_by_path)
    if not all_documents:
        all_documents = sorted(set(pdf_rows_by_document) | set(selected_rows_by_document) | set(docling_diagnostics))
    documents: List[Dict[str, Any]] = []
    for document in all_documents:
        pdf_rows = pdf_rows_by_document.get(document, [])
        selected_rows = selected_rows_by_document.get(document, [])
        comparison = compare(pdf_rows, selected_rows)
        observability = docling_diagnostics.get(document, {})
        benchmark_meta = benchmark_documents_by_path.get(document, {})
        source_kind = str(observability.get("source_kind", "")).strip() or str(benchmark_meta.get("source_kind", "")).strip()
        diagnostics = {
            "reconciliation_repairs": _safe_int(observability.get("reconciliation_repairs")),
            "tsr_duplicate_rows_demoted": _safe_int(observability.get("tsr_duplicate_rows_demoted")),
            "consistency_failures": _safe_int(observability.get("consistency_failures")),
            "normalization_corrections": _safe_int(observability.get("normalization_corrections")),
        }
        returncode = observability.get("returncode")
        diagnostics["failure_type"] = _failure_type(returncode, selected_rows)
        documents.append(
            {
                "ticker": _document_ticker(document, default=str(observability.get("ticker", "")).strip() or ticker),
                "document": document,
                "source_kind": source_kind,
                "document_classifier": dict(observability.get("document_classifier", {}) or {}),
                "extractor_selected": str(observability.get("extractor_selected", "docling")).strip() or "docling",
                "skip_reason": observability.get("skip_reason"),
                "fallback_triggered": bool(observability.get("fallback_triggered", False)),
                "docling_row_count_before_filtering": _safe_int(
                    observability.get("docling_row_count_before_filtering")
                ),
                "fallback_reason": observability.get("fallback_reason"),
                "fallback_suppressed": bool(observability.get("fallback_suppressed", False)),
                "fallback_suppression_reason": (
                    str(observability.get("fallback_suppression_reason") or "").strip() or None
                ),
                "context_rows": _safe_int(observability.get("context_rows")),
                "rejected_rows": _safe_int(observability.get("rejected_rows")),
                "rejection_reasons": dict(observability.get("rejection_reasons", {}) or {}),
                "tsr_tables_processed": _safe_int(observability.get("tsr_tables_processed")),
                "accuracy": {
                    "agreement": comparison["agree"],
                    "docling_only": comparison["docling_only"],
                    "pdftotext_only": comparison["pdf_only"],
                },
                "coverage": {
                    "rows": len(selected_rows),
                    "metric_keys": _coverage_metric_keys(selected_rows),
                },
                "diagnostics": diagnostics,
            }
        )
    return documents


def build_pipeline_diagnostics_payload(
    documents: List[Dict[str, Any]],
    documents_skipped: Optional[List[Dict[str, Any]]] = None,
    financial_documents_processed: Optional[int] = None,
    nonfinancial_documents_skipped: Optional[int] = None,
) -> Dict[str, Any]:
    total_documents = len(documents)
    agreement_docs = 0
    fallback_docs = 0
    consistency_failure_docs = 0
    reconciliation_docs = 0
    for document in documents:
        accuracy = document.get("accuracy", {})
        diagnostics = document.get("diagnostics", {})
        if (
            isinstance(accuracy, dict)
            and _safe_int(accuracy.get("docling_only")) == 0
            and _safe_int(accuracy.get("pdftotext_only")) == 0
        ):
            agreement_docs += 1
        if bool(document.get("fallback_triggered", False)):
            fallback_docs += 1
        if isinstance(diagnostics, dict) and _safe_int(diagnostics.get("consistency_failures")) > 0:
            consistency_failure_docs += 1
        if isinstance(diagnostics, dict) and _safe_int(diagnostics.get("reconciliation_repairs")) > 0:
            reconciliation_docs += 1

    documents_skipped = list(documents_skipped or [])
    financial_documents_processed = total_documents
    nonfinancial_documents_skipped = len(documents_skipped)

    denominator = float(total_documents or 1)
    return {
        "documents": documents,
        "documents_skipped": documents_skipped,
        "summary": {
            "agreement_rate": agreement_docs / denominator,
            "fallback_rate": fallback_docs / denominator,
            "consistency_failure_rate": consistency_failure_docs / denominator,
            "reconciliation_rate": reconciliation_docs / denominator,
            "financial_documents_processed": _safe_int(financial_documents_processed),
            "nonfinancial_documents_skipped": _safe_int(nonfinancial_documents_skipped),
        },
    }


def validate_pipeline_diagnostics_payload(payload: Dict[str, Any]) -> None:
    documents = list(payload.get("documents", []) or [])
    documents_skipped = list(payload.get("documents_skipped", []) or [])
    summary = payload.get("summary", {})
    if not isinstance(summary, dict):
        raise RuntimeError("pipeline diagnostics summary mismatch")
    if _safe_int(summary.get("financial_documents_processed")) != len(documents):
        raise RuntimeError("pipeline diagnostics summary mismatch")
    if _safe_int(summary.get("nonfinancial_documents_skipped")) != len(documents_skipped):
        raise RuntimeError("pipeline diagnostics summary mismatch")


def write_pipeline_diagnostics(
    documents: List[Dict[str, Any]],
    out_path: Path,
    documents_skipped: Optional[List[Dict[str, Any]]] = None,
    financial_documents_processed: Optional[int] = None,
    nonfinancial_documents_skipped: Optional[int] = None,
) -> Dict[str, Any]:
    payload = build_pipeline_diagnostics_payload(
        documents,
        documents_skipped=documents_skipped,
        financial_documents_processed=financial_documents_processed,
        nonfinancial_documents_skipped=nonfinancial_documents_skipped,
    )
    validate_pipeline_diagnostics_payload(payload)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return payload


def compare(rows_pdf: list, rows_docling: list) -> dict:
    """Compare two extraction outputs. Keys: (metric, period_end)."""
    by_pdf = {}
    for r in rows_pdf:
        k = _row_key(r)
        if k not in by_pdf:
            by_pdf[k] = []
        by_pdf[k].append(_row_value(r))

    by_docling = {}
    for r in rows_docling:
        k = _row_key(r)
        if k not in by_docling:
            by_docling[k] = []
        by_docling[k].append(_row_value(r))

    def norm_vals(vals):
        seen = set()
        for v in vals:
            try:
                x = round(float(v), 2)
                seen.add(x)
            except (TypeError, ValueError):
                seen.add(v)
        return seen

    matched_keys = _matched_comparison_keys(by_pdf, by_docling)
    matched_pdf_keys = {pdf_key for pdf_key, _ in matched_keys}
    matched_docling_keys = {docling_key for _, docling_key in matched_keys}
    pdf_only = set(by_pdf) - matched_pdf_keys
    docling_only = set(by_docling) - matched_docling_keys

    agree = 0
    disagree = 0
    disagree_examples = []
    for pdf_key, docling_key in matched_keys:
        vp = norm_vals(by_pdf[pdf_key])
        vd = norm_vals(by_docling[docling_key])
        if vp == vd:
            agree += 1
        else:
            disagree += 1
            if len(disagree_examples) < 50:
                disagree_examples.append(
                    {
                        "key": {
                            "metric": docling_key[0],
                            "statement_period_end": docling_key[1],
                        },
                        "pdftotext_values": sorted(vp),
                        "docling_values": sorted(vd),
                    }
                )

    return {
        "total_pdf": len(rows_pdf),
        "total_docling": len(rows_docling),
        "unique_keys_pdf": len(by_pdf),
        "unique_keys_docling": len(by_docling),
        "agree": agree,
        "disagree": disagree,
        "pdf_only": len(pdf_only),
        "docling_only": len(docling_only),
        "disagree_examples": disagree_examples,
        "docling_only_examples": list(docling_only)[:10],
        "pdf_only_examples": list(pdf_only)[:10],
    }


def main():
    ap = argparse.ArgumentParser(description="Compare pdftotext vs Docling extraction accuracy")
    ap.add_argument("--max-tickers", type=int, default=5, help="Max tickers to run (default 5)")
    ap.add_argument("--tickers", nargs="*", help="Specific ticker symbols (e.g. 10X 29M). Overrides --max-tickers.")
    ap.add_argument("--cpu", action="store_true", help="Force CPU fallback for Docling (default is GPU)")
    ap.add_argument("--timeout", type=int, default=900, help="Timeout per ticker per extractor (sec)")
    ap.add_argument("--out-dir", default=str(OUT_DIR), help="Output directory")
    ap.add_argument(
        "--pipeline-diagnostics-out",
        default=str(ROOT / "reports" / "pipeline_diagnostics.json"),
        help="Per-document pipeline diagnostics JSON output path.",
    )
    ap.add_argument(
        "--allow-empty",
        action="store_true",
        help="Treat empty canonical extractor output as success (default is fail-fast).",
    )
    ap.add_argument(
        "--enforce-gates",
        action="store_true",
        help="Keep financial/coverage gates enforced during benchmarking. Default disables hard gates for comparison runs.",
    )
    ap.add_argument(
        "--include-nonfinancial",
        action="store_true",
        help="Include non-financial source_kind documents in benchmarking. Default benchmarks only canonical_report and appendix_report.",
    )
    ap.add_argument(
        "--max-workers",
        type=int,
        default=_default_max_workers(),
        help="Max per-document worker processes. Default: min(8, cpu_count()). Use 1 to disable parallelism.",
    )
    args = ap.parse_args()
    extractor_python = print_runtime_info()

    if not DOCS.exists():
        print(f"Docs dir not found: {DOCS}", file=sys.stderr)
        return 2

    if args.tickers:
        tickers = []
        for t in args.tickers:
            d = DOCS / t
            if d.is_dir():
                corpus = collect_benchmark_corpus(d, include_nonfinancial=args.include_nonfinancial)
                if corpus["total_pdf_count"] == 0:
                    print(f"  Skip {t}: no PDFs found", file=sys.stderr)
                    continue
                tickers.append((t, str(d), corpus))
                if not corpus["documents"]:
                    print(
                        f"  Skip {t}: no benchmark documents after source_kind filtering "
                        f"({corpus['nonfinancial_documents_skipped']} non-financial skipped)",
                        file=sys.stderr,
                    )
            else:
                print(f"  Skip {t}: dir not found", file=sys.stderr)
    else:
        tickers = []
        for d in sorted(DOCS.iterdir()):
            if not d.is_dir():
                continue
            corpus = collect_benchmark_corpus(d, include_nonfinancial=args.include_nonfinancial)
            if corpus["total_pdf_count"] == 0 or not corpus["documents"]:
                continue
            tickers.append((d.name, str(d), corpus))
            if len(tickers) >= args.max_tickers:
                break

    if not tickers:
        if args.include_nonfinancial:
            print("No tickers found", file=sys.stderr)
        else:
            print("No benchmark documents found after source_kind filtering", file=sys.stderr)
        return 2

    out_base = Path(args.out_dir)
    out_base.mkdir(parents=True, exist_ok=True)

    runnable_tickers = [item for item in tickers if item[2]["documents"]]
    print(f"Comparing extractors on {len(runnable_tickers)} tickers: {[t[0] for t in runnable_tickers]}\n")

    all_comparisons = []
    pipeline_documents: List[Dict[str, Any]] = []
    documents_skipped: List[Dict[str, Any]] = []
    financial_documents_processed_total = 0
    nonfinancial_documents_skipped_total = 0
    failed_tickers = []
    failed_documents: List[Dict[str, Any]] = []
    for ticker, pdf_dir, corpus in tickers:
        financial_documents_processed_total += _safe_int(corpus.get("financial_documents_processed"))
        nonfinancial_documents_skipped_total += _safe_int(corpus.get("nonfinancial_documents_skipped"))
        documents_skipped.extend(list(corpus.get("documents_skipped", []) or []))

        benchmark_documents = list(corpus.get("documents", []) or [])
        total_pdf_count = _safe_int(corpus.get("total_pdf_count"))
        if not benchmark_documents:
            print(
                f"  {ticker} ({total_pdf_count} PDFs) ... skipped: no benchmark documents after source_kind filtering"
            )
            continue

        benchmark_document_count = len(benchmark_documents)
        print(f"  {ticker} ({benchmark_document_count} benchmark / {total_pdf_count} PDFs)")
        benchmark_run = benchmark_ticker_documents(
            ticker,
            benchmark_documents,
            out_base,
            timeout_sec=args.timeout,
            cpu=args.cpu,
            enforce_gates=args.enforce_gates,
            allow_empty=args.allow_empty,
            python_executable=extractor_python,
            max_workers=args.max_workers,
        )
        ticker_failed_documents = list(benchmark_run.get("failed_documents", []) or [])
        failed_documents.extend(ticker_failed_documents)
        successful_documents = list(benchmark_run.get("successful_documents", []) or [])
        if not successful_documents:
            failed_tickers.append(
                {
                    "ticker": ticker,
                    "error": "no_successful_pdf_runs",
                    "failed_documents": len(ticker_failed_documents),
                }
            )
            print(f"    no successful benchmark PDFs; failed_pdfs={len(ticker_failed_documents)}")
            continue

        filtered_pdf_result = benchmark_run["pdftotext_result"]
        filtered_docling_result = benchmark_run["docling_result"]
        cmp = compare(filtered_pdf_result["canonical_rows"], filtered_docling_result["canonical_rows"])
        cmp["ticker"] = ticker
        cmp["pdf_count"] = total_pdf_count
        cmp["financial_documents_processed"] = _safe_int(corpus.get("financial_documents_processed"))
        cmp["nonfinancial_documents_skipped"] = _safe_int(corpus.get("nonfinancial_documents_skipped"))
        all_comparisons.append(cmp)
        pipeline_documents.extend(
            build_pipeline_documents(
                ticker,
                filtered_pdf_result,
                filtered_docling_result,
                benchmark_documents=successful_documents,
            )
        )

        print(
            f"    summary pdf={cmp['unique_keys_pdf']} docling={cmp['unique_keys_docling']} "
            f"agree={cmp['agree']} disagree={cmp['disagree']} "
            f"docling_only={cmp['docling_only']} pdf_only={cmp['pdf_only']} "
            f"failed_pdfs={len(ticker_failed_documents)}"
        )

    # Summary report
    report_path = out_base / "comparison_report.json"
    with open(report_path, "w") as f:
        json.dump(
            {
                "tickers": [c["ticker"] for c in all_comparisons],
                "comparisons": all_comparisons,
                "failed_tickers": failed_tickers,
                "failed_documents": failed_documents,
                "summary": {
                    "total_agree": sum(c["agree"] for c in all_comparisons),
                    "total_disagree": sum(c["disagree"] for c in all_comparisons),
                    "total_docling_only": sum(c["docling_only"] for c in all_comparisons),
                    "total_pdf_only": sum(c["pdf_only"] for c in all_comparisons),
                    "financial_documents_processed": financial_documents_processed_total,
                    "nonfinancial_documents_skipped": nonfinancial_documents_skipped_total,
                    "failed_documents": len(failed_documents),
                },
            },
            f,
            indent=2,
        )
    print(f"\nReport: {report_path}")
    pipeline_diagnostics_path = Path(args.pipeline_diagnostics_out)
    pipeline_payload = write_pipeline_diagnostics(
        pipeline_documents,
        pipeline_diagnostics_path,
        documents_skipped=documents_skipped,
        financial_documents_processed=financial_documents_processed_total,
        nonfinancial_documents_skipped=nonfinancial_documents_skipped_total,
    )
    print(f"Pipeline diagnostics: {pipeline_diagnostics_path}")

    total_agree = sum(c["agree"] for c in all_comparisons)
    total_disagree = sum(c["disagree"] for c in all_comparisons)
    total_both = total_agree + total_disagree
    if failed_tickers:
        print(f"Failed ticker runs: {len(failed_tickers)}")
    if failed_documents:
        print(f"Failed PDF runs: {len(failed_documents)}")
    if not all_comparisons:
        print("No successful comparisons were produced.")
        return 1
    if not pipeline_payload.get("documents"):
        print("No pipeline diagnostics were produced.")
        return 1
    if total_both > 0:
        pct = 100 * total_agree / total_both
        print(f"Accuracy: {total_agree}/{total_both} ({pct:.1f}%) agreement where both extracted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
