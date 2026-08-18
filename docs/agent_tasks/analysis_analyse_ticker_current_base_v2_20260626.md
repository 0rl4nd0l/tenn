---
job_id: analysis_analyse_ticker_current_base_v2_20260626
lane: Query Orchestration
supporting_lanes:
  - Evaluation
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/analysis_analyse_ticker_current_base_v2_20260626.md
  - financial-engine_v2/backend/app/modules/orchestrator.py
  - financial-engine_v2/backend/tests/test_analysis_modules.py
  - reports/agent_jobs/analysis_analyse_ticker_current_base_v2_20260626/README.md
  - reports/agent_jobs/analysis_analyse_ticker_current_base_v2_20260626/STATE.md
  - reports/agent_jobs/analysis_analyse_ticker_current_base_v2_20260626/VALIDATION.md
  - reports/agent_jobs/analysis_analyse_ticker_current_base_v2_20260626/status.json
  - reports/agent_jobs/analysis_analyse_ticker_current_base_v2_20260626/diff-check.json
  - reports/agent_jobs/analysis_analyse_ticker_current_base_v2_20260626/PR_BODY.md
  - reports/agent_jobs/analysis_analyse_ticker_current_base_v2_20260626/REVIEW.md
approval_required: true
approval_reference: "User requested safe issue fixing and closeout."
timeout_seconds: 14400
output_dir: reports/agent_jobs/analysis_analyse_ticker_current_base_v2_20260626
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: push_branch_open_pr_and_close_issue253_if_gated
---

# Analyse Ticker Current Base V2

## Objective

Fix issue #253 from current canonical by making the documented
`analyse_ticker()` helper instantiate `TickerContextLoader` before calling
`load()`.

## Scope

- Repair `financial-engine_v2/backend/app/modules/orchestrator.py`.
- Add a focused regression in
  `financial-engine_v2/backend/tests/test_analysis_modules.py`.
- Preserve existing analysis module behavior outside the entrypoint wiring.
- Publish and merge only after focused validation and GitHub checks pass.
- Close issue #253 only after canonical merge containment is verified.

## Forbidden

- DB, Qdrant, Redis, news, memory, source-document, prompt, parser,
  gold-label, migration, service, model, GPU, or config changes.
- Broad analysis-module rewrites.
- Branch deletion, pruning, reset, stash, rebase, cherry-pick, forced push, or
  unrelated cleanup.
- Issue close before canonical containment is verified.

## Validation

- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-issue253-analyse-ticker-current-base-v2-20260626 --topic "issue 253 analyse ticker current base repair" --json`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/analysis_analyse_ticker_current_base_v2_20260626.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/analysis_analyse_ticker_current_base_v2_20260626.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/analysis_analyse_ticker_current_base_v2_20260626.md --repo-root .`
- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_analysis_modules.py -q`
- `uv run --with ruff ruff format --check financial-engine_v2/backend/app/modules/orchestrator.py financial-engine_v2/backend/tests/test_analysis_modules.py` (non-gating observation only; canonical files require broad pre-existing reformat, so final diff keeps minimal style-preserving scope)
- `uv run --with ruff ruff check financial-engine_v2/backend/app/modules/orchestrator.py financial-engine_v2/backend/tests/test_analysis_modules.py`
- `python3 -m py_compile financial-engine_v2/backend/app/modules/orchestrator.py financial-engine_v2/backend/tests/test_analysis_modules.py`
- `git diff --check`
- `python3 -m json.tool reports/agent_jobs/analysis_analyse_ticker_current_base_v2_20260626/status.json`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/analysis_analyse_ticker_current_base_v2_20260626.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/analysis_analyse_ticker_current_base_v2_20260626.md --repo-root .`

## Done Criteria

- `analyse_ticker()` no longer calls `load()` as an unbound class method.
- The helper constructs `TickerContextLoader` with the analysis RAG callback.
- Local and GitHub validation pass.
- Issue #253 is closed only after the merged commit is verified contained in
  canonical.
