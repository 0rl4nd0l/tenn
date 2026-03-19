# Architecture Stewardship Archive Manifest (2026-03-09)

This archive captures legacy or redundant scripts moved during the stewardship cleanup pass.

## Files moved

- `auto_self_train_financial_extractor.py` — no active references found; training/retrain orchestration path appears superseded by current metric extraction + validation flows.
- `ocl-aliases.sh` — developer convenience script with no active runtime/docs references.
- `run_extraction_quality_cycle.sh` — legacy workflow wrapper no longer used by CI, open loops, or active operator docs.
- `run_review_with_retrain.sh` — legacy batch loop wrapper not referenced by active orchestration.
- `test_local_codex_agent.py` — test utility not part of active runtime and not referenced by CI.
- `test_news_pipeline_ingest.py` — targeted test utility not referenced by active runtime and not covered by required CI paths.

## Rationale

- Preserve historical context while removing active-directory noise for operator navigation.
- Keep `financial-engine_v2` and root orchestration scripts as the canonical runtime surface.
