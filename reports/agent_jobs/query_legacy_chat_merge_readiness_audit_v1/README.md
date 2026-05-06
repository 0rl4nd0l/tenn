# query_legacy_chat_merge_readiness_audit_v1

## Preflight Declaration

Lane: Query Orchestration  
Supporting lanes: Provenance, Reporting  
Branch: `preserve/dirty-work-20260430T065748Z`  
Worktree: `/mnt/sdb2/home/l4nd0/tenn` (`pwd` resolves through the `/home/l4nd0/tenn` symlink)  
Execution mode: AUDIT ONLY / REPORT ONLY  
Intended files:
- `docs/agent_tasks/query_legacy_chat_merge_readiness_audit_v1.md`
- `reports/agent_jobs/query_legacy_chat_merge_readiness_audit_v1/README.md`

Contested surfaces touched: none modified. Runtime/backend files were inspected read-only.  
Collision risk: LOW for audit artifacts; HIGH for direct runtime integration in the dirty preserve worktree.  
Decision: proceed with audit only; do not integrate in this worktree.

Target system layer: backend API route / Analysis metadata compatibility, with Client/Reporting consumers.  
Relevant contract rules: backend authority, Cockpit as client/orchestration only, backend-owned retrieval, no parallel retrieval implementation, no unsupported source-backed labels.  
What must not change: retrieval ranking, ingestion, Qdrant, `news.sqlite`, memory DBs, financial truth/extraction, deep research, source drawer UI, Cockpit UI/design work, and dirty preserve files.  
Why safe: this task only creates audit artifacts and uses Git inspection commands. No code, test, runtime, data store, merge, cherry-pick, stash, reset, or commit operation was run.  
GPU process check: not required; no llama-server spawn/restart or GPU dependency.

## Required Preflight Evidence

- `pwd`: `/home/l4nd0/tenn`; `realpath .`: `/mnt/sdb2/home/l4nd0/tenn`
- Branch: `preserve/dirty-work-20260430T065748Z`
- Preserve HEAD: `4f9736ce7d683db6d1786a215b0f6efc286f90e9`
- Recent preserve commits:
  - `4f9736c milestone(ui): cockpit home state-aware market desk v0`
  - `33ef633 milestone(reporting): streamline cockpit UX flows and empty states`
  - `c68abe1 fix(reporting): render textual sources from evidence envelope`
  - `998d103 fix(query): add evidence taxonomy envelope to orchestrator`
- Active task card markers: `TENN_AGENT_TASK_CARD` unset; `.tenn/active_agent_task` absent.
- `python` command availability: absent in this shell; `python3 --version` returned `Python 3.10.12`.
- Task-card validation with `python3 scripts/agent_job_contract.py validate docs/agent_tasks/query_legacy_chat_merge_readiness_audit_v1.md`: `ok: true`.
- Registry root: `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry`, shared scope.
- Registry `list-active`: one active Provenance job, `source_label_998d68e_clean_integration_retry_20260506`, owning `financial-engine_v2/backend/app/routes/cockpit_api.py`, `financial-engine_v2/backend/tests/test_build_ui_sources.py`, its task card, and reports.
- Registry `check-overlap` for this audit card: `ok: false` because existing unrelated dirty preserve-worktree files are outside this audit card's `allowed_files`. No active-job lane/file overlap with this audit card's allowed write paths was reported.
- Registry claim: not attempted because the registry overlap check was not safe (`ok: false`). Release is therefore not required.
- Final registry `list-active`: `active_jobs: []`.
- Final task-card `check-diff`: `ok: false` because the preserve worktree still contains unrelated pre-existing dirty files outside this audit card's `allowed_files`; it wrote `reports/agent_jobs/query_legacy_chat_merge_readiness_audit_v1/diff-check.json`.
- `git diff --check`: passed with no output.

## Worktrees Inspected

Preserve worktree:
- Path: `/mnt/sdb2/home/l4nd0/tenn`
- Branch: `preserve/dirty-work-20260430T065748Z`
- HEAD: `4f9736ce7d683db6d1786a215b0f6efc286f90e9`
- Status: dirty with untracked task-card/design/export artifacts, including this audit card.

Patch worktree:
- Path: `/mnt/sdb2/home/l4nd0/tenn-legacy-chat-envelope-compat-v1`
- Branch: `safe/query-legacy-chat-envelope-compat-v1`
- HEAD: `9fc3d158f0cab218ae17343c00a56cf4d66cc240`
- Status: clean (`git status --short --untracked-files=all` produced no entries).

