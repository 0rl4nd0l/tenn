# Validation

## Commands Run Before Mutation

| Command | Exit | Result |
| --- | ---: | --- |
| `git fetch origin refs/heads/migration/clean-runtime-baseline-reconstruct-v1:refs/remotes/origin/migration/clean-runtime-baseline-reconstruct-v1` | 0 | Canonical fetched. |
| `pwd` | 0 | Logical path reported as `/home/l4nd0/tenn`. |
| `pwd -P` | 0 | Physical path `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`. |
| `realpath /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` | 0 | Physical path confirmed. |
| `git remote -v` | 0 | Origin is `https://github.com/0rl4nd0l/tenn.git`. |
| `git branch --show-current` | 0 | `control-plane/dev-flow-agent-task-ledger-v1-20260616`. |
| `git rev-parse HEAD` | 0 | `137535b81a5b60d1f94ca630605caadccc4e1b99`. |
| `git rev-parse --abbrev-ref --symbolic-full-name @{u}` | 0 | `origin/control-plane/dev-flow-agent-task-ledger-v1-20260616`. |
| `git status --short --untracked-files=all` | 0 | Three modified skill files and two untracked task cards. |
| `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` | 0 | `active_jobs: []`; no lock acquired. |
| `gh pr view 367 ...` | 0 | PR #367 is open. |
| `gh pr view 368 ...` | 0 | PR #368 is merged. |
| `gh pr view 370 ...` | 0 | PR #370 is merged. |
| `gh pr view 373 ...` | 0 | PR #373 is merged. |

## Classification Checks

| Command | Exit | Result |
| --- | ---: | --- |
| `git diff -- .agents/skills/tenn-fix/SKILL.md .agents/skills/tenn-git-guard/SKILL.md .agents/skills/tenn-worker/SKILL.md` | 0 | Dirty patch is a 75-line validation-environment section across three skills. |
| `git diff origin/migration/clean-runtime-baseline-reconstruct-v1 -- .agents/skills/tenn-fix/SKILL.md .agents/skills/tenn-git-guard/SKILL.md .agents/skills/tenn-worker/SKILL.md` | 0 | Raw dirty working tree would regress PR #368 content; not replayed. |
| `git show origin/migration/clean-runtime-baseline-reconstruct-v1:docs/agent_tasks/dev_flow_skills_bloat_audit_v1_20260617.md` | 0 | Skills-bloat task card exists in canonical. |
| `git cat-file -e origin/migration/clean-runtime-baseline-reconstruct-v1:docs/agent_tasks/validation_environment_autonomy_skill_update_v1_20260617.md` | 128 | Validation-environment task card absent from canonical. |
| `git grep -n "Validation Environment Autonomy" origin/migration/clean-runtime-baseline-reconstruct-v1 -- .agents docs reports scripts tests` | 1 | Exact guidance absent from canonical. |
| `git cherry -v origin/migration/clean-runtime-baseline-reconstruct-v1 HEAD` | 0 | Original branch has two local commits not on canonical. |

## Clean Worktree Validation

| Command | Exit | Result |
| --- | ---: | --- |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/validation_environment_autonomy_skill_update_v1_20260617.md` | 1 then 0 | Initial run failed because `output_dir` did not match `job_id`; task card was patched to `job_id: dev_flow_dirty_branch_classification_v1_20260618`; rerun passed with `ok: true`. |
| `python3 scripts/agent_job_contract.py check-artifacts docs/agent_tasks/validation_environment_autonomy_skill_update_v1_20260617.md` | 1 then 0 | Initial run failed on the same task-card issue; rerun found all seven required report files. |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/validation_environment_autonomy_skill_update_v1_20260617.md --no-write-report` | 1 then 0 | Initial run failed on the same task-card issue; rerun passed for the three skill files and preserved task card. Reports are ignored, so `check-artifacts` is the report-bundle guard until force-add/staging. |
| `git diff --check` | 0 | No whitespace errors. |
| `sed -n '1,8p' ...; rg -n '^# ' ...` for the three changed skills | 0 | YAML `name` fields and primary H1s are present. |
| `git diff --name-only -- .` with allowed path exclusions | 0 | No unexpected non-ignored changed paths. |
| `git diff --name-only -- financial-engine_v2 scripts artifacts count-24` | 0 | No product/runtime/data/extraction/count-24/script/artifact changes in the clean worktree. |
| `git status --short --untracked-files=all` | 0 | Three modified skill files and one untracked task card before staging; report bundle is ignored by default. |
| `git status --ignored --short reports/agent_jobs/dev_flow_dirty_branch_classification_v1_20260618 docs/agent_tasks/validation_environment_autonomy_skill_update_v1_20260617.md` | 0 | Task card visible as untracked; report bundle visible as ignored. |
| `git add -f ... && git add ...` | 1 then 0 | Initial staging failed because `.agents/` is ignored; rerun used `git add -f` for `.agents` and `reports/`, and normal `git add` for the task card. |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/validation_environment_autonomy_skill_update_v1_20260617.md --no-write-report` after staging | 0 | Passed with all 11 staged changed files inside `allowed_files`. |
| `git diff --cached --check` | 0 | No staged whitespace errors. |
| `git diff --cached --name-status` | 0 | Staged exactly three modified skill files, one task card, and seven report files. |

## Staging Note

Because `reports/` is ignored, the report bundle must be added with `git add -f`
before commit.
