# Ideation combinations — implementation program plan

> **For agentic workers:** Execute milestones in order unless noted. Use `ce:brainstorm` on a single milestone before large diffs. Checkbox steps (`- [ ]`) track progress. This plan **does not** replace `docs/superpowers/plans/2026-03-21-extraction-redesign.md`; it **coordinates** that work with real-gold gates, FX policy, and Cockpit/ops observability.

**Branch:** `plan/ideation-combinations-2026-04-11`  
**Ideation source:** `docs/ideation/2026-04-11-open-ideation.md`  
**Authority:** `docs/architecture/SYSTEM_CONTRACT.md` (single canonical pipeline, Cockpit as client only, no shadow extraction writers)

---

## Goals

| Program | Combination | Outcome |
|--------|-------------|---------|
| **Alpha** | #1 + #3 + #7 | Canonical multipass extraction fully aligned with approved redesign; real-gold quality gate; FX + fixture depth per `docs/architecture/16_currency_and_fx_policy.md` |
| **Beta** | #2 + #4 | Authoritative Cockpit contract + conformance audit; single operator runbook linking health, mutex, GPU guard, RAG stability, embed signals |

---

## Non-goals (both programs)

- No second production extraction pipeline or alternate DB upsert path for metrics (SYSTEM_CONTRACT).
- No Cockpit-side authoritative retrieval or direct Qdrant/Postgres reads for financial truth when backend is configured.
- No invented FX rates or overwriting native extracted values with converted numbers in the same column (FX policy).
- No bundling of unrelated cockpit-ui or intel-ops refactors into these milestones unless a contract line requires it.

---

## Recommended sequencing across programs

1. **Beta — Milestones A→C** (docs + audit matrix + runbook) first or in parallel with **Alpha — M1 audit** — low coupling, fast risk reduction for operators.
2. **Alpha — M1→M2** before relying on real-gold for merge gates.
3. **Alpha — M3** (failure classes) with **Beta** in maintenance mode (link runbook to real-gold script when M2 lands).
4. **Alpha — M4** (FX) only after explicit approval for any schema/migration work.
5. **Alpha — M5** (fixtures/thresholds) overlaps M3–M4; tighten thresholds after noise drops.

---

# Program Alpha — Extraction backbone + real-gold + FX/fixtures

**Spec / prior plan:** `docs/superpowers/specs/2026-03-21-extraction-redesign.md`, `docs/superpowers/plans/2026-03-21-extraction-redesign.md`  
**Eval / real-gold:** `docs/architecture/12_evaluation_and_drift_monitoring.md`, `scripts/run_real_extraction_eval.py`, `financial-engine_v2/backend/app/main.py` (`POST /api/extraction-eval/real-gold`), `financial-engine_v2/backend/app/services/extraction_gold_eval.py`  
**FX policy:** `docs/architecture/16_currency_and_fx_policy.md`

## Alpha — M1: Redesign closure and canonical path audit

- [ ] Produce a short **delta doc** (append to this plan or `docs/claude/STATE.md` excerpt): approved 2026-03-21 plan tasks vs current tree (what is done, what remains, what must not be deleted yet).
- [ ] Confirm `financial-engine_v2/backend/app/services/pipeline.py` delegates metric persistence through the **single** multipass path; no stray imports of legacy extraction for production upsert.
- [ ] `pytest financial-engine_v2/backend/tests/test_extraction_capability_guards.py` green.
- [ ] `pytest financial-engine_v2/backend/tests/test_multipass_extraction.py` `test_pipeline_stages.py` green.
- [ ] `python -m ruff check financial-engine_v2/backend` clean for touched files.

**Contract checkpoint:** One canonical extraction write path; structural vs semantic boundaries unchanged (SYSTEM_CONTRACT §2–3, §7–8).

## Alpha — M2: Real-gold gate — definition + automation shell

- [ ] Document gate semantics: metric scope, tolerances, corpus fingerprint, artifact layout (extend `12_evaluation_and_drift_monitoring.md` and/or `financial-engine_v2/data/extraction_gold_real/README.md`).
- [ ] Align `scripts/run_real_extraction_eval.py` with `POST /api/extraction-eval/real-gold` where practical (`REAL_GOLD_SUPPORTED_METRICS` and friends).
- [ ] Add or confirm **manual** `workflow_dispatch` CI job (optional schedule later) that uploads JSON/MD artifacts only — no destructive DB mutation.
- [ ] `pytest financial-engine_v2/backend/tests/test_extraction_gold_eval.py` green.

**Contract checkpoint:** Real-gold is measurement only; API key patterns unchanged; no silent semantic change to extraction.

## Alpha — M3: Failure-class remediation (net_debt, RIO / currency class)

- [ ] Targeted changes in `multipass_extraction.py` / `docling_extract.py` / eval comparison as needed; gold JSON updates only per corpus rules (PDF-sourced labels).
- [ ] Before/after report via `run_real_extraction_eval.py` (subset acceptable).
- [ ] Regression tests for fixed classes.

**Contract checkpoint:** §3.3 explicit values; §3.5 no fabrication; until M4, non-AUD handling follows FX policy (e.g. `ok_low_confidence` — no fake conversion).

## Alpha — M4: FX conversion (policy-compliant)

