# State

state: PR_OPENED

## Current State

- Task card: `docs/agent_tasks/tenn_system_brief_v0_20260709.md`
- Branch: `local/home-tenn-canonical-current-v5-20260707`
- HEAD: `8da4ca0a90babff86c3c05107131eff6ce4ca733`
- Publish branch: `control-plane/tenn-system-brief-v0-20260709-adopt`
- Repo helper: `scripts/system_brief.py`
- Tests: `scripts/test_system_brief.py`
- Host skill: `/home/l4nd0/.codex/skills/tenn-system-brief/SKILL.md`

## Risk Notes

- The helper is read-only and depends on current local evidence plus `gh` reads.
- Missing candidate state or unavailable GitHub is represented as
  `DATA_MISSING`.
- The host skill is installed locally and the repo helper now exists in
  `/home/l4nd0/tenn`.
- Orlando approved publish prep. The repo files were committed on publish branch
  `control-plane/tenn-system-brief-v0-20260709-adopt` and opened as draft PR
  #491.
