---
job_id: extraction_broad_robustness_docs_root_v1_20260601
lane: Evaluation
supporting_lanes:
  - Financial Truth
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_broad_robustness_docs_root_v1_20260601.md
  - financial-engine_v2/scripts/broad_extraction_test.py
  - financial-engine_v2/scripts/test_broad_extraction_test.py
  - docs/claude/STATE.md
  - reports/agent_jobs/extraction_broad_robustness_docs_root_v1_20260601/README.md
  - reports/agent_jobs/extraction_broad_robustness_docs_root_v1_20260601/status.json
  - reports/agent_jobs/extraction_broad_robustness_docs_root_v1_20260601/validation.json
  - reports/agent_jobs/extraction_broad_robustness_docs_root_v1_20260601/diff-check.json
  - reports/agent_jobs/extraction_broad_robustness_docs_root_v1_20260601/source_inventory.json
  - reports/agent_jobs/extraction_broad_robustness_docs_root_v1_20260601/focused_test_stdout.txt
  - reports/agent_jobs/extraction_broad_robustness_docs_root_v1_20260601/ruff_stdout.txt
  - reports/agent_jobs/extraction_broad_robustness_docs_root_v1_20260601/py_compile_stdout.txt
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_broad_robustness_docs_root_v1_20260601
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
---

# Extraction Broad Robustness Docs Root V1

## Objective

Unblock broader extraction robustness evidence by making
`financial-engine_v2/scripts/broad_extraction_test.py` discover source PDFs
from the active docs root instead of only the empty repo-local
`financial-engine_v2/data/asx/docs` tree.

This is report/evaluation plumbing only. It does not run extraction, start
runtime services, submit canary documents, write canonical financial rows, copy
source PDFs, or mutate data stores.

## Session Declaration

- Agent: Codex.
- Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Intended files: only this task card, the broad robustness script, its focused
  test, the report bundle, and `docs/claude/STATE.md`.
- Contested surfaces touched: none from AGENTS.md.
- Collision risk: MEDIUM because this supports extraction evaluation, resolved
  by exact allowlist and no runtime/datastore mutation.
- Decision: proceed in SAFE EXTENSION MODE after validation and claim.

## Contract Check

- Target layer: Evaluation tooling around metric extraction.
- Relevant rules: backend remains the sole authority for canonical financial
  truth; extraction must not infer or substitute values; source PDFs remain
  read-only inputs; evaluation artifacts must not authorize canonical writes.
- What must not change: parser routing, prompts, schema, source PDFs, runtime
  services, model/GPU config, database/Qdrant/news/memory stores, Cockpit UI,
  or GitHub state.
- Why safe: the change only makes a robustness helper resolve the same host
  docs roots already used by backend configuration. It still produces
  robustness evidence only, not accuracy or persistence approval.
- GPU process check required: no. This task does not start, restart, or depend
  on llama-server.

## Required Implementation

- Support explicit `--docs-root`.
- Respect `DOCS_ROOT` and `DATA_ROOT` when choosing the source PDF root.
- Fall back to the repo-local root and then `/data/asx/docs` when no explicit
  root is supplied.
- Avoid crashing when the repo-local docs root is missing or empty.
- Preserve stable source-path identifiers for external `/data/asx/docs` files.
- Add focused tests for root resolution, discovery, and record path rendering.

## Forbidden

- Runtime backend startup, llama/router/worker startup, canary execution,
  broad extraction run, backfill, direct SQL, source-PDF copy/mutation,
  parser/prompt/schema changes, Qdrant or embedding writes, Cockpit UI changes,
  GitHub mutation, and production datastore mutation.

## Required Validation

- Task card validation and registry claim.
- Focused pytest for the new broad robustness script tests.
- Targeted Ruff for touched Python files.
- `py_compile` for touched Python files.
- Source-root inventory probe that counts repo-local and host docs roots
  without opening PDFs.
- `python3 scripts/agent_job_contract.py check-diff <this card>`.
- `git diff --check` and `git diff --cached --check`.
- Registry release after commit.
