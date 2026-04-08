# TENN

Current active runtime is `financial-engine_v2`.

## Run in 4 steps
1. Create and activate the canonical local venv:
   - `python3 -m venv financial-engine_v2/.venv`
   - `export PATH="$PWD/financial-engine_v2/.venv/bin:$PATH"`
2. Install deps:
   - `pip install -r requirements.txt`
   - `python -m playwright install chromium`
3. Start deterministic local backend mode:
   - `LOCAL_BACKEND_PROFILE=isolated bash financial-engine_v2/scripts/run_local_backend.sh`
4. Verify health:
   - `curl -sS http://127.0.0.1:8000/api/health`

For agents and deterministic local backend startup, `financial-engine_v2/scripts/run_local_backend.sh` is the canonical entrypoint.
`python run.py` remains a supported batch/orchestration path, but it is not the canonical "system is up" signal.

Canonical environment and runtime docs:
- `docs/setup/environment.md`
- `docs/setup/runtime.md`
- `docs/setup/troubleshooting.md`
- `docs/entrypoints.md`

Repository governance note:
- `LICENSE_STATUS.md` (top-level Tenn license intent pending maintainer decision)

## Local Backend Status
Current verified local backend entrypoint is:
- `financial-engine_v2/scripts/run_local_backend.sh`

Two supported local profiles:
- `LOCAL_BACKEND_PROFILE=isolated`
  - safe smoke mode
  - embeddings/Qdrant/extraction off
  - `/chat` returns a degraded response instead of failing
- `LOCAL_BACKEND_PROFILE=full`
  - verified working with local Qdrant + local llama.cpp + commentary retrieval
  - known-good docs are in [financial-engine_v2/README.md](/home/l4nd0/tenn/financial-engine_v2/README.md)

Known current behavior:
- `/chat` retrieves from `commentary_chunks` and optional `commentary_chunks_v2`, not `asx_docs`
- local launcher now keeps `DATA_ROOT` on the repo `data/` directory unless explicitly overridden
- explicit shell env overrides `.env` and `.env.local` for local runs

Batch/orchestration path:
- `python run.py`
  - delegates to `financial-engine_v2/run.py`
  - useful for workflow runs
  - not the canonical backend bootstrap path for agents

## Validated Baseline (2026-03-19)
Validated command sequence:
1. `bash scripts/start_system.sh`
2. `bash scripts/validate_system.sh`
3. `python -m ruff check autodev financial-engine_v2/backend scripts`
4. `pytest autodev/tests`
5. `pytest financial-engine_v2/backend/tests`
6. `pytest scripts`
7. `bash scripts/run_canonical_dataset_checks.sh`
8. `python scripts/check_canonical_regression.py --baseline reports/baselines/canonical_eval_baseline_latest.json --news-report reports/news_eval_report.json --company-report reports/company_eval_report_v2.json --reference-report reports/eval_queries_report.json`
9. `python scripts/validate_financial_metrics_gates.py reports/financial_metrics.json --out-json reports/financial_metrics.gates.json`
10. `python scripts/validate_financial_coverage_gates.py reports/financial_metrics.json --out-json reports/financial_metrics.coverage_gates.json`

Current passing gate set:
- Ruff gate across `autodev`, `financial-engine_v2/backend`, and `scripts`
- Pytest gate across `autodev/tests`, `financial-engine_v2/backend/tests`, and `scripts`
- Canonical dataset eval + canonical regression baseline gate
- Financial metrics hard gates
- Financial coverage gates

Operational notes:
- In restricted environments where socket creation is blocked, health/smoke can return `SKIP due restricted environment`; this is expected and non-fatal.
- Canonical dataset checks support CPU fallback by default (`REQUIRE_CUDA=0`), and only require GPU when `REQUIRE_CUDA=1`.
- Canonical regression depends on these baseline fixtures:
  - `reports/baselines/canonical_eval_baseline_latest.json`
  - `reports/news_eval_queries.json`
  - `reports/company_eval_queries.json`
  - `reports/eval_queries.json`
- Full runbook is in `docs/validation_baseline.md`.

## PDF Extraction Learning Loop

The extraction pipeline supports adaptive routing via a learning loop (`services/extraction/`). It optimizes method selection over time through metrics-based preference updates and periodic LLM skill reviews. Enable via `learning_loop.enabled = True` in pipeline orchestrator config. Design spec: `docs/superpowers/specs/2026-04-08-pdf-extraction-learning-loop-design.md`.

## System Contract

**[docs/architecture/SYSTEM_CONTRACT.md](docs/architecture/SYSTEM_CONTRACT.md)** is the authoritative specification for this system's data integrity, pipeline behavior, retrieval logic, model usage, and agent behavior.

All contributors and agents (Claude, Codex, or any other) MUST comply with this contract. Changes that violate it will be rejected. If in doubt, read the contract first.

---

## Scope
`financial-engine_v2/` is the primary live runtime.
Root `scripts/` still contains auxiliary pipelines, tests, and tooling, but it is not the main launcher surface for the active engine.

## Legacy scripts
Legacy root launcher scripts are archived in:
- `scripts/archive/legacy_root_20260218/`
