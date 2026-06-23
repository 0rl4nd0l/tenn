# Validation

## Commands And Results

| Command | Exit | Result |
| --- | ---: | --- |
| `git fetch origin migration/clean-runtime-baseline-reconstruct-v1 && git rev-parse origin/migration/clean-runtime-baseline-reconstruct-v1` | 0 | Canonical verified at `1a0f1a03741d692089a0125ecb2f10691b8da597`. |
| `git worktree add -b control-plane/portable-guard-first-guidance-v1-20260623 /home/l4nd0/tenn-portable-guard-first-guidance-v1-20260623 origin/migration/clean-runtime-baseline-reconstruct-v1` | 0 | Created fresh docs-only worktree from canonical. |
| `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "portable guard first-class active guidance" --json` | 0 | `final_decision=pass`, `guard_support_status=PASS`, `registry_status=PASS`, `ledger_status=PASS`. |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/portable_guard_first_guidance_v1_20260623.md` | 0 | Task card validates. |
| Docs grep order check across active guidance files | 0 | Portable guard command appears before repo-local `scripts/agent_*` command references in all checked files. |
| Visible skill count check | 0 | Before `10`, after `10`. |
| Skill frontmatter/H1 check | 0 | All 10 repo-backed skill files have YAML frontmatter and H1. |
| `git diff --check` | 0 | No whitespace errors. |
| Forbidden product/runtime/data/extraction/count-24/Greyhound path guard | 0 | No forbidden product/runtime/data/extraction/count-24/Greyhound paths changed. |
| Host-global path guard | 0 | No host-global or `.codex/` paths changed. |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/portable_guard_first_guidance_v1_20260623.md --repo-root .` | 0 | Allowed diff only; wrote `diff-check.json`. |

## Docs Grep Evidence

```text
PASS AGENTS.md guard_line=211 repo_line=218
PASS docs/README.md guard_line=30 repo_line=40
PASS docs/dev_flow/CONTROL_PLANE_STATUS.md guard_line=38 repo_line=42
PASS docs/dev_flow/CODEX_OPERATOR_GUIDE.md guard_line=20 repo_line=128
PASS docs/dev_flow/SKILLS_SURFACE.md guard_line=94 repo_line=none
PASS .agents/skills/tenn-git-guard/SKILL.md guard_line=24 repo_line=89
PASS .agents/skills/tenn-handoff/SKILL.md guard_line=36 repo_line=40
PASS .agents/skills/tenn-financial-metric-extraction/SKILL.md guard_line=15 repo_line=24
```

## Collision Evidence

- Portable guard preflight reported a separate
  `control_plane_docs_skills_surface_stale_report_cleanup_v1_20260623`
  registry record with broad docs allowlists.
- `ps -p <recorded-pid> -o pid=,etime=,cmd=` exited `1`; the recorded process
  was not alive.
- `gh pr list --repo 0rl4nd0l/tenn --state open --head control-plane/docs-skills-surface-stale-report-cleanup-v1-20260623 --json number,title,headRefName,baseRefName,updatedAt,isDraft`
  exited `0` and returned `[]`.
- `git ls-remote --heads origin control-plane/docs-skills-surface-stale-report-cleanup-v1-20260623 control-plane/portable-guard-first-guidance-v1-20260623`
  exited `0` with no matching remote branch before this task pushed.
- The stale registry record was not cleaned or mutated.

## Final Closeout Reruns

- `git diff --check`: exit `0`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/portable_guard_first_guidance_v1_20260623.md --repo-root .`: exit `0`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/portable_guard_first_guidance_v1_20260623.md --repo-root . --no-write-report`: exit `0`.
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/portable_guard_first_guidance_v1_20260623.md --repo-root .`: exit `0`.
- `git diff --cached --check`: exit `0`.
