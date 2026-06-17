# Skill Recommendations

## Keep As Core User-Facing Tenn Commands

| Skill | Recommendation | Reason |
| --- | --- | --- |
| `tenn-issue` | `CORE_KEEP` | Best entry point for vague work, issue packets, duplicate checks, and exact next goals. |
| `tenn-fix` | `CORE_KEEP` | Main implementation orchestrator after task card or issue packet approval. |
| `tenn-review-board` | `CORE_KEEP` for high-risk work | Required for critical decisions, but should not be used for trivial edits. |
| `tenn-explain` | `CORE_KEEP` | Gives Orlando direct plain-English explanation without mutating state. |
| `tenn-goal-report` | `CORE_KEEP` as `/goal` backend | Needed for long report-producing runs and validation closeout. |
| `tenn-financial-metric-extraction` | `CORE_KEEP` for issue-backed Financial Truth only | High-value domain wrapper; trigger must stay narrow. |

## Keep As Backend Guards

| Skill | Recommendation | Reason |
| --- | --- | --- |
| `tenn-git-guard` | `BACKEND_KEEP` | Canonical branch/worktree/registry/task-ledger preflight. |
| `tenn-task-card-registry-safety` | `BACKEND_KEEP` | Exact task-card and allowed-files enforcement. |
| `tenn-worker` | `BACKEND_KEEP` | Subagent contract, not a user command. |
| `tenn-code-reviewer` | `BACKEND_KEEP` | Final review gate; should wrap host `code-reviewer`. |
| `tenn-improve-codebase-architecture` | `BACKEND_KEEP` | Useful architecture wrapper, but not routine. |
| host `diagnose` | `BACKEND_KEEP` | Keep separate discipline, invoke through `/issue` or `/fix` when repro/debug loop is needed. |
| host `code-reviewer` / `code-fixer` | `BACKEND_KEEP` | Valuable generic specialists, but Tenn wrapper must enforce scope. |
| host `function-quality` | `BACKEND_KEEP` | Strong read-only analysis, especially under Financial Truth wrappers. |
| host `handoff` | `BACKEND_KEEP` until repo-native handoff exists | Useful temp handoff, but not repo-visible enough. |

## Merge Or Rehome

| Skill | Action | Future target |
| --- | --- | --- |
| `tenn-auto-progress` | `MERGE_INTO_WRAPPER` | Fold candidate ranking into `tenn-issue`; keep dry-run scripts as backend utilities. |
| `tenn-frame-design` | `RENAME_OR_REHOME` | Move schema into `docs/dev_flow/templates/FRAME.md` and `OPERATOR_NOTES.md`; expose as `/goal --frame` behavior. |
| `tenn-git-hygiene` | `MERGE_INTO_WRAPPER` partially | Keep deep two-shot hygiene as reference; move mandatory preflight to `tenn-git-guard`. |
| host `zoom-out` | `MERGE_INTO_WRAPPER` behavior | Fold into `tenn-explain` as "higher-level explanation" mode. |
| host `triage` / `to-issues` / `to-prd` | `RENAME_OR_REHOME` behavior | Tenn issue wrappers should own label mapping and GitHub write gates. |

## Deprecate As Active Tenn Surfaces

| Skill/surface | Recommendation | Why |
| --- | --- | --- |
| `.codex/skills/cockpit-flag-orchestrator` | `DEPRECATE` as active default | It assumes backend API/service/commit/resolve behavior and stale CLAUDE-era context. |
| host `news-pipeline-remaining-fixes` | `DEPRECATE` after stale continuation is closed | Too specific to an older report; future news work should go through issue/task-card. |
| direct host `triage` for Tenn | `DEPRECATE` | Uses generic labels and issue flow that conflicts with Tenn label docs. |

## Owner-Boundary Skills

These should never be part of the default Tenn day-to-day command set:

- system skill creation/install/plugin creation
- host/global mutation or install skills
- Vast.ai/GPU provisioning
- Graphify corpus generation unless explicitly requested
- plugin-owned investment banking/public equity/Hugging Face/Google Drive/OpenAI/iOS/macOS/web/security skills except in their explicit domain
- `architecture-cleanup-steward` when cleanup/deletion is possible
- `grill-with-docs` when it would mutate docs
- `prototype` when it would create exploratory artifacts

## Recommended Operator Surface

Keep Orlando-facing docs to this short set:

```text
/issue
/fix
/review-board
/explain
/goal
/handoff or /save once repo-native handoff exists
```

All other repo and host skills should be described as backend helpers selected
by those commands, not things Orlando must choose manually.
