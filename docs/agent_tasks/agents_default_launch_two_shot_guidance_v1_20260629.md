---
job_id: agents_default_launch_two_shot_guidance_v1_20260629
lane: Reporting
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/agents_default_launch_two_shot_guidance_v1_20260629
mutation_mode: safe_extension
production_data_access: false
closeout_scope: docs_only
allowed_files:
  - docs/agent_tasks/agents_default_launch_two_shot_guidance_v1_20260629.md
  - AGENTS.md
---

# Agents Default Launch And Two-Shot Guidance

## Objective

Update `AGENTS.md` so normal Tenn sessions start from `/home/l4nd0/tenn` as the
canonical launch path and so two-shot workstreams apply beyond Git Hygiene to
other non-trivial, high-risk, ambiguous, or multi-step Tenn work.

## Scope

- Docs-only Tenn control-plane instruction update.
- Keep the diff limited to `AGENTS.md` and this task card.
- Do not touch product, runtime, extraction, data, services, source PDFs, gold
  labels, prompts, DB, Qdrant, Redis, host-global files, or GitHub settings.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/agents_default_launch_two_shot_guidance_v1_20260629.md`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/agents_default_launch_two_shot_guidance_v1_20260629.md --no-write-report`
- `bash scripts/check_markdown_hygiene.sh`
- `git diff --check`

## Closeout Scope

Closeout scope: docs-only.
