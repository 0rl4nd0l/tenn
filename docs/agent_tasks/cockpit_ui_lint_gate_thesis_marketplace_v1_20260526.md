---
job_id: cockpit_ui_lint_gate_thesis_marketplace_v1_20260526
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_ui_lint_gate_thesis_marketplace_v1_20260526.md
  - reports/agent_jobs/cockpit_ui_lint_gate_thesis_marketplace_v1_20260526/README.md
  - reports/agent_jobs/cockpit_ui_lint_gate_thesis_marketplace_v1_20260526/status.json
  - reports/agent_jobs/cockpit_ui_lint_gate_thesis_marketplace_v1_20260526/validation.json
  - reports/agent_jobs/cockpit_ui_lint_gate_thesis_marketplace_v1_20260526/diff-check.json
  - cockpit-ui/components/cockpit/thesis-audit/thesis-audit-screen.tsx
  - cockpit-ui/components/cockpit/marketplace/mission-screen.tsx
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/cockpit_ui_lint_gate_thesis_marketplace_v1_20260526
mutation_mode: safe_extension
production_data_access: false
---

# Cockpit UI Lint Gate Thesis And Marketplace

Safe-extension task for issue #89.

## Lane

Primary lane: Evaluation.

## Objective

Restore the Cockpit UI lint gate by fixing the known Thesis Audit and
Marketplace lint violations without disabling rules globally or refactoring
unrelated UI.

## Scope

Allowed:

- Create this task card and report artifacts.
- Update `cockpit-ui/components/cockpit/thesis-audit/thesis-audit-screen.tsx`
  for the unescaped quote and unused catch variable lint violations.
- Update `cockpit-ui/components/cockpit/marketplace/mission-screen.tsx` for
  the listing media image lint violation while preserving real listing media.

Forbidden:

- Do not change backend/runtime/data/memory/extraction surfaces.
- Do not change canonical financial truth, parser routing, prompts, gold
  labels, model/runtime/GPU/service config, or production data.
- Do not disable lint rules globally or hide unrelated warnings.
- Do not replace real listing media with placeholder-only UI.
- Do not touch unrelated dirty work.

## Acceptance Criteria

- `corepack pnpm --dir cockpit-ui exec eslint app components lib tests --max-warnings=0` passes.
- Marketplace listing media rendering remains real media backed by the listing URL when present.
- Any lint exception is local and documented rather than global.
- No unrelated UI refactor is included.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_ui_lint_gate_thesis_marketplace_v1_20260526.md --write-report`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_ui_lint_gate_thesis_marketplace_v1_20260526.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_ui_lint_gate_thesis_marketplace_v1_20260526.md`
- `corepack pnpm --dir cockpit-ui exec eslint app components lib tests --max-warnings=0`
- Focused rendered or static validation if Marketplace media behavior changes.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_ui_lint_gate_thesis_marketplace_v1_20260526.md`
- release the registry claim before final report
