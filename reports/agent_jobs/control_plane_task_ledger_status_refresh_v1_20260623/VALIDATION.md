# Validation

## Preflight

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/control_plane_task_ledger_status_refresh_v1_20260623.md`
  - Result: ok.
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
  - Result: ok, no active jobs.
- `python3 scripts/agent_task_ledger.py resolve-path`
  - Result:
    `/home/l4nd0/tenn-extraction-handoff-continuation-v1-20260621/.git/tenn-agent-registry/task-ledger.jsonl`.
- `python3 scripts/agent_task_ledger.py validate`
  - Result after snapshot: ok, `data_missing=["live"]`, committed entries=5.

## Ledger Evidence

- `python3 scripts/agent_task_ledger.py export-summary`
  - Result: failed closed because the resolved live ledger file is missing.
- `find /home/l4nd0/tenn-* -maxdepth 4 -path '*tenn-agent-registry/task-ledger.jsonl' -type f -print 2>/dev/null`
  - Result: no alternate bounded Tenn ledger file found.
- `python3 scripts/agent_task_ledger.py validate --entry-file docs/agent_registry/task_ledger/LEDGER.jsonl`
  - Result: ok, entry_count=5.
- `python3 scripts/agent_task_ledger.py summarize --format markdown`
  - Result: live `DATA_MISSING`; committed snapshot present with 5 merged entries.

## GitHub Evidence

- `gh pr view 380 --json number,title,state,mergedAt,mergeCommit,baseRefName,headRefName,url`
  - Result: `MERGED`, merge commit `4d62fec4e855b313ae89136e947510c627b9bcde`.
- `gh pr view 382 --json number,title,state,mergedAt,mergeCommit,baseRefName,headRefName,url`
  - Result: `MERGED`, merge commit `154888ecca6220ab598efcd140a2c2b62fca3da7`.
- `gh pr view 383 --json number,title,state,mergedAt,mergeCommit,baseRefName,headRefName,url`
  - Result: `MERGED`, merge commit `d6eeff4f3114096844dcb88e715ae39c9802487e`.
- `gh pr view 385 --json number,title,state,mergedAt,mergeCommit,baseRefName,headRefName,url`
  - Result: `MERGED`, merge commit `3df289e65e9dd97d6f9434c8eba29297145d7d83`.
- `gh pr view 386 --json number,title,state,mergedAt,mergeCommit,baseRefName,headRefName,url`
  - Result: `MERGED`, merge commit `e402bf38e5b959f56c1bed6b35e18ba7371cd8f6`.

## Final Checks

- `scripts/sync_codex_skills.sh`
  - Result: ok, dry run only, `would_link=10`, `linked=0`.
- `git diff --check`
  - Result: ok.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/control_plane_task_ledger_status_refresh_v1_20260623.md --repo-root .`
  - Result: ok, wrote
    `reports/agent_jobs/control_plane_task_ledger_status_refresh_v1_20260623/diff-check.json`.
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/control_plane_task_ledger_status_refresh_v1_20260623.md --repo-root .`
  - Result: ok, all 5 expected report artifacts present.
- Product/runtime/data/extraction/count-24 path guard.
  - Result: ok, no matching changed paths.
- Host-global path guard.
  - Result: ok, no matching changed paths.
- Skill-surface changed-path guard.
  - Result: ok, no matching changed paths.

## Closeout Classification

- Result: `DONE`.
- Runtime functionality proof: not required; task card declares
  `closeout_scope: control_plane_only`, and the change only updates
  control-plane ledger/docs/report artifacts.
- Remaining risk: live branch-independent task ledger remains `DATA_MISSING`
  and should be restored or intentionally reconfigured in a separate registry
  task if that live duplicate-work source is required.
