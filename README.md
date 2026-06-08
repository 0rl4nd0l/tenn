# TENN

Current active runtime is `financial-engine_v2`.

## Canonical Execution (Agents)

Canonical entrypoint documentation: `docs/entrypoints.md`.

Short boot sequence:
1. `pip install -r requirements.txt`
2. `bash financial-engine_v2/scripts/run_local_backend.sh`
3. `bash financial-engine_v2/scripts/smoke_local.sh`

Note: `python run.py` is **NOT** the canonical startup path for agents (it is a batch runner).

## Lightweight Execution Workflow
- Track live work state in `STATE.md`.
- Use phase gates in `docs/phase_checklist.md`.
- Keep both files updated during runs and before handoff.

## Batch workflow runner

Use this only when you intentionally want to run configured ingestion workflows.
For backend/API startup, use the canonical execution path above.

1. Create/activate your main venv at repo root.
2. Install deps:
   - `pip install -r requirements.txt`
   - `python -m playwright install chromium`
3. Run:
   - `python run.py`

That command delegates to `financial-engine_v2/run.py`, where workflow defaults
are hardcoded.

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
