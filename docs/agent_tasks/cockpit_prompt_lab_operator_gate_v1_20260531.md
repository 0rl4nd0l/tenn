---
job_id: cockpit_prompt_lab_operator_gate_v1_20260531
lane: Reporting
supporting_lanes:
  - Query Orchestration
  - Runtime
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_prompt_lab_operator_gate_v1_20260531.md
  - reports/agent_jobs/cockpit_prompt_lab_operator_gate_v1_20260531/README.md
  - reports/agent_jobs/cockpit_prompt_lab_operator_gate_v1_20260531/status.json
  - reports/agent_jobs/cockpit_prompt_lab_operator_gate_v1_20260531/validation.json
  - reports/agent_jobs/cockpit_prompt_lab_operator_gate_v1_20260531/diff-check.json
  - reports/agent_jobs/cockpit_prompt_lab_operator_gate_v1_20260531/operator_gate_evidence.md
  - cockpit-ui/components/cockpit/settings/settings-screen.tsx
  - cockpit-ui/components/cockpit/settings/settings-screen.test.tsx
  - cockpit-ui/components/cockpit/settings/prompt-lab-panel.tsx
  - cockpit-ui/lib/api-client.ts
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_cockpit_prompt_lab.py
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
stale_after_seconds: 7200
output_dir: reports/agent_jobs/cockpit_prompt_lab_operator_gate_v1_20260531
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: pr_create
related_issue: 147
---

# Cockpit Prompt Lab Operator Gate

## Objective

Fix the issue #147 control-plane gap where normal Cockpit Settings exposes
Prompt Lab prompt-stack previews and LLM dry-run controls without an explicit
operator gate.

## Session Declaration

- Agent: Codex.
- Worktree:
  `/home/l4nd0/tenn-reporting-prompt-lab-operator-gate-v1-20260601`.
- Branch: `safe/reporting-prompt-lab-operator-gate-v1-20260601`.
- Parent live branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Issue: #147.
- Primary lane: Reporting.
- Supporting lanes: Query Orchestration and Runtime.
- Intended files: this task card, this job's report artifacts, Prompt Lab UI/API
  client files, focused tests, and the narrow backend prompt routes.
- Contested surfaces touched: `financial-engine_v2/backend/app/routes/cockpit_api.py`.
- Collision risk: HIGH by contested surface, but active registry overlap is
  disjoint from this task; use isolated worktree, exact allowlist, and stop on
  any new overlap.
- Decision: proceed as SAFE EXTENSION after validation, overlap check, and
  registry claim.

## Contract Check

- Target system layer: Cockpit client/orchestration UI plus backend Cockpit
  prompt-control routes.
- Relevant contract rules: backend remains authority; Cockpit is client and
  orchestration only; Cockpit must not bypass retrieval/storage or expose
  operator/runtime controls as normal analyst workflow.
- What must not change: financial truth, extraction, parser routing, prompt
  content semantics, retrieval, memory stores, source/evidence labels, Qdrant,
  Postgres, production data, runtime/model/GPU configuration, and service state.
- Why safe: the change introduces an explicit disabled-by-default operator gate
  and intent header for Prompt Lab route/preview/dry-run access. It does not
  alter prompt generation, chat routing, or LLM runtime configuration.
- GPU process check required: no. This task does not spawn, restart, or depend
  on `llama-server`; tests use fakes and do not run live dry-runs.

## Required Behavior

- Normal Settings does not show the Prompt Lab tab unless operator access is
  explicitly enabled for the UI build.
- Backend prompt route inventory, prompt preview, and prompt dry-run reject
  requests unless backend operator access is explicitly enabled.
- Prompt preview and dry-run require an explicit Prompt Lab intent header.
- When access is enabled and intent is present, existing Prompt Lab behavior is
  preserved.
- Dry-run tests must prove rejected requests do not reach the fake LLM client.

## Forbidden

- Production DB/Qdrant/news/memory writes.
- Canonical financial truth changes.
- Parser routing, extraction prompts, or gold labels.
- Runtime/model/GPU/service configuration changes.
- Broad auth redesign.
- Deleting Prompt Lab instead of gating it deliberately.
- Live prompt dry-run against a real LLM.
- Unrelated dirty work, cleanup, branch mutation, stash, reset, rebase, or merge.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_prompt_lab_operator_gate_v1_20260531.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_prompt_lab_operator_gate_v1_20260531.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_prompt_lab_operator_gate_v1_20260531.md --repo-root .`
- Focused backend Prompt Lab tests.
- Focused frontend Settings/Prompt Lab tests.
- Targeted frontend ESLint for touched UI/client files.
- Cockpit UI TypeScript check.
- Python compile for touched backend files.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_prompt_lab_operator_gate_v1_20260531.md --repo-root .`
- Registry release and final status check.

## Final Report Requirements

- Files changed.
- Exact validation commands and results.
- Evidence that normal Settings hides Prompt Lab by default.
- Evidence that backend prompt routes reject ungated requests.
- Evidence that enabled operator path still works.
- Explicit statement that no production data, memory, retrieval, financial truth,
  prompt semantics, GPU/runtime configuration, or live LLM dry-run changed.
