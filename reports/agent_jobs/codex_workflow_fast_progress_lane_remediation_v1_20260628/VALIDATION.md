# Validation

## V4 Current-Base Refresh Commands

| Command | Result |
| --- | --- |
| `git fetch origin migration/clean-runtime-baseline-reconstruct-v1 control-plane/codex-workflow-fast-progress-lane-current-v1-20260628` | pass; canonical `origin/migration/clean-runtime-baseline-reconstruct-v1` at `265a0d5a8125254c099e391087724097d6200517`; PR #460 branch at `d7998a9c3fa1dbb060e930d246366a33d161698f` |
| `git apply --3way /tmp/codex-workflow-fast-progress-v3-d7998a9c.patch` | pass; validated v3 diff replayed onto current canonical without merge, rebase, or cherry-pick |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/codex_workflow_fast_progress_lane_remediation_v1_20260628.md` | pass, `ok: true` |
| `python3 scripts/agent_task_ledger.py --repo-root . validate` | pass, `ok: true`, live and committed sources checked |
| `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` | pass, read-only; zero active jobs |
| `python3 .agents/skills/tenn-git-guard/tests/test_tenn_git_guard.py` | pass, 11 tests |
| `python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "codex workflow fast progress lane v4 current-base replay" --fallback-sample-limit 3 --json` | pass as smoke; final decision blocked only because intended task edits made the worktree dirty |
| `python3 -m venv financial-engine_v2/.venv && financial-engine_v2/.venv/bin/python -m pip install ruff==0.15.6 pytest PyYAML` | pass; restored ignored local hook tooling in this fresh worktree |
| `bash .githooks/pre-push` | pass; ruff passed, hook/tooling tests `68 passed, 1 warning`, markdown hygiene passed |
| `find .agents/skills -maxdepth 2 -name SKILL.md \| sort \| wc -l` | 12; no new visible skill added |
| `git diff --check` | pass |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/codex_workflow_fast_progress_lane_remediation_v1_20260628.md --no-write-report` | pass, `ok: true` |
| `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/codex_workflow_fast_progress_lane_remediation_v1_20260628.md` | pass, `ok: true` |
| `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/codex_workflow_fast_progress_lane_remediation_v1_20260628.md --repo-root .` | pass, `ok: true` |
| `git fetch origin migration/clean-runtime-baseline-reconstruct-v1 control-plane/codex-workflow-fast-progress-lane-current-v1-20260628` | pass after local commit; canonical remained `265a0d5a8125254c099e391087724097d6200517`, PR #460 branch remained `d7998a9c3fa1dbb060e930d246366a33d161698f` |
| `git rev-list --left-right --count HEAD...origin/migration/clean-runtime-baseline-reconstruct-v1` | pass after local commit; `1 0`, exactly one commit ahead and zero behind |
| `python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "PR #460 v4 current-base replay post-commit" --fallback-sample-limit 3 --json` | pass after local commit; `VALID_TASK_WORKTREE`, `stop_reimplementation=false`, `NO_MATCHING_ACTIVE_WORK_FOUND`, ledger `PASS`, registry `PASS`, final decision `pass` |
| `bash .githooks/pre-push` | pass after local commit; ruff passed, hook/tooling tests `68 passed, 1 warning`, markdown hygiene passed |

## V3 Current-Base Refresh Commands