## Confirmed Facts

1. `c68abe138eb41afe489f76a276d28567cbc12568` is contained in preserve HEAD.
2. `9defaed58dc0af1738003ac0215f89205ea02f7d` is not contained in preserve HEAD.
3. `9fc3d158f0cab218ae17343c00a56cf4d66cc240` is not contained in preserve HEAD.
4. The merge base of preserve HEAD and `9defaed58dc0af1738003ac0215f89205ea02f7d` is `c68abe138eb41afe489f76a276d28567cbc12568`.
5. The merge base of preserve HEAD and `9fc3d158f0cab218ae17343c00a56cf4d66cc240` is also `c68abe138eb41afe489f76a276d28567cbc12568`.
6. `9defaed58dc0af1738003ac0215f89205ea02f7d` has parent `c68abe138eb41afe489f76a276d28567cbc12568`.
7. `9fc3d158f0cab218ae17343c00a56cf4d66cc240` has parent `9defaed58dc0af1738003ac0215f89205ea02f7d`.
8. `git cherry -v HEAD safe/query-legacy-chat-envelope-compat-v1` reports both `9defaed58dc0af1738003ac0215f89205ea02f7d` and `9fc3d158f0cab218ae17343c00a56cf4d66cc240` as not patch-equivalent to preserve HEAD.
9. The isolated patch commit changes:
   - `docs/agent_tasks/query_legacy_chat_envelope_compat_v1.md`
   - `financial-engine_v2/backend/app/routes/chat.py`
   - `financial-engine_v2/backend/app/services/tenn_chat.py`
   - `financial-engine_v2/backend/tests/test_chat_route.py`
   - `reports/agent_jobs/query_legacy_chat_envelope_compat_v1/README.md`
   - `reports/agent_jobs/query_legacy_chat_envelope_compat_v1/diff-check.json`
10. No preserve dirty/untracked file overlaps those six patch paths.
11. No preserve post-`c68abe1` committed path overlaps the patch branch's post-`c68abe1` paths.
12. `git merge-tree c68abe138eb41afe489f76a276d28567cbc12568 HEAD 9fc3d158f0cab218ae17343c00a56cf4d66cc240` produced no conflict markers or `CONFLICT`/`changed in both` diagnostics.
13. Current preserve `financial-engine_v2/backend/app/main.py` includes `chat_router` both with no prefix and with `prefix="/api"`, so the `@router.post("/chat")` handler serves both `POST /chat` and `POST /api/chat`.
14. Current preserve `financial-engine_v2/backend/app/routes/chat.py` calls `tenn_chat.chat_with_tenn()` directly and returns `{"type": "analysis", "content": ...}` for analysis mode.
15. The patch keeps `tenn_chat.chat_with_tenn()` as the execution path and wraps the returned content with a legacy evidence envelope before JSON-safe serialization.
16. The patch adds `SOURCE_LABEL_TAXONOMY_VERSION = "source_label_semantics_v1"` to `tenn_chat.py`.
17. The patch adds route tests for degraded runtime, unknown unclassified legacy sources, no-hit not being claim-verified, and preservation of memory/personal/web/news/financial-truth role labels.
18. The patch report states focused validation passed: Ruff on changed Python files, `test_chat_route.py`, `test_tenn_chat_and_weighting.py`, combined focused pytest (`28 passed, 1 warning`), `git diff --check`, and task-card `check-diff`.
19. The patch report states broader QueryOrchestrator/source UI test collection was blocked on that base by missing `app.models.companies`.
20. In the current preserve filesystem, `financial-engine_v2/backend/app/models/companies.py` exists but is ignored by `.gitignore:65:models/` and is not tracked by HEAD. In the clean patch worktree it is missing.
21. Report artifacts under `reports/` are ignored by `.git/info/exclude:31:reports/`. This audit report would need `git add -f` if the user wants it committed.

## Ancestry Summary

```text
* 9fc3d15 (safe/query-legacy-chat-envelope-compat-v1) fix(query): harden legacy chat evidence envelope
* 9defaed (audit/query-legacy-api-chat-taxonomy-v1) audit(query): classify legacy chat taxonomy gap
| * 4f9736c (preserve/dirty-work-20260430T065748Z) milestone(ui): cockpit home state-aware market desk v0
| * 33ef633 milestone(reporting): streamline cockpit UX flows and empty states
|/
* c68abe1 fix(reporting): render textual sources from evidence envelope
o 998d103 fix(query): add evidence taxonomy envelope to orchestrator
```

