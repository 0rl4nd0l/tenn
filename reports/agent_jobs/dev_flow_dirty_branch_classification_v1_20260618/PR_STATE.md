# PR State

Canonical was fetched from
`origin/migration/clean-runtime-baseline-reconstruct-v1` before classification.
The fetched canonical HEAD is
`98e632996aae3bff82627a02b75e64cddd927420`, which is PR #373's merge commit.

## PR #367

- State: `OPEN`
- Title: `[Control Plane] Add task ledger runtime and handoff workflow`
- Head: `control-plane/agent-ledger-runtime-handoff-v1-20260617`
- Base: `migration/clean-runtime-baseline-reconstruct-v1`
- Merge commit: `null`
- Relevant files: `.agents/skills/tenn-fix/SKILL.md`,
  `.agents/skills/tenn-git-guard/SKILL.md`,
  `.agents/skills/tenn-worker/SKILL.md`, task-ledger files, handoff templates,
  `scripts/agent_task_ledger.py`, and ledger tests.
- Classification impact: PR #367 covers task-ledger/handoff plumbing, not the
  validation-environment guidance found in the dirty worktree.

## PR #368

- State: `MERGED`
- Merged at: `2026-06-17T07:33:11Z`
- Merge commit: `8df126c50abbad6481d906faa2f7229effdc7691`
- Title: `[Control Plane] Add docs freshness and model routing`
- Relevant files: `.agents/skills/tenn-fix/SKILL.md`,
  `.agents/skills/tenn-git-guard/SKILL.md`,
  `.agents/skills/tenn-worker/SKILL.md`,
  `docs/agent_tasks/dev_flow_skills_bloat_audit_v1_20260617.md`, docs-flow
  templates, and the skills-bloat report bundle.
- Classification impact: PR #368 covers the untracked skills-bloat task card
  and the canonical docs-impact/model-routing skill guidance. The raw dirty
  skill patch would regress this merged content, so only the novel additive
  validation guidance was preserved.

## PR #370

- State: `MERGED`
- Merged at: `2026-06-17T22:10:24Z`
- Merge commit: `e555f540019a50462da1596a6c2986260468b4d8`
- Title: `[Control Plane] Add OpenCode worker bridge`
- Relevant files: `.agents/skills/codex-worker-bridge/SKILL.md`,
  `scripts/opencode_worker_bridge.py`, tests, templates, task card, and report
  bundle.
- Classification impact: PR #370 does not cover the dirty `tenn-worker`,
  `tenn-fix`, or `tenn-git-guard` validation-environment guidance.

## PR #373

- State: `MERGED`
- Merged at: `2026-06-18T05:50:15Z`
- Merge commit: `98e632996aae3bff82627a02b75e64cddd927420`
- Title: `[Control Plane] Harden OpenCode worker bridge safety`
- Relevant files: `.agents/skills/codex-worker-bridge/SKILL.md`,
  `scripts/opencode_worker_bridge.py`, tests, task card, and report bundle.
- Classification impact: PR #373 establishes the current canonical HEAD and is
  unrelated to the dirty validation-environment guidance.

## PR #374

- State: `OPEN`
- URL: `https://github.com/0rl4nd0l/tenn/pull/374`
- Title: `[Control Plane] Preserve validation environment autonomy guidance`
- Head: `control-plane/validation-environment-autonomy-preserve-v1-20260618`
- Base: `migration/clean-runtime-baseline-reconstruct-v1`
- Initial commit:
  `90e37007e1baf2c4cbca3cd54774715f71eb105e`
- Last checked merge state: `UNSTABLE`
- Last checked checks:
  `lint-and-test` queued, `scan` in progress.
- Classification impact: PR #374 is the clean preservation path for the novel
  validation-environment guidance. It intentionally excludes the already-merged
  skills-bloat card and the old branch's two unrelated local commits.
