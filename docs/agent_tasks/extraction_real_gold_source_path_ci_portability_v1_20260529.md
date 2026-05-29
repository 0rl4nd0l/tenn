---
job_id: extraction_real_gold_source_path_ci_portability_v1_20260529
lane: Evaluation
supporting_lanes:
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_real_gold_source_path_ci_portability_v1_20260529.md
  - reports/agent_jobs/extraction_real_gold_source_path_ci_portability_v1_20260529/README.md
  - reports/agent_jobs/extraction_real_gold_source_path_ci_portability_v1_20260529/status.json
  - reports/agent_jobs/extraction_real_gold_source_path_ci_portability_v1_20260529/diff-check.json
  - docs/claude/STATE.md
  - financial-engine_v2/backend/tests/test_extraction_gold_eval.py
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_real_gold_source_path_ci_portability_v1_20260529
mutation_mode: safe_extension
production_data_access: false
related_issue: 96
---

# Extraction Real-Gold Source Path CI Portability V1

## Objective

Repair the relevant GitHub Actions failure on PR #128 without weakening source
truth locally. GitHub-hosted CI does not have the host-mounted ASX source PDF
tree, so `test_extraction_gold_eval.py` must not require `/data/asx/docs` by
default. It must still validate that corpus source paths are local, PDF-shaped,
and allowlisted, and it must support an explicit strict source-asset mode for
local/operator validation.

## Scope

- Primary lane: Evaluation.
- Supporting lane: Provenance.
- Branch: `safe/extraction-real-gold-source-path-resolver-v1-20260529`.
- Base PR: https://github.com/0rl4nd0l/tenn/pull/128
- Mode: SAFE EXTENSION.

## Contract Check

- Target system layer: Evaluation/Provenance test behavior for real-gold corpus
  validation.
- Relevant contract rules: source evidence must remain explicit and
  auditable; missing source assets must be surfaced as `DATA_MISSING` rather
  than fabricated; no extraction or persistence path may infer facts from
  missing evidence.
- What must not change: production extraction/backfill behavior, DB/Qdrant/news
  /memory stores, source PDFs, canonical financial truth rows, parser routing,
  extraction prompts, runtime/model/GPU/service config, schemas, Cockpit UI,
  and GitHub issue state.
- Why safe: this task only makes the test distinguish metadata safety from
  host-local source-file availability. Strict openability remains available
  through an explicit environment gate and is run in local validation.
- GPU process check required: no. This task does not start, stop, restart, or
  depend on `llama-server`.

## Required Behavior

- Default CI mode:
  - load the real-gold corpus;
  - preserve operating-cash-flow alias validation;
  - validate every `source_file` through the allowlisted resolver;
  - accept resolver `FileNotFoundError` as environment `DATA_MISSING` only.
- Strict local mode:
  - when `TENN_REQUIRE_REAL_GOLD_SOURCE_ASSETS=1`, fail if any corpus source
    file is missing from all allowlisted source roots.
- Do not catch `ValueError` or `PermissionError`; unsafe or malformed paths must
  still fail.

## Forbidden

- Runtime reload, canary, extraction, or backfill.
- Production DB writes or direct SQL mutation.
- Qdrant, news, memory, source-PDF, or canonical-truth mutation.
- Parser routing, extraction prompt, gold-label, schema, runtime/model/GPU
  config, or Cockpit UI changes.
- GitHub issue comment/close/label/milestone mutation.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_real_gold_source_path_ci_portability_v1_20260529.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_real_gold_source_path_ci_portability_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_real_gold_source_path_ci_portability_v1_20260529.md --repo-root .`
- `python -m pytest -q financial-engine_v2/backend/tests/test_extraction_gold_eval.py`
- `TENN_REQUIRE_REAL_GOLD_SOURCE_ASSETS=1 python -m pytest -q financial-engine_v2/backend/tests/test_extraction_gold_eval.py`
- Ruff and `py_compile` for touched test file.
- JSON validation for report artifacts.
- `git diff --check`.
- Source PDF/new binary staging check.
- Task-card `check-diff`.
- Registry release and final read-only status.

## Final Report Requirements

Report branch, PR, exact CI failure addressed, files changed, validation
commands/results, confirmation that strict source-asset validation still passes
locally, confirmation that no runtime/canary/datastore/source mutation occurred,
and remaining blockers.
