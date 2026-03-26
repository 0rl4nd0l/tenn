"""
Extraction Workbench — backend logic for interactive extraction testing.

Provides:
  - Fixture listing and PDF serving
  - Extraction job runner with configurable knobs
  - Metrics comparison against expected values
"""

import json, os, subprocess, sys, threading, time
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).resolve().parents[2]
FE_ROOT = REPO_ROOT / "financial-engine_v2"
FIXTURES_DIR = FE_ROOT / "backend" / "tests" / "eval_fixtures"
EVAL_CONFIG = FE_ROOT / "backend" / "tests" / "eval_config.json"
DOCS_ROOT = FE_ROOT / "data" / "asx" / "docs"
HISTORY_DIR = Path(__file__).parent / "extraction_history"

METRIC_FIELDS = [
    "revenue", "ebit", "np_attributable", "operating_cf",
    "investing_cf", "financing_cf", "capex", "cash_end",
    "net_debt", "shares_outstanding",
]

# ── Job storage ───────────────────────────────────────────────────────────────
_JOBS: dict[str, dict] = {}
_JOBS_LOCK = threading.Lock()


def list_fixtures() -> list[dict]:
    """Return all eval fixtures with metadata."""
    fixtures = []
    for fp in sorted(FIXTURES_DIR.glob("*.json")):
        try:
            data = json.loads(fp.read_text())
            pdf_path = data.get("pdf_path", "")
            abs_pdf = FE_ROOT / pdf_path
            fixtures.append({
                "name": fp.stem,
                "ticker": data.get("ticker", ""),
                "period_type": data.get("period_type", ""),
                "period_end": data.get("period_end", ""),
                "currency": data.get("currency", "AUD"),
                "scale": data.get("scale", ""),
                "pdf_path": pdf_path,
                "pdf_exists": abs_pdf.exists(),
                "pdf_size_mb": round(abs_pdf.stat().st_size / 1e6, 1) if abs_pdf.exists() else 0,
                "metric_count": len([k for k, v in data.get("metrics", {}).items() if v is not None]),
                "expected_nulls": data.get("expected_nulls", []),
            })
        except Exception:
            pass
    return fixtures


def load_fixture(name: str) -> dict | None:
    """Load a single fixture by stem name."""
    fp = FIXTURES_DIR / f"{name}.json"
    if not fp.exists():
        return None
    return json.loads(fp.read_text())


def load_eval_config() -> dict:
    """Load eval_config.json."""
    try:
        return json.loads(EVAL_CONFIG.read_text())
    except Exception:
        return {}


def resolve_pdf_path(relative_path: str) -> Path:
    """Resolve a fixture's pdf_path to absolute."""
    return FE_ROOT / relative_path


def list_available_pdfs(ticker: str = "") -> list[dict]:
    """List PDFs in the docs directory, optionally filtered by ticker."""
    pdfs = []
    search_root = DOCS_ROOT / ticker if ticker else DOCS_ROOT
    if not search_root.exists():
        return pdfs
    for pdf in sorted(search_root.rglob("*.pdf"))[:100]:
        pdfs.append({
            "path": str(pdf.relative_to(FE_ROOT)),
            "name": pdf.name,
            "ticker": pdf.relative_to(DOCS_ROOT).parts[0] if len(pdf.relative_to(DOCS_ROOT).parts) > 0 else "",
            "size_mb": round(pdf.stat().st_size / 1e6, 1),
        })
    return pdfs


def list_tickers() -> list[str]:
    """List all ticker directories under docs root."""
    if not DOCS_ROOT.exists():
        return []
    return sorted(d.name for d in DOCS_ROOT.iterdir() if d.is_dir())


# ── History storage ───────────────────────────────────────────────────────────

