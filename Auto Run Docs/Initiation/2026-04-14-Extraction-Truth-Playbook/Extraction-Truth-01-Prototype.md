# Phase 01: Runnable Truth Review Prototype

This phase delivers a backend-first extraction prototype that can be executed end to end without user decisions: the canonical backend boots, a limited real-gold extraction evaluation runs against the current corpus, flagged documents become reviewable through backend-owned review sessions, and the existing verification surface shows backend-authoritative truth rather than a parallel interpretation. By the end of the phase there must be a visible working loop the user can run and inspect.

## Tasks

- [x] Establish the reuse map and implementation boundary before changing code:
  - Search existing extraction and review surfaces first so this phase extends current behavior instead of recreating it: `financial-engine_v2/backend/app/services/multipass_extraction.py`, `extraction_eval.py`, `extraction_gold_eval.py`, `extraction_review.py`, `financial-engine_v2/backend/app/api/context.py`, `financial-engine_v2/backend/app/main.py`, `cockpit-ui/components/cockpit/verification/verification-screen.tsx`, and `scripts/run_real_extraction_eval.py`.
  - Write a structured Markdown artifact at `docs/ops/extraction-truth/phase-01-baseline.md` with YAML front matter (`type: report`, `tags: [extraction, eval, verification, backend-authority]`) capturing reusable entrypoints, contract-sensitive boundaries, prototype success criteria, and exact commands the later tasks will prove.
  - State explicitly in that artifact that backend APIs remain the only authority for extraction truth, confidence, provenance, and review state; Cockpit may display and orchestrate only.
  - Completed 2026-04-14: baseline written at `docs/ops/extraction-truth/phase-01-baseline.md`; reuse map confirms Phase 01 must extend the existing `/api/extraction-eval/real-gold`, `/api/extraction-review/*`, and `/api/context/verification` loop rather than creating a parallel evaluator or review path.

- [x] Make the real-gold prototype runnable through existing backend-owned entrypoints:
  - Reuse `/api/extraction-eval/real-gold` and `scripts/run_real_extraction_eval.py` instead of introducing a new eval path.
  - Tighten only the blocking gaps that prevent a small-corpus run from completing cleanly with stable JSON and Markdown outputs under the existing `reports/` locations.
  - Keep the implementation contract-safe: no schema change unless already unavoidable, no alternate financial store, no FX fabrication, and no client-side extraction logic.
  - Completed 2026-04-14: added shared worktree-aware real-gold path resolution so the existing backend endpoint and CLI runner can discover the canonical corpus and source PDFs from sibling git worktrees instead of aborting when the active code-edit worktree only has placeholder data files.
  - Validation 2026-04-14: `python -m pytest scripts/test_run_real_extraction_eval.py financial-engine_v2/backend/tests/test_real_gold_paths.py -q` passed (`12 passed`), `ruff check` passed on the touched files, and `scripts/run_real_extraction_eval.py --limit 1` now completes and writes JSON/Markdown/CSV artifacts while recording extraction configuration errors inside the report payload rather than crashing on missing corpus/PDF paths.
  - Completed 2026-04-14: aligned the runner with backend authority by making `scripts/run_real_extraction_eval.py` post to `/api/extraction-eval/real-gold` and persist the existing `reports/extraction_real_eval_*` artifacts from the backend response instead of re-running a separate local evaluator.
  - Validation 2026-04-14: `financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/app/main.py scripts/run_real_extraction_eval.py scripts/test_run_real_extraction_eval.py financial-engine_v2/backend/tests/test_extraction_gold_eval.py` passed, and `financial-engine_v2/.venv/bin/pytest -q financial-engine_v2/backend/tests/test_extraction_gold_eval.py scripts/test_run_real_extraction_eval.py` passed (`18 passed`).

- [x] Make flagged metrics reviewable from backend truth in the same prototype loop:
  - Reuse the extraction review service and existing `/api/extraction-review/*` surfaces before adding anything new.
  - Fill only the missing backend or UI glue required to load a review session for the evaluated runs, show provenance and snippet evidence, and persist review decisions or wrong-queue exports through backend-managed files.
  - If a display surface is missing data, add it to the backend response or typed client contract instead of deriving it inside Cockpit.
  - Completed 2026-04-14: `/api/extraction-eval/real-gold` now creates backend-owned review sessions for flagged real-gold documents and returns `review_session_id`/review metadata so Cockpit can open the existing `/api/extraction-review/session/{session_id}` flow without inventing a parallel review path.
  - Completed 2026-04-14: the Cockpit real-gold tab now exposes an `Open Review` action for flagged documents, which switches back into the review tab and loads backend-provided provenance/snippet evidence from the saved session.
  - Validation 2026-04-14: `financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/app/main.py financial-engine_v2/backend/app/services/extraction_review.py financial-engine_v2/backend/tests/test_extraction_gold_eval.py financial-engine_v2/backend/tests/test_extraction_review_service.py` passed, `financial-engine_v2/.venv/bin/pytest -q financial-engine_v2/backend/tests/test_extraction_gold_eval.py financial-engine_v2/backend/tests/test_extraction_review_service.py` passed (`29 passed`), `pnpm build` passed in `cockpit-ui/`, and `pnpm exec playwright test tests/verification.spec.ts --reporter=line` passed (`9 passed`).

- [x] Add targeted automated coverage for the prototype path:
  - Extend backend tests around the real-gold endpoint, extraction review session lifecycle, and any new error handling or response fields.
  - Extend Cockpit or `cockpit-ui` verification tests only if the prototype path changes those surfaces.
  - Search for existing test patterns first in `financial-engine_v2/backend/tests/test_extraction_gold_eval.py`, `test_extraction_review_service.py`, `test_cockpit_api_models.py`, and `cockpit-ui/tests/verification.spec.ts` before creating new test scaffolding.
  - Completed 2026-04-15: added backend coverage for real-gold review-session failure reporting and persisted review-session round-trip loading, plus verification UI coverage that real-gold rows without backend review sessions surface the fallback reason while only reviewable rows expose `Open Review`.
  - Validation 2026-04-15: `financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/tests/test_extraction_gold_eval.py financial-engine_v2/backend/tests/test_extraction_review_service.py` passed; `financial-engine_v2/.venv/bin/python -m pytest -q financial-engine_v2/backend/tests/test_extraction_gold_eval.py financial-engine_v2/backend/tests/test_extraction_review_service.py` passed (`31 passed`); `pnpm exec playwright test tests/verification.spec.ts --reporter=line` passed (`9 passed`).

- [ ] Run the prototype end to end and prove it works:
  - Use the canonical boot path: `financial-engine_v2/scripts/run_local_backend.sh`, then verify `curl -sS http://127.0.0.1:8000/api/health`.
  - Run a limited real-gold evaluation through the script and, where useful, through the backend API with a small `limit` so the result is fast and inspectable.
  - Load or create an extraction review session for at least one evaluated document and verify that the selected run exposes confidence, provenance, and snippet evidence from backend-owned data.

- [ ] Capture the working prototype outputs and checkpoint the milestone:
  - Write `docs/ops/extraction-truth/phase-01-prototype-report.md` with YAML front matter (`type: report`, `related: ['[[phase-01-baseline]]']`) summarizing what worked, which documents were evaluated, which items were reviewable, which gaps were explicitly quarantined for later phases, and links to generated `reports/` artifacts.
  - If this phase reaches a working milestone, create the required milestone commit using the repo’s `milestone(<subsystem>): ...` format with tested evidence from the commands and tests above.
