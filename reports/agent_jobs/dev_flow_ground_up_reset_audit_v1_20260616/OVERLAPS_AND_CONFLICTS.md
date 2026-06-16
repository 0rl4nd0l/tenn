# Overlaps And Conflicts

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
