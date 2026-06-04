# Parked Entry: extraction-appendix4d-profit-after-tax-alias-v1-20260602

- Status: `PARKED_SUPERSEDED`
- Branch: `safe/extraction-appendix4d-profit-after-tax-alias-v1-20260602`
- Lane: Financial Truth
- Worktree: `/home/l4nd0/tenn-extraction-appendix4d-profit-after-tax-alias-v1-20260602`
- HEAD: `9eb6f076a830f79a3f26aac1de4841b1e78c2d12`

## Why Parked

Evidence is strong enough to preserve, but this branch is no longer the
preferred integration surface. Later Appendix 4D wrapper-gate work carries the
source-bound wrapper metric-minimum path and targeted GPT proof. Preserve this
branch as historical alias evidence only.

## Evidence Present

- Task card exists.
- Summary status: `implemented`
- Summary says:
  - pytest: `5 passed`
  - `py_compile`: passed
  - `git diff --check`: passed
  - task-card validate: passed
  - targeted GPT Appendix 4D verification: not run
  - `validation.json`: missing

## Risk

- Medium.
- Canonical metric alias policy touched without the later wrapper-gate boundary.

## Recommended Next Action

Do not merge this branch. Use the later wrapper-gate work as the review source
after it is rebased or salvaged into a clean canonical worktree.