def _save_history(fixture_name: str, run_data: dict) -> None:
    """Append a run result to the fixture's history file."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    hist_file = HISTORY_DIR / f"{fixture_name}.json"
    history = []
    if hist_file.exists():
        try:
            history = json.loads(hist_file.read_text())
        except Exception:
            history = []
    # Keep last 50 runs
    history.append(run_data)
    history = history[-50:]
    hist_file.write_text(json.dumps(history, indent=1, default=str))


def get_history(fixture_name: str) -> list[dict]:
    """Return historical runs for a fixture."""
    hist_file = HISTORY_DIR / f"{fixture_name}.json"
    if not hist_file.exists():
        return []
    try:
        return json.loads(hist_file.read_text())
    except Exception:
        return []


# ── Gap detector ─────────────────────────────────────────────────────────────

def detect_gaps(payload: dict, fixture: dict | None) -> list[dict]:
    """Detect extraction quality gaps. Returns list of {field, type, detail}."""
    gaps = []
    provenance = payload.get("provenance", {})
    metrics = {m: payload.get(m) for m in METRIC_FIELDS}

    for field in METRIC_FIELDS:
        val = metrics.get(field)
        prov = provenance.get(field, "")

        # Gap: metric has a value but no provenance (came from nowhere)
        if val is not None and not prov:
            gaps.append({"field": field, "type": "no_provenance",
                         "detail": f"Value {val} extracted but no provenance recorded"})

        # Gap: metric is None but fixture expects a value
        if val is None and fixture:
            expected = fixture.get("metrics", {}).get(field)
            expected_nulls = set(fixture.get("expected_nulls", []))
            if expected is not None and field not in expected_nulls:
                gaps.append({"field": field, "type": "missing_value",
                             "detail": f"Expected {expected} but extraction returned None"})

        # Gap: provenance says "unknown" row ref
        if ":unknown" in prov:
            gaps.append({"field": field, "type": "unknown_row",
                         "detail": f"Source identified ({prov.split(':')[0]}) but row reference unknown"})

        # Gap: derived value (calculated, not directly extracted)
        if prov.startswith("derived:"):
            gaps.append({"field": field, "type": "derived",
                         "detail": f"Computed from other fields: {prov}"})

    # Scale gaps
    scale = payload.get("scale", "unknown")
    if scale == "unknown":
        gaps.append({"field": "_scale", "type": "unknown_scale",
                     "detail": "Scale not detected from headers or LLM — values may be wrong magnitude"})

    # Confidence gap
    conf = payload.get("confidence_metrics", 0)
    if conf < 0.5:
        gaps.append({"field": "_confidence", "type": "low_confidence",
                     "detail": f"LLM confidence {conf:.0%} is below 50% threshold"})

    # Period gap
    if not payload.get("period_end"):
        gaps.append({"field": "_period", "type": "no_period",
                     "detail": "Period end date not detected — wrong column may have been extracted"})

    return gaps


def metric_matches(extracted: float | None, expected: float | None, tolerance: float) -> dict:
    """Compare a single metric. Returns {match, extracted, expected, tolerance, pct_diff}."""
    if expected is None:
        return {"match": extracted is None, "extracted": extracted, "expected": None,
                "tolerance": tolerance, "pct_diff": None, "status": "null_check"}
    if extracted is None:
        return {"match": False, "extracted": None, "expected": expected,
                "tolerance": tolerance, "pct_diff": None, "status": "missing"}
    if expected == 0:
        match = abs(extracted) < 1e-6
        return {"match": match, "extracted": extracted, "expected": expected,
                "tolerance": tolerance, "pct_diff": None, "status": "zero_check"}
    pct_diff = abs(extracted - expected) / abs(expected)
    return {"match": pct_diff <= tolerance, "extracted": extracted, "expected": expected,
            "tolerance": tolerance, "pct_diff": round(pct_diff, 6), "status": "compared"}


def compare_results(extracted_metrics: dict, fixture: dict) -> dict:
    """Compare extracted metrics against fixture expected values."""
    config = load_eval_config()
    global_tolerances = config.get("tolerances", {})
    fixture_tolerances = fixture.get("tolerances", {})
    expected_nulls = set(fixture.get("expected_nulls", []))
    expected_metrics = fixture.get("metrics", {})
    provenance = extracted_metrics.get("provenance", {})

    comparisons = {}
    matches = 0
    total = 0

    for field in METRIC_FIELDS:
        if field in expected_nulls:
            expected_val = None
        else:
            expected_val = expected_metrics.get(field)
            if expected_val is None:
                continue  # not in fixture, skip

        tolerance = fixture_tolerances.get(field, global_tolerances.get(field, 0.01))
        extracted_val = extracted_metrics.get(field)

        result = metric_matches(extracted_val, expected_val, tolerance)
        result["provenance"] = provenance.get(field, "")
        comparisons[field] = result
        total += 1
        if result["match"]:
            matches += 1

    accuracy = round(matches / total, 4) if total > 0 else 0

    # Period info from extraction
    period_info = {
        "period_type": extracted_metrics.get("period_type"),
        "period_end": str(extracted_metrics.get("period_end", "") or ""),
        "period_start": str(extracted_metrics.get("period_start", "") or ""),
        "confidence_metrics": extracted_metrics.get("confidence_metrics"),
    }
    # Expected period from fixture
    fixture_period = {
        "period_type": fixture.get("period_type"),
        "period_end": fixture.get("period_end"),
        "currency": fixture.get("currency"),
    }

    # Gaps
    gaps = detect_gaps(extracted_metrics, fixture)

    # Scale info
    scale_info = {
        "effective": extracted_metrics.get("scale", "unknown"),
        "currency": extracted_metrics.get("currency", "AUD"),
    }

    return {
        "accuracy": accuracy,
        "matches": matches,
        "total": total,
        "comparisons": comparisons,
        "period": period_info,
        "fixture_period": fixture_period,
        "gaps": gaps,
        "scale": scale_info,
    }


def start_extraction_job(
    fixture_name: str | None = None,
    pdf_path: str | None = None,
    config: dict | None = None,
) -> str:
    """Start an extraction job in a background thread. Returns job_id."""
    config = config or {}
    job_id = f"extract_{int(time.time())}_{fixture_name or 'custom'}"

    fixture = None
    if fixture_name:
        fixture = load_fixture(fixture_name)
        if fixture and not pdf_path:
            pdf_path = fixture.get("pdf_path", "")

    if not pdf_path:
        with _JOBS_LOCK:
            _JOBS[job_id] = {"status": "error", "error": "No PDF path provided"}
        return job_id

    abs_pdf = resolve_pdf_path(pdf_path)
    if not abs_pdf.exists():
        with _JOBS_LOCK:
            _JOBS[job_id] = {"status": "error", "error": f"PDF not found: {pdf_path}"}
        return job_id

    with _JOBS_LOCK:
        _JOBS[job_id] = {
            "status": "running",
            "fixture_name": fixture_name,
            "pdf_path": pdf_path,
            "config": config,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "output": [],
            "result": None,
            "comparison": None,
        }

    thread = threading.Thread(
        target=_run_extraction,
        args=(job_id, str(abs_pdf), fixture, config),
        daemon=True,
    )
    thread.start()
    return job_id


def _run_extraction(job_id: str, abs_pdf: str, fixture: dict | None, config: dict):
    """Run extraction in a subprocess using a helper script."""
    env = os.environ.copy()

    # Apply config overrides
    if config.get("model"):
        env["EXTRACT_MODEL"] = config["model"]
    if config.get("extraction_url"):
        env["EXTRACTION_LLAMACPP_URL"] = config["extraction_url"]
    if config.get("llm_api_key"):
        env["LLM_API_KEY"] = config["llm_api_key"]
    elif not env.get("LLM_API_KEY"):
        # Default for local llama-server started with --api-key
        env["LLM_API_KEY"] = "local-openai-key"
    if config.get("skip_narrative"):
        env["EXTRACTION_SKIP_NARRATIVE"] = "1"
    if config.get("no_parallel"):
        env["EXTRACTION_PARALLEL"] = "0"
    if config.get("no_filter_rows"):
        env["EXTRACTION_FILTER_ROWS"] = "0"
    if config.get("no_skip_redundant"):
        env["EXTRACTION_SKIP_REDUNDANT"] = "0"
    if config.get("force_pymupdf"):
        env["FORCE_PYMUPDF"] = "1"
    if config.get("anthropic_key"):
        env["ANTHROPIC_API_KEY"] = config["anthropic_key"]
    if config.get("claude_model"):
        env["EVAL_CLAUDE_MODEL"] = config["claude_model"]

    # Build the extraction runner script
    ticker = fixture.get("ticker", "UNKNOWN") if fixture else "CUSTOM"
    doc_id = fixture.get("document_id", "test_run") if fixture else "test_run"

    script = f"""
