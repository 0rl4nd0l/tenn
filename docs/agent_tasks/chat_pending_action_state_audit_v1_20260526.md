---
job_id: chat_pending_action_state_audit_v1_20260526
lane: Query Orchestration
supporting_lanes:
  - Reporting
owner: Codex
mutation_mode: safe_extension
production_data_access: false
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/chat_pending_action_state_audit_v1_20260526
allowed_files:
  - docs/agent_tasks/chat_pending_action_state_audit_v1_20260526.md
  - cockpit-ui/tests/chat-browser-regression.spec.ts
  - reports/agent_jobs/chat_pending_action_state_audit_v1_20260526/README.md
  - reports/agent_jobs/chat_pending_action_state_audit_v1_20260526/status.json
  - reports/agent_jobs/chat_pending_action_state_audit_v1_20260526/validation.json
  - reports/agent_jobs/chat_pending_action_state_audit_v1_20260526/diff-check.json
  - reports/agent_jobs/chat_pending_action_state_audit_v1_20260526/browser_regression_route_parity.md
inspect_only_surfaces:
  - cockpit-ui/components/cockpit/chat/chat-screen.tsx
  - cockpit-ui/components/cockpit/chat/terminal-message.tsx
  - cockpit-ui/components/cockpit/chat/terminal-message.test.tsx
  - /home/l4nd0/.gemini/tmp/tenn-nvme-clean-baseline-reconstruct-v1/ui-audit-gemini-20260526/audit-results.json
  - /home/l4nd0/.gemini/tmp/tenn-nvme-clean-baseline-reconstruct-v1/ui-audit-gemini-20260526/chat-2.png
github_issue: 120
---

# Task: chat_pending_action_state_audit_v1_20260526

## Objective
Audit and lock regression coverage for GitHub issue #120:
`[Query Orchestration] Pending action proposal can block the next normal chat prompt`.

## Execution Posture
- SAFE EXTENSION.
- Prefer test/report-only work if current code already satisfies the expected behavior.
- Do not mutate backend, runtime, data stores, Qdrant, news stores, memory stores, extraction, parser routing, prompts, gold labels, or model/GPU/service config.
- Do not weaken required confirmation for real mutating actions.

## Expected Behavior
1. A normal prompt submitted while an action proposal is visible must complete as a separate chat turn.
2. The pending action must not run from the normal prompt.
3. Explicit `Confirm` / `Cancel` controls must remain the only way to act on the proposed action.
4. If implementation is needed, keep it scoped to the chat pending-action state path and add regression coverage first.

## Allowed Scope
- Add this task card.
- Add the report bundle under `reports/agent_jobs/chat_pending_action_state_audit_v1_20260526/`.
- Add focused regression coverage in `cockpit-ui/tests/chat-browser-regression.spec.ts`.
- Inspect the current chat UI state code and Gemini audit evidence.

## Required Output
- `reports/agent_jobs/chat_pending_action_state_audit_v1_20260526/README.md`
- `reports/agent_jobs/chat_pending_action_state_audit_v1_20260526/status.json`
- `reports/agent_jobs/chat_pending_action_state_audit_v1_20260526/validation.json`
- `reports/agent_jobs/chat_pending_action_state_audit_v1_20260526/diff-check.json`
- `reports/agent_jobs/chat_pending_action_state_audit_v1_20260526/browser_regression_route_parity.md`

## Validation
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/chat_pending_action_state_audit_v1_20260526.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/chat_pending_action_state_audit_v1_20260526.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/chat_pending_action_state_audit_v1_20260526.md`
- Focused Playwright chat regression test for the pending-action follow-up path.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/chat_pending_action_state_audit_v1_20260526.md`
- `git diff --check`
- release registry claim

## Hard Stops
- Exact duplicate PR/report already covers issue #120.
- Active registry collision on the same chat UI/test files.
- Fix requires forbidden backend/data/runtime/memory/financial-truth mutation.
- Validation cannot prove the follow-up prompt path without explanation.
