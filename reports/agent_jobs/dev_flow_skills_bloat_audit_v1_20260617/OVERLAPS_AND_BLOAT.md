# Overlaps And Bloat

## Highest-Impact Overlaps

| Overlap | Problem | Recommendation |
| --- | --- | --- |
| `tenn-git-guard` vs `tenn-git-hygiene` | Both talk about branch, dirty state, registry, ledgers, duplicate work, and stop decisions. | Make `tenn-git-guard` the mandatory backend preflight. Keep `tenn-git-hygiene` only for explicit two-shot cleanup/hygiene audits. |
| `tenn-issue` vs `tenn-auto-progress` | Both rank next work and draft task-card-ish packets. | Fold auto-progress candidate ranking into `tenn-issue`; stop surfacing `tenn-auto-progress` as a daily skill. |
| `tenn-goal-report` vs `tenn-frame-design` | Both create `/goal` state and report artifacts. | Keep `tenn-goal-report`; rehome frame schema into templates and optional long-goal mode. |
| `tenn-fix` vs host `code-fixer` vs `tdd` | All can drive edits. | `tenn-fix` owns scope and task-card permission; host skills are internal tactics. |
| `tenn-code-reviewer` vs host `code-reviewer` vs security review skills | Multiple review gates can run on the same diff. | `tenn-code-reviewer` is the ordinary final gate; security skills only for explicit security scan/finding work. |
| `tenn-review-board` vs host issue-resolution reviewer | Both produce a decision on risky work. | Board for pre-action or merge/owner decisions; issue-resolution reviewer for closeout truth. |
| host `triage` / `to-issues` / `to-prd` vs Tenn issue wrappers | Generic labels and issue flows conflict with Tenn issue docs. | Use Tenn wrappers and docs; keep generic host skills host-only. |

## Skills With Too-Broad Triggers

| Skill | Risky phrase | Risk |
| --- | --- | --- |
| `tenn-auto-progress` | "choose the next safe unit of work" | Can capture broad owner intent and produce planning loops instead of execution. |
| `tenn-git-hygiene` | "dirty files, stale uncommitted work, merge/rebase candidates" | Can make ordinary preflight feel like a cleanup audit. |
| `tenn-frame-design` | "long-running /goal work" | Can add Frame artifacts to tasks that only need a README. |
| host `diagnose` | "reports a bug, says something is broken" | Could bypass Tenn issue/task-card framing if used raw. |
| host `to-issues` | "break down work into issues" | Can create duplicate GitHub backlog without Tenn duplicate gates. |
| legacy `cockpit-flag-orchestrator` | "investigate and fix... commit... resolve backend flag records" | Directly crosses service, commit, and backend mutation boundaries. |

## Report-Only Loop Sources

| Source | Loop pattern | Break condition |
| --- | --- | --- |
| `/issue` followed by another `/issue` | issue packet creates another planning packet. | Next artifact must be `/fix`, review board, owner decision, issue/PR mutation approval, or explicit park. |
| `tenn-auto-progress` | ranking creates draft task cards but no executor. | Make it internal to `/issue`; choose one next card or stop with owner decision. |
| `tenn-frame-design` | Frame plus STATE plus notes can become a plan about plans. | Use only for long or risky goals; skip for narrow changes. |
| `tenn-review-board` | Board can recommend another board/review. | `BOARD_DECISION.json` must choose one actionable decision. |
| host issue finder | broad sweeps create more candidate issues. | Cap findings and require GitHub tracker or `NO_FOLLOWUP`. |

## Stale Or Confusing Surfaces

- `.codex/skills/cockpit-flag-orchestrator` exists but `docs/agents/skill-registry.md`
  labels `.codex/skills` as legacy/custom unless explicitly grandfathered.
- Host Tenn issue skills are more detailed than repo wrappers in some areas,
  but they are outside repo control and should not be treated as current repo
  truth.
- Plugin cache exposes many high-quality specialty skills, but they add noise
  to Tenn selection unless hidden behind explicit domain triggers.
- Active sibling worktree
  `/home/l4nd0/tenn-agent-ledger-runtime-handoff-v1-20260617` is changing
  ledger/handoff skills and templates. This audit should not implement in the
  same files until that work is resolved.

## Are There Too Many User-Facing Skills?

Yes. The repo should present at most six day-to-day commands. Most skills should
be backend guards selected by those commands. The current surface asks Orlando
to choose between planning, guard, frame, hygiene, review, worker, and host
skills that should be routing details.
