# NVMe Runtime Audit Artifact Checkpoint

Job: `nvme_runtime_audit_artifact_checkpoint_v1_20260519`  
Lane: `Evaluation`  
Mode: `safe_extension`  
Runtime root: `/home/l4nd0/tenn-runtime -> /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`  
Branch: `migration/clean-runtime-baseline-reconstruct-v1`  
Pre-commit HEAD: `5dd7ee84b49e`

## Confirmed Facts

- This checkpoint task card was created at `docs/agent_tasks/nvme_runtime_audit_artifact_checkpoint_v1_20260519.md`.
- Task-card validation passed:
  `python3 scripts/agent_job_contract.py validate docs/agent_tasks/nvme_runtime_audit_artifact_checkpoint_v1_20260519.md`.
- Required preflight confirmed:
  - `pwd`: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
  - `readlink -f /home/l4nd0/tenn-runtime`: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
  - branch: `migration/clean-runtime-baseline-reconstruct-v1`
  - HEAD: `5dd7ee84b49e`
- Initial plain `git status --short` showed only the five recent untracked audit task cards.
- `git status --short --ignored docs/agent_tasks reports/agent_jobs` showed the five recent untracked task cards plus ignored report directories under `reports/agent_jobs/`.
- Registry `list-active` returned `active_jobs: []`.
- Registry `check-overlap` passed with no issues for this checkpoint task card.
- Registry `claim` succeeded for `nvme_runtime_audit_artifact_checkpoint_v1_20260519`.
- The first `check-diff` run proved the repo-local matcher requires exact report child paths; the task card was tightened to include exact files under the same requested report directories.
- Final `check-diff` passed with no disallowed files after the exact child paths were added.
- Registry `release` succeeded and final `list-active` returned `active_jobs: []`.
- All five source audit task cards listed in this checkpoint allowlist exist.
- All five source audit report directories listed in this checkpoint allowlist exist.
- The checkpoint report directory exists and contains registry `status.json` plus this `README.md`.

## Preserved Audit Conclusions

- Tenn live stack was relaunched from `/home/l4nd0/tenn-runtime`, which resolves to the clean NVMe runtime baseline.
- Backend Docker mounts in the relaunch report point `/data` and `/reports` at `/mnt/tenn-nvme2/tenn/financial-engine_v2/...`.
- `/api/cockpit/home` is intentionally owned by the Next.js BFF in this branch/profile; a direct backend `/api/cockpit/home` 404 is expected.
- `/api/news/status` is intentionally absent in this branch/profile; current news/Home surfaces use other routes.
- APEX is actually loaded on the Tesla M40 behind the local llama.cpp-compatible `:8001` runtime.
- The direct APEX/M40 12-request tiny soak passed and is classified `APEX_M40_DIRECT_STABLE` only for direct local `:8001` tiny sequential prompts.
- Wider Cockpit chat remains separate from the direct soak classification because app-level source guards and prompt expansion can change behavior.
- Cockpit Home `PARTIAL` is honest missing/deferred producer state, not evidence of NVMe runtime failure or route-parity failure.

## DATA_MISSING

- This checkpoint did not rerun runtime, GPU, route, Home, Docker, model, DB, Qdrant, news, memory, parser, extraction, or UI smokes.
- This checkpoint did not inspect or mutate production data.
- This checkpoint did not verify ignored report directories outside the explicit allowlist.
- A committed report cannot truthfully contain its own final Git object id because the commit hash includes the report content. The final commit hash must be read after commit with `git rev-parse --short=12 HEAD` and recorded in the operator closeout.
- Final post-commit plain `git status --short` is not available inside this pre-commit report artifact. The staged set is expected to leave no plain-status task/report dirt after commit if the commit succeeds.

## Exact Artifacts Preserved

Task cards:

- `docs/agent_tasks/nvme_runtime_audit_artifact_checkpoint_v1_20260519.md`
- `docs/agent_tasks/route_parity_home_news_status_audit_v1_20260519.md`
- `docs/agent_tasks/nvme2_live_stack_relaunch_from_runtime_v1_20260519.md`
- `docs/agent_tasks/apex_m40_runtime_stability_audit_v1_20260519.md`
- `docs/agent_tasks/apex_m40_direct_runtime_soak_audit_v1_20260519.md`
- `docs/agent_tasks/cockpit_home_missing_producers_audit_v1_20260519.md`

Report artifacts:

- `reports/agent_jobs/route_parity_home_news_status_audit_v1_20260519/README.md`
- `reports/agent_jobs/route_parity_home_news_status_audit_v1_20260519/diff-check.json`
- `reports/agent_jobs/route_parity_home_news_status_audit_v1_20260519/status.json`
- `reports/agent_jobs/nvme2_live_stack_relaunch_from_runtime_v1_20260519/README.md`
- `reports/agent_jobs/nvme2_live_stack_relaunch_from_runtime_v1_20260519/cockpit_reboot_full.log`
- `reports/agent_jobs/nvme2_live_stack_relaunch_from_runtime_v1_20260519/cockpit_start_new_detached.log`
- `reports/agent_jobs/apex_m40_runtime_stability_audit_v1_20260519/README.md`
- `reports/agent_jobs/apex_m40_runtime_stability_audit_v1_20260519/diff-check.json`
- `reports/agent_jobs/apex_m40_direct_runtime_soak_audit_v1_20260519/README.md`
- `reports/agent_jobs/apex_m40_direct_runtime_soak_audit_v1_20260519/diff-check.json`
- `reports/agent_jobs/cockpit_home_missing_producers_audit_v1_20260519/README.md`
- `reports/agent_jobs/nvme_runtime_audit_artifact_checkpoint_v1_20260519/README.md`
- `reports/agent_jobs/nvme_runtime_audit_artifact_checkpoint_v1_20260519/status.json`
- `reports/agent_jobs/nvme_runtime_audit_artifact_checkpoint_v1_20260519/diff-check.json` after final `check-diff` writes it.

## Force-Add Status

Reports are ignored in this checkout, so the allowed report directories must be staged with `git add -f`.

Only these specific report directories are allowed for force-add:

- `reports/agent_jobs/route_parity_home_news_status_audit_v1_20260519/`
- `reports/agent_jobs/nvme2_live_stack_relaunch_from_runtime_v1_20260519/`
- `reports/agent_jobs/apex_m40_runtime_stability_audit_v1_20260519/`
- `reports/agent_jobs/apex_m40_direct_runtime_soak_audit_v1_20260519/`
- `reports/agent_jobs/cockpit_home_missing_producers_audit_v1_20260519/`
- `reports/agent_jobs/nvme_runtime_audit_artifact_checkpoint_v1_20260519/`

No broad `reports/agent_jobs/` force-add is permitted for this checkpoint.

## Commit Hash

Commit hash in this committed report: `DATA_MISSING_SELF_REFERENTIAL_COMMIT_HASH`.

The actual checkpoint commit hash must be read after the commit. This report intentionally avoids embedding a stale or impossible self-referential SHA.

## Final Git Status

Final post-commit status in this committed report: `DATA_MISSING_UNTIL_AFTER_COMMIT`.

Expected normal status after a successful commit: no plain `git status --short` output for the preserved task/report artifacts. Ignored report directories outside this allowlist may still appear only when using `git status --ignored`.

## Registry Status

- `list-active` before claim: `active_jobs=[]`.
- `check-overlap`: passed.
- `claim`: succeeded.
- `release`: succeeded.
- Final `list-active`: `active_jobs=[]`.

## Project Memory Save Recommendation

SAVE_RECOMMENDED: persist that the May 19 NVMe runtime baseline audit artifacts were checkpointed together, including route parity resolved as BFF-owned Home and absent `/api/news/status`, direct local APEX/M40 tiny-soak stability, and honest Cockpit Home `PARTIAL` producer state. Also persist that this was an artifact-only checkpoint and did not re-run runtime or production-data validation.