## Preserve Dirty-File Overlap Analysis

Patch-surface overlap with dirty preserve files: none.

Dirty preserve files in relevant lanes:
- Query Orchestration: `docs/agent_tasks/query_legacy_api_chat_taxonomy_audit_v1.md`, this audit task card.
- Provenance: `docs/agent_tasks/source_label_998d68e_integration_review.md`.
- Reporting / UI-design artifacts: `docs/agent_tasks/cockpit_home_backend_bff_contract_audit_v1.md`, `docs/agent_tasks/verification-metric-clickthrough-review-v1.md`, `docs/agent_tasks/verification_lock_dirty_preserve_gate_20260506.md`, `tenn_cockpit_home_design_export_20260506/**`, `tenn_prompt_contracts_response_guidelines.zip`.
- Backend API dirty files: none found in `git status --short --untracked-files=all`.
- Backend tests dirty files: none found in `git status --short --untracked-files=all`.

## Inferred Facts

- Cherry-picking only `9fc3d158f0cab218ae17343c00a56cf4d66cc240` onto a clean branch from current preserve HEAD should be mechanically clean, based on common base, no changed-path overlap, no dirty patch-path overlap, and conflict-free `merge-tree` output.
- Directly cherry-picking into `/mnt/sdb2/home/l4nd0/tenn` is operationally unsafe because the preserve worktree is intentionally dirty and live, even though the patch paths do not overlap the dirty files.
- Preserving `9defaed58dc0af1738003ac0215f89205ea02f7d` is useful for audit-history continuity, but not required for the runtime compatibility patch. It only adds the legacy taxonomy audit task/report artifacts.
- Merging the whole patch branch is less controlled than cherry-picking the patch commit because it includes both audit and implementation artifacts and gives less explicit selection control.
- The cleanest integration lane is a fresh clean integration branch/worktree from preserve HEAD, then cherry-pick the implementation commit, validate, and only then merge/fast-forward through the normal branch process.

## Speculative Claims

- Actual external traffic to legacy `/chat` or `/api/chat` was not measured in this audit.
- The patch's semantic behavior on preserve HEAD is expected to match the isolated patch worktree because the touched backend files did not change after `c68abe1`, but this was not proven by running tests after an actual cherry-pick.
- Broader QueryOrchestrator/source-label tests may still be blocked in a clean integration worktree until the ignored/untracked `companies.py` situation is resolved in a separate lane.

## DATA_MISSING

- No actual cherry-pick, merge, or integration validation was performed because this task is audit-only.
- No live backend or HTTP smoke was run.
- No production data, access logs, Qdrant, `news.sqlite`, memory DB, ingestion, or financial-truth evidence was inspected.
- Registry claim evidence is missing because claim was not safe after `check-overlap` returned `ok: false` due unrelated dirty preserve files outside this card.
- Broader source-label / QueryOrchestrator collection status on a clean preserve-derived integration branch is unverified.

## Audit Question Answers

1. Current preserve HEAD: `4f9736ce7d683db6d1786a215b0f6efc286f90e9`.
2. Current patch worktree HEAD: `9fc3d158f0cab218ae17343c00a56cf4d66cc240`.
3. Ancestry: preserve and patch both contain `c68abe1`; patch is `c68abe1 -> 9defaed -> 9fc3d15`; preserve is `c68abe1 -> 33ef633 -> 4f9736c`.
4. `9fc3d158f0ca` is not contained in preserve HEAD.
5. `9defaed58dc0` is not contained in preserve HEAD.
6. Integrating `9fc3d158f0ca` touches the six files listed in Confirmed Fact 9.
7. None of those files overlap dirty/untracked files in the preserve worktree.
8. Yes, dirty preserve files exist in Query Orchestration, Provenance, and Reporting artifact areas. No dirty backend API or backend test files were found.
9. Cherry-picking only `9fc3d158f0ca` appears mechanically clean. It is semantically acceptable as a focused compatibility bridge, but unsafe to do directly in the dirty preserve worktree.
10. `9defaed58dc0` is useful for audit traceability, not required for runtime integration.
11. Safest integration path: no integration in the dirty preserve worktree now; later create a fresh clean integration branch/worktree from preserve HEAD and cherry-pick only `9fc3d158f0ca`. If audit-history preservation is explicitly desired, cherry-pick `9defaed58dc0` first in that clean worktree, then `9fc3d158f0ca`.
12. Validation after integration is listed below.
13. `/save` is recommended for the audit card and this report, but do not bundle unrelated dirty Cockpit UI/design/export artifacts with this audit.