import sys, json, os, time, logging

# Route ALL logging to stdout so the workbench UI can stream it
logging.basicConfig(
    stream=sys.stdout, level=logging.INFO,
    format="[%(levelname).1s %(name)s] %(message)s",
    force=True,
)
# Suppress noisy libraries
for _quiet in ("httpx", "httpcore", "urllib3", "filelock", "PIL"):
    logging.getLogger(_quiet).setLevel(logging.WARNING)

sys.path.insert(0, "{FE_ROOT / 'backend'}")
os.chdir("{FE_ROOT}")

print("[workbench] Loading extraction modules...", flush=True)
from app.services.multipass_extraction import (
    run_multipass_extraction, _run_pass1_classifier, _run_pass2_locator,
    _detect_scale_from_tables, _table_to_markdown, METRIC_FIELDS,
)
from app.services.docling_extract import extract_structured

doc_meta = {{"document_id": "{doc_id}", "ticker": "{ticker}", "title": "workbench_test"}}

print("[workbench] Starting extraction: {{ticker}} / {{doc_id}}", flush=True)
print("[workbench] PDF: {abs_pdf}", flush=True)
start = time.time()
result = run_multipass_extraction("{abs_pdf}", doc_meta, None, skip_narrative={config.get("skip_narrative", False)})
elapsed = round(time.time() - start, 1)
print(f"[workbench] Extraction complete: status={{result.status}}, {{elapsed}}s", flush=True)

