# TENN

Current active runtime is `financial-engine_v2`.

## Canonical Execution (Agents)

Canonical entrypoint documentation: `docs/entrypoints.md`.

Short boot sequence:
1. `pip install -r requirements.txt`
2. `pip install -r financial-engine_v2/backend/requirements.txt`
3. `bash financial-engine_v2/scripts/run_local_backend.sh`
4. `bash financial-engine_v2/scripts/smoke_local.sh`

Note: `python run.py` is **NOT** the canonical startup path for agents (it is a batch runner).

## Lightweight Execution Workflow
- Track live work state in `STATE.md`.
- Use phase gates in `docs/phase_checklist.md`.
- Keep both files updated during runs and before handoff.

## Run the backend in 3 steps
1. Create/activate the shared venv at repo root (`/workspace/.venv` in Cursor Cloud)
   and ensure `financial-engine_v2/.venv` exists or symlinks to it.
2. Install deps:
   - `pip install -r requirements.txt`
   - `pip install -r financial-engine_v2/backend/requirements.txt`
   - `python -m playwright install chromium` (needed for MarketIndex PDF downloads)
3. Run and validate the canonical backend:
   - `bash financial-engine_v2/scripts/run_local_backend.sh`
   - `bash financial-engine_v2/scripts/smoke_local.sh`

The backend is considered up when `GET /api/health` responds. The canonical local
mode uses SQLite, sync tasks, and disables embeddings, extraction, and Qdrant by
default.

## Batch runner
`python run.py` delegates to `financial-engine_v2/run.py` and runs configured
batch workflows such as full-history ingestion, daily MarketIndex collection,
or daily ASX market-wide ingestion.
Use it when you explicitly want those workflows; it is not the deterministic
system startup path.

## Isolated AU News Collector (`newspaper4k`)
For a separate, research-only AU finance article collector, use:
- `integrations/newspaper4k_au/`
- setup and run instructions: `integrations/newspaper4k_au/README.md`

This integration is optional and isolated from the default runtime.

## Legacy scripts
Old root scripts are archived in:
- `scripts/archive/legacy_root_20260218/`

## Local Coding LLM Router
Use a small local coding model for token-heavy/simple tasks, with automatic tiering.

Quick examples:
- `python3 scripts/local_coding_router.py "Summarize and reformat this patch diff..."`
- `python3 scripts/local_coding_router.py --route simple --prompt-file ./my_prompt.txt`
- `cat ./my_prompt.txt | python3 scripts/local_coding_router.py --print-meta`

Useful flags:
- `--route auto|simple|standard|deep|fallback`
- `--model <name>` to force a specific local model
- `--num-ctx <n>` to cap context window
- `--num-predict <n>` to cap output tokens

Defaults are tuned for this host:
- `simple`: `qwen2.5-coder:7b`
- `standard`: `llama3.1:8b`
- `deep`: `qwen2.5:32b`
- `fallback`: `phi3:mini`
