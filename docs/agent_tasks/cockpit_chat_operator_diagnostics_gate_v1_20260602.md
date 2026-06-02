---
job_id: cockpit_chat_operator_diagnostics_gate_v1_20260602
lane: Reporting
supporting_lanes:
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_chat_operator_diagnostics_gate_v1_20260602.md
  - docs/claude/STATE.md
  - cockpit-ui/components/cockpit/chat/chat-screen.tsx
  - cockpit-ui/components/cockpit/chat/chat-operator-diagnostics.ts
  - cockpit-ui/components/cockpit/chat/chat-operator-diagnostics.test.ts
  - cockpit-ui/tests/chat-browser-regression.spec.ts
  - reports/agent_jobs/cockpit_chat_operator_diagnostics_gate_v1_20260602/README.md
  - reports/agent_jobs/cockpit_chat_operator_diagnostics_gate_v1_20260602/status.json
  - reports/agent_jobs/cockpit_chat_operator_diagnostics_gate_v1_20260602/validation.json
  - reports/agent_jobs/cockpit_chat_operator_diagnostics_gate_v1_20260602/diff-check.json
  - reports/agent_jobs/cockpit_chat_operator_diagnostics_gate_v1_20260602/browser-regression.md
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_chat_operator_diagnostics_gate_v1_20260602
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: issue_comment_and_pr
related_issue: 108
operator_approval_source: "User shifted the active goal to UI-focused Reporting work and asked whether work is advancing real operational issues; issue #108 is a product-facing chat safety/usability bug where normal users see operator Codex repair controls."
---

# Cockpit Chat Operator Diagnostics Visibility Gate

## Objective

Fix issue #108 for normal Cockpit chat users: auto-diagnostic and poor-feedback
handoff messages must not render internal report paths, API diagnostic links,
draft repair prompt paths, investigation packet paths, copied Codex prompt
status, or `Deploy Codex` controls in normal chat.

Preserve an explicit operator diagnostics mode so existing operator repair
controls can still render when enabled by `NEXT_PUBLIC_COCKPIT_OPERATOR_DIAGNOSTICS=1`.

## Session Declaration

Agent: Codex

Branch: `safe/cockpit-chat-operator-diagnostics-gate-v1-20260602`

Worktree:
`/home/l4nd0/tenn-cockpit-chat-operator-diagnostics-gate-v1-20260602`

Lane: Reporting

Execution mode: SAFE EXTENSION MODE

Intended files: this task card, `chat-screen.tsx`, focused chat diagnostics
helper/test files, focused browser regression coverage, `docs/claude/STATE.md`,
and this report bundle.

Contested surfaces touched: `cockpit-ui/components/cockpit/chat/`.

Collision risk: MEDIUM. The chat surface is contested and PR #256 touches
`chat-screen.tsx`, but current evidence shows #256 changes only the deploy-route
request header while this task changes normal-chat diagnostic message rendering.
No active registry job owns chat UI files.

Decision: proceed after validation, active-job check, overlap check, and
registry claim.

## Contract Check

Target system layer: Cockpit client UI only.

Relevant contract rules: `SYSTEM_CONTRACT.md` §1.2 Cockpit client role, §1.3
retrieval boundary, and §2 mandatory flow. Backend remains authoritative for all
data and diagnostic persistence.

What must not change: backend APIs, diagnostic route guards, feedback storage,
query orchestration, retrieval, memory storage, financial truth, source/evidence
labels, Qdrant/Postgres, runtime/model/GPU configuration, service config, or
diagnostic artifact generation.

Why safe: the change only gates what the normal chat UI renders. It does not
change diagnostic capture, deploy routes, backend state, or any canonical data
surface.

GPU process check required: no. This task does not spawn, restart, or depend on
llama-server.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_chat_operator_diagnostics_gate_v1_20260602.md --write-report`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_chat_operator_diagnostics_gate_v1_20260602.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_chat_operator_diagnostics_gate_v1_20260602.md --repo-root .`
- Focused chat diagnostics Vitest.
- Focused `/full-chat` browser regression for normal-user diagnostic hiding.
- Targeted ESLint for touched chat files.
- Cockpit UI TypeScript if practical.
- JSON validation for report artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_chat_operator_diagnostics_gate_v1_20260602.md --repo-root .`
- Registry release and final active-job check.

## Hard Stops

- Exact duplicate implementation PR found.
- Active registry overlap on chat UI files.
- Proposed fix requires backend route/security changes already covered by PR
  #248/#256 or issue #222.
- Proposed fix changes source/evidence labels, query orchestration, memory,
  financial truth, runtime/model/GPU config, or diagnostic persistence.
- Operator diagnostics cannot be preserved behind an explicit mode.
