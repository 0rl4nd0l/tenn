---
job_id: extraction_post_pr299_accepted_output_audit_v1_20260606
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_post_pr299_accepted_output_audit_v1_20260606.md
  - reports/agent_jobs/extraction_post_pr299_accepted_output_audit_v1_20260606/README.md
  - reports/agent_jobs/extraction_post_pr299_accepted_output_audit_v1_20260606/integration_review.json
  - reports/agent_jobs/extraction_post_pr299_accepted_output_audit_v1_20260606/accepted_output_audit.json
  - reports/agent_jobs/extraction_post_pr299_accepted_output_audit_v1_20260606/source_evidence.json
  - reports/agent_jobs/extraction_post_pr299_accepted_output_audit_v1_20260606/status.json
  - reports/agent_jobs/extraction_post_pr299_accepted_output_audit_v1_20260606/validation.json
  - reports/agent_jobs/extraction_post_pr299_accepted_output_audit_v1_20260606/diff-check.json
  - reports/agent_jobs/extraction_post_pr299_accepted_output_audit_v1_20260606/raw_commands.log
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 14400
output_dir: reports/agent_jobs/extraction_post_pr299_accepted_output_audit_v1_20260606
mutation_mode: safe_extension
production_data_access: false
---

# Post-PR299 Accepted-Output Audit

## Objective

Review and locally integrate the post-PR299 broad-accuracy push branch if clean,
then audit the accepted count-16 outputs for DXC, LBL, and AZJ to decide
whether they are truth-safe, report-only, need quarantine, or need a narrow
repair.

## Scope

Source worktree:
`/home/l4nd0/tenn-post-pr299-broad-accuracy-push-v1-20260606`.

Source branch:
`safe/extraction-post-pr299-broad-accuracy-push-v1-20260606`.

Integration worktree:
`/home/l4nd0/tenn-post-pr299-integration-accepted-output-audit-v1-20260607`.

Integration branch:
`integrate/extraction-post-pr299-accepted-output-audit-v1-20260607`.

Mode: RESULT REVIEW -> ACCEPTED OUTPUT AUDIT.

Risk: HIGH for financial truth.

## Input Evidence

- Source branch final commit:
  `55209fb52c31661f00d35db8044efdf9456195cc`.
- Source branch known commits:
  - `9c9107bb`: candidate-exclusion taxonomy repair.
  - `12e60429`: exactly-one count-16 validation.
  - `e9703b3c`: failure taxonomy plus selected-table scale repair.
  - `55209fb5`: final closeout commit.
- Remote canonical branch at review start:
  `origin/migration/clean-runtime-baseline-reconstruct-v1`.
- Count-16 sample result:
  `ok=9`, `ok_low_confidence=0`, `failed=7`, `exceptions=0`.

## Contract Check

Target system layer: extraction source classification, table-scale binding,
accepted-output audit evidence, and optional quarantine/validation gates.

Relevant contract rules: canonical financial values must be explicit,
source-bound, deterministic, auditable, and provenance-linked. LLM outputs do
not define canonical financial truth. Do not relax truth gates or infer
financial values from narrative/disclosure text.

What must not change: source PDFs, prompts, gold labels, schemas, runtime/model/
GPU/service configuration, DB/Qdrant/news/memory stores, broad extraction
sample size, full ticker-universe extraction, or backfill behavior.

Why safe: Phase 1 integration is a clean fast-forward in an isolated worktree;
Phase 2 audits existing count-16 artifacts and source PDFs read-only. A code
change is allowed only for one narrow source-bound fix or quarantine behavior
if the accepted-output evidence is clear and covered by tests.

GPU process check required: no. This task does not run count-24/count-32, broad
extraction, backfill, or a random sample rerun.

## Required Integration Review

- Confirm baseline, source, and integration worktree path, branch, HEAD, remote,
  status, canonical branch, and registry state.
- Inspect source branch commits and diff scope.
- Confirm changed files are scoped to extraction candidate taxonomy,
  selected-table scale repair, tests, docs, task cards, and reports.
- Stop on conflicts or unrelated dirt.
- If clean, integrate via a local clean fast-forward/cherry-pick/PR-equivalent
  branch according to repo convention.
- Validate after integration with focused pytest, py_compile, ruff if
  available, JSON validation, git diff checks, task-card check-diff, no source
  PDFs staged, and registry/list-active evidence.
- Do not run another sample.

## Required Accepted-Output Audit

Audit the accepted count-16 outputs for:

- DXC
- LBL
- AZJ

For each document, identify exact document ID, source path, title, accepted
status, extracted metrics, source row labels, source table/page evidence,
selected table scale, document-level scale, period, currency, and
confidence/trust state.

Classify each accepted output as one or more of:

- truth-safe;
- ok but report-only;
- needs quarantine;
- scale-binding bug;
- rounding-policy issue;
- selected-table mismatch;
- `DATA_MISSING`.

## Repair Rules

Implement at most one narrow source-bound fix only if it is clear and testable.
Otherwise produce a containment or repair prompt. Do not implement broad
inference, broad fuzzy exclusions, relaxed truth gates, prompt changes, schema
changes, or datastore mutation.

## Hard Stops

- No count-24 or count-32.
- No random sample rerun.
- No broad extraction or backfill.
- No production DB/Qdrant/news/memory mutation.
- No source PDF edits.
- No prompt, gold-label, runtime, model, GPU, or schema changes.
- No unrelated cleanup, reset, stash, branch deletion, rebase, or dirty parent
  merge.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_post_pr299_accepted_output_audit_v1_20260606.md`
- JSON validation for generated report artifacts.
- Focused pytest if code changed.
- `python3 -m py_compile` if code changed.
- Ruff on touched Python files if available and code changed.
- `git diff --check`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_post_pr299_accepted_output_audit_v1_20260606.md --repo-root .`
- Verify no source PDFs are staged.
- Registry/list-active evidence.

## Final Report Requirements

Report integration result, accepted-output audit table for DXC/LBL/AZJ, whether
any accepted rows are unsafe, whether quarantine is required, whether count-24
is justified, remaining `DATA_MISSING`, validation results, files touched,
unsafe actions avoided, and explicit confirmation that no broad extraction,
backfill, count-24/count-32, random sample rerun, or full ticker extraction ran.
