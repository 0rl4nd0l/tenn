# HANDOFF — tooling-install-v2 + storage-migration-followup (2026-04-07)

**Branch:** `cloud/session-20260319`

---

## Completed

| Item | Status | Evidence |
|------|--------|----------|
| pandera[pydantic]>=0.19.0 | INSTALLED v0.30.1 | ExtractionOutputSchema (25 cols) loads cleanly |
| exchange_calendars>=4.0 | INSTALLED v4.13.2 | XASX smoke test passes (Australia Day correct) |
| yfinance | ALREADY IN requirements.txt | `yfinance>=0.2.40` already at line 34 |
| import-linter>=2.1 | INSTALLED | In requirements-dev.txt; design doc produced |
| KV cache flags | ALREADY SET | `--cache-type-k q8_0 --cache-type-v q8_0` at run_llama_server.sh:113 |
| pypdfium2 | ALREADY INSTALLED | v5.6.0 via docling transitive dep |
| Tenn runtime-data moved to NVMe | COMPLETE | `.env.local` now points at `/mnt/nvme/tenn/runtime-data` |
| Root Ollama store archived/pruned | COMPLETE | keep-set reduced to `qwen2.5:32b` and `gpt-oss:20b-cloud`; archive saved under `.archives/ollama-root-store-2026-04-07` |

## Skipped

| Item | Reason |
|------|--------|
| N-gram spec decoding (--spec-type ngram-simple) | :8001 not running at session time. Cannot add flag or benchmark without live server. |

**Action needed for ngram spec:** When :8001 is next started:
1. Add `--spec-type ngram-simple` to `scripts/run_llama_server.sh` after the KV cache flags (line 113)
2. Restart :8001, confirm health
3. Run eval: `pytest backend/tests/test_extraction_eval.py::test_live_eval_accuracy_against_fixtures -m live_eval -v`
4. Spot-check one chat request for quality (eval only covers extraction, not chat)
5. If post-score < pre-score by >2pp: revert flag

## Files Created

- `backend/app/services/validation/__init__.py`
- `backend/app/services/validation/extraction_schemas.py` — pandera schema (NOT activated)
- `backend/app/utils/__init__.py`
- `backend/app/utils/trading_calendar.py` — XASX trading day utilities (4 functions)
- `backend/requirements-dev.txt` — dev-only deps (import-linter)
- `docs/architecture/import_linter_design.md` — layer → package mapping for import-linter config
- `scripts/migrate_runtime_to_nvme.sh` — migrate Tenn runtime-data and repo GGUFs onto `/mnt/nvme/tenn`
- `scripts/archive_prune_root_ollama_store.py` — archive inactive root Ollama models to HDD and prune the root store keep-set
- `.archives/ollama-root-store-2026-04-07/archive-summary.json` — archived inactive root Ollama manifests/blobs inventory

## Files Modified

- `backend/requirements.txt` — added pandera[pydantic]>=0.19.0, exchange_calendars>=4.0

## Verification

- ruff check: new files clean (0 errors)
- pytest: 401 passed, 0 failures (non-eval suite, 678s)
- XASX smoke test: Australia Day 2024 correctly identified as non-trading
- storage validation: `/mnt/nvme` free space improved to ~`59G`; root Ollama store reduced to ~`19G`
- workload validation: docs-heavy local validation kept `/proc/pressure/io avg10` in the low single digits and `vmstat wa` near `1%` after warm-up

## Eval Baseline

- Last successful: 58.33% (2026-03-24T07:15:44Z)
- Most recent: 0.0% (2026-03-31T23:45:50Z) — server down, not regression
- Gate threshold: 85% (unmet — pre-existing)
- This session did NOT touch extraction pipeline; no eval regression possible

## Deferred Workstreams

| Workstream | Why Deferred | Scope |
|------------|-------------|-------|
| nomic-embed-text v1.5 | Full Qdrant rebuild + downtime window | 1 session |
| GBNF JSON Schema enforcement | Pydantic schema design per extraction pass | 1-2 sessions |
| import-linter config | services/ is flat — split needed first (see design doc) | 1 session |
| pyasx + company master table | New companies model + Alembic migration | 1 session |
| ASIC short positions | Greenfield: model + migration + ASIC provider | 1 session |
| OpenFIGI | Greenfield: model + migration + API client | 1 session |
| AZJ CID-font encoding | PDF lacks ToUnicode CMap — research problem, not parser swap | Indefinite |

## Next Session Candidates

1. **N-gram spec decoding** — start :8001, add flag, benchmark eval + chat
2. **Eval baseline investigation** — 58.33% → target 85%+
3. **import-linter config** — review design doc, decide services/ split
4. **Unified schema migration** — companies + instrument_identifiers (enables pyasx, OpenFIGI)

---

## Storage Migration Update (2026-04-07)

Completed host-local storage work:

- migrated Tenn runtime data to `/mnt/nvme/tenn/runtime-data`
- migrated GGUF llama.cpp router assets to `/mnt/nvme/tenn/models`
- updated `financial-engine_v2/.env.local` to point runtime data and docs paths at NVMe
- kept llama.cpp as the primary Tenn serving path
- pruned root Ollama store to retain only `qwen2.5:32b` and `gpt-oss:20b-cloud`
- archived inactive root Ollama models to `/mnt/sdb2/home/l4nd0/tenn/.archives/ollama-root-store-2026-04-07`

Validation summary:

- docs-heavy local validation workload against `/mnt/nvme/tenn/runtime-data/asx/docs` no longer reproduced the earlier severe IO pressure
- `/proc/pressure/io avg10` remained in the low single digits during validation instead of the earlier 50+ spikes
- `vmstat wa` settled around 1% after warm-up

Operational notes:

- isolated-profile backend validation may still fall back to `/tmp/financial-engine_v2-fe_local_runtime.db` for a writable SQLite runtime DB
- post-cleanup host free space is roughly `59G` on NVMe, so the system is healthier but still not spacious