| Command | Result |
| --- | --- |
| `git fetch origin migration/clean-runtime-baseline-reconstruct-v1 control-plane/codex-workflow-fast-progress-lane-current-v1-20260628` | pass; canonical `origin/migration/clean-runtime-baseline-reconstruct-v1` at `87e49247a0ddbf5e35fd6b7c2b61ea5a1fe9d74c`; PR #460 branch at `d3dfd1a746f96ddd4be542046d611d4cf8e32933` |
| `git apply --3way /tmp/codex-workflow-fast-progress-v2-4e5beeef.patch` | pass; validated v2 diff replayed onto current canonical without merge, rebase, or cherry-pick |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/codex_workflow_fast_progress_lane_remediation_v1_20260628.md` | pass, `ok: true` |
| `python3 scripts/agent_task_ledger.py --repo-root . validate` | pass, `ok: true`, live and committed sources checked |
| `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` | pass, read-only; zero active jobs |
| `python3 .agents/skills/tenn-git-guard/tests/test_tenn_git_guard.py` | pass, 11 tests |
| `python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "codex workflow fast progress lane v3 current-base replay" --fallback-sample-limit 3 --json` | pass as smoke; final decision blocked only because intended task edits made the worktree dirty |
| `python3 -m venv financial-engine_v2/.venv && financial-engine_v2/.venv/bin/python -m pip install ruff==0.15.6 pytest PyYAML` | pass; restored ignored local hook tooling in this fresh worktree |
| `bash .githooks/pre-push` | pass; ruff passed, hook/tooling tests `68 passed, 1 warning`, markdown hygiene passed |
| `find .agents/skills -maxdepth 2 -name SKILL.md \| sort \| wc -l` | 12; no new visible skill added |
| `git diff --check` | pass |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/codex_workflow_fast_progress_lane_remediation_v1_20260628.md --no-write-report` | pass, `ok: true` |
| `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/codex_workflow_fast_progress_lane_remediation_v1_20260628.md` | pass, `ok: true` |
| `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/codex_workflow_fast_progress_lane_remediation_v1_20260628.md --repo-root .` | pass, `ok: true` |
| `git fetch origin migration/clean-runtime-baseline-reconstruct-v1 control-plane/codex-workflow-fast-progress-lane-current-v1-20260628` | pass after local commit; canonical remained `87e49247a0ddbf5e35fd6b7c2b61ea5a1fe9d74c`, PR #460 branch remained `d3dfd1a746f96ddd4be542046d611d4cf8e32933` |
| `git rev-list --left-right --count HEAD...origin/migration/clean-runtime-baseline-reconstruct-v1` | pass after local commit; `1 0`, exactly one commit ahead and zero behind |
| `python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "PR #460 v3 current-base replay post-commit" --fallback-sample-limit 3 --json` | pass after local commit; `VALID_TASK_WORKTREE`, `stop_reimplementation=false`, `NO_MATCHING_ACTIVE_WORK_FOUND`, ledger `PASS`, registry `PASS`, final decision `pass` |
| `bash .githooks/pre-push` | pass after local commit; ruff passed, hook/tooling tests `68 passed, 1 warning`, markdown hygiene passed |
| owner approval | pass; Orlando approved exact force-with-lease update of PR #460 branch after v3 validation |

## V2 Current-Base Refresh Commands

