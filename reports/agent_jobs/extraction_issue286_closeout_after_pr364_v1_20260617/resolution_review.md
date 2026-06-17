# Issue 286 Resolution Review

Date: 2026-06-17

Issue: #286 `[Financial Truth] Add field-level provenance and accounting number parsing to extraction outputs`

Verdict: PASS_CLOSEOUT

Classification: ROOT_CAUSE_FIXED, READY_TO_CLOSE

## Evidence Matrix

| Acceptance / scope | Evidence | Grade | Decision |
| --- | --- | --- | --- |
| Issue #286 is open and asks for persisted traceability plus accounting-number parsing | `gh issue view 286` body and comments | VERIFIED | closeout review applies |
| PR #364 is merged | `gh pr view 364` state `MERGED`, merged at `2026-06-17T00:45:34Z`, merge commit `f6b8a606d391f7e040aa97746098a981edb49841` | VERIFIED | persistence boundary landed |
| Canonical contains PR #364 | `git merge-base --is-ancestor f6b8a606d391f7e040aa97746098a981edb49841 origin/migration/clean-runtime-baseline-reconstruct-v1` | VERIFIED | merged work is visible on canonical |
| Accounting number parsing | PR #349 merged, CI green; `test_pass3a_parses_common_accounting_number_strings` exists; report validation records RED then GREEN | VERIFIED | satisfied |
| Payload-level `field_provenance` | PR #350 merged, CI green; `test_pass4_emits_structured_field_provenance_for_metrics` exists; report validation records RED then GREEN | VERIFIED | satisfied |
| Consumers prefer structured field provenance | PR #351 merged, CI green; provenance adapter, extraction eval, and review tests exist; report validation records RED then GREEN | VERIFIED | satisfied |
| Persisted per-metric provenance | PR #364 merged, CI green; `ASXPeriodicFinancial.metric_provenance` model column, Alembic `0009_metric_provenance`, and `_upsert_financial_rows` wiring exist | VERIFIED | satisfied |
| Persisted provenance only for written metrics | `test_upsert_persists_metric_field_provenance_for_written_values` verifies revenue provenance persists and null/absent metrics do not | VERIFIED | satisfied |
| Existing extraction tests still pass | PR #364 `lint-and-test` success on head `5b20299a`; log recorded 3077 backend tests passed plus 89 autodev tests passed | VERIFIED | satisfied |
| Active registry conflict | read-only registry reports `active_jobs: []` | VERIFIED | no conflict |
| Task ledger | live and committed ledger files unavailable | DATA_MISSING | bounded fallback evidence is sufficient for closeout; no implementation starts |

## Reviewer Passes

### Root Cause Reviewer

The issue had two root causes: extraction output lacked deterministic field-level evidence, and persisted financial rows could not retain per-metric provenance. PRs #349, #350, #351, and #364 address the mechanism across parser/payload/consumer/persistence layers, not a ticker-specific symptom.

Decision: ROOT_CAUSE_FIXED.

### Regression Reviewer

The merged changes are class-level and covered by focused tests plus green PR CI. No broad extraction/backfill was run or required for closeout. Existing extraction test suites passed in CI after PR #364.

Decision: READY_TO_CLOSE.

### Boundary Reviewer

This closeout mutates only report/task-card artifacts locally and issue #286 on GitHub if accepted. No product/runtime/data/extraction files are changed in this closeout run. No DB, Qdrant, Redis, news, memory, source PDFs, gold labels, prompts, runtime, model/GPU, or service config is touched.

Decision: PASS.

### Financial Truth / Provenance Reviewer

The resulting path carries structured provenance from extraction payloads into persisted `ASXPeriodicFinancial.metric_provenance` keyed by metric. The focused persistence test verifies document id, extraction run id, page, row reference/excerpt, scale, currency, period evidence, and null-metric exclusion for persisted provenance.

Decision: PASS_CLOSEOUT.

### Skeptic / Opposition Reviewer

Strongest reason to keep open: issue body also suggested avoiding weaker/null overwrites. Current #286 acceptance criteria do not explicitly require overwrite precedence, and the merged persistence test ensures provenance does not get stored for null metric values. If overwrite precedence becomes a separate production-readiness concern, it should be tracked as a separate bounded issue rather than keeping #286 open after its stated acceptance criteria are satisfied.

Decision: no blocking remaining gap for #286.

## Final Arbitration

All explicit acceptance criteria are satisfied:

- each persisted metric can trace to document/run/source excerpt/page when available;
- common accounting formats are covered;
- existing extraction tests pass.

Close gate: COMPLETED_WITH_EVIDENCE.
