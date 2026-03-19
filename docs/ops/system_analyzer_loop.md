# System Analyzer Loop

Purpose:
- Provide a bounded, recommendation-first analyzer for the local AI backend.
- Observe runtime health, benchmark artifacts, routing consistency, RAG guardrails, and runtime write-path drift.
- Emit structured reports and optional gated patch candidates without mutating code by default.

Loop modes:
- `recommend` (default): observe, validate, score, recommend.
- `prepare_patch`: include gated patch-candidate metadata in the report.
- `apply_gated`: requires explicit acknowledgement and still remains non-mutating in this implementation; approval is recorded in the report state only.

Safety:
- bounded execution with per-check timeout and global watchdog
- partial-report safe state on failure
- default safe state remains `recommend`
- no schema changes
- no queue topology changes
- router feedback remains read-only and can only bias existing adaptive reasoning fallbacks

Artifact paths:
- report history: `${DATA_ROOT}/reports/system_analyzer/<run_id>.json`
- latest report: `${DATA_ROOT}/reports/system_analyzer/latest.json`
- patch candidate metadata: `${DATA_ROOT}/reports/system_analyzer/patch_candidates/<run_id>.json`
- benchmark hint artifact: `${DATA_ROOT}/reports/model_benchmark.json`

Here `DATA_ROOT` resolves from `settings.data_root`.

Router feedback hook:
- adaptive reasoning routes may read `${DATA_ROOT}/reports/system_analyzer/latest.json` when `ROUTER_FEEDBACK_ENABLED=true`
- stale reports older than `ANALYZER_MAX_AGE_SECONDS` are ignored
- missing, stale, malformed, or benchmark-missing artifacts resolve to no-op behavior
- feedback may only degrade the preferred reasoning score or prefer the existing fallback candidate; it does not rewrite queue policy or skip the fallback chain

Validation commands:
- `python3 financial-engine_v2/scripts/run_system_analyzer.py --no-write`
- `python3 -m pytest financial-engine_v2/backend/tests/test_model_routing.py -q`

Validation prerequisites:
- backend Python environment must include analyzer runtime dependencies such as `pydantic-settings`
- targeted tests require `pytest` to be installed in the active interpreter

Validation preflight:
- `python3 -c "import importlib.util, sys; missing=[name for name in ('pydantic_settings', 'pytest') if importlib.util.find_spec(name) is None]; print('\\n'.join(missing)); raise SystemExit(0 if not missing else 1)"`
- if preflight reports missing modules, record an environment-only blocker and do not treat the analyzer loop as a code failure

Checks included:
- backend `/api/health`
- backend `/api/system/status` when reachable
- llama.cpp model endpoint reachability
- conditional Ollama model endpoint reachability
- benchmark artifact presence and freshness
- router fallback-chain crosscheck
- RAG ticker-filter strict-first plus fallback crosscheck
- runtime write-path drift against `DATA_ROOT` policy
