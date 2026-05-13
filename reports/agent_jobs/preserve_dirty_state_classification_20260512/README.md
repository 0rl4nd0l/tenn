# Preserve Dirty State Classification - 2026-05-12

Lane:
Reporting

Branch:
`preserve/dirty-work-20260430T065748Z`

Worktree:
`/mnt/hdd-data/home/l4nd0/tenn`

Execution mode:
AUDIT ONLY

Intended files:
- `docs/agent_tasks/preserve_dirty_state_classification_20260512.md`
- `reports/agent_jobs/preserve_dirty_state_classification_20260512/README.md`

Contested surfaces touched:
None. Source files were read only.

Collision risk:
MEDIUM. Existing dirty state touches Cockpit UI/config and runtime launcher files, but this audit only writes task/report artifacts.

Decision:
audit only

## Confirmed Facts

- Current branch is `preserve/dirty-work-20260430T065748Z`.
- Current HEAD at preflight was `dabbc456e42f737d12e6a1d979e6189e0936e865`.
- Initial `git status --short --untracked-files=all` before this audit card was created showed seven dirty paths:
  - `M cockpit-ui/components/cockpit/settings/settings-screen.tsx`
  - `M cockpit-ui/lib/cockpit-store.ts`
  - `M financial-engine_v2/config/cockpit.yaml`
  - `M scripts/run_llama_server.sh`
  - `?? docs/agent_tasks/cockpit_upgrade_integration_readiness_20260509.md`
  - `?? docs/agent_tasks/eval_instrumentation_dirty_worktree_audit_20260509.md`
  - `?? docs/agent_tasks/news_memo_signal_routing_candidate_fixture_integration_v1.md`
