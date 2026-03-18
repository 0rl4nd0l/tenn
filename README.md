# TENN

Current active runtime is `financial-engine_v2`.

## Lightweight Execution Workflow
- Track live work state in `STATE.md`.
- Use phase gates in `docs/phase_checklist.md`.
- Keep both files updated during runs and before handoff.

## Run in 3 steps
1. Create/activate your main venv at repo root.
2. Install deps:
   - `pip install -r requirements.txt`
   - `python -m playwright install chromium`
3. Run:
   - `python run.py`

That single command delegates to `financial-engine_v2/run.py`, where defaults are hardcoded.

## Runtime workflow map (financial-engine_v2)
- `full_history`: `financial-engine_v2/scripts/full_history_ticker_sync.py`
- `daily_marketindex`: `financial-engine_v2/scripts/daily_marketindex_action.py`
- `daily_asx_marketwide`: `financial-engine_v2/scripts/daily_asx_marketwide_action.py`
- Additional bulk workflows:
  - `financial-engine_v2/scripts/asx_enrichment_sweep_action.py`
  - `financial-engine_v2/scripts/run_asx_enrichment_chunked.py`
  - `financial-engine_v2/scripts/probe_all_system_tickers.py`

For detailed flags, runbooks, marker states, and API surface, use:
- `financial-engine_v2/README.md`

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
