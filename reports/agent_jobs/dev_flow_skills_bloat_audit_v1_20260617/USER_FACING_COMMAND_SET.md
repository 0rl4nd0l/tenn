# User-Facing Command Set

## Smallest Daily Set

| Command | Use it for | Should pick backend skills |
| --- | --- | --- |
| `/issue` | Convert a vague problem or "what next?" into one executable packet. | `tenn-git-guard`, task ledger, `diagnose` when needed, auto-progress ranking internally. |
| `/fix` | Implement exactly one approved task card or issue packet. | `tenn-git-guard`, task-card safety, `tenn-worker`, `tdd`, `code-fixer`, `tenn-code-reviewer`. |
| `/review-board` | Make high-risk proceed/block/park/supersede/ask-owner decisions. | git guard, architecture/security/domain perspectives, model tier `critical`. |
| `/explain` | Explain status, branch, issue, PR, report, hook, skill, or architecture in plain language. | `tenn-git-guard` when current-state claims matter. |
| `/goal` | Long-running or report-producing work with a visible state machine. | `tenn-goal-report`, optional frame templates, validation closeout. |
| `/handoff` or `/save` | Continue in another session. | future `tenn-handoff` plus host `handoff` as temp fallback. |

## Hide From Day-To-Day Operator Workflow

- `tenn-git-guard`
- `tenn-task-card-registry-safety`
- `tenn-worker`
- `tenn-code-reviewer`
- `tenn-improve-codebase-architecture`
- `tenn-auto-progress`
- `tenn-frame-design`
- `tenn-git-hygiene`
- host `code-reviewer`
- host `code-fixer`
- host `function-quality`
- host `triage`, `to-issues`, `to-prd`
- plugin-owned specialty skills

## Suggested Command Routing

```text
User asks "what should we do?"        -> /issue
User asks "fix this approved thing"   -> /fix
User asks "is this ready/merge/safe?" -> /review-board or tenn-code-reviewer
User asks "what is going on?"         -> /explain
User gives long audit/report goal     -> /goal
User says "save/handoff"              -> /handoff once repo-native exists
```

## Operator Text To Add Later

```markdown
Most Tenn work starts with `/issue`, `/fix`, `/review-board`, `/explain`, or
`/goal`. Do not choose backend skills manually unless you are explicitly
debugging the workflow. Backend guards choose git, task-card, registry, docs,
model, and worker behavior.
```
