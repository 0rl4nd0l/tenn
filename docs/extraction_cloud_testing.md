# Extraction Cloud Testing

## Lane

This repo supports an `eval-only` cloud setup for extraction testing.

It does not currently provide a safe, repo-portable full extraction cloud bootstrap.

## Scope

Use `bash scripts/setup_eval_cloud.sh` when you need a cloud/dev environment that can:

- install the authoritative Tenn Python manifests
- run targeted extraction-eval unit tests
- run deterministic scorecard CLIs
- optionally install dev-only eval helpers for DuckDB or MLflow artifact analysis

This setup intentionally does not:

- start `llama-server`
- configure Qdrant, Redis, or Postgres
- provision host-local GGUF models
- depend on `financial-engine_v2/.env` secrets
- claim live extraction eval readiness

## Why Eval-Only

Confirmed repo evidence points to the evaluation lane as the safe cloud target:

- Authoritative manifests are already rooted in `requirements.txt`, which includes `financial-engine_v2/backend/requirements.txt` and `financial-engine_v2/worker/requirements.txt`.
- CI installs `pip install -r requirements.txt` and runs pytest without any full extraction runtime bootstrap. See `.github/workflows/ci.yml`.
- Deterministic scorecard entrypoints already exist:
  - `financial-engine_v2/scripts/extraction_eval_scorecard.py`
  - `financial-engine_v2/scripts/extraction_gold_eval_scorecard.py`
- The real-gold eval runner is an evaluation tool, not a runtime/bootstrap path:
  - `scripts/run_real_extraction_eval.py`
  - `scripts/run_real_extraction_eval_mlflow.py`
  - `scripts/analyze_real_extraction_eval_duckdb.py`

Confirmed repo evidence does not support a portable full extraction cloud bootstrap:

- Full extraction depends on `llama.cpp` topology rules and canonical ports `8001` / `8002`. See `docs/architecture/SYSTEM_CONTRACT.md` and `scripts/run_llama_server.sh`.
- The canonical local llama.cpp setup assumes host-local model paths such as `/mnt/nvme/tenn/models` and optional host override file `~/.config/tenn/llama-server.env`.
- The deprecated dedicated extraction launcher still assumes a local GGUF path and port `8002`. See `scripts/run_extraction_server.sh`.
- Real live extraction eval requires local PDFs that are gitignored under `financial-engine_v2/data/asx/docs/` or `financial-engine_v2/data/extraction_gold_real/`. See `docs/architecture/12_evaluation_and_drift_monitoring.md`.
- The Docker path is host-networked and mounts host-local model directories into the backend container, which is not a generic cloud bootstrap. See `financial-engine_v2/docker-compose.yml`.
- Docling GPU guidance is Tesla M40 and local-venv specific, with CPU fallback documented as a runtime workaround rather than a cloud bootstrap contract. See `docs/ops/docling_gpu_tesla_m40.md`.

## Authoritative Inputs

Confirmed manifests:

- `requirements.txt`
- `financial-engine_v2/backend/requirements.txt`
- `financial-engine_v2/worker/requirements.txt`
- optional: `financial-engine_v2/backend/requirements-dev.txt`

Confirmed bootstrap/install paths already in repo:

- `README.md`
- `financial-engine_v2/README.md`
- `.github/workflows/ci.yml`
- `financial-engine_v2/backend/Dockerfile`

## Supported Commands

Minimal setup:

```bash
bash scripts/setup_eval_cloud.sh
```

Include DuckDB / MLflow helpers:

```bash
bash scripts/setup_eval_cloud.sh --with-dev
```

Include Playwright Chromium for broader repo workflows:

```bash
bash scripts/setup_eval_cloud.sh --with-playwright
```

Reuse an existing venv and only validate:

```bash
bash scripts/setup_eval_cloud.sh --skip-install
```

## What The Script Validates

The script runs only deterministic evaluation checks that do not require local runtime services:

- `financial-engine_v2/backend/tests/test_extraction_eval_harness.py`
- `financial-engine_v2/backend/tests/test_extraction_gold_eval.py`
- `scripts/test_run_real_extraction_eval.py`
- `financial-engine_v2/scripts/extraction_eval_scorecard.py --indent 0`

These checks validate the evaluation harness, trust/scorecard helpers, and the real-eval runner's local auth/bootstrap behavior without running live extraction.

## Live Eval Requirements

Confirmed live extraction eval remains local-runtime dependent:

- `pytest -m live_eval financial-engine_v2/backend/tests/test_extraction_eval.py`
- `scripts/run_real_extraction_eval.py`

These require some combination of:

- reachable `llama.cpp` endpoint on `LLAMACPP_URL` or `EXTRACTION_LLAMACPP_URL`
- valid `LLM_API_KEY` or `OPENAI_API_KEY`
- local PDFs under the gitignored data paths
- docling / PyMuPDF runtime dependencies
- model availability matching `EXTRACT_MODEL`

Because those dependencies are host-local and partially secret-bearing, they are intentionally out of scope for `setup_eval_cloud.sh`.

## Recommendation

Use the eval-only script for cloud PRs, CI-like validation, and scorecard work.

Keep full extraction testing on a prepared local/runtime host until the repo gains a clearly documented, portable contract for:

- model provisioning
- PDF corpus availability
- secret injection
- llama.cpp startup ownership
- GPU vs CPU expectations
