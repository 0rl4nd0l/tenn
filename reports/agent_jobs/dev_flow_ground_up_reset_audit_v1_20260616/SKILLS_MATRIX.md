# Skills Matrix

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
