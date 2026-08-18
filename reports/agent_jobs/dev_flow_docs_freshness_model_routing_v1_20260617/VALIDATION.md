# Validation

## Planned Checks

- Task-card validate.
- Registry list-active read-only.
- Parse changed `SKILL.md` files.
- Markdown/template field check.
- `git diff --check`.
- Task-card `check-diff --no-write-report`.
- Task-card report-artifact check.
- Changed-path guard.
- Product/runtime/data/extraction guard.
- Count-24 guard.
- Host-global guard.
- Final status.

## Results

| Check | Result |
| --- | --- |
| `git fetch origin migration/clean-runtime-baseline-reconstruct-v1` | pass |
| clean sibling worktree from canonical base | pass |
| repo/branch/HEAD/upstream/status preflight | pass |
| `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` | pass; `active_jobs=[]` |
| live task ledger | `DATA_MISSING` |
| committed task ledger | `DATA_MISSING` |
| duplicate-work search | pass with warning for related open PR #367 |
| skills-bloat audit canonical check | missing on canonical; preserved in this branch |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/dev_flow_docs_freshness_model_routing_v1_20260617.md` | pass |
| changed `SKILL.md` frontmatter/H1/required-field parse | pass |
| markdown/template required-field check | pass |
| `git diff --check` | pass |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/dev_flow_docs_freshness_model_routing_v1_20260617.md --no-write-report` | pass |
| `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/dev_flow_docs_freshness_model_routing_v1_20260617.md` | pass |
| changed-path guard | pass |
| product/runtime/data/extraction/count-24 guard | pass |
| host-global guard | pass |

## Changed-Path Guard

Only approved control-plane docs, skills, templates, task cards, and report
artifacts changed.

## Boundary Guard

- Product/runtime/data/extraction paths changed: no.
- Count-24 paths changed: no.
- Host-global paths changed: no.
- Dependency files, lockfiles, CI config, system packages, production/runtime
  venvs, runtime services, and model-provider config changed: no.

## Residual Risk

Open PR #367 touches several related control-plane skills and creates the
repo-native handoff workflow. This PR may need a small rebase or manual
reconciliation after #367 merges or is parked.
