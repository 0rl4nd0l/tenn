# Troubleshooting

## 401 embedding or LLM auth errors

- Confirm `LLM_API_KEY` matches the local OpenAI-compatible server expectation.
- If you use separate embedding auth, verify the embedding server accepts the same token or set the appropriate embedding-specific auth env in your runtime.
- Re-run `python scripts/check_environment.py` to confirm the resolved endpoints are the ones you expect.

## Missing collections or empty retrieval

- Check `QDRANT_URL` and confirm Qdrant is reachable on `6333`.
- Confirm the configured collection name still matches the runtime expectation.
- If `ENABLE_QDRANT=false`, retrieval-dependent routes will degrade or return empty results by design.

## Port conflicts

- `8001` is reserved for llama.cpp (canonical LLM endpoint).
- `6333` is reserved for Qdrant.
- `6379` is reserved for Redis.
- `11434` is reserved for Ollama.
- If a port is already taken, change the env var and the service startup command together. Do not change code defaults in one place only.

## Venv issues

- Activate the venv you want to use before running scripts.
- The active scripts now expect `python` on `PATH` instead of `.venv/bin/python`.
- If `python` is missing, activate the intended venv and retry.

## DATA_ROOT issues

- `DATA_ROOT` must be writable.
- `docs_root`, analyzer reports, SQLite defaults, MarketIndex defaults, and Cockpit backend artifacts (reports/exports, feedback bundles, memory stores) derive from `DATA_ROOT`.
- If you move `DATA_ROOT`, either keep the derived defaults or override the dependent paths explicitly in `financial-engine_v2/.env`.
- If Cockpit loads config from an unexpected root, set `COCKPIT_REPO_ROOT` explicitly and confirm `COCKPIT_CONFIG` resolves to the intended file (for Docker this is commonly `/config/cockpit.yaml`).

## Safe degradation rules

- Missing env vars fall back to defaults.
- Unreachable optional endpoints should degrade gracefully instead of hard-crashing.
- `ROUTER_FEEDBACK_ENABLED=false` disables analyzer feedback without changing routing code.
