# Tenn Control Plane Doctor Skill

## Status

`DONE_WITH_RISK`

The repo-backed skill, UI metadata, skill-surface routing updates, and focused
validation are complete in a clean current-canonical task worktree. The bounded
closeout is one local commit; publication and host installation remain separate
approval boundaries.

## Outcome

- Added `tenn-control-plane-doctor` as a first-class read-only diagnostic skill.
- Reused `scripts/control_plane_doctor.py`; added no backend script or duplicate
  checking logic.
- Preserved doctor exit `0`, `1`, and `2` semantics and the four status classes.
- Required JSON contract validation and plain-language evidence classification.
- Kept doctor functionality separate from underlying runtime functionality.
- Added explicit hard stops before remediation and protected mutations.
- Increased the visible repo skill count from `12` to `13` with an approved
  design justification in `docs/dev_flow/SKILLS_SURFACE.md`.

## Files Touched

- `.agents/skills/tenn-control-plane-doctor/SKILL.md`
- `.agents/skills/tenn-control-plane-doctor/agents/openai.yaml`
- `docs/README.md`
- `docs/dev_flow/SKILLS_SURFACE.md`
- `docs/agent_tasks/tenn_control_plane_doctor_skill_v1_20260711.md`
- Five report artifacts in this directory

## Files Intentionally Not Touched

- `scripts/control_plane_doctor.py` and its tests
- `AGENTS.md` and existing Tenn skills
- Host/global skills or Codex configuration
- Systemd, hooks, deployed automation, runtime, data, extraction, ledger,
  registry, or GitHub state

## Runtime Functionality Proof

| Field | Required evidence |
| --- | --- |
| intended output | One valid doctor JSON document whose process exit matches `summary.exit_code` and whose checks use the documented status contract. |
| live output location | Command stdout from `python3 scripts/control_plane_doctor.py --repo-root . --json`; no persistent doctor output. |
| pre-run max timestamp or count | Existing merged doctor contract: eight checks. |
| post-run max timestamp or count | Current skill-candidate proof: one parsed JSON document containing eight checks. |
| rows/files inserted or updated after run start | `0` runtime/data rows or doctor output files; only task-card-allowed repo/report files changed. |
| readiness/gate status | Skill validation passed; JSON schema, read-only flag, exit parity, status set, and check shape passed. Real doctor returned expected diagnostic exit `1`. |
| exact command/query used | `PYTHONDONTWRITEBYTECODE=1 python3 scripts/control_plane_doctor.py --repo-root . --json` plus an inline JSON contract assertion. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | `WORKING` for the doctor command and wrapper contract. |
| remaining blocker | Underlying control-plane warnings remain separate approval-gated remediation; no underlying automation/runtime functionality claim was made. |

result: WORKING

## Remaining Risk

- Repo publication and host picker visibility are not proven by a local commit.
- The current doctor result contains warnings and missing evidence; the new
  skill explains them but deliberately does not repair them.
- Forward-testing with an independent agent was not used because this task did
  not authorize subagent work and the workflow is covered by deterministic
  structure and live-command checks.
