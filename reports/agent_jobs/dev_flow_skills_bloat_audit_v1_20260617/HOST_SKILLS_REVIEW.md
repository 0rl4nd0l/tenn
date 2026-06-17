# Host Skills Review

## Host Skill Roots Inspected

| Root | Count | Decision |
| --- | ---: | --- |
| `/home/l4nd0/.codex/skills` | 36 | Keep host-only; wrap Tenn-relevant workflows. |
| `/home/l4nd0/.agents/skills` | 1 | Owner-boundary specialty surface. |
| `/home/l4nd0/.codex/plugins/cache/openai-curated` | 66 | Plugin-domain only. |
| `/home/l4nd0/.codex/plugins/cache/openai-curated-remote` | 71 | Plugin-domain only. |

## Host Skills That Should Remain Host-Only

- `diagnose`
- `code-reviewer`
- `code-fixer`
- `function-quality`
- `improve-codebase-architecture`
- `architecture-check`
- `architecture-cleanup-steward`
- `handoff`
- `triage`
- `to-issues`
- `to-prd`
- `tdd`
- `pdf`
- `playwright`
- `playwright-interactive`
- `performance-check`
- `rag-stability-eval`
- `prompt-crafter`
- `prompt-structure-reference`
- `graphify`

Reason: these are useful tools, but raw invocation lacks Tenn task-card,
registry, issue-label, current-evidence, and forbidden-surface discipline.

## Host Skills Worth Repo Wrapping

| Host skill | Existing or future Tenn wrapper |
| --- | --- |
| `diagnose` | Invoke from `tenn-issue` or `tenn-fix` only when repro/debug loop is needed. |
| `code-reviewer` | Existing `tenn-code-reviewer`. |
| `code-fixer` | Existing `tenn-fix`. |
| `function-quality` | Existing `tenn-financial-metric-extraction`; possible future feature-quality wrapper. |
| `improve-codebase-architecture` | Existing `tenn-improve-codebase-architecture`. |
| `handoff` | Future `tenn-handoff` or repo template. |
| `triage` / `to-issues` / `to-prd` | Tenn issue docs and `tenn-issue`; no direct raw use. |

## Plugin Skills

Plugin-provided skills are good specialty tools but noisy in Tenn day-to-day
selection. Keep them behind explicit plugin/domain triggers:

- iOS/macOS app work
- web app/data visualization work
- security scans
- GitHub PR/CI/comment workflows
- Google Drive/Docs/Sheets/Slides
- OpenAI developer apps/API key workflows
- Hugging Face models/datasets/jobs
- investment banking workflows
- public equity investing workflows

Recommendation: do not mirror plugin skills into Tenn docs. Document one line:
"Plugin skills are explicit-domain tools, not default Tenn workflow choices."

## Host Mutation Rules

- Do not mutate host-global skills or hooks without explicit owner approval.
- Do not sync `.agents/skills` into `$CODEX_HOME/skills` without a task card and
  host-global mutation approval.
- Do not treat host skills as current repo truth when repo `AGENTS.md` or
  `.agents/skills` disagree.
- If host skill behavior is needed repeatedly for Tenn, wrap the behavior in a
  Tenn repo skill or template rather than editing host-global state ad hoc.
