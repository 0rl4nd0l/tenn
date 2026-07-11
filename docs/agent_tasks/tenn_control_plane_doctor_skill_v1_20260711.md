---
job_id: tenn_control_plane_doctor_skill_v1_20260711
lane: Reporting
supporting_lanes:
  - Repo Hygiene
owner: Codex
allowed_files:
  - .agents/skills/tenn-control-plane-doctor/SKILL.md
  - .agents/skills/tenn-control-plane-doctor/agents/openai.yaml
  - docs/README.md
  - docs/dev_flow/SKILLS_SURFACE.md
  - docs/agent_tasks/tenn_control_plane_doctor_skill_v1_20260711.md
  - reports/agent_jobs/tenn_control_plane_doctor_skill_v1_20260711/README.md
  - reports/agent_jobs/tenn_control_plane_doctor_skill_v1_20260711/STATE.md
  - reports/agent_jobs/tenn_control_plane_doctor_skill_v1_20260711/DECISIONS.md
  - reports/agent_jobs/tenn_control_plane_doctor_skill_v1_20260711/VALIDATION.md
  - reports/agent_jobs/tenn_control_plane_doctor_skill_v1_20260711/NEXT_GOAL.md
approval_required: true
approval_context: "USER_APPROVED_2026-07-11: create a concise repo-backed tenn-control-plane-doctor skill from fresh canonical; do not duplicate doctor logic or mutate host skills, GitHub, runtime, data, extraction, ledger, or registry state."
timeout_seconds: 3600
output_dir: reports/agent_jobs/tenn_control_plane_doctor_skill_v1_20260711
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: false
live_ledger_mutation_allowed: false
docs_impact: DOCS_UPDATED
docs_checked:
  - docs/README.md
  - docs/dev_flow/SKILLS_SURFACE.md
docs_changed:
  - docs/README.md
  - docs/dev_flow/SKILLS_SURFACE.md
docs_followup: "none"
reason: "A new visible repo-backed skill changes Tenn skill routing, inventory, and operator invocation guidance."
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "The task is a narrow control-plane workflow wrapper with policy-sensitive skill-surface documentation and no product/runtime mutation."
worker_model_allowed: false
worker_decision_limit: "No workers; skill wording, routing justification, validation, and documentation form one small coupled bundle."
escalation_needed: false
task_scope: safe_extension
base_ref: origin/migration/clean-runtime-baseline-reconstruct-v1
base_head: 2c9324a9e69d6c0a66d7a3f2090e39f5e6a5a35c
---

# Tenn Control Plane Doctor Skill

## Objective

Add a concise, first-class Tenn skill that safely invokes and explains the
existing read-only `scripts/control_plane_doctor.py` diagnostic without
duplicating its implementation or widening into remediation.

## Visible-Skill Design Note

This entrypoint intentionally increases the visible repo-backed skill count.
The doctor represents distinct operator intent: run a deterministic, strictly
read-only control-plane diagnostic and stop before repair. Hiding that intent
inside `tenn-explain` or `tenn-fix` would make invocation less discoverable and
could blur the hard boundary between diagnosis and mutation. The skill remains
small and delegates all deterministic checks to the existing script.

## Exact Changes

- Add only `SKILL.md` and `agents/openai.yaml` under the new skill directory.
- Require checkout identity, Tenn Dev Status, Git Guard, doctor execution,
  JSON parsing, evidence labels, and ranked next-action guidance.
- Require Runtime Functionality Proof only for underlying runtime claims; do
  not equate a working doctor with healthy inspected systems.
- Update the documentation source map and skill-surface inventory/count.
- Add task-local report and validation artifacts.

## Hard Stops

- Do not copy or reimplement `scripts/control_plane_doctor.py` logic.
- Do not repair doctor findings.
- Do not mutate host skills, hooks, systemd, GitHub, runtime, data,
  extraction, ledger, or registry state.
- Do not push, open a PR, merge, retarget, or delete branches/worktrees.

## Done Criteria

- Skill structure and UI metadata validate.
- Trigger description and default prompt name the intended workflow.
- Skill invokes the existing doctor and preserves its exit `0/1/2` semantics.
- Output contract classifies every check and separates diagnostic proof from
  underlying system functionality.
- Visible skill count and documentation routing are updated and justified.
- Exact allowlist, focused behavior checks, diff review, and final Git Guard
  pass, followed by one local commit.
