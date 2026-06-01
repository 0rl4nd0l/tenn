---
job_id: extraction_broad_robustness_after_candidate_scale_followup_v1_20260601
lane: Evaluation
supporting_lanes:
  - Financial Truth
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_broad_robustness_after_candidate_scale_followup_v1_20260601.md
  - docs/claude/STATE.md
  - reports/agent_jobs/extraction_broad_robustness_after_candidate_scale_followup_v1_20260601/README.md
  - reports/agent_jobs/extraction_broad_robustness_after_candidate_scale_followup_v1_20260601/status.json
  - reports/agent_jobs/extraction_broad_robustness_after_candidate_scale_followup_v1_20260601/validation.json
  - reports/agent_jobs/extraction_broad_robustness_after_candidate_scale_followup_v1_20260601/diff-check.json
  - reports/agent_jobs/extraction_broad_robustness_after_candidate_scale_followup_v1_20260601/preflight.json
  - reports/agent_jobs/extraction_broad_robustness_after_candidate_scale_followup_v1_20260601/runtime_startup.json
  - reports/agent_jobs/extraction_broad_robustness_after_candidate_scale_followup_v1_20260601/runtime_shutdown.json
  - reports/agent_jobs/extraction_broad_robustness_after_candidate_scale_followup_v1_20260601/broad_sample_stdout.txt
  - reports/agent_jobs/extraction_broad_robustness_after_candidate_scale_followup_v1_20260601/broad_sample_results.json
  - reports/agent_jobs/extraction_broad_robustness_after_candidate_scale_followup_v1_20260601/broad_sample_summary.json
  - reports/agent_jobs/extraction_broad_robustness_after_candidate_scale_followup_v1_20260601/failure_digest.json
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_broad_robustness_after_candidate_scale_followup_v1_20260601
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
operator_approval_source: User approved full production runtime necessary to complete the extraction goal and then said "you may launch"; this card is bounded to one report-only post-fix broad robustness sample with runtime cleanup.
---

# Extraction Broad Robustness After Candidate Scale Followup V1

## Objective

Run one bounded, deterministic broad extraction robustness sample after
`181ff690` landed meeting/proxy notice exclusion, non-financial operational
update exclusion, and Appendix 4C USD thousand scale detection.

This is not a gold accuracy run. The helper has no ground truth and does not
authorize canonical writes, canary promotion, broad backfill, or full extraction
graduation.

## Session Declaration

- Agent: Codex.
- Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Intended files: only this task card, `docs/claude/STATE.md`, and this report
  bundle.
- Contested surfaces touched: none by file edit.
- Collision risk: MEDIUM/HIGH by Financial Truth runtime semantics, resolved by
  exact allowlist, active registry claim, GPU guards, and report-only execution.
- Decision: proceed in SAFE EXTENSION MODE after validation and claim.

## Contract Check

- Target layer: Evaluation tooling around Extraction.
- Relevant rules: backend remains authoritative for canonical financial truth;
  metric extraction must not infer or substitute; source PDFs are read-only;
  evaluation artifacts do not authorize canonical writes.
- What must not change: backend canary/process routes, parser prompts, schemas,
  source PDFs, database/Qdrant/news/memory stores, Cockpit UI, GitHub state, or
  production data.
- Why safe: the sample directly exercises existing extraction code through a
  report-only helper and writes only local report artifacts.
- GPU process check required: yes. Run `scripts/gpu_process_guard.sh --check`
  before startup and clean up the llama router/GPU activity token afterward.

## Required Execution

- Validate and claim this task card.
- Confirm no active conflicting jobs.
- Confirm GPU/process/port guards are clear.
- Start only the local llama router needed by the broad helper.
- Run:
  `financial-engine_v2/.venv/bin/python financial-engine_v2/scripts/broad_extraction_test.py --count 8 --seed 20260601 --docs-root /data/asx/docs --output-dir reports/agent_jobs/extraction_broad_robustness_after_candidate_scale_followup_v1_20260601`
- Preserve stdout, full JSON result, summary, and a failure digest in this
  report bundle.
- Stop the llama router and clear GPU guard state.

## Forbidden

- Backend startup, `POST /api/process/document/{document_id}`,
  `/api/extraction-eval/real-gold`, canary execution, broad backfill, direct
  SQL, source-PDF copy/mutation, parser/prompt/schema changes, Qdrant or
  embedding writes, Cockpit UI changes, GitHub mutation, and production
  datastore mutation.

## Required Validation

- Task-card validation and registry claim.
- Runtime preflight artifact.
- Broad sample artifact parse via JSON tooling.
- Task-card `check-diff`.
- `git diff --check` and `git diff --cached --check`.
- Registry release after commit.
