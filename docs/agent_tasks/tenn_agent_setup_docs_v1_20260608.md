---
job_id: tenn_agent_setup_docs_v1_20260608
lane: Evaluation
owner: Codex
allowed_files:
  - AGENTS.md
  - docs/agent_tasks/tenn_agent_setup_docs_v1_20260608.md
  - docs/agents/issue-tracker.md
  - docs/agents/triage-labels.md
  - docs/agents/domain.md
  - reports/agent_jobs/tenn_agent_setup_docs_v1_20260608/README.md
approval_required: true
timeout_seconds: 1200
output_dir: reports/agent_jobs/tenn_agent_setup_docs_v1_20260608
mutation_mode: safe_extension
production_data_access: false
---

# Tenn Agent Setup Docs V1

## Objective

Add Tenn-specific `docs/agents/` configuration for generic engineering skills
that expect an issue tracker, triage label vocabulary, and domain-doc layout.
This is inspired by Matt Pocock's `setup-matt-pocock-skills`, but must not
import its default labels or generic mutation posture into Tenn.

## Scope

Allowed:

- Add `docs/agents/issue-tracker.md`.
- Add `docs/agents/triage-labels.md`.
- Add `docs/agents/domain.md`.
- Add a short `AGENTS.md` pointer to those docs.
- Add a closeout report under `reports/agent_jobs/`.

Forbidden:

- Product, runtime, data, extraction, prompt, gold-label, DB, Qdrant, Redis,
  news, memory, source-PDF, backfill, service, model, or GPU mutation.
- GitHub issue, label, PR, or branch mutation beyond an explicitly approved
  scoped branch/PR for this docs-only slice.
- Dependency installs.
- Generic Matt Pocock label defaults such as `needs-triage`, `needs-info`, or
  `ready-for-agent` unless they are explicitly mapped to existing Tenn labels.
- Running extraction samples, broad extraction, count-24, count-32, or backfill.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/tenn_agent_setup_docs_v1_20260608.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/tenn_agent_setup_docs_v1_20260608.md --no-write-report`
- Final `git status --short --untracked-files=all`

No runtime or extraction tests are required because this is a docs/control-plane
configuration slice only.
