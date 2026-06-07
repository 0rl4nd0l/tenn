---
job_id: extraction_post_pr301_candidate_exclusion_taxonomy_v1_20260607
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Query Orchestration
  - Provenance
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_post_pr301_candidate_exclusion_taxonomy_v1_20260607.md
  - reports/agent_jobs/extraction_post_pr301_candidate_exclusion_taxonomy_v1_20260607/README.md
  - reports/agent_jobs/extraction_post_pr301_candidate_exclusion_taxonomy_v1_20260607/source_classification_audit.json
  - reports/agent_jobs/extraction_post_pr301_candidate_exclusion_taxonomy_v1_20260607/status.json
  - reports/agent_jobs/extraction_post_pr301_candidate_exclusion_taxonomy_v1_20260607/validation.json
  - reports/agent_jobs/extraction_post_pr301_candidate_exclusion_taxonomy_v1_20260607/diff-check.json
  - reports/agent_jobs/extraction_post_pr301_candidate_exclusion_taxonomy_v1_20260607/raw_commands.log
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/scripts/broad_extraction_test.py
  - financial-engine_v2/scripts/test_broad_extraction_test.py
  - docs/extraction/metric_extraction_contract.md
  - docs/architecture/12_evaluation_and_drift_monitoring.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 14400
output_dir: reports/agent_jobs/extraction_post_pr301_candidate_exclusion_taxonomy_v1_20260607
mutation_mode: safe_extension
production_data_access: false
---

# Post-PR301 Candidate Exclusion Taxonomy

## Objective

Add narrow deterministic source-title/source-text exclusions for known
false-positive document classes so future bounded samples are less polluted,
while preserving valid financial-report candidates.

## Scope

Branch:
`safe/extraction-post-pr301-broad-accuracy-push-v1-20260607`.

Worktree:
`/home/l4nd0/tenn-post-pr301-broad-accuracy-push-v1-20260607`.

Mode: SAFE EXTENSION. Do not run a broad sample in this phase.

## Known Classes

- Meeting, AGM, proxy, and notice-of-meeting documents.
- Board-change notices.
- Operational project updates.
- Share-sale or gross-proceeds announcements.
- Pre-results or segment re-presentation documents.
- Obvious non-financial notices admitted by prior samples.

## Contract Check

Target system layer: extraction source-document classification and Evaluation
scorecard taxonomy.

Relevant contract rules: metric extraction must not infer or substitute values;
normalization may only convert explicit units; source-document classification
must stay deterministic and source-metadata bound.

What must not change: canonical metric ontology, source PDFs, prompts, gold
labels, schemas, runtime/model/GPU/service config, DB/Qdrant/news/memory stores,
and valid annual, half-year, Appendix 4C/4D/4E/5B, wrapper-report, or
financial-statement candidates.

Why safe: this repair only excludes source classes whose titles or first-page
source text clearly identify non-financial-report documents before extraction
candidate inclusion.

GPU process check required: no.

## Requirements

- Add only narrow source-title/source-text exclusions.
- Do not add broad fuzzy exclusions.
- Preserve valid annual, half-year, Appendix 4C/4D/4E/5B, financial statement,
  and wrapper-report candidates.
- Update candidate and scorecard reason taxonomy together.
- Add focused tests for each false-positive class and no-overblock tests for
  valid financial reports.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_post_pr301_candidate_exclusion_taxonomy_v1_20260607.md`
- Safe registry active-record inspection or `DATA_MISSING`.
- Focused pytest for source classification and taxonomy behavior.
- `python3 -m py_compile` for touched Python files.
- Ruff on touched Python files if available.
- JSON validation for report artifacts.
- `git diff --check`.
- `git diff --cached --check` if staging.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_post_pr301_candidate_exclusion_taxonomy_v1_20260607.md --repo-root .`
- Verify no source PDFs are staged.

## Final Report Requirements

Report audited evidence, rules added, tests run, validation status, files
touched, unsafe actions avoided, `DATA_MISSING`, and whether Milestone 3 may
proceed.