# Capture diagnostic data for the workbench
diagnostics = {{}}
try:
    structured = extract_structured("{abs_pdf}")
    # Scale info
    header_scale = _detect_scale_from_tables(structured.tables)
    llm_scale = (result.payload or {{}}).get("scale", "unknown")
    diagnostics["scale"] = {{
        "header_detected": header_scale,
        "llm_detected": llm_scale,
        "effective": llm_scale,
        "match": header_scale == llm_scale or header_scale == "unknown",
    }}
    # Labelled tables with raw markdown
    labelled = _run_pass2_locator(structured.tables)
    raw_tables = {{}}
    for label, table in labelled:
        md = _table_to_markdown(table, max_rows=40) or ""
        raw_tables[label] = {{
            "page": getattr(table, "page_number", None),
            "rows": len(table.rows) if hasattr(table, "rows") else 0,
            "markdown": md[:4000],
        }}
    diagnostics["raw_tables"] = raw_tables
    diagnostics["table_count"] = len(structured.tables)
    diagnostics["labelled_count"] = len(labelled)
except Exception as diag_err:
    diagnostics["error"] = str(diag_err)

out = {{
    "status": result.status,
    "elapsed_s": elapsed,
    "payload": result.payload,
    "error": result.error,
    "sections": [s.__dict__ if hasattr(s, '__dict__') else str(s) for s in (result.sections or [])],
    "diagnostics": diagnostics,
}}
print("__RESULT_JSON__")
print(json.dumps(out, default=str))
"""

    def _append_output(line: str):
        with _JOBS_LOCK:
            if job_id in _JOBS:
                _JOBS[job_id]["output"].append(line)

    try:
        proc = subprocess.Popen(
            [sys.executable, "-c", script],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, env=env, cwd=str(FE_ROOT),
        )

        # Store proc so cancel_job can kill it
        with _JOBS_LOCK:
            if job_id in _JOBS:
                _JOBS[job_id]["_proc"] = proc

        result_json = None
        capturing = False
        for line in proc.stdout:
            stripped = line.rstrip()
            if stripped == "__RESULT_JSON__":
                capturing = True
                continue
            if capturing:
                try:
                    result_json = json.loads(stripped)
                except Exception:
                    pass
                capturing = False
            else:
                _append_output(stripped)

        proc.wait(timeout=600)

        with _JOBS_LOCK:
            job = _JOBS.get(job_id)
            if job:
                # If already cancelled by cancel_job(), don't overwrite status
                if job["status"] == "cancelled":
                    pass
                elif result_json:
                    job["result"] = result_json
                    job["status"] = "done"
                    # Run comparison if we have a fixture
                    if fixture and result_json.get("payload"):
                        job["comparison"] = compare_results(
                            result_json["payload"], fixture
                        )
                    # Gap detection (works with or without fixture)
                    if result_json.get("payload"):
                        job["gaps"] = detect_gaps(result_json["payload"], fixture)
                    # Save to history
                    fixture_name = job.get("fixture_name")
                    if fixture_name and result_json.get("payload"):
                        _save_history(fixture_name, {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "accuracy": job.get("comparison", {}).get("accuracy"),
                            "matches": job.get("comparison", {}).get("matches"),
                            "total": job.get("comparison", {}).get("total"),
                            "elapsed_s": result_json.get("elapsed_s"),
                            "status": result_json.get("status"),
                            "scale": (result_json.get("payload") or {}).get("scale"),
                            "confidence": (result_json.get("payload") or {}).get("confidence_metrics"),
                            "gap_count": len(job.get("gaps", [])),
                            "per_metric": {
                                field: {
                                    "extracted": (result_json.get("payload") or {}).get(field),
                                    "match": (job.get("comparison", {}).get("comparisons", {}).get(field, {})).get("match"),
                                }
                                for field in METRIC_FIELDS
                            },
                            "config": config,
                        })
                else:
                    job["status"] = "error"
                    job["error"] = "No result JSON captured from extraction"
                job.pop("_proc", None)

    except Exception as exc:
        with _JOBS_LOCK:
            if job_id in _JOBS:
                _JOBS[job_id]["status"] = "error"
                _JOBS[job_id]["error"] = str(exc)


# Metric → table type mapping (for per-metric retry)
METRIC_TO_TABLE = {
    "revenue": "income_statement",
    "ebit": "income_statement",
    "np_attributable": "income_statement",
    "operating_cf": "cashflow_statement",
    "investing_cf": "cashflow_statement",
    "financing_cf": "cashflow_statement",
    "capex": "cashflow_statement",
    "cash_end": "cashflow_statement",
    "net_debt": "balance_sheet",
    "shares_outstanding": "balance_sheet",
}


def retry_metric(pdf_path: str, metric: str, config: dict | None = None) -> str:
    """Re-run extraction for just the table that contains a specific metric.
    Returns a job_id that can be polled."""
    config = config or {}
    table_type = METRIC_TO_TABLE.get(metric, "highlights")
    job_id = f"retry_{metric}_{int(time.time())}"

    abs_pdf = resolve_pdf_path(pdf_path)
    if not abs_pdf.exists():
        with _JOBS_LOCK:
            _JOBS[job_id] = {"status": "error", "error": f"PDF not found: {pdf_path}"}
        return job_id

    with _JOBS_LOCK:
        _JOBS[job_id] = {
            "status": "running",
            "metric": metric,
            "table_type": table_type,
            "output": [],
            "result": None,
        }

    env = os.environ.copy()
    if config.get("llm_api_key"):
        env["LLM_API_KEY"] = config["llm_api_key"]
    elif not env.get("LLM_API_KEY"):
        env["LLM_API_KEY"] = "local-openai-key"
    if config.get("extraction_url"):
        env["EXTRACTION_LLAMACPP_URL"] = config["extraction_url"]

    script = f"""
