# Dev Flow Ground-Up Reset Audit

State: DONE_WITH_RISK

## Decision

Tenn should keep the existing host `diagnose` skill as the core debugging
discipline and build a Tenn-native `/issue` wrapper around it. Do not replace
`diagnose`. The future daily command set should be:

- `/issue`: intake, Git/GitHub/report preflight, optional diagnose loop, issue
  packet, milestones, context pack, and next goal.
- `/review-board`: independent perspectives plus a required decision artifact.
- `/fix`: one bounded execution orchestrator that deploys workers, integrates,
  validates, and prepares PRs only when approved.
- `worker`: bounded subagent contract with one lane, one worktree, one result.
- `code-reviewer`: final diff/PR review gate.
- `/explain`: first-class layman-depth explanation skill.
- `/improve-codebase-architecture`: first-class architecture improvement flow,
  but Tenn-wrapped and task-card gated.
- `tenn-git-guard`: native Git Hygiene backend called by every command.

## Highest-Signal Findings

- The repo already has useful Tenn-native primitives: `AGENTS.md`,
  `tenn-git-hygiene`, `tenn-frame-design`, `tenn-goal-report`,
  `tenn-task-card-registry-safety`, `scripts/agent_job_contract.py`,
  `scripts/agent_job_registry.py`, and `scripts/agent_job_hook.py`.
- The bloat is not that these primitives exist. The bloat is that operators
  must remember when to invoke them. Git Hygiene, task-card validation, registry
  visibility, dirty-state classification, and report closeout should be backend
  guards in `/issue`, `/review-board`, and `/fix`.
- Host/global skills are useful but too generic for Tenn day-to-day use. They
  should be wrapped or routed through Tenn commands rather than copied wholesale
  into repo instructions.
- Scribe is useful as a capture role, but should not remain a separate
  top-level concept. Fold it into `STATE.md`, `DECISIONS.md`, and optional
  `OPERATOR_NOTES.md`.
- Frame Design should not be a user-invoked day-to-day command. It should
  become the default artifact template for long `/issue` and `/fix` runs.
- Auto-progress should become the candidate-ranking engine inside `/issue`, not
  a standalone command Orlando must remember.
- The current worktree fleet is large: 479 Tenn worktree entries were found.
  The classifier bucketed 82 dev-flow/control-plane worktrees, 331
  product/runtime/extraction worktrees, 5 prunable metadata entries, and 61
  unknown/review-needed entries.

## Evidence Used

- Current cwd:
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Current branch:
  `safe/cockpit-news-context-date-filter-merge-packets-preserve-v1-20260609`.
- Current HEAD: `661f4a089b1eb9b25b1d2eceb9d659b689e5828e`.
- Current `origin/migration/clean-runtime-baseline-reconstruct-v1`:
  `227e1ce0d4e99c4a13ece8012a44adeba4585cdf`.
- Root `AGENTS.md`, repo `.agents/skills`, repo `.codex`, `.claude/commands`,
  hooks, registry/task-card scripts, merge parking docs, and agent docs.
- Host read-only surfaces: `~/.codex/config.toml`, `~/.codex/hooks/*.py`,
  `~/.codex/rules/default.rules`, `~/.codex/skills`, and
  `~/.codex/goals_1.sqlite` schema.
- Read-only GitHub context: issue #78, issue #291, issue #234, PR #320,
  PR #344, and focused issue/PR searches for dev-flow terms.

## Risk And DATA_MISSING

- Normal `git status` in this checkout failed with
  `fatal: this operation must be run in a work tree`; explicit
  `GIT_DIR`/`GIT_WORK_TREE` worked. A later plain `git status --short` also
  returned normally. This is recorded as a transient checkout health risk.
- An earlier explicit status probe showed unrelated dirty hook/report paths, but
  final explicit status showed only this audit task card as non-ignored. Those
  hook/report paths were not touched.
- Worktree status checks timed out for some large or degraded worktrees.
- GitHub searches were read-only; no GitHub mutation occurred.

## Files Touched

- `docs/agent_tasks/dev_flow_ground_up_reset_audit_v1_20260616.md`
- `reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/*`

## Files Intentionally Not Touched

- Product/runtime/data/extraction files.
- Source PDFs, gold labels, DB, Qdrant, Redis, news, memory, prompts, schema,
  model/runtime/GPU/service config, and backfills.
- Host-global Codex files.
- Count-24 extraction approval packet.
- Existing dirty hook/report artifacts.
- Branches, worktrees, PRs, and GitHub issues.

## Next Recommended Prompt

Use this after reading the audit:

```text
/goal Implement the dev-flow reset Shot 1 only: create Tenn-native command
wrappers for /issue, /review-board, /fix, /explain, and tenn-git-guard as
instruction-only skills or docs. Do not delete old skills. Do not mutate
product/runtime/data/extraction. Produce a task card, implementation plan, and
approval manifest first.
```
