# Extraction Goal Proof Matrix V2

Job: `extraction_goal_proof_matrix_v2_20260529`

Generated: `2026-05-29T12:57:51Z`

Branch: `audit/extraction-goal-proof-matrix-v2-20260529`

Baseline audited: `migration/clean-runtime-baseline-reconstruct-v1` at
`7ee06fbdad5f954056981769eef3ba25bee86480`
(`milestone(extraction): block third canary on runtime preflight`).

Mode: SAFE EXTENSION, report-only.

## Decision

The active ten-item extraction goal is **not complete**.

Current baseline evidence proves several hardening slices, but not the full end
state. The approved third canary was not run because GPU health is still not
cleanly verifiable and loaded backend/worker code cannot be proven current
without a reload that the existing third-canary phrase does not authorize. Full
accurate extraction graduation remains unproven.

No runtime reload, canary run, `POST /api/process/document`, broad extraction,
backfill, production DB write, Qdrant/news/memory mutation, source-PDF mutation,
parser/prompt/gold-label/schema change, service/GPU/model config change,
Cockpit UI work, issue mutation, PR mutation, or GitHub comment was performed
by this task.

## Ten-Item Status

1. Preserve and publish current truth-gate patch: **partially proven**.
   Baseline contains `5788b18a` (`guard pre-canary truth persistence`) and
   subsequent integrated extraction hardening. Published PR state is still
   messy: #129 is green but draft, while #125-#128 remain stale/failing.
2. Move advisory blocking upstream into candidate selection: **proven for
   baseline scope**. Baseline contains `a64d2295`; focused tests cover
   advisory candidate exclusion.
3. Formalize source document classification: **proven for baseline scope**.
   `docs/extraction/metric_extraction_contract.md` documents
   `financial_report`, `advisory_only_document`, and `unknown_document`, with
   focused tests in `test_extraction_pre_canary_truth_gates.py`.
4. Implement Scale Policy V1: **proven for current policy slice**. Baseline
   contains `26ca0c4a`; focused tests cover units, millions/billions/trillions,
   and explicit IDR/Rp trillion handling without FX conversion.
5. Harden metric ontology: **partial**. `metric_ontology_v1` is documented and
   focused tests pass, but persisted metric schema alignment remains outside the
   completed baseline scope and #98 remains the policy boundary.
6. Harden period semantics: **proven for current AAU blocker scope**. Baseline
   contains `c45f8f57`; focused tests cover explicit source period-end evidence
   and period conflicts.
7. Build a real gold/eval corpus from canary failures: **partial**. AAU canary
   fixture work is represented on the audited baseline; PR #129 consolidates
   the BHP real-gold work with green checks but remains draft and unmerged. The
   broad real-gold eval file still fails the repo-relative 10X source-PDF
   assertion in this worktree.
8. Add pre-persistence scorecard gates: **proven as report-local gate**.
   Baseline contains `47508882`; the gate does not authorize canonical writes
   or broad backfills.
9. Run a third canary only under approval: **blocked before canary**. The
   approval phrase was received, but runtime preflight blocked execution. Direct
   `nvidia-smi` still fails with the GPU handle error.
10. Graduate to full accurate extraction: **not proven**. Requires successful
   approved canary execution, actual payload scorecard gates, resolution of
   source-reviewability/schema boundaries, and broader accuracy evidence.

## Current Runtime Evidence

- `/api/health`: `{"status":"ok"}`
- `/api/queue/status`: Redis connected, all queues `0`.
- `scripts/gpu_process_guard.sh --check`: exit `0` with repeated `nvidia-smi`
  query warnings.
- Direct `nvidia-smi`: exit `255`, `Unable to determine the device handle for
  GPU0000:25:00.0: Unknown Error`.
- Registry: one unrelated stale Query Orchestration job; no file overlap with
  this report task.

## Current PR Evidence

- PR #129 `[codex] consolidate BHP real-gold corpus baseline`: open draft,
  mergeable, `lint-and-test` success and `scan` success.
- PR #128 `[codex] resolve real-gold source path validation`: open draft,
  conflicting, `lint-and-test` failure and `scan` success.
- PR #127 `[codex] capture BHP canary eval regression`: open draft,
  conflicting, `lint-and-test` failure and `scan` success.
- PR #126 `[codex] exclude advisory canary candidates`: open draft, mergeable,
  `lint-and-test` failure and `scan` success.
- PR #125 `[codex] guard pre-canary truth persistence`: open draft, mergeable,
  `lint-and-test` failure, CodeQL failure, scan success.

This task did not comment on, close, retarget, mark ready, or edit any PR.

## Validation

Passed:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_goal_proof_matrix_v2_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_goal_proof_matrix_v2_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_goal_proof_matrix_v2_20260529.md --repo-root .`
- `gh pr list --state open --limit 10 --json number,title,isDraft,headRefName,baseRefName,mergeable,statusCheckRollup,updatedAt,url`
- `/api/health` and `/api/queue/status` read-only probes.
- `scripts/gpu_process_guard.sh --check` and direct `nvidia-smi` blocker probe.
- Focused extraction hardening suite:
  `227 passed in 2.33s`.

Known failing validation:

- `test_extraction_gold_eval.py`: `23 passed, 1 failed` on
  `test_load_real_gold_corpus_accepts_operating_cash_flow_alias_and_assets_exist`
  because the 10X source PDF is not present at the repo-relative
  `financial-engine_v2/data/asx/docs/...` path in this worktree.

Passed after report generation:

- JSON validation for `objective_matrix.json`, `status.json`, and
  `diff-check.json`.
- `git diff --check` and `git diff --cached --check`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_goal_proof_matrix_v2_20260529.md --repo-root .`
- Code-reviewer pass over the report-only diff: no critical, warning, or
  suggestion findings.
- `python3 scripts/agent_job_registry.py release extraction_goal_proof_matrix_v2_20260529 --repo-root .`

## Next Safe Step

Do not mark the goal complete. The next non-runtime cleanup is to explicitly
supersede or close out the stale extraction PR stack (#125-#128) in favor of the
green consolidated PR #129, but that should be done under a separate task card
that allows GitHub PR mutation.

The next runtime step remains blocked until GPU health is clean. After that,
create a fresh approval-required runtime task card that explicitly authorizes
only backend/worker/gpu_worker reload, proves loaded code, reruns queue/source
path/GPU gates, and submits the seven approved documents one at a time.