import sys, json, os, time
sys.path.insert(0, "{FE_ROOT / 'backend'}")
os.chdir("{FE_ROOT}")

from app.services.multipass_extraction import (
    _run_pass1_classifier, _run_pass2_locator,
    _extract_single_table, _detect_scale_from_tables,
    _table_to_markdown, SCALE_MULTIPLIERS, METRIC_FIELDS,
)
from app.services.docling_extract import extract_structured

structured = extract_structured("{abs_pdf}")
first_page_text = "\\n".join(
    s.get("text", "") for s in structured.sections if s.get("page", 0) <= 1
)[:6000]

# Pass 1
pass1 = _run_pass1_classifier("retry", first_page_text, None)
header_scale = _detect_scale_from_tables(structured.tables)
if header_scale != "unknown":
    pass1["scale"] = header_scale

scale = pass1.get("scale", "unknown") or "unknown"
multiplier = SCALE_MULTIPLIERS.get(scale, 1)

# Pass 2 — find the target table
labelled = _run_pass2_locator(structured.tables)
target_type = "{table_type}"
target_tables = [(l, t) for l, t in labelled if l == target_type]

results = []
for label, table in target_tables:
    md = _table_to_markdown(table, max_rows=50) or ""
    print("TABLE: " + label + " page=" + str(getattr(table, 'page_number', '?')))
    print(md[:2000])
    print("---END TABLE---")
    r = _extract_single_table(label, table, pass1, scale, multiplier, None)
    if r:
        results.append(r)