- `.tenn/active_agent_task` was absent.
- `python3 scripts/agent_job_registry.py list-active` returned `ok: true`, `active_jobs: []`, registry scope `shared`.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/preserve_dirty_state_classification_20260512.md` returned `ok: true`.
- Registry claim for this task failed because the existing dirty files are outside this audit card's `allowed_files`.
- The three pre-existing untracked task cards are not tracked by git; `git ls-files --stage` returned no entries for them.
- `scripts/run_llama_server.sh` has a 12-line unstaged diff adding optional `LLAMA_SERVER_CUDA_VISIBLE_DEVICES` and `LLAMA_SERVER_DISABLE_CUDA_GRAPHS` handling.
- The three model-default diffs are one-line changes from `model:qwen3.5-35b-a3b-apex` to `model:qwen2.5-14b-instruct` in:
  - `cockpit-ui/components/cockpit/settings/settings-screen.tsx`
  - `cockpit-ui/lib/cockpit-store.ts`
  - `financial-engine_v2/config/cockpit.yaml`
- Final `git diff --name-status` and `git status --short --untracked-files=all -- <four tracked paths>` showed no remaining tracked modifications in the four source/runtime files listed above.
- Final `git status --short --untracked-files=all` showed only four untracked task-card files, including this audit card.
- Commit `c0549d754cb501254873b34c66d9aec7d12b95d8` (`milestone(reporting): wire home market update signals`) touches only Cockpit Home source/test files plus task/report artifacts.
- Commit `0e5e7df9d155` (`milestone(memory): update news memo signal-routing ticker fixture`) touches one backend test fixture plus task/report artifacts, not production code.
- Commit `49a5d34a49b1` (`milestone(extraction-eval): enforce auditable real-gold KPI provenance`) is the source branch tip for the separate evaluation dirty-worktree audit, not a current modified file in this preserve worktree.

## Inferred Facts

- The two Cockpit UI default-model edits and `financial-engine_v2/config/cockpit.yaml` edit likely come from the same local runtime/model-selection session because they apply the same replacement and have matching file timestamps on 2026-05-12 around 19:26.
- The `scripts/run_llama_server.sh` edit is likely an intentional local runtime control patch because it adds env-gated GPU selection and CUDA graph disabling without changing defaults when those env vars are unset.
- The Cockpit upgrade task card is intentional audit output; its report recommends `c0549d7` as the next bounded Cockpit Home news snapshot source-only integration.
- The eval instrumentation task card is intentional audit output; its report classifies an external eval worktree as high-value preservation work, not current preserve source state.
- The news memo signal-routing integration task card is intentional but currently blocked by the dirty worktree guard; its report says no integration was performed.
- The model-default edits are risky to leave unstated during extraction reruns because they alter runtime/chat defaults and may obscure which model served validation, even if extraction code remains pinned elsewhere.

## DATA_MISSING

- No active owner could be proven for the four modified tracked files; there is no active registry claim and no active task marker.
- No commit, task card, or report was found in the current turn that explicitly owns the three model-default edits.
- The four tracked source/runtime diffs disappeared during this audit. I did not edit those files, stage files, reset files, or run cleanup commands, so the actor and exact mechanism are DATA_MISSING.
- No runtime process inspection or health checks were run for this audit because runtime restarts and operational mutation were prohibited.
- The exact source session for `scripts/run_llama_server.sh` is unverified; only the diff shape and recent commit history support the runtime-control inference.
- The report directory is ignored by git status, so its README is not visible in final short status even though it was written.

## Dirty File Table By Lane

| File | State at preflight | Lane / owner if inferable | Likely source branch/session | Status | Blocks Reporting integration? | Blocks extraction canonical_core rerun? | Recommended handling | Evidence |
|---|---:|---|---|---|---|---|---|---|
| `cockpit-ui/components/cockpit/settings/settings-screen.tsx` | modified | Reporting; owner DATA_MISSING | Unknown local model-default session | risky | Not a source overlap with `c0549d7`, but blocks task-card claim and can contaminate UI validation | No direct extraction-code overlap; can confuse runtime model assumptions | Preserve intentionally in a dedicated config/model-default task or revert only with owner approval; leave untouched now | `git diff` one-line model default replacement; recent path commits include `33ef633`, `4f3d9e1`; file timestamp 2026-05-12 19:26 |
| `cockpit-ui/lib/cockpit-store.ts` | modified | Reporting; owner DATA_MISSING | Unknown local model-default session | risky | Not a Home source overlap, but blocks task-card claim and changes persisted chat default | No direct extraction-code overlap; can confuse runtime model assumptions | Preserve intentionally in a dedicated config/model-default task or revert only with owner approval; leave untouched now | `git diff` one-line `DEFAULT_CHAT_MODEL` replacement; recent path commits include `4e3fc03`, `4f3d9e1`; file timestamp 2026-05-12 19:26 |
| `financial-engine_v2/config/cockpit.yaml` | modified | Query Orchestration / Reporting config; owner DATA_MISSING | Unknown local model-default session | risky | Does not overlap Home source files, but blocks task-card claim and affects backend-served Cockpit config | Potential blocker for rerun reproducibility if Cockpit/runtime config is read during validation | Preserve or document in a config task before baseline reruns; do not silently carry into canonical eval | `git diff` one-line model replacement; recent path commits include `20ca64d`, `567d0f1`; file timestamp 2026-05-12 19:26 |
| `scripts/run_llama_server.sh` | modified | Runtime/Ops supporting Evaluation; owner DATA_MISSING | Unknown local runtime-control session | intentional-looking, risky until owned | Does not overlap Home source files, but blocks task-card claim | Yes, if the rerun depends on llama-server launch behavior or GPU/device selection | Preserve as a dedicated runtime patch or archive as report artifact only after owner decision; leave untouched now | `git diff` adds env-gated CUDA device and graph toggles; recent path commits include `516f1c5`, `cfd0e41`, `9aae854`, `8c6085d` |
| `docs/agent_tasks/cockpit_upgrade_integration_readiness_20260509.md` | untracked | Reporting; owner Claude per frontmatter | Cockpit upgrade audit session | intentional | Blocks task-card claim; content supports the next Home news snapshot handoff | No direct extraction overlap | Commit/preserve with its report artifacts or move through an approved docs cleanup; leave untouched now | Frontmatter owner/lane; matching report exists under `reports/agent_jobs/cockpit_upgrade_integration_readiness_20260509/` |
| `docs/agent_tasks/eval_instrumentation_dirty_worktree_audit_20260509.md` | untracked | Evaluation; owner Claude per frontmatter | Eval instrumentation dirty-worktree audit | intentional | Blocks task-card claim only | Indirectly relevant because it records eval instrumentation preservation context, but no current source overlap | Commit/preserve with its report artifacts; leave untouched now | Frontmatter owner/lane; matching report classifies `/mnt/sdb2/home/l4nd0/tenn-eval-instrumentation-20260421` |
| `docs/agent_tasks/news_memo_signal_routing_candidate_fixture_integration_v1.md` | untracked | Memory with Query Orchestration/Evaluation support; owner Codex per frontmatter | News memo fixture integration task | intentional, blocked | Blocks task-card claim; does not overlap `c0549d7` Home files | No extraction baseline overlap | Keep as blocked-task evidence or preserve with reports after resolving registry policy | Frontmatter owner/lane; matching final report says integration was blocked before cherry-pick |

Note: the first four rows classify the tracked source/runtime files as they existed at preflight. By final status, those files were no longer dirty. Because this is a live shared worktree and this audit did not modify them, treat the preflight diffs as externally resolved but not provenance-closed.

## Blockers For Cockpit Home News Snapshot Integration

- No dirty file currently overlaps the source-only target files from `c0549d7`:
  - `cockpit-ui/components/cockpit/home/home-page.tsx`
  - `cockpit-ui/lib/cockpit-home-api.ts`
  - `cockpit-ui/lib/cockpit-home-api.test.ts`
- The final dirty state still blocks normal task-card claim/check-diff for a follow-up integration unless the three older untracked task cards are preserved, allowed, or moved through an approved docs cleanup.
- The preflight model-default edits would have contaminated UI/runtime validation, but they were not present in final git diff. Recheck before integration because the ownership and removal mechanism are unverified.

Conclusion: source-only application is not semantically blocked by file overlap. It remains procedurally blocked in this shared preserve worktree by untracked task-card state unless the follow-up task explicitly includes or first preserves those docs artifacts. A clean isolated worktree remains the safest path.

## Blockers For Extraction canonical_core Rerun

- At preflight, `scripts/run_llama_server.sh` was a direct runtime launcher diff. By final status, it was no longer dirty. Re-verify immediately before any rerun because the transient diff was externally resolved.
- At preflight, `financial-engine_v2/config/cockpit.yaml` changed the Cockpit LLM model default. By final status, it was no longer dirty. It is not canonical extraction logic, but a recurrence would confuse model/runtime evidence if a rerun uses shared backend/Cockpit configuration.
- The Cockpit UI files do not block extraction evaluation directly.
- The untracked task cards do not affect extraction execution, but they block registry claims/check-diff for task-card-governed work.

Conclusion: final status has no tracked runtime/config diff, so there is no current source-file blocker to an extraction canonical_core rerun from git status alone. Because transient runtime/config diffs existed during preflight, re-run branch/HEAD/status and capture model/runtime evidence immediately before the rerun.

## Recommended Next Safe Action

1. Preserve the three pre-existing intentional task cards and their matching reports in a docs-only checkpoint, or move them under an approved archival task.
2. Treat the preflight model-default/runtime diffs as DATA_MISSING until an owner explains their removal or they are reintroduced under a task card.
3. Run the Cockpit Home news snapshot integration from a clean isolated worktree or after the registry guard can be satisfied.
4. Run extraction canonical_core only after a fresh clean-status preflight and captured model/default/runtime evidence.

## Final Git Status

Command:

```bash
git status --short --untracked-files=all
```

Output:

```text
?? docs/agent_tasks/cockpit_upgrade_integration_readiness_20260509.md
?? docs/agent_tasks/eval_instrumentation_dirty_worktree_audit_20260509.md
?? docs/agent_tasks/news_memo_signal_routing_candidate_fixture_integration_v1.md
?? docs/agent_tasks/preserve_dirty_state_classification_20260512.md
```

Final `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/preserve_dirty_state_classification_20260512.md` result:

- `ok: false`
- Disallowed files:
  - `docs/agent_tasks/cockpit_upgrade_integration_readiness_20260509.md`
  - `docs/agent_tasks/eval_instrumentation_dirty_worktree_audit_20260509.md`
  - `docs/agent_tasks/news_memo_signal_routing_candidate_fixture_integration_v1.md`
- Additional issue: audit-only diff check reported code-change risk because dirty files outside the task-card allowed set existed during the check.

No registry claim was acquired, so no registry release was needed.