## Integration Risk

LOW for a clean isolated integration branch/worktree.  
MEDIUM if done on the shared preserve branch after unrelated dirty work is committed/stashed/archived, because the branch is live and active registry jobs exist.  
HIGH if cherry-picked directly into the current dirty preserve worktree.

## Safest Integration Recommendation

Recommended: create a fresh clean integration worktree/branch from preserve HEAD and cherry-pick only `9fc3d158f0cab218ae17343c00a56cf4d66cc240` there. Do not merge the whole patch branch and do not cherry-pick into the current dirty preserve worktree.

Use `9defaed58dc0af1738003ac0215f89205ea02f7d` only if the user wants the audit commit preserved in the integration branch history. It is not a runtime prerequisite for `9fc3d158f0ca`.

## Later Commands To Run If Safe

Do not run these from the dirty preserve worktree. Run them later only after confirming no active relevant registry overlap.

```bash
cd /mnt/sdb2/home/l4nd0/tenn
BASE="$(git rev-parse preserve/dirty-work-20260430T065748Z)"
git worktree add -b integrate/query-legacy-chat-envelope-compat-v1 ../tenn-query-legacy-chat-envelope-compat-v1 "$BASE"
cd ../tenn-query-legacy-chat-envelope-compat-v1
git status --short --untracked-files=all
python3 scripts/agent_job_contract.py validate docs/agent_tasks/query_legacy_chat_envelope_compat_v1.md
python3 scripts/agent_job_registry.py list-active
python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/query_legacy_chat_envelope_compat_v1.md
python3 scripts/agent_job_registry.py claim docs/agent_tasks/query_legacy_chat_envelope_compat_v1.md
git cherry-pick -x 9fc3d158f0cab218ae17343c00a56cf4d66cc240
```

If audit-history preservation is explicitly required:

```bash
git cherry-pick -x 9defaed58dc0af1738003ac0215f89205ea02f7d
git cherry-pick -x 9fc3d158f0cab218ae17343c00a56cf4d66cc240
```

## Post-Integration Validation

```bash
financial-engine_v2/.venv/bin/python -m ruff check \
  financial-engine_v2/backend/app/routes/chat.py \
  financial-engine_v2/backend/app/services/tenn_chat.py \
  financial-engine_v2/backend/tests/test_chat_route.py

financial-engine_v2/.venv/bin/python -m pytest \
  financial-engine_v2/backend/tests/test_chat_route.py -q

financial-engine_v2/.venv/bin/python -m pytest \
  financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py -q

financial-engine_v2/.venv/bin/python -m pytest \
  financial-engine_v2/backend/tests/test_chat_route.py \
  financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py -q

git diff --check
python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/query_legacy_chat_envelope_compat_v1.md
python3 scripts/agent_job_registry.py release query_legacy_chat_envelope_compat_v1
```

Do not repair the broader `app.models.companies` / QueryOrchestrator collection issue in this integration unless a separate task card explicitly assigns that work.

## Report Artifact Git Handling

- `docs/agent_tasks/query_legacy_chat_merge_readiness_audit_v1.md` is not ignored and appears in `git status`.
- `reports/agent_jobs/query_legacy_chat_merge_readiness_audit_v1/README.md` is ignored by `.git/info/exclude:31:reports/`.
- `reports/agent_jobs/query_legacy_chat_merge_readiness_audit_v1/diff-check.json` is also ignored by the same reports rule.
- If these report artifacts should be committed, they need `git add -f reports/agent_jobs/query_legacy_chat_merge_readiness_audit_v1/README.md reports/agent_jobs/query_legacy_chat_merge_readiness_audit_v1/diff-check.json`.

## Final Status Before Closeout

Final preserve `git status --short --untracked-files=all` still shows the unrelated dirty task-card/design/export artifacts plus this audit task card. The ignored report artifacts do not appear in normal status.

Final patch worktree status: clean.

Registry release status: no release needed because no claim was acquired.

/save recommendation: yes, save the audit task card and report. Keep unrelated dirty Cockpit UI/design/export/task-card artifacts out of any legacy-chat integration commit.
