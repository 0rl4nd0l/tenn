# Validation

## Commands

- PASS: `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn --topic "persist null merge-base stale-path guard fix" --json`
  - result: blocked stale/non-canonical `/home/l4nd0/tenn`; no edits were made
    there.
- PASS: host-global vs repo-backed comparison before port.
  - result: repo-backed skill lacked only the null-merge-base stale-path helper,
    stale-path branch, and regression test.
- PASS: host-global vs repo-backed comparison after port.
  - result: repo-backed and host-global script/test are aligned for this fix.
- PASS: `python3 scripts/agent_job_contract.py validate docs/agent_tasks/null_merge_base_stale_path_guard_v1_20260623.md`
- PASS: `python3 .agents/skills/tenn-git-guard/tests/test_tenn_git_guard.py`
  - result: `Ran 9 tests ... OK`
- PASS: `python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "null merge-base stale path regression" --json`
  - result: guard command executed; current task worktree is dirty with intended
    related changes, so the guard blocks mutation as designed.
- PASS: repo-backed guard against `/home/l4nd0/tenn-merge-parking-registry-integrate-v1-20260604`
  - classification: STALE_PATH
  - final_decision: block
  - stop_reimplementation: true
  - merge_base_with_canonical: null
- PASS: visible repo-backed skill count check.
  - result: `skill_count=10`
- PASS: `git diff --check`
- PASS: forbidden product/runtime/data/extraction/count-24 path guard.
- PASS: Greyhound path guard.
- PASS: host-global path guard.
  - result: host-global files were not changed; comparison-only reads were used.
- PASS: `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/null_merge_base_stale_path_guard_v1_20260623.md --repo-root .`
  - result: `ok=true`; no disallowed files.
- PASS: `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/null_merge_base_stale_path_guard_v1_20260623.md --repo-root .`

## Scope Guard

This task is control-plane-only. It does not prove runtime functionality and
does not claim any product/runtime/data/extraction/count-24 behavior changed.