out = {{
    "metric": "{metric}",
    "table_type": target_type,
    "pass1": pass1,
    "scale": scale,
    "tables_found": len(target_tables),
    "results": results,
    "raw_tables": [{{
        "label": l,
        "page": getattr(t, "page_number", None),
        "markdown": (_table_to_markdown(t, max_rows=50) or "")[:4000],
    }} for l, t in target_tables],
}}
print("__RESULT_JSON__")
print(json.dumps(out, default=str))
"""

    def _run():
        try:
            proc = subprocess.Popen(
                [sys.executable, "-c", script],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, env=env, cwd=str(FE_ROOT),
            )
            with _JOBS_LOCK:
                if job_id in _JOBS:
                    _JOBS[job_id]["_proc"] = proc

            result_json = None
            capturing = False
            for line in proc.stdout:
                stripped = line.rstrip()
                if stripped == "__RESULT_JSON__":
                    capturing = True
                    continue
                if capturing:
                    try:
                        result_json = json.loads(stripped)
                    except Exception:
                        pass
                    capturing = False
                else:
                    with _JOBS_LOCK:
                        if job_id in _JOBS:
                            _JOBS[job_id]["output"].append(stripped)

            proc.wait(timeout=300)
            with _JOBS_LOCK:
                job = _JOBS.get(job_id)
                if job:
                    if job.get("status") == "cancelled":
                        pass
                    elif result_json:
                        job["result"] = result_json
                        job["status"] = "done"
                    else:
                        job["status"] = "error"
                        job["error"] = "No result captured"
                    job.pop("_proc", None)
        except Exception as exc:
            with _JOBS_LOCK:
                if job_id in _JOBS:
                    _JOBS[job_id]["status"] = "error"
                    _JOBS[job_id]["error"] = str(exc)

    threading.Thread(target=_run, daemon=True).start()
    return job_id


def get_job(job_id: str) -> dict | None:
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return None
        return {k: v for k, v in job.items() if not k.startswith("_")}


def list_jobs() -> dict:
    with _JOBS_LOCK:
        return {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in _JOBS.items()}


def cancel_job(job_id: str) -> dict:
    """Kill a running extraction job. Returns status dict."""
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if not job:
            return {"ok": False, "error": "Job not found"}
        if job["status"] != "running":
            return {"ok": False, "error": f"Job is {job['status']}, not running"}
        proc = job.get("_proc")
        if proc and proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
        job["status"] = "cancelled"
        job["error"] = "Cancelled by user"
        job.pop("_proc", None)
        return {"ok": True}


# ── Chat sessions ────────────────────────────────────────────────────────────
_CHATS: dict[str, dict] = {}
_CHATS_LOCK = threading.Lock()


def _build_chat_context(job_data: dict) -> str:
    """Build a system context string from an extraction job result."""
    parts = ["You are an extraction debugging assistant for the Tenn financial data pipeline.",
             "The user has just run an extraction and wants to understand the results.",
             "Answer concisely. Reference specific metrics, pages, and provenance when relevant.",
             ""]

    payload = (job_data.get("result") or {}).get("payload") or {}
    comparison = job_data.get("comparison") or {}
    diagnostics = (job_data.get("result") or {}).get("diagnostics") or {}
    gaps = job_data.get("gaps") or []

    parts.append("## Extraction Summary")
    parts.append(f"- Status: {(job_data.get('result') or {}).get('status', '?')}")
    parts.append(f"- Period: {payload.get('period_type', '?')} ending {payload.get('period_end', '?')}")
    parts.append(f"- Currency: {payload.get('currency', '?')}")
    parts.append(f"- Scale: {payload.get('scale', '?')}")
    parts.append(f"- Confidence: {payload.get('confidence_metrics', '?')}")
    parts.append(f"- PDF: {job_data.get('pdf_path', '?')}")
    parts.append("")

    parts.append("## Extracted Metrics")
    provenance = payload.get("provenance", {})
    comps = comparison.get("comparisons", {})
    for m in METRIC_FIELDS:
        val = payload.get(m)
        prov = provenance.get(m, "")
        c = comps.get(m, {})
        expected = c.get("expected")
        match = c.get("match")
        status = "MATCH" if match else ("MISS" if match is not None else "-")
        diff = c.get("pct_diff")
        diff_str = f" ({diff*100:.1f}% off)" if diff else ""
        parts.append(f"- {m}: {val} {status}{diff_str} [expected: {expected}] source: {prov}")
    parts.append("")

    if gaps:
        parts.append("## Quality Gaps")
        for g in gaps:
            parts.append(f"- [{g['type']}] {g['field']}: {g['detail']}")
        parts.append("")

    scale_diag = diagnostics.get("scale", {})
    if scale_diag:
        parts.append("## Scale Detection")
        parts.append(f"- Header: {scale_diag.get('header_detected', '?')}, LLM: {scale_diag.get('llm_detected', '?')}, Match: {scale_diag.get('match', '?')}")
        parts.append("")

    raw_tables = diagnostics.get("raw_tables", {})
    if raw_tables:
        parts.append("## Source Tables (first 500 chars each — ask me to show more if needed)")
        for label, tbl in raw_tables.items():
            parts.append(f"### {label} (page {tbl.get('page', '?')}, {tbl.get('rows', '?')} rows)")
            parts.append((tbl.get("markdown", ""))[:500])
            parts.append("")

    return "\n".join(parts)


def start_chat(job_id: str) -> dict:
    """Start an interactive Claude Code session in tmux, seeded with extraction context."""
    import shutil
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
    if not job:
        return {"ok": False, "error": "Job not found"}
    if not shutil.which("tmux"):
        return {"ok": False, "error": "tmux not installed — run: sudo apt install tmux"}

    chat_id = f"chat_{int(time.time())}_{job_id[:20]}"
    tmux_session = f"ext-chat-{chat_id[-8:]}"
    context = _build_chat_context(job)

    # Write context to a file Claude can read
    log_dir = REPO_ROOT / ".claude" / "monitors" / "chat_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    context_file = log_dir / f"{chat_id}.context.md"
    context_file.write_text(context)
    output_log = log_dir / f"{chat_id}.log"
    output_log.write_text("")

    # Start interactive claude in tmux
    subprocess.run(
        ["tmux", "new-session", "-d", "-s", tmux_session, "-x", "200", "-y", "50",
         "bash", "-c", f'script -q -f {output_log} -c "claude --model sonnet"; sleep 5'],
        cwd=str(REPO_ROOT),
    )

    with _CHATS_LOCK:
        _CHATS[chat_id] = {
            "job_id": job_id,
            "messages": [],
            "status": "thinking",
            "_tmux": tmux_session,
            "_log": str(output_log),
            "_log_pos": 0,
            "_context_file": str(context_file),
        }

    # Wait for claude to boot, then send context
    def _seed():
        time.sleep(4)
        initial = (
            f"Read {context_file} — it has the full extraction results I want to discuss. "
            f"Summarise the key findings (accuracy, misses, gaps) then wait for my questions."
        )
        _chat_tmux_send(tmux_session, initial)
        _chat_wait_response(chat_id, "Load extraction context")

    threading.Thread(target=_seed, daemon=True).start()
    return {"ok": True, "chat_id": chat_id}


def _chat_tmux_send(session: str, message: str) -> None:
    """Send a message to a tmux claude session."""
    if "\n" in message and len(message) > 200:
        tmp = REPO_ROOT / ".claude" / "monitors" / "chat_logs" / "_tmux_buf.txt"
        tmp.write_text(message)
        subprocess.run(["tmux", "load-buffer", str(tmp)], timeout=5)
        subprocess.run(["tmux", "paste-buffer", "-t", session], timeout=5)
    else:
        for line in message.split("\n"):
            subprocess.run(["tmux", "send-keys", "-t", session, "-l", line], timeout=5)
            subprocess.run(["tmux", "send-keys", "-t", session, "Enter"], timeout=5)
            time.sleep(0.1)
    subprocess.run(["tmux", "send-keys", "-t", session, "Enter"], timeout=5)


def _chat_wait_response(chat_id: str, user_msg: str) -> None:
    """Tail the script log until Claude finishes responding."""
    import re
    with _CHATS_LOCK:
        chat = _CHATS.get(chat_id)
        if not chat:
            return
        chat["messages"].append({"role": "user", "text": user_msg})
        log_path = Path(chat["_log"])
        start_pos = chat["_log_pos"]

    start_time = time.time()
    stable_count = 0
    last_size = start_pos
    collected = []

    while time.time() - start_time < 180:
        time.sleep(2)
        try:
            current_size = log_path.stat().st_size
        except Exception:
            continue
        if current_size > last_size:
            with open(log_path, "r", errors="replace") as f:
                f.seek(last_size)
                collected.append(f.read())
            last_size = current_size
            stable_count = 0
        else:
            stable_count += 1
            if stable_count >= 3 and collected:
                break

    raw = "".join(collected)
    # Strip all ANSI/VT100 escape sequences
    clean = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', raw)
    clean = re.sub(r'\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)', '', clean)
    clean = re.sub(r'\x1b\[\?[0-9;]*[a-zA-Z]', '', clean)
    clean = re.sub(r'\x1b[>=<][^\n]*', '', clean)
    clean = re.sub(r'\x1b\([AB0-9]', '', clean)
    # Strip carriage returns, box drawing, spinner chars
    clean = re.sub(r'\r', '', clean)
    clean = re.sub(r'[╭╮╰╯│─┌┐└┘├┤┬┴┼▐▛▜▝▘█▌▍▎▏⎿✶✻✽✢●◐]', '', clean)
    clean = re.sub(r'[⏵⏵]', '', clean)
    # Filter lines
    lines = []
    skip_patterns = [
        'Claude Code v', 'Sonnet 4', 'Claude Max', '~/tenn',
        'bypass permissions', 'shift+tab', 'ctrl+', 'esc to interrupt',
        'Gusting', 'Crunching', 'Reading', 'Stop says:', 'Stop hook',
        'SessionStart:', 'MILESTONE NOT', 'MEMORY CHECK', 'FEEDBACK:',
        'SESSION MEMORY', 'hook error', 'ACTIVE FEEDBACK', 'RELEVANT MEMORIES',
        'Recent activity', 'Welcome back', '/resume for more', "What's new",
        'Added `', 'release-notes', 'Organization', 'Ran ', 'Permission denied',
    ]
    for l in clean.split("\n"):
        stripped = l.strip()
        if not stripped or len(stripped) < 2:
            continue
        if any(p in stripped for p in skip_patterns):
            continue
        lines.append(stripped)
    response = "\n".join(lines).strip()
    if not response:
        tmux_name = "?"
        with _CHATS_LOCK:
            c = _CHATS.get(chat_id)
            if c:
                tmux_name = c.get("_tmux", "?")
        response = f"(response in terminal — run: tmux attach -t {tmux_name})"

    with _CHATS_LOCK:
        chat["messages"].append({"role": "assistant", "text": response})
        chat["status"] = "ready"
        chat["_log_pos"] = last_size


def send_chat_message(chat_id: str, user_message: str) -> dict:
    """Send a follow-up to the tmux claude session."""
    with _CHATS_LOCK:
        chat = _CHATS.get(chat_id)
    if not chat:
        return {"ok": False, "error": "Chat not found"}
    if chat["status"] == "thinking":
        return {"ok": False, "error": "Already processing a message"}

    tmux_session = chat.get("_tmux")
    if not tmux_session:
        return {"ok": False, "error": "No tmux session"}

    check = subprocess.run(["tmux", "has-session", "-t", tmux_session], capture_output=True, timeout=5)
    if check.returncode != 0:
        return {"ok": False, "error": "tmux session ended — start a new chat"}

    with _CHATS_LOCK:
        chat["status"] = "thinking"
        try:
            chat["_log_pos"] = Path(chat["_log"]).stat().st_size
        except Exception:
            pass

    def _run():
        _chat_tmux_send(tmux_session, user_message)
        _chat_wait_response(chat_id, user_message)

    threading.Thread(target=_run, daemon=True).start()
    return {"ok": True}


def get_chat(chat_id: str) -> dict | None:
    with _CHATS_LOCK:
        chat = _CHATS.get(chat_id)
        if not chat:
            return None
        return {k: v for k, v in chat.items() if not k.startswith("_")}
