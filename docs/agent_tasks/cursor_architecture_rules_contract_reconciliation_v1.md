---
job_id: cursor_architecture_rules_contract_reconciliation_v1
lane: Evaluation
requested_primary_lane: Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/cursor_architecture_rules_contract_reconciliation_v1.md
  - reports/agent_jobs/cursor_architecture_rules_contract_reconciliation_v1/
  - reports/agent_jobs/cursor_architecture_rules_contract_reconciliation_v1/README.md
  - reports/agent_jobs/cursor_architecture_rules_contract_reconciliation_v1/status.json
  - reports/agent_jobs/cursor_architecture_rules_contract_reconciliation_v1/validation.json
  - reports/agent_jobs/cursor_architecture_rules_contract_reconciliation_v1/diff-check.json
  - .claude/commands/architecture-check.md
  - .claude/commands/architecture-cleanup.md
  - .claude/commands/function-quality.md
  - .claude/commands/repo-audit.md
  - docs/claude/commands.md
  - AGENTS.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/cursor_architecture_rules_contract_reconciliation_v1
mutation_mode: safe_extension
production_data_access: false
---

# Cursor Architecture Rules Contract Reconciliation V1

Resolve GitHub issue #139 by retiring stale command/documentation references to missing `.cursor/rules` architecture rule files and pointing agents at the authoritative Tenn system contract.

## Scope

- Update current agent and Claude command docs that still require `.cursor/rules`.
- Preserve architecture enforcement by routing checks to `docs/architecture/SYSTEM_CONTRACT.md` and relevant `docs/architecture/*.md` documents.
- Record `.cursor/rules` as `DATA_MISSING`, not restored from fabricated content.

## Forbidden

- No backend/runtime/frontend product code changes.
- No DB/Qdrant/news/memory writes.
- No canonical financial truth, parser routing, extraction prompt, or gold-label changes.
- No recreated `.cursor/rules` files unless tracked source content is found.
- No historical report rewrites.
- No unrelated dirty work.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cursor_architecture_rules_contract_reconciliation_v1.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cursor_architecture_rules_contract_reconciliation_v1.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cursor_architecture_rules_contract_reconciliation_v1.md`
- `rg` proving active agent and command docs no longer require `.cursor/rules`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cursor_architecture_rules_contract_reconciliation_v1.md`
