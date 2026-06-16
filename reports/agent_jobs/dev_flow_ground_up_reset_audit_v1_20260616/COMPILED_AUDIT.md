# Dev Flow Ground-Up Reset Audit - Compiled Report

This file compiles the complete report bundle into one Markdown document.

## Contents

- [Readme](#readme)
- [Inventory](#inventory)
- [Skills Matrix](#skills-matrix)
- [Rules And Agents Matrix](#rules-and-agents-matrix)
- [Hooks Matrix](#hooks-matrix)
- [Host Codex Surface](#host-codex-surface)
- [Worktree Matrix](#worktree-matrix)
- [Git Hygiene Integration](#git-hygiene-integration)
- [Operator Workflow](#operator-workflow)
- [Overlaps And Conflicts](#overlaps-and-conflicts)
- [Target Architecture](#target-architecture)
- [Deprecation Plan](#deprecation-plan)
- [Implementation Sequence](#implementation-sequence)
- [Owner Decisions](#owner-decisions)
- [Validation](#validation)

---

# Readme

Source: `reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/README.md`

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

---

# Inventory

Source: `reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/INVENTORY.md`

## Canonical Repo Surface

Current origin base inspected:
`origin/migration/clean-runtime-baseline-reconstruct-v1` at
`227e1ce0d4e99c4a13ece8012a44adeba4585cdf`.

| Surface | Evidence | Classification | Recommendation |
| --- | --- | --- | --- |
| Root `AGENTS.md` | Present, current repo constitution. | `CORE_KEEP` | Keep short; route procedures to skills. |
| Nested `AGENTS.md` | `find . -name AGENTS.md` found only root. | `UNKNOWN_NEEDS_OWNER_DECISION` | No nested split needed unless a product subtree needs different rules. |
| `.agents/skills/tenn-auto-progress` | Present in origin and current repo. | `MERGE_INTO_NEW_WORKFLOW` | Use as `/issue` candidate-ranking engine. |
| `.agents/skills/tenn-financial-metric-extraction` | Present. | `OWNER_BOUNDARY` | Keep for Financial Truth only; not dev-flow core. |
| `.agents/skills/tenn-frame-design` | Present. | `MERGE_INTO_NEW_WORKFLOW` | Make default long-run frame template. |
| `.agents/skills/tenn-git-hygiene` | Present. | `MERGE_INTO_NEW_WORKFLOW` | Become `tenn-git-guard` backend. |
| `.agents/skills/tenn-goal-report` | Present. | `CORE_KEEP` | Keep as closeout/report state machine. |
| `.agents/skills/tenn-task-card-registry-safety` | Present. | `CORE_KEEP` | Keep as task-card and registry guard. |
| `.codex/config.toml` | Repo hooks enabled. | `CORE_KEEP` | Keep minimal. |
| `.codex/hooks.json` | Graphify pretool plus Stop task-card hook. | `CORE_KEEP` | Keep; fix path drift through Git guard. |
| `.codex/skills/cockpit-flag-orchestrator` | Repo legacy/custom skill. | `OWNER_BOUNDARY` | Do not fold into dev-flow reset. |
| `.claude/commands/*` | Many command docs mirror host skills. | `RENAME_OR_REHOME` | Treat as Claude reference, not canonical Tenn command set. |
| `.githooks/pre-commit` | Python staged-file Ruff gate. | `CORE_KEEP` | Keep as local Git hook. |
| `.githooks/pre-push` | Ruff, hook/tooling tests, markdown hygiene. | `CORE_KEEP` | Keep, but current file is dirty and owner-bound. |
| `scripts/agent_job_contract.py` | Validates cards, artifacts, diff scope. | `CORE_KEEP` | Make every command call it. |
| `scripts/agent_job_registry.py` | Shared active-job registry. | `CORE_KEEP` | Make every command call read-only list first. |
| `scripts/agent_job_hook.py` | Hook wrapper around card and registry checks. | `CORE_KEEP` | Keep as Stop/BeforeTool guard. |
| `scripts/auto_progress.py` | Present on origin, absent from this older branch working tree. | `MERGE_INTO_NEW_WORKFLOW` | Candidate-ranking engine inside `/issue`. |
| `docs/agents/*` | Skill registry, issue tracker, labels, domain docs. | `CORE_KEEP` | Keep as Tenn adapter layer for generic skills. |
| `docs/agent_registry/merge_parking` | Merge parking registry. | `CORE_KEEP` | Feed Git guard branch/parking checks. |
| `docs/agent_tasks/**` | Large task-card corpus. | `CORE_KEEP` | Keep exact contract, but reduce manual operator burden. |
| `reports/agent_jobs/**` | Evidence/closeout corpus. | `CORE_KEEP` | Keep, but avoid report-only loops through action decisions. |

## Host/Global Surface

| Surface | Evidence | Classification | Recommendation |
| --- | --- | --- | --- |
| `~/.codex/config.toml` | Trusted projects, plugins, hooks, goals, memories. | `OWNER_BOUNDARY` | Read-only for repo commands; do not mutate from Tenn. |
| `~/.codex/hooks/goal_optimizer_pre_tool.py` | High-burn goal warning. | `CORE_KEEP` | Keep as host guard. |
| `~/.codex/hooks/pre_apply_patch.py` | Sensitive path warning. | `CORE_KEEP` | Keep as warning-only host guard. |
| `~/.codex/hooks/post_apply_patch.py` | Ruff/chmod/backend-test side effects. | `UNKNOWN_NEEDS_OWNER_DECISION` | Useful but can surprise Tenn report-only runs. |
| `~/.codex/hooks/stop_check.py` | Uncommitted-state warning. | `MERGE_INTO_NEW_WORKFLOW` | Align with Tenn `tenn-git-guard` messaging. |
| `~/.codex/rules/default.rules` | One path-specific allow rule. | `DEPRECATE` | Not a scalable Tenn rule surface. |
| `~/.codex/goals_1.sqlite` | `thread_goals` schema present. | `CORE_KEEP` | Read-only status source for `/goal` tooling. |

## GitHub Context

| Item | Status | Relevance |
| --- | --- | --- |
| Issue #78 | Open | Broad agent markdown and Codex repo docs refresh tracker. |
| Issue #291 | Open | Auto-progress controller issue and target workflow description. |
| Issue #234 | Open | Current report-first repo hygiene candidate used by auto-progress. |
| PR #300 | Merged | Read-only registry and control-plane refresh. |
| PR #302 | Merged | Added `tenn-frame-design`. |
| PR #303 | Merged | Added `tenn-git-hygiene`. |
| PR #320 | Merged | Formalized two-shot dev-flow autonomy. |
| PR #344 | Merged | Added auto-progress V2 read-only planner. |
| PR #345 | Merged | Fixed terminal Stop-hook loop after handoff. |

---

# Skills Matrix

Source: `reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/SKILLS_MATRIX.md`

## Repo-Backed Tenn Skills

| Skill | Path | Plain English | Use Case | Artifacts | Mutates? | Hands-Off Safety | Overlap | Classification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `tenn-auto-progress` | `.agents/skills/tenn-auto-progress/SKILL.md` | Ranks GitHub issues and drafts planning packets without executing. | Orlando asks what safe work to do next. | Issue scans, rankings, context packs, draft cards. | Report-local only by default. | Safe if read-only and GitHub writes stay disabled. | Overlaps `/issue`. | `MERGE_INTO_NEW_WORKFLOW` |
| `tenn-financial-metric-extraction` | `.agents/skills/tenn-financial-metric-extraction/SKILL.md` | Financial Truth extraction guardrails. | Source-bound metric extraction work. | Scorecards, reports, task cards. | Can mutate extraction only with explicit approval. | Not a dev-flow command. | Domain safety. | `OWNER_BOUNDARY` |
| `tenn-frame-design` | `.agents/skills/tenn-frame-design/SKILL.md` | Creates Frame, State, operator notes, optional Scribe. | Long or risky goals. | `FRAME.md`, `STATE.md`, `OPERATOR_NOTES.md`, optional `SCRIBE.md`. | Report-local. | Safe as template. | Overlaps goal report. | `MERGE_INTO_NEW_WORKFLOW` |
| `tenn-git-hygiene` | `.agents/skills/tenn-git-hygiene/SKILL.md` | Classifies dirty work, branches, worktrees, and cleanup risk. | Any repo-control or dirty-state work. | Manifests, ledgers, approval packets. | Report-local by default; cleanup needs approval. | Safe when backend guard, risky as standalone cleanup habit. | Overlaps task-card safety and goal report. | `MERGE_INTO_NEW_WORKFLOW` |
| `tenn-goal-report` | `.agents/skills/tenn-goal-report/SKILL.md` | State machine and closeout report rules for `/goal`. | Long goal closeout. | `README.md`, validation, blockers, next prompt. | Report-local. | Safe. | Overlaps Frame state. | `CORE_KEEP` |
| `tenn-task-card-registry-safety` | `.agents/skills/tenn-task-card-registry-safety/SKILL.md` | Validates task-card scope, dirty state, and registry read-only checks. | Before implementation-capable work. | Task-card validation and final diff evidence. | No mutation by default. | Essential. | Overlaps Git guard. | `CORE_KEEP` |

## Host/Global Dev-Flow Skills

| Skill | Path | Plain English | Use Case | Artifacts | Mutates? | Hands-Off Safety | Overlap | Classification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `diagnose` | `~/.codex/skills/diagnose/SKILL.md` | Disciplined bug loop: reproduce, hypothesize, instrument, fix, test. | Something is broken or slow. | Repro loops, tests, postmortem. | Can mutate during fix phase. | Excellent if wrapped by Tenn preflight. | `/issue`, `/fix`. | `CORE_KEEP` |
| `code-reviewer` | `~/.codex/skills/code-reviewer/SKILL.md` | Structured diff review. | Before PR/merge. | JSON findings. | Read-only unless delegating. | Safe if diff scope is bounded. | `/review-board`, `/fix`. | `CORE_KEEP` |
| `code-fixer` | `~/.codex/skills/code-fixer/SKILL.md` | Applies review findings. | After review identifies fixes. | Change summary. | Mutates code. | Needs `/fix` task-card gate. | `/fix`. | `MERGE_INTO_NEW_WORKFLOW` |
| `improve-codebase-architecture` | `~/.codex/skills/improve-codebase-architecture/SKILL.md` | Finds deepening/refactor opportunities. | Architecture improvement work. | HTML reports, possible docs/ADR updates. | Can mutate docs/design later. | Needs Tenn wrapper; temp HTML default conflicts with report-bundle evidence. | architecture-check, review-board. | `CORE_KEEP` |
| `architecture-check` | `~/.codex/skills/architecture-check/SKILL.md` | Validates changes against invariant rules. | Before backend/RAG/vector changes. | Markdown verdict. | Read-only. | Safe, but references `.cursor/rules` that may be stale/missing. | architecture cleanup. | `MERGE_INTO_NEW_WORKFLOW` |
| `architecture-cleanup-steward` | `~/.codex/skills/architecture-cleanup-steward/SKILL.md` | Audits/prunes unused architecture docs/components. | Architecture cleanup. | Findings and cleanup proposals. | Can delete/edit if used directly. | Too broad for hands-off default. | improve-codebase-architecture. | `RENAME_OR_REHOME` |
| `tenn-issue-finder` | `~/.codex/skills/tenn-issue-finder/SKILL.md` | Finds and triages Tenn issues. | Backlog discovery. | Issue audits. | Read-only by default. | Useful as `/issue` scanner. | auto-progress. | `MERGE_INTO_NEW_WORKFLOW` |
| `tenn-issue-closeout` | `~/.codex/skills/tenn-issue-closeout/SKILL.md` | Safely closes, parks, or leaves issues open. | After validated work. | Closeout verdicts. | GitHub writes only with approval. | Safe when approval-gated. | `/fix` closeout. | `MERGE_INTO_NEW_WORKFLOW` |
| `tenn-issue-resolution-reviewer` | `~/.codex/skills/tenn-issue-resolution-reviewer/SKILL.md` | Skeptical post-fix reviewer. | Before closing issues/PRs. | Review verdict. | Read-only by default. | Strong reviewer role. | review-board, code-reviewer. | `MERGE_INTO_NEW_WORKFLOW` |
| `triage` | `~/.codex/skills/triage/SKILL.md` | Generic issue-tracker triage. | Generic issue workflows. | Issue comments/labels. | GitHub writes. | Unsafe direct because labels do not match Tenn without adapter. | `/issue`. | `DEPRECATE` |
| `to-issues` | `~/.codex/skills/to-issues/SKILL.md` | Breaks plans into tracker issues. | PRD/planning conversion. | Draft/published issues. | GitHub writes after approval. | Use inside `/issue` as draft-only by default. | triage. | `MERGE_INTO_NEW_WORKFLOW` |
| `handoff` | `~/.codex/skills/handoff/SKILL.md` | Writes temp handoff. | Conversation transfer. | Temp handoff doc. | Writes temp file. | Useful, but Tenn should prefer report-local `STATE.md`/`NEXT_GOAL.md`. | goal-report. | `MERGE_INTO_NEW_WORKFLOW` |

## Direct Answers

1. Existing `diagnose` should remain standalone and `/issue` should wrap it.
2. `explain` should be added as first-class `tenn-explain`.
3. `improve-codebase-architecture` should be first-class, but Tenn-wrapped.
4. Git Hygiene should become a backend guard used by every workflow.
5. Scribe should fold into `STATE.md`, `DECISIONS.md`, and operator notes.
6. Frame Design should become the default artifact template for long `/issue`
   and `/fix` runs.
7. Auto-progress should become candidate ranking inside `/issue`.
8. Unnecessary report-only loops come from standalone Git Hygiene, standalone
   auto-progress packets, repeated issue closeout reviews, and Frames that do
   not lead to decisions.
9. Necessary safety pieces are task cards, registry read-only checks, changed
   path guards, GitHub read-before-write, worker worktree ownership, Stop hooks,
   and final code review.
10. Smallest daily command set: `/issue`, `/review-board`, `/fix`, `/explain`,
    `/improve-codebase-architecture`, with `code-reviewer` and `worker` as
    internal roles.

---

# Rules And Agents Matrix

Source: `reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/RULES_AND_AGENTS_MATRIX.md`

| Surface | What It Does | Useful? | Overlap/Problem | Classification | Action |
| --- | --- | --- | --- | --- | --- |
| `AGENTS.md` | Stable Tenn constitution: target verification, evidence hierarchy, safety boundaries, task cards, registry, validation, GitHub rules. | Yes. | Long but still high-signal. | `CORE_KEEP` | Keep short and avoid adding command procedures. |
| `docs/agents/skill-registry.md` | Defines active repo skill root and legacy/tool-specific surfaces. | Yes. | Critical because `.codex/skills` in repo is legacy/custom. | `CORE_KEEP` | Keep. |
| `docs/agents/issue-tracker.md` | Adapts generic issue skills to Tenn GitHub issue rules. | Yes. | Overlaps AGENTS GitHub section. | `CORE_KEEP` | Keep as detailed reference. |
| `docs/agents/triage-labels.md` | Maps generic roles to Tenn labels. | Yes. | Prevents generic `triage` label drift. | `CORE_KEEP` | Keep. |
| `docs/agents/domain.md` | Tells generic skills which Tenn docs replace generic `CONTEXT.md`/ADR assumptions. | Yes. | Essential adapter for host skills. | `CORE_KEEP` | Keep. |
| `.claude/commands/*` | Tool-specific command prompts for Claude. | Mixed. | Duplicates host skills and Tenn repo policy. | `RENAME_OR_REHOME` | Keep as Claude-only reference, not Tenn canonical command list. |
| Host `~/.codex/rules/default.rules` | One prefix allow rule for an old news loader py_compile. | Low. | Too path-specific and stale as a general rule surface. | `DEPRECATE` | Do not copy into Tenn. |
| `.codex/skills/cockpit-flag-orchestrator` | Cockpit feedback artifact processor. | Yes for Cockpit. | Product/control-plane boundary, not general dev-flow. | `OWNER_BOUNDARY` | Leave out of reset. |

## Missing Or Stale Surfaces

- No nested `AGENTS.md` files were found. That is acceptable for now.
- No first-class repo `tenn-explain` skill exists.
- No first-class repo `tenn-review-board`, `tenn-fix`, `tenn-worker`, or
  `tenn-git-guard` skill exists.
- Generic `architecture-check` still references `.cursor/rules/*`; current repo
  evidence points agents to `docs/architecture/*` and `docs/agents/domain.md`.
  Treat direct `.cursor/rules` assumptions as stale unless live files prove
  otherwise.

---

# Hooks Matrix

Source: `reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/HOOKS_MATRIX.md`

| Hook Surface | Current Behavior | Useful? | Risk | Classification | Recommendation |
| --- | --- | --- | --- | --- | --- |
| Repo `.codex/hooks.json` PreToolUse | Emits Graphify reminder for shell commands when graph exists. | Sometimes. | Low, can distract. | `CORE_KEEP` | Keep but make quiet. |
| Repo `.codex/hooks.json` Stop | Runs `python3 scripts/agent_job_hook.py --platform codex --event Stop`. | Yes. | Path drift can block or warn incorrectly. | `CORE_KEEP` | Keep; Git guard should preflight hook health. |
| Repo `.githooks/pre-commit` | Runs Ruff on staged Python if venv Ruff exists. | Yes. | Skips silently if Ruff missing. | `CORE_KEEP` | Keep. |
| Repo `.githooks/pre-push` | Runs Ruff, hook/tooling pytest, markdown hygiene. | Yes. | Current file is dirty in this checkout; owner-bound. | `CORE_KEEP` | Preserve, review separately before cleanup. |
| Claude hooks | Session memory, edit warnings, auto Ruff/chmod/test, Stop reminders. | Mixed. | Tool-specific and can be noisy. | `RENAME_OR_REHOME` | Keep as Claude surface, not Tenn universal policy. |
| Host `goal_optimizer_pre_tool.py` | Warns on high-burn commands in active goals. | Yes. | Warning-only. | `CORE_KEEP` | Keep. |
| Host `pre_apply_patch.py` | Warns on sensitive paths. | Yes. | Warning-only. | `CORE_KEEP` | Keep. |
| Host `post_apply_patch.py` | Runs Ruff/chmod/backend tests after patches. | Mixed. | Can create side effects in report-only runs. | `UNKNOWN_NEEDS_OWNER_DECISION` | Decide whether Tenn report-only paths should be exempt. |
| Host `stop_check.py` | Warns about uncommitted state. | Yes. | Defaults to `/home/l4nd0/tenn` if repo detection fails. | `MERGE_INTO_NEW_WORKFLOW` | Align with Tenn `tenn-git-guard`. |

## Hook Integration Target

Hooks should not be the primary workflow brain. They should enforce or warn on:

- active task card exists when mutation starts;
- diff stays inside allowed files;
- registry read-only/list-active is possible;
- dirty state and report artifacts are visible at Stop;
- no broad output or high-burn exploration continues unchecked.

The operator-facing commands should run the same checks before work starts so
Stop hooks are a backstop, not the first time a problem is discovered.

---

# Host Codex Surface

Source: `reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/HOST_CODEX_SURFACE.md`

Read-only host inspection found:

- `~/.codex/config.toml`
- `~/.codex/hooks/*.py`
- `~/.codex/rules/default.rules`
- `~/.codex/skills/**`
- `~/.codex/goals_1.sqlite`

No host-global file was mutated.

## Config

Host config enables hooks, memories, goals, multi-agent, remote control,
Playwright, Jam, Chorus, GitHub, Google Drive, OpenAI developer, security, web,
iOS, macOS, data visualization, and fiscal plugins. Multiple Tenn project paths
are trusted.

Classification: `OWNER_BOUNDARY`.

Recommendation: Tenn repo workflows may read this as environment context, but
must not rely on host plugin availability for repo safety. Repo skills and
scripts should remain the Tenn source of truth.

## Goals DB

`~/.codex/goals_1.sqlite` exists. Schema includes `thread_goals` with `active`,
`paused`, `blocked`, `usage_limited`, `budget_limited`, and `complete` status.

Classification: `CORE_KEEP`.

Recommendation: Use for goal-state reporting and burn warnings only. Do not use
as a substitute for report-local `STATE.md`.

## Host Skills

Relevant day-to-day host skills should be routed through Tenn wrappers:

- keep `diagnose`;
- keep `code-reviewer`;
- keep `improve-codebase-architecture`;
- merge issue/triage/closeout pieces into `/issue` and `/fix`;
- do not expose generic `triage` directly to Tenn labels.

## Host Hooks

Host hooks are valuable, but not all are Tenn-native. In particular,
`post_apply_patch.py` can run format/test commands after patches. It did not
change this report bundle, but the future Git guard should explicitly mark
whether the current run is report-only and whether post-patch side effects are
acceptable.

---

# Worktree Matrix

Source: `reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/WORKTREE_MATRIX.md`

Read-only command:

```text
git worktree list --porcelain
```

Classifier result:

| Bucket | Count | Meaning | Recommended Disposition |
| --- | ---: | --- | --- |
| `DEV_FLOW_CONTROL_PLANE` | 82 | Worktrees likely tied to agents, auto-progress, Codex, repo hygiene, issue closeout, merge gates, or workflow control. | Preserve and review before cleanup. |
| `PRODUCT_RUNTIME_EXTRACTION` | 331 | Product, runtime, Cockpit, query, memory, news, extraction, parser, financial truth, source/provenance work. | Owner-boundary; ignore for dev-flow cleanup unless a separate issue owns it. |
| `PRUNABLE_METADATA` | 5 | Worktree metadata points to missing `/tmp` paths. | Review under explicit cleanup approval only. |
| `UNKNOWN_NEEDS_REVIEW` | 61 | Could not safely classify by path/branch keywords or status timed out. | Preserve and review in a later hygiene packet. |
| Total | 479 | Tenn worktree entries. | No deletion or pruning in this run. |

## Current Checkout

| Field | Value |
| --- | --- |
| Path | `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` |
| Branch | `safe/cockpit-news-context-date-filter-merge-packets-preserve-v1-20260609` |
| HEAD | `661f4a089b1eb9b25b1d2eceb9d659b689e5828e` |
| Status | Normal Git status failed; explicit `GIT_DIR`/`GIT_WORK_TREE` status worked. |
| Dirty files | Pre-existing `.githooks/pre-push` and two `git_hook_install_execution` report files, plus this audit card/report. |
| Classification | `UNKNOWN_NEEDS_OWNER_DECISION` |
| Disposition | Preserve; do not clean or repair in this audit. |

## Notable Dev-Flow Worktrees

| Path | Branch | Dirty | Classification | Disposition |
| --- | --- | --- | --- | --- |
| `/home/l4nd0/tenn-agent-contract-registry-main-v1-20260607` | `safe/agent-contract-registry-main-v1-20260607` | clean | `CORE_KEEP` | Review as registry history. |
| `/home/l4nd0/tenn-auto-progress-issue234-phase3-dry-run-review-20260615` | `control-plane/issue234-diff-check-dirt-classification-v1-20260615` | clean | `MERGE_INTO_NEW_WORKFLOW` | Preserve as auto-progress issue-to-card evidence. |
| `/home/l4nd0/tenn-auto-progress-issue291-planner-v2-20260612` | `control-plane/auto-progress-issue291-planner-v2-20260612` | clean | `MERGE_INTO_NEW_WORKFLOW` | Canonical auto-progress evidence. |
| `/home/l4nd0/tenn-auto-progress-phase1-issue281-pr-v1-20260611` | `control-plane/auto-progress-phase1-issue281-closeout-v1-20260611` | clean | `MERGE_INTO_NEW_WORKFLOW` | Preserve. |
| `/home/l4nd0/tenn-git-hygiene-skill-v1-20260607` | `safe/tenn-git-hygiene-skill-v1-20260607` | clean | `MERGE_INTO_NEW_WORKFLOW` | Historical source for Git guard. |
| `/home/l4nd0/tenn-goal-monitor-stop-loop-fix-v1-20260613` | `control-plane/goal-monitor-stop-loop-fix-v1-20260613` | clean | `CORE_KEEP` | Preserve as Stop-hook loop evidence. |
| `/home/l4nd0/tenn-control-plane-pr-closeout-v1-20260607` | detached at PR #300 merge | dirty:1 | `UNKNOWN_NEEDS_OWNER_DECISION` | Preserve; review separately. |
| `/home/l4nd0/tenn-codex-automations-v1-20260516` | `safe/codex-automated-audit-runners-v1-20260516` | dirty:3 | `UNKNOWN_NEEDS_OWNER_DECISION` | Preserve; likely automation history. |
| `/home/l4nd0/tenn-pr335-merge-gate-v1-20260609` | `safe/pr335-merge-gate-v1-20260609` | dirty:1 | `UNKNOWN_NEEDS_OWNER_DECISION` | Preserve; merge-gate evidence. |

## Prunable Metadata Entries

These are metadata-only findings. No prune was run.

| Path | Branch/State | HEAD | Classification |
| --- | --- | --- | --- |
| `/tmp/tenn-appendix4d4e-contract-audit` | `audit/appendix4d4e-contract-expansion-v1` | `5bfdc3f4` | `OWNER_BOUNDARY` |
| `/tmp/tenn-merge-parking-review-wrapper-gate-20260604` | detached | `669d0030` | `OWNER_BOUNDARY` |
| `/tmp/tenn-origin-main-news-verify-20260607` | detached | `7443d9f2` | `OWNER_BOUNDARY` |
| `/tmp/tenn-replay-pr-LskTtF` | `codex/extraction-provenance-replay-reports-v1-20260608` | `a4fd1988` | `OWNER_BOUNDARY` |
| `/tmp/tenn-selector-pr-ziyrOK` | `codex/extraction-scale-table-selector-v1-20260608` | `55ef1fa1` | `OWNER_BOUNDARY` |

## Policy

Native Git Hygiene should not try to make this fleet clean automatically. It
should classify, preserve, and recommend. Cleanup requires a separate exact
approval manifest.

---

# Git Hygiene Integration

Source: `reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/GIT_HYGIENE_INTEGRATION.md`

Git Hygiene should become a required backend guard named `tenn-git-guard`, not a
separate command Orlando must remember.

## Preflight For Every Command

Every `/issue`, `/review-board`, and `/fix` run should do:

1. Identify worktree path, branch, HEAD, base, remote, and upstream.
2. Compare base relationship to `origin/migration/clean-runtime-baseline-reconstruct-v1`.
3. Read status with normal Git; if that fails, try explicit worktree gitdir; if
   both fail, stop with `DATA_MISSING`.
4. Run `python3 scripts/agent_job_registry.py list-active --read-only`.
5. Classify dirty files as task/report, hook/config, product/runtime/data,
   extraction/source, generated, user-owned unknown, or DATA_MISSING.
6. Search related PRs/issues read-only before suggesting mutation.
7. Detect owner-boundary paths and stale/superseded branches.

## Post-Run Enforcement

Every command should end with:

- changed-path guard;
- task-card validate and `check-diff` when safe;
- report-local `STATE.md` or `README.md`;
- worker result check if subagents ran;
- no unreported dirty files in worker worktrees;
- next goal or blocked state.

## Stop-Hook Integration

Stop hooks should be backstops only. The workflow should discover dirty-state,
registry, and allowlist problems before work starts. Stop hooks then verify:

- active task card still validates;
- current diff is inside allowlist;
- active registry status is visible;
- report/STATE exists when needed;
- no unexplained dirty state remains.

## Cleanup Rule

No cleanup unless explicitly approved. Git guard may recommend:

- ignore;
- preserve;
- review;
- park;
- later clean.

It may not delete, prune, stash, reset, merge, rebase, cherry-pick, push, or
mutate GitHub by default.

---

# Operator Workflow

Source: `reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/OPERATOR_WORKFLOW.md`

## When Something Is Broken

Use `/issue`.

Expected behavior:

- ask at most one or two clarifying questions if needed;
- run Git guard preflight;
- inspect current issue/PR/report evidence;
- invoke the `diagnose` loop only when a reproducible bug or performance
  regression is actually in scope;
- produce `ISSUE.md`, `MILESTONES.md`, context pack, and `NEXT_GOAL.md`.

## When Orlando Wants An Explanation

Use `/explain`.

It should explain:

- what the thing is;
- why it exists;
- current state;
- risks;
- what changed;
- what is still broken;
- what Orlando should do next.

It should write `EXPLAIN.md` when the topic is non-trivial or likely to be
reused.

## When Orlando Wants Implementation

Use `/fix`.

Expected behavior:

- read issue/board decision;
- run Git guard;
- create or validate a task card;
- spawn bounded workers only when useful;
- integrate one coherent change;
- run focused validation;
- run code review;
- prepare PR only with approval.

## Before Risky Merges

Use `/review-board`, then `code-reviewer`.

`/review-board` should produce `BOARD.md`, `BOARD_DECISION.json`, and
`NEXT_GOAL.md`. It must end with a decision: merge, fix first, park, supersede,
or block.

## Repo Hygiene

Do not run cleanup by default. Git Hygiene should happen automatically inside
every command. Invoke a full hygiene audit only when Orlando explicitly wants a
fleet/branch/worktree cleanup plan.

## What Requires Owner Approval

- GitHub writes;
- commits, pushes, PR creation, merge, rebase, cherry-pick;
- branch deletion, worktree removal, prune, stash, reset, clean;
- product/runtime/data/extraction mutation;
- DB/Qdrant/Redis/news/memory/source-PDF/gold-label/model/GPU/service changes;
- broad dependency, CI, or hook behavior changes.

## Avoiding Report-Only Loops

Every report-only command must end with one of:

- execute next safe task;
- ask for a specific approval;
- park with an owner decision;
- close as no-op with evidence;
- create one concrete next goal.

Do not create another report whose only output is "run another report".

## Avoiding Dirty Worktree Sprawl

- one worker, one worktree, one lane, one result file;
- no worker leaves unreported dirt;
- workers never share a mutation surface;
- all worker output goes into `WORKER_RESULT.md`;
- orchestrator integrates or parks worker output before ending.

---

# Overlaps And Conflicts

Source: `reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/OVERLAPS_AND_CONFLICTS.md`

| Overlap | Problem | Recommendation | Classification |
| --- | --- | --- | --- |
| `diagnose` vs proposed `/issue` | Diagnose is a debugging discipline, not full issue framing. | `/issue` wraps `diagnose`; do not replace it. | `CORE_KEEP` |
| `tenn-auto-progress` vs `/issue` | Both rank/select next work. | Use auto-progress as `/issue` candidate engine. | `MERGE_INTO_NEW_WORKFLOW` |
| `tenn-frame-design` vs `tenn-goal-report` | Both write state artifacts. | Frame is planning template; goal report is closeout. | `MERGE_INTO_NEW_WORKFLOW` |
| Scribe vs `OPERATOR_NOTES.md`/`DECISIONS.md` | Scribe as a standalone concept adds vocabulary. | Fold Scribe into durable notes and decisions. | `MERGE_INTO_NEW_WORKFLOW` |
| `tenn-git-hygiene` vs `tenn-task-card-registry-safety` | Both preflight dirty state and registry. | Merge as `tenn-git-guard` backend; keep task-card script as engine. | `MERGE_INTO_NEW_WORKFLOW` |
| `code-reviewer` vs `/review-board` | Code review is not multi-perspective board review. | Keep code-reviewer as final diff gate. | `CORE_KEEP` |
| `improve-codebase-architecture` vs `architecture-check` | One proposes improvements, one checks invariants. | Keep both roles; Tenn wrapper selects which. | `CORE_KEEP` |
| Generic `triage` vs Tenn labels | Generic labels conflict with Tenn label vocabulary. | Deprecate direct use; use Tenn `/issue`. | `DEPRECATE` |
| Host hooks vs repo hooks | Both warn/check dirty state and task-card scope. | Align messages; repo commands should preflight before hooks fire. | `MERGE_INTO_NEW_WORKFLOW` |

## Unnecessary Report-Only Loops

- auto-progress planning packet followed by another planning packet without
  owner decision;
- hygiene audit followed by hygiene audit without an approval manifest;
- issue-resolution review followed by closeout review followed by board review
  without a final disposition;
- Frame artifacts that do not produce `NEXT_GOAL.md` or `WAITING_ON_USER`.

## Necessary Safety Pieces

- task cards before implementation-capable edits;
- exact `allowed_files`;
- read-only registry list-active;
- dirty-file classification;
- GitHub read-before-write;
- worker worktree ownership;
- Stop hook and final changed-path guard;
- final code review before merge.

---

# Target Architecture

Source: `reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/TARGET_ARCHITECTURE.md`

## Smallest Future Stack

| Component | Purpose | Invoked By | Inputs | Outputs | Allowed Mutations | Stop States | Git Hygiene Relation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `tenn-issue` | Frame vague problems into executable issues. | Orlando `/issue`. | User problem, repo/GitHub/report evidence. | `ISSUE.md`, `MILESTONES.md`, context pack, `NEXT_GOAL.md`. | Report-local drafts only by default. | `DONE`, `DONE_WITH_RISK`, `WAITING_ON_USER`, `DATA_MISSING`. | Mandatory preflight and candidate ranking. |
| `tenn-review-board` | Independent perspectives and decision. | Orlando before risky decisions. | Issue, PR, branch, report, diff. | `BOARD.md`, `BOARD_DECISION.json`, `NEXT_GOAL.md`. | Report-local. | merge/fix/park/block/supersede. | Must classify branch/PR/dirty state first. |
| `tenn-fix` | Orchestrate implementation. | Orlando `/fix`. | Issue or board decision, task card. | `STATE.md`, validation, PR draft/URL if approved. | Task-card allowlist only. | done, blocked, waiting, validation failed. | Owns worker worktrees and post-run diff. |
| `tenn-worker` | Bounded subagent execution. | `tenn-fix`. | Worker brief, lane, worktree, allowed paths. | `WORKER_RESULT.md`. | Only assigned scope. | completed, blocked, data-missing. | One worker, one worktree, no unreported dirt. |
| `tenn-explain` | Layman-depth explanation. | Orlando `/explain`. | Issue, PR, branch, report, subsystem, skill. | `EXPLAIN.md` when durable. | Report-local only. | done or data-missing. | Runs read-only Git guard for branch/PR topics. |
| `tenn-code-reviewer` | Final diff/PR review. | `tenn-fix`, Orlando. | Diff, task card, validation logs. | `PR_REVIEW.md`. | Read-only by default. | pass/fail/block. | Refuses review if diff scope unknown. |
| `tenn-improve-codebase-architecture` | Find or execute structural improvements. | Orlando. | Domain docs, code map, issue/board decision. | Architecture report, bounded task card. | Report-only unless execution mode approved. | recommendation, waiting, fixed, blocked. | Must use task-card and Git guard for execution. |
| `tenn-git-guard` | Quiet backend safety guard. | Every command. | Worktree, branch, dirty files, PRs, registry. | preflight JSON/markdown, dirty classification. | None by default. | pass, warning, block, data-missing. | The Git Hygiene backend. |

## Minimum Artifact Set

| Artifact | Keep? | Role |
| --- | --- | --- |
| `ISSUE.md` | Yes | Problem framing and current evidence. |
| `MILESTONES.md` | Yes | Phased route from issue to completion. |
| `BOARD.md` | Yes | Multi-perspective review narrative. |
| `BOARD_DECISION.json` | Yes | Machine-readable decision. |
| `NEXT_GOAL.md` | Yes | Concrete next command/prompt. |
| `STATE.md` | Yes | Current orchestrator state. |
| `WORKER_RESULT.md` | Yes | Worker closeout. |
| `PR_REVIEW.md` | Yes | Final code review. |
| `DECISIONS.md` | Yes | Durable owner/agent decisions. |
| `EXPLAIN.md` | Yes | Durable explanation. |

## Product/Runtime/Extraction Boundary

All target components default to no product/runtime/data/extraction mutation.
Execution mode requires a task card, exact allowlist, owner approval when
crossing high-risk boundaries, and focused validation.

---

# Deprecation Plan

Source: `reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/DEPRECATION_PLAN.md`

This is a plan only. Nothing was deleted or cleaned.

## Keep

- `diagnose`
- `code-reviewer`
- `improve-codebase-architecture`
- repo `AGENTS.md`
- repo `.agents/skills/tenn-goal-report`
- repo `.agents/skills/tenn-task-card-registry-safety`
- task-card/registry/hook scripts
- merge parking registry

## Merge Into New Workflow

- `tenn-auto-progress` into `/issue`
- `tenn-frame-design` into `/issue` and `/fix` long-run templates
- `tenn-git-hygiene` into `tenn-git-guard`
- host `tenn-issue-finder`, `tenn-issue-closeout`,
  `tenn-issue-resolution-reviewer` into `/issue`, `/fix`, and
  `/review-board`
- `handoff` into report-local `STATE.md`/`NEXT_GOAL.md`

## Rename Or Rehome

- Claude command docs remain Claude-specific references.
- Architecture cleanup should be Tenn-wrapped and not use stale `.cursor/rules`
  assumptions by default.

## Deprecate

- Direct generic `triage` for Tenn because labels and mutation behavior differ.
- Host `~/.codex/rules/default.rules` as a general Tenn rule source.

## Owner Boundary

- Host Codex config and hooks.
- Cockpit flag orchestrator.
- Financial Truth extraction skill.
- Worktree cleanup/pruning.
- Current dirty `.githooks/pre-push` and existing dirty report artifacts.

## Delete Candidates

No delete candidate is safe to name from this report-only audit alone. Deletion
requires a follow-up cleanup task with exact path hashes, ownership evidence,
and approval.

---

# Implementation Sequence

Source: `reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/IMPLEMENTATION_SEQUENCE.md`

## Shot 1: Design And Wrappers

1. Create task card for dev-flow wrappers only.
2. Add instruction-only repo skills:
   - `tenn-issue`
   - `tenn-review-board`
   - `tenn-fix`
   - `tenn-worker`
   - `tenn-explain`
   - `tenn-code-reviewer`
   - `tenn-improve-codebase-architecture`
   - `tenn-git-guard`
3. Do not delete or edit existing host skills.
4. Make wrappers point to existing skills/scripts.
5. Add example artifact templates.
6. Validate task card, registry read-only, `git diff --check`, and path guard.

## Shot 2: Backend Guard Integration

1. Add a report-only Git guard script or wrapper only if approved.
2. Make `/issue`, `/review-board`, and `/fix` call Git guard preflight.
3. Add worktree/branch/PR relationship output.
4. Add worker result enforcement.
5. Keep cleanup disabled.

## Shot 3: Trial Run

1. Run `/issue` on issue #78 or #291 without GitHub writes.
2. Produce `ISSUE.md`, `MILESTONES.md`, context pack, and `NEXT_GOAL.md`.
3. Review whether the command reduced operator burden.

## Shot 4: Controlled Execution

1. Run `/fix` on one low-risk control-plane issue.
2. Use one worker if useful.
3. Run focused validation and code-reviewer.
4. Stop before PR unless approved.

## Success Criteria

- Orlando can use fewer commands.
- Git Hygiene is automatic and quiet.
- Report-only loops end in decisions.
- Workers cannot leave invisible dirt.
- Product/runtime/extraction boundaries stay explicit.

---

# Owner Decisions

Source: `reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/OWNER_DECISIONS.md`

These need Orlando's decision before implementation or cleanup.

| Decision | Options | Recommendation |
| --- | --- | --- |
| `/diagnose` vs `/issue` | Replace diagnose, rename diagnose, or wrap diagnose. | Wrap diagnose with `/issue`; keep diagnose. |
| Add `/explain` | Host-only, repo skill, or no first-class skill. | Add repo `tenn-explain`. |
| Architecture command | Use host skill directly or Tenn wrapper. | Add Tenn wrapper around host `improve-codebase-architecture`. |
| Git Hygiene | Standalone command or backend guard. | Backend guard for every command. |
| Scribe | Keep separate or fold into state/decisions. | Fold into `STATE.md`, `DECISIONS.md`, and operator notes. |
| Auto-progress | Standalone or candidate engine. | Candidate engine inside `/issue`. |
| Generic `triage` | Use directly or deprecate. | Deprecate direct use for Tenn. |
| Host `post_apply_patch.py` | Keep broad, exempt report-only, or disable for Tenn. | Decide separately; likely exempt report-only paths. |
| Worktree cleanup | Start cleanup now or separate approved wave. | Separate approved wave only. |
| Dirty `.githooks/pre-push` in current checkout | Adopt, revert, park, or preserve. | Preserve and review in a dedicated hook task. |

---

# Validation

Source: `reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/VALIDATION.md`

## Commands Run

| Command | Exit | Result |
| --- | ---: | --- |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/dev_flow_ground_up_reset_audit_v1_20260616.md` | 0 | Passed. |
| `python3 scripts/agent_job_registry.py list-active --read-only` | 0 | Passed; `active_jobs: []`, `read_only: true`, `lock_acquired: false`. |
| `git ls-remote origin refs/heads/migration/clean-runtime-baseline-reconstruct-v1` | 0 | Remote base resolved to `227e1ce0d4e99c4a13ece8012a44adeba4585cdf`. |
| `git worktree list --porcelain` | 0 | 479 Tenn worktree entries found. |
| Worktree classifier | 0 | 82 dev-flow/control-plane, 331 product/runtime/extraction, 5 prunable metadata, 61 unknown/review-needed. |
| `gh auth status` | 0 | Authenticated read-only inspection available. |
| Focused `gh issue` and `gh pr` reads | 0 | Read-only context gathered for issues #78/#291/#234 and PRs #320/#344. |
| `git diff --check` with explicit `GIT_DIR`/`GIT_WORK_TREE` | 0 | Passed. |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/dev_flow_ground_up_reset_audit_v1_20260616.md --no-write-report` | 0 | Passed; changed non-ignored file is only the audit task card. |
| `python3 scripts/agent_job_contract.py check-artifacts docs/agent_tasks/dev_flow_ground_up_reset_audit_v1_20260616.md` | 0 | Passed; all 15 report files exist and are non-empty. |
| Final changed-path guard | 0 | Non-ignored changes: only `docs/agent_tasks/dev_flow_ground_up_reset_audit_v1_20260616.md`; report files appear under ignored `reports/`. |

## Known Validation Risks

- A mid-run normal `git status` failed with
  `fatal: this operation must be run in a work tree`; later normal status and
  explicit `GIT_DIR`/`GIT_WORK_TREE` status succeeded. Treat this as transient
  checkout fragility, not repaired by this audit.
- A mid-run explicit status probe showed unrelated dirty hook/report paths, but
  final status did not. This audit did not modify those paths.

## No-Mutation Confirmations

- No product/runtime/data/extraction files were intentionally edited.
- No host-global Codex files were edited.
- No GitHub mutation was performed.
- No branch/worktree deletion, prune, clean, reset, stash, merge, rebase,
  cherry-pick, push, or force-push was performed.
- No product/runtime/data/extraction path appeared in the final non-ignored
  changed-path guard.
