---
job_id: issue_281_lint_gate_resolution_review_v1_20260611
owner: Codex
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
status: approved
approval_required: true
allow_unapproved_safe_extension: false
mutation_mode: audit_only
production_data_access: false
output_dir: reports/agent_jobs/issue_281_lint_gate_resolution_review_v1_20260611
allowed_files:
  - docs/agent_tasks/issue_281_lint_gate_resolution_review_v1_20260611.md
  - reports/agent_jobs/issue_281_lint_gate_resolution_review_v1_20260611/README.md
  - reports/agent_jobs/issue_281_lint_gate_resolution_review_v1_20260611/ISSUE_REFRESH.md
  - reports/agent_jobs/issue_281_lint_gate_resolution_review_v1_20260611/EVIDENCE.md
  - reports/agent_jobs/issue_281_lint_gate_resolution_review_v1_20260611/CLOSEOUT_PACKET.md
  - reports/agent_jobs/issue_281_lint_gate_resolution_review_v1_20260611/GITHUB_APPROVAL_PACKET.md
  - reports/agent_jobs/issue_281_lint_gate_resolution_review_v1_20260611/DATA_MISSING.md
  - reports/agent_jobs/issue_281_lint_gate_resolution_review_v1_20260611/VALIDATION.md
timeout_seconds: 3600
---

# Issue 281 Lint Gate Resolution Review

## Objective

Verify whether issue #281 is already satisfied by current CI, documentation, and
dependency evidence. Produce a closeout packet and stop before GitHub mutation.

## Evidence To Refresh

- GitHub issue #281 state, labels, body, and comments.
- `.github/workflows/ci.yml` Ruff step.
- `docs/validation_baseline.md` Ruff command and tool pin note.
- `financial-engine_v2/backend/requirements.txt` Ruff pin.
- `requirements.txt` include chain, if needed.
- Any open PRs that mention Ruff, lint, type gates, or #281.

## Allowed Actions

- Read repo control-plane, CI, docs, and dependency files needed to verify #281.
- Write the report files listed in `allowed_files`.
- Run task-card validation and whitespace checks.
- Optionally run `python -m ruff --version` only if the local environment already
  has dependencies available.

## Forbidden Actions

- Do not edit `.github/workflows/ci.yml`, requirements, docs, backend, scripts,
  product/runtime/data/extraction files, prompts, source PDFs, gold labels, DB,
  Qdrant, news, memory, services, model/GPU config, or production data.
- Do not install dependencies.
- Do not run full Ruff, pytest, product/runtime/extraction validation, service
  starts, backfills, or broad tests.
- Do not commit, push, merge, rebase, cherry-pick, reset, stash, clean, delete
  branches, remove worktrees, or mutate GitHub.
- Do not comment on or close issue #281 without explicit owner approval.

## Acceptance Criteria

- Evidence states whether #281 acceptance criteria appear satisfied,
  partially satisfied, stale, blocked, or `DATA_MISSING`.
- If satisfied, produce a GitHub approval packet with proposed comment/close
  text but do not send it.
- If not satisfied, draft the next implementation task-card candidate with exact
  allowed files and owner approval requirements.
- Record all validation commands and exit statuses.

## Phase 3 Stop State

Expected stop state: `WAITING_ON_USER` for GitHub close/comment approval if #281
is satisfied, or `DONE_WITH_RISK` if evidence is incomplete.
