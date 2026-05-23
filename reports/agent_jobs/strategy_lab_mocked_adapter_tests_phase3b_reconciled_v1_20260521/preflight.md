# Preflight

## Worktree

- `pwd`: `/home/l4nd0/tenn-strategy-lab-mocked-adapter-tests-phase3b-reconciled-v1-20260521`
- Repo root: `/home/l4nd0/tenn-strategy-lab-mocked-adapter-tests-phase3b-reconciled-v1-20260521`
- Branch: `safe/strategy-lab-mocked-adapter-tests-phase3b-reconciled-v1-20260521`
- HEAD: `76042591ab19ae3ed1aba554b1635919e51d5844`
- Recent commits:
  - `76042591 feat(financial-truth): add asx comparator artifact schema`
  - `f425ebc1 milestone(evaluation): checkpoint route parity audit`
  - `d5fcd71d milestone(financial-truth): add asx sidecar gate report`
  - `8e38d267 feat(financial-truth): add asx document type sidecar artifacts`
  - `a56911ac feat(financial-truth): add pure asx document type classifier`

## Tenn Symlink

- `/home/l4nd0/tenn` is a broken symlink to `/mnt/hdd-data/home/l4nd0/tenn`.
- Because that path is unusable, this job used a fresh isolated worktree from the clean NVMe baseline at HEAD `76042591`.

## Task-Card And Registry Tooling

- `python3 scripts/agent_job_contract.py --help`: supports `validate` and `check-diff`.
- `python3 scripts/agent_job_registry.py --help`: supports `list-active`, `claim`, `heartbeat`, `release`, and `check-overlap`.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521.md`: `ok=true`.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521.md --repo-root /home/l4nd0/tenn-strategy-lab-mocked-adapter-tests-phase3b-reconciled-v1-20260521`: `ok=true`, no issues.
- Claim status: claimed successfully after refreshing the task card allowed file list.

## Active Jobs At Claim Time

No active job overlapped this job's exact allowed docs, tests, or report paths.

Active non-overlapping jobs seen during preflight:

- `asx_appendix5b_sidecar_parser_v1_20260521`, lane `Financial Truth`.
- `cockpit_feature_honesty_audit_v1_20260521`, lane `Reporting`.
- `post_nvme_next_work_orchestrator_v1_20260521`, lane `Evaluation`.

## Dirty Surface Before Implementation

The fresh isolated worktree initially had no dirty files. After task-card creation and claim, dirty files were limited to the new task card and the registry-created report `status.json`.

No unrelated dirty files were cleaned, stashed, reset, removed, unstaged, merged, cherry-picked, or modified.
