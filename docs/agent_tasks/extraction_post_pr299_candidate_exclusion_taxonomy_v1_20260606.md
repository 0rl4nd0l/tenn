---
job_id: extraction_post_pr299_candidate_exclusion_taxonomy_v1_20260606
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Query Orchestration
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_post_pr299_candidate_exclusion_taxonomy_v1_20260606.md
  - reports/agent_jobs/extraction_post_pr299_candidate_exclusion_taxonomy_v1_20260606/README.md
  - reports/agent_jobs/extraction_post_pr299_candidate_exclusion_taxonomy_v1_20260606/source_classification_audit.json
  - reports/agent_jobs/extraction_post_pr299_candidate_exclusion_taxonomy_v1_20260606/status.json
  - reports/agent_jobs/extraction_post_pr299_candidate_exclusion_taxonomy_v1_20260606/validation.json
  - reports/agent_jobs/extraction_post_pr299_candidate_exclusion_taxonomy_v1_20260606/diff-check.json
  - reports/agent_jobs/extraction_post_pr299_candidate_exclusion_taxonomy_v1_20260606/raw_commands.log
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/scripts/broad_extraction_test.py
  - financial-engine_v2/scripts/test_broad_extraction_test.py
  - docs/extraction/metric_extraction_contract.md
  - docs/architecture/12_evaluation_and_drift_monitoring.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 14400
output_dir: reports/agent_jobs/extraction_post_pr299_candidate_exclusion_taxonomy_v1_20260606
mutation_mode: safe_extension
production_data_access: false
---

# Post-PR299 Candidate Exclusion Taxonomy

## Objective

Add narrow deterministic source-classification exclusions for known
false-positive document classes from the post-PR297 taxonomy:

- meeting or proxy notices;
- board-change notices;
- operational project updates;
- share-sale or gross-proceeds announcements;
- pre-results or segment re-presentation documents.

## Scope

Branch:
`safe/extraction-post-pr299-broad-accuracy-push-v1-20260606`.

Worktree:
`/home/l4nd0/tenn-post-pr299-broad-accuracy-push-v1-20260606`.

Mode: AUDIT FIRST / SAFE EXTENSION. Do not run a broad sample in this phase.

## Contract Check

Target system layer: Extraction source-document classification and Evaluation
scorecard taxonomy.

Relevant contract rules: metric extraction must not infer or substitute values;
normalization may only convert explicit units; backend extraction remains the
authority; source-document classification must stay deterministic and
source-metadata bound.

What must not change: canonical metric ontology, source PDFs, prompts, gold
labels, schemas, runtime/model/GPU/service config, DB/Qdrant/news/memory stores,
and valid annual, half-year, Appendix 4C/4D/4E/5B, or financial-statement
candidates.

Why safe: the intended repair only excludes source classes whose titles or
source text clearly identify non-financial-report documents before extraction
candidate inclusion.

GPU process check required: no. This phase does not start or depend on
llama-server.

## Requirements

- Audit the five known false-positive docs: EQR AGM/proxy-style material, MAH
  operational project update, FCL board-change notice, HRZ share-sale/gross
  proceeds announcement, and MPL pre-results/segment re-presentation document.
- Add narrow title/source-text rules only where the class is clear.
- Preserve valid annual, half-year, Appendix 4C/4D/4E/5B, and
  financial-statement candidates.
- Update candidate and scorecard reason taxonomy together.
- Add focused tests proving false positives are excluded and valid reports are
  not overblocked.
- Do not run a sample in this phase.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_post_pr299_candidate_exclusion_taxonomy_v1_20260606.md`
- Safe registry/list-active check or `DATA_MISSING`.
- Focused pytest for source classification and taxonomy behavior.
- `python3 -m py_compile` for touched Python files.
- Ruff on touched Python files if available.
- JSON validation for report artifacts.
- `git diff --check`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_post_pr299_candidate_exclusion_taxonomy_v1_20260606.md --repo-root .`
- Verify no source PDFs are staged.
- Commit if validation is clean.

## Final Report Requirements

Report audited document evidence, rules added, tests run, validation status,
files touched, unsafe actions avoided, `DATA_MISSING`, and whether Phase 2 is
allowed to proceed.