- [ ] Design sign-off: rate source, date alignment, storage shape (separate columns/tables per `16_currency_and_fx_policy.md`).
- [ ] Implement conversion + metadata; **do not** overwrite raw extracted metrics in place.
- [ ] Unit tests with mocked rates; integration tests avoid live FX provider dependency in CI.
- [ ] If schema changes: dedicated migration review (repo migration-reviewer / human).

**Contract checkpoint:** No gap-filling with invented rates; single canonical semantic path for stored facts.

## Alpha — M5: Fixture diversity + threshold matrix

- [ ] Expand `financial-engine_v2/backend/tests/eval_fixtures/` and/or real-gold toward 4D/4E/5B / broader IFRS shapes (proportionate to CI budget).
- [ ] Extend threshold config: distinguish **synthetic** gate (`eval_config.json`) vs **real-gold** thresholds (new file or section — avoid conflating lanes).
- [ ] Document runtime/cost for `live_eval` and real-gold in `docs/validation_baseline.md` or eval doc.

**Contract checkpoint:** Broader fixtures are regression signal, not a substitute for explicit metric rules.

---

# Program Beta — Cockpit contract + operator observability

**SYSTEM_CONTRACT:** §1.2 Cockpit role, §1.3 retrieval boundary  
**Signals:** `financial-engine_v2/cockpit/integrations/backend_api.py`, `financial-engine_v2/backend/app/routes/cockpit_api.py`, `cockpit-ui/app/api/cockpit/`, `financial-engine_v2/backend/app/services/router_state.py`, `scripts/gpu_process_guard.sh`, `financial-engine_v2/scripts/evaluate_rag_stability.py`

## Beta — Milestone A: Authoritative Cockpit contract doc

- [ ] Add **Cockpit contract** doc under `docs/architecture/` or `docs/ops/` (one home + cross-links from `SYSTEM_CONTRACT.md` §1.2 table).
- [ ] Cover: Python Cockpit (`BackendApiClient`), FastAPI `/api/cockpit/*`, Next.js BFF `/api/cockpit/*`, streaming event shapes for chat (pointer to `test_cockpit_api_chat_stream.py`), auth header names **without** secret values.
- [ ] Explicitly document **`GET /api/health`** vs **`GET /api/cockpit/health`** (liveness vs aggregated dependency view).

**Verification:** Peer review against SYSTEM_CONTRACT; no credentials in markdown.

## Beta — Milestone B: Conformance audit matrix

- [ ] Markdown table: contract requirement → implementation locations (TUI, `cockpit_api.py`, `cockpit-ui`, tests).
- [ ] Row-level outcome: **conform / intentional deviation / deprecate** with owner note.
- [ ] Reference extraction mutex fields from `GET /api/cockpit/config` (`router_state` / `cockpit_api.py`).

**Verification:** After any code change in this milestone, `pytest financial-engine_v2/backend/tests/test_cockpit_api_*.py` (relevant subset) green.

## Beta — Milestone C: Unified operator runbook

- [ ] New `docs/ops/` runbook (link-only table): API health, cockpit health, extraction activity, `gpu_process_guard.sh`, RAG stability outputs (`financial-engine_v2/reports/rag_stability/`), embed model / vector baseline pointers (`reports/runtime_embedding_model.txt`, `reports/vector_baseline.json` per existing docs).
- [ ] Call out **profile-dependent** steps (e.g. isolated vs full backend) so smoke runs are not misread.
- [ ] State supported consumer patterns: when to call backend `:8000` vs Next BFF.

**Verification:** Operator dry-run using only the runbook completes all rows.

## Beta — Milestone D (optional): Single-pane aggregator

- [ ] Thin CLI or minimal HTML that shells out / fetches **only** documented endpoints — no duplicate truth.
- [ ] If touching `cockpit-ui`, same PR updates contract + runbook when behavior changes.

---

## Open questions (human / product)

1. **FX:** Rate provider, rate type (daily close vs period end), licensing for automation.
2. **CI:** Self-hosted runner with llama vs local-only real-gold; corpus distribution for gitignored PDFs.
3. **Real-gold policy:** Block merge on regression vs alert-only; per-metric vs aggregate thresholds.
4. **Cockpit:** Canonical operator default for health (`/api/health` vs `/api/cockpit/health`) and external client patterns (direct backend vs Next).

---

## Verification commands (baseline)

```bash
python -m ruff check financial-engine_v2/backend financial-engine_v2/cockpit scripts
pytest financial-engine_v2/backend/tests/test_extraction_capability_guards.py financial-engine_v2/backend/tests/test_extraction_gold_eval.py -q
pytest financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py -q
```

Full backend suite and `bash financial-engine_v2/scripts/run_local_backend.sh` + `curl -sS http://127.0.0.1:8000/api/health` per `docs/entrypoints.md` before closing each major milestone.

---

## References

- `docs/ideation/2026-04-11-open-ideation.md`
- `docs/architecture/SYSTEM_CONTRACT.md`
- `docs/architecture/12_evaluation_and_drift_monitoring.md`
- `docs/architecture/16_currency_and_fx_policy.md`
- `docs/claude/STATE.md` (docs-governance / extraction-quality rows)