| Command | Result |
| --- | --- |
| `git fetch origin migration/clean-runtime-baseline-reconstruct-v1 control-plane/codex-workflow-fast-progress-lane-current-v1-20260628` | pass; canonical `origin/migration/clean-runtime-baseline-reconstruct-v1` at `129c299633db8cd3256bebf02afcd762c73413a1`; PR #460 branch at `d3dfd1a746f96ddd4be542046d611d4cf8e32933` |
| `git apply --3way /tmp/codex-workflow-fast-progress-pr460-d3dfd1a7.patch` | pass; PR #460 diff replayed onto current canonical without merge, rebase, or cherry-pick |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/codex_workflow_fast_progress_lane_remediation_v1_20260628.md` | pass, `ok: true` |
| `python3 scripts/agent_task_ledger.py --repo-root . validate` | pass, `ok: true`, live and committed sources checked |
| `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` | pass, read-only; zero active jobs |
| `python3 .agents/skills/tenn-git-guard/tests/test_tenn_git_guard.py` | pass, 11 tests |
| `python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "codex workflow fast progress lane v2 current-base replay" --fallback-sample-limit 3 --json` | pass as smoke; summary fallback returned branch/worktree dicts capped at 3 samples; final decision blocked only because intended task edits made the worktree dirty |
| `python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "codex workflow fast progress lane v2 current-base replay" --fallback-detail full --json` | pass as smoke; full fallback returned branch/worktree lists |
| `python3 -m venv financial-engine_v2/.venv && financial-engine_v2/.venv/bin/python -m pip install ruff==0.15.6 pytest PyYAML` | pass; restored ignored local hook tooling in this fresh worktree |
| `bash .githooks/pre-push` | pass; ruff passed, hook/tooling tests `68 passed, 1 warning`, markdown hygiene passed |
| `find .agents/skills -maxdepth 2 -name SKILL.md \| sort \| wc -l` | 12; no new visible skill added |
| skill frontmatter/H1 check script | pass |
| `git diff --check` | pass |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/codex_workflow_fast_progress_lane_remediation_v1_20260628.md --no-write-report` | pass, `ok: true` |
| `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/codex_workflow_fast_progress_lane_remediation_v1_20260628.md` | pass, `ok: true` |
| `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/codex_workflow_fast_progress_lane_remediation_v1_20260628.md --repo-root .` | pass, `ok: true` |

## Prior PR #460 Commands

| Command | Result |
| --- | --- |
| `git fetch origin migration/clean-runtime-baseline-reconstruct-v1` | pass; canonical `origin/migration/clean-runtime-baseline-reconstruct-v1` at `7a0bab4ca9337c6c9d735f23d5898d9b306ecc2d` |
| `git apply --3way /tmp/codex-workflow-fast-progress-lane-093d4811.patch` | pass; allowlisted stale-branch diff replayed onto current canonical |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/codex_workflow_fast_progress_lane_remediation_v1_20260628.md` | pass, `ok: true` |
| `python3 scripts/agent_task_ledger.py --repo-root . validate` | pass, `ok: true`, live and committed sources checked |
| `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` | pass, read-only; zero active jobs |
| `python3 .agents/skills/tenn-git-guard/tests/test_tenn_git_guard.py` | pass, 11 tests |
| `python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "codex workflow fast progress lane remediation current-base" --fallback-sample-limit 3 --json` | pass as smoke; summary fallback returned branch/worktree dicts capped at 3 samples; final decision blocked only because intended task edits made the worktree dirty |
| `python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "codex workflow fast progress lane remediation current-base" --fallback-detail full --json` | pass as smoke; full fallback returned branch/worktree lists |
| `python3 -m venv financial-engine_v2/.venv && financial-engine_v2/.venv/bin/python -m pip install ruff==0.15.6 pytest PyYAML` | pass; restored ignored local hook tooling in this fresh worktree |
| `bash .githooks/pre-push` | pass; ruff passed, hook/tooling tests `68 passed, 1 warning`, markdown hygiene passed |
| `find .agents/skills -maxdepth 2 -name SKILL.md \| sort \| wc -l` | 12; no new visible skill added |
| skill frontmatter/H1 check script | pass |
| `git diff --check` | pass |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/codex_workflow_fast_progress_lane_remediation_v1_20260628.md --no-write-report` | pass, `ok: true` |
| `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/codex_workflow_fast_progress_lane_remediation_v1_20260628.md` | pass, `ok: true` |
| `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/codex_workflow_fast_progress_lane_remediation_v1_20260628.md --repo-root .` | pass, `ok: true` |
| `python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "codex workflow fast progress lane current-base post-commit" --fallback-sample-limit 3 --json` | pass after local commit; `VALID_TASK_WORKTREE`, `stop_reimplementation=false`, `NO_MATCHING_ACTIVE_WORK_FOUND`, ledger `PASS`, registry `PASS`, final decision `pass` |
| `git rev-list --left-right --count HEAD...origin/migration/clean-runtime-baseline-reconstruct-v1` | pass after fetch; `1 0`, exactly one commit ahead and zero behind |
| `git status --short --branch --untracked-files=all` | clean tracked status; branch ahead 1 of canonical |
| `git push -u origin HEAD:control-plane/codex-workflow-fast-progress-lane-current-v1-20260628` | pass; pre-push hook reran and passed, remote branch created |
| `gh pr create --base migration/clean-runtime-baseline-reconstruct-v1 --head control-plane/codex-workflow-fast-progress-lane-current-v1-20260628` | pass; opened PR #460 |

## Changed-Path Guards

- Product/runtime/data/extraction/count-24 files changed: none.
- Host-global files changed: none.
- Visible repo skill count increased: no.
- Runtime Functionality Proof required: no, control-plane-only task.

## Known Caveat

The installed host guard runner may not have this repo change yet. The docs now
tell agents to use the repo-backed fallback from a current Tenn control-plane
checkout if the host runner rejects `--fallback-detail` or still emits full
fallback rows by default.
