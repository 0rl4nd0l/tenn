# Dirty Preserve Worktree Classification After Cockpit Home Contract

Lane: Evaluation
Supporting lanes: Reporting, Provenance
Branch: `preserve/dirty-work-20260430T065748Z`
Worktree: `/mnt/sdb2/home/l4nd0/tenn`
Execution mode: AUDIT ONLY
Intended files:
- `docs/agent_tasks/dirty_preserve_worktree_classification_post_home_contract_20260507.md`
- `reports/agent_jobs/dirty_preserve_worktree_classification_post_home_contract_20260507/**`
Contested surfaces touched: none
Collision risk: MEDIUM for audit/report work; HIGH for starting Cockpit Home BFF route v1 in this dirty preserve worktree
Decision: audit only

## Contract Scope

- Target system layer: Evaluation report artifacts, with Reporting/Provenance classification of Cockpit worktree leftovers.
- Relevant contract rules: backend remains authority (`SYSTEM_CONTRACT.md` section 1.1); Cockpit is client/orchestration only (section 1.2); no cross-layer retrieval/storage work (section 2); source/evidence labels must not be fabricated or backed by wrong evidence (AGENTS source/evidence label safety).
- What must not change: backend runtime, frontend runtime, Cockpit Home BFF wiring, query orchestration, source labels, chat behavior, memory stores, financial truth, Qdrant, news stores, databases, ingestion, reindexing, staging, commits, cleanup, moves, deletes, or archives.
- Why this audit is safe: only this task card and this report directory were written; all other artifacts were inspected read-only.
- GPU process check: not required. This audit did not spawn, restart, or depend on llama-server.

## Branch / HEAD / Worktree / Registry Status

Preflight and final evidence:

| Item | Result |
| --- | --- |
| Agent | Codex |
| Branch | `preserve/dirty-work-20260430T065748Z` |
| Final HEAD | `cbeeab57554b` |
| Final HEAD subject | `milestone(cockpit-ui): restore settings sidebar navigation` |
| Worktree | `/mnt/sdb2/home/l4nd0/tenn` |
| Task-card validation | `ok: true` |
| Initial registry list-active | `active_jobs: []` |
| Final registry list-active | `active_jobs: []` |
| Registry check-overlap | `ok: false` because `legacy_chat_envelope_merge_strategy_audit_v1.md` and `marketplace_matches_workflow_audit_v1.md` are dirty outside this card |
| Claim | skipped because check-overlap was not safe |
| Transient active job observed | `backend-import-validity-companies-model-v1`, lane `Reporting`, worktree `/mnt/sdb2/home/l4nd0/tenn-backend-import-validity-companies-model-v1`, stale `false`; released before final status |
| Active process note | a shell watcher was observed attempting to claim `marketplace_matches_workflow_audit_v1.md`; final process check no longer showed that watcher |

Milestone SHA note:

- The prompt names `47cb4c510cf5 feat(reporting): add cockpit home contract scaffold`.
- Current branch contains `f7a7454 milestone(reporting): cockpit home contract scaffold`, which has the same changed file list as `47cb4c510cf5`.
- `47cb4c510cf5` is not an ancestor of final HEAD (`git merge-base --is-ancestor` exit 1); `f7a7454` is an ancestor (exit 0).
- The committed Cockpit Home contract scaffold files are clean and tracked:
  - `cockpit-ui/lib/cockpit-home-contract.test.ts`
  - `cockpit-ui/lib/cockpit-home-contract.ts`
  - `cockpit-ui/types/cockpit-home.ts`
  - `docs/agent_tasks/cockpit_home_contract_design_v1.md`
  - `reports/agent_jobs/cockpit_home_contract_design_v1/README.md`
  - `reports/agent_jobs/cockpit_home_contract_design_v1/diff-check.json`

## Current Dirty / Untracked / Ignored Inventory

Final visible `git status --short --untracked-files=all`:

```text
?? docs/agent_tasks/dirty_preserve_worktree_classification_post_home_contract_20260507.md
?? docs/agent_tasks/legacy_chat_envelope_merge_strategy_audit_v1.md
?? docs/agent_tasks/marketplace_matches_workflow_audit_v1.md
```

Relevant ignored artifact inventory under `docs/agent_tasks`, `reports/agent_jobs`, and called-out Cockpit Home handoff paths:

```text
?? docs/agent_tasks/dirty_preserve_worktree_classification_post_home_contract_20260507.md
?? docs/agent_tasks/legacy_chat_envelope_merge_strategy_audit_v1.md
?? docs/agent_tasks/marketplace_matches_workflow_audit_v1.md
!! reports/agent_jobs/cockpit_home_backend_bff_contract_audit_v1/diff-check.json
!! reports/agent_jobs/dirty_preserve_worktree_classification_20260506/README.md
!! reports/agent_jobs/dirty_preserve_worktree_classification_20260506/diff-check.json
!! reports/agent_jobs/legacy_chat_envelope_merge_strategy_audit_v1/README.md
!! reports/agent_jobs/legacy_chat_envelope_merge_strategy_audit_v1/diff-check.json
!! reports/agent_jobs/marketplace_matches_workflow_audit_v1/README.md
!! reports/agent_jobs/marketplace_matches_workflow_audit_v1/diff-check.json
!! reports/agent_jobs/preserve_merge_readiness_source_label_chat_20260506/README.md
!! reports/agent_jobs/preserve_merge_readiness_source_label_chat_20260506/diff-check.json
!! reports/agent_jobs/preserve_merge_readiness_source_label_chat_20260506/validation.json
!! reports/agent_jobs/query_legacy_api_chat_taxonomy_audit_v1/README.md
!! reports/agent_jobs/query_legacy_api_chat_taxonomy_audit_v1/diff-check.json
!! reports/agent_jobs/query_legacy_chat_envelope_integration_status_20260506/README.md
!! reports/agent_jobs/query_legacy_chat_envelope_integration_status_20260506/diff-check.json
!! reports/agent_jobs/reporting_textual_sources_list_v1/diff-check.json
!! reports/agent_jobs/source_label_998d68e_integration_review/README.md
!! reports/agent_jobs/source_label_998d68e_integration_review/diff-check.json
!! reports/agent_jobs/verification-metric-clickthrough-review-v1/diff-check.json
!! reports/agent_jobs/verification-metric-clickthrough-review-v1/validation.json
!! reports/agent_jobs/verification_lock_dirty_preserve_gate_20260506/README.md
!! reports/agent_jobs/verification_lock_dirty_preserve_gate_20260506/diff-check.json
```

Called-out paths:

| Path | Current worktree result | Evidence |
| --- | --- | --- |
| `tenn_cockpit_home_design_export_20260506/` | absent from final worktree | targeted `find`, `test -e`, and scoped `git status --ignored` returned no current path |
| `tenn_prompt_contracts_response_guidelines.zip` | absent from final worktree | targeted root zip scan and `test -e` returned no current path |
| `tenn_cockpit_home_design_export_20260506/**` | present in `stash@{8}` only | `git stash show --include-untracked --name-only stash@{8}` |
| `tenn_prompt_contracts_response_guidelines.zip` | present in `stash@{8}` only | `git stash show --include-untracked --name-only stash@{8}` |

The full required `git status --ignored --short` command was run. It returned about 1000 ignored entries, mostly local tool state, caches, venvs, build outputs, screenshots, runtime data, SQLite files, generated financial/eval reports, and local secrets/env files. Those global ignored artifacts are not Cockpit Home preserve artifacts and should remain outside this cleanup decision unless a separate repo-wide ignored-artifact cleanup task is created.

## Classification Table

| Path | Status | Likely lane | Likely source/job | Cockpit Home BFF overlap | Treatment | Approval required | Safe next command, not run |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `docs/agent_tasks/dirty_preserve_worktree_classification_post_home_contract_20260507.md` | untracked | Evaluation | current audit | No direct runtime overlap | keep_and_commit_now | No | `git add docs/agent_tasks/dirty_preserve_worktree_classification_post_home_contract_20260507.md reports/agent_jobs/dirty_preserve_worktree_classification_post_home_contract_20260507/README.md` |
| `reports/agent_jobs/dirty_preserve_worktree_classification_post_home_contract_20260507/README.md` | untracked/ignored under `reports/` | Evaluation | current audit | No direct runtime overlap | keep_and_commit_now | No | `git add -f reports/agent_jobs/dirty_preserve_worktree_classification_post_home_contract_20260507/README.md` |
| `reports/agent_jobs/dirty_preserve_worktree_classification_post_home_contract_20260507/diff-check.json` | ignored | Evaluation | current audit task-card check-diff evidence | No direct runtime overlap | keep_and_commit_now | No | `git add -f reports/agent_jobs/dirty_preserve_worktree_classification_post_home_contract_20260507/diff-check.json` |
| `docs/agent_tasks/legacy_chat_envelope_merge_strategy_audit_v1.md` | untracked | Query Orchestration | legacy chat envelope merge audit | No direct Home BFF file overlap; conceptual chat handoff overlap only | move_to_separate_lane | No for commit decision; yes before delete/archive | `git add docs/agent_tasks/legacy_chat_envelope_merge_strategy_audit_v1.md && git add -f reports/agent_jobs/legacy_chat_envelope_merge_strategy_audit_v1/README.md reports/agent_jobs/legacy_chat_envelope_merge_strategy_audit_v1/diff-check.json` |
| `reports/agent_jobs/legacy_chat_envelope_merge_strategy_audit_v1/README.md` | ignored | Query Orchestration | legacy chat envelope merge audit report | No direct Home BFF file overlap | move_to_separate_lane | No for commit decision; yes before delete/archive | same as above |
| `reports/agent_jobs/legacy_chat_envelope_merge_strategy_audit_v1/diff-check.json` | ignored | Query Orchestration | generated diff-check evidence | No | move_to_separate_lane | No for commit decision; yes before delete/archive | same as above |
| `docs/agent_tasks/marketplace_matches_workflow_audit_v1.md` | untracked | Reporting | Marketplace Matches workflow audit | No direct Home BFF file overlap; same broad Reporting lane | move_to_separate_lane | No for commit decision; yes before delete/archive | `git add docs/agent_tasks/marketplace_matches_workflow_audit_v1.md && git add -f reports/agent_jobs/marketplace_matches_workflow_audit_v1/README.md reports/agent_jobs/marketplace_matches_workflow_audit_v1/diff-check.json` |
| `reports/agent_jobs/marketplace_matches_workflow_audit_v1/README.md` | ignored | Reporting | blocked Marketplace audit report | No direct Home BFF file overlap | move_to_separate_lane | No for commit decision; yes before delete/archive | same as above |
| `reports/agent_jobs/marketplace_matches_workflow_audit_v1/diff-check.json` | ignored | Reporting | generated diff-check evidence | No | move_to_separate_lane | No for commit decision; yes before delete/archive | same as above |
| `reports/agent_jobs/cockpit_home_backend_bff_contract_audit_v1/diff-check.json` | ignored | Reporting | Cockpit Home backend/BFF audit diff-check | Yes, historical BFF audit artifact | DATA_MISSING | Yes before delete/archive | `test -f reports/agent_jobs/cockpit_home_backend_bff_contract_audit_v1/README.md || echo DATA_MISSING` |
| `reports/agent_jobs/dirty_preserve_worktree_classification_20260506/README.md` | ignored | Evaluation | previous dirty-preserve classification | No direct overlap | already_superseded | Yes before delete/archive | `git add -f reports/agent_jobs/dirty_preserve_worktree_classification_20260506/README.md reports/agent_jobs/dirty_preserve_worktree_classification_20260506/diff-check.json` |
| `reports/agent_jobs/dirty_preserve_worktree_classification_20260506/diff-check.json` | ignored | Evaluation | previous classification diff-check | No | already_superseded | Yes before delete/archive | same as above |
| `reports/agent_jobs/preserve_merge_readiness_source_label_chat_20260506/README.md` | ignored | Evaluation / Provenance / Query Orchestration | preserve merge readiness audit | No direct Home BFF file overlap; source-label conceptual overlap | already_superseded | Yes before delete/archive | `git add -f reports/agent_jobs/preserve_merge_readiness_source_label_chat_20260506/README.md reports/agent_jobs/preserve_merge_readiness_source_label_chat_20260506/diff-check.json reports/agent_jobs/preserve_merge_readiness_source_label_chat_20260506/validation.json` |
| `reports/agent_jobs/preserve_merge_readiness_source_label_chat_20260506/diff-check.json` | ignored | Evaluation | generated evidence | No | already_superseded | Yes before delete/archive | same as above |
| `reports/agent_jobs/preserve_merge_readiness_source_label_chat_20260506/validation.json` | ignored | Evaluation | generated evidence | No | already_superseded | Yes before delete/archive | same as above |
| `reports/agent_jobs/query_legacy_api_chat_taxonomy_audit_v1/README.md` | ignored | Query Orchestration / Provenance | blocked legacy `/api/chat` taxonomy audit | Conceptual chat/source-label overlap only | archive_only | Yes before delete/archive | `git add -f reports/agent_jobs/query_legacy_api_chat_taxonomy_audit_v1/README.md reports/agent_jobs/query_legacy_api_chat_taxonomy_audit_v1/diff-check.json` |
| `reports/agent_jobs/query_legacy_api_chat_taxonomy_audit_v1/diff-check.json` | ignored | Query Orchestration / Provenance | generated evidence | Conceptual only | archive_only | Yes before delete/archive | same as above |
| `reports/agent_jobs/query_legacy_chat_envelope_integration_status_20260506/README.md` | ignored | Query Orchestration | legacy chat integration status audit | Conceptual chat handoff overlap only | already_superseded | Yes before delete/archive | `git add -f reports/agent_jobs/query_legacy_chat_envelope_integration_status_20260506/README.md reports/agent_jobs/query_legacy_chat_envelope_integration_status_20260506/diff-check.json` |
| `reports/agent_jobs/query_legacy_chat_envelope_integration_status_20260506/diff-check.json` | ignored | Query Orchestration | generated evidence | Conceptual only | already_superseded | Yes before delete/archive | same as above |
| `reports/agent_jobs/reporting_textual_sources_list_v1/diff-check.json` | ignored | Reporting / Provenance | textual sources list task evidence | Source-display conceptual overlap | DATA_MISSING | Yes before delete/archive | `git add -f reports/agent_jobs/reporting_textual_sources_list_v1/diff-check.json` |
| `reports/agent_jobs/source_label_998d68e_integration_review/README.md` | ignored | Provenance | source-label integration review | Conceptual source-label overlap; no Home BFF file overlap | move_to_separate_lane | No for Provenance commit decision; yes before delete/archive | `git add -f reports/agent_jobs/source_label_998d68e_integration_review/README.md reports/agent_jobs/source_label_998d68e_integration_review/diff-check.json` |
| `reports/agent_jobs/source_label_998d68e_integration_review/diff-check.json` | ignored | Provenance | generated evidence | Conceptual source-label overlap | move_to_separate_lane | No for Provenance commit decision; yes before delete/archive | same as above |
| `reports/agent_jobs/verification-metric-clickthrough-review-v1/diff-check.json` | ignored | Reporting / Evaluation | Verification metric clickthrough evidence | No direct Home BFF file overlap | already_superseded | Yes before delete/archive | `git add -f reports/agent_jobs/verification-metric-clickthrough-review-v1/diff-check.json reports/agent_jobs/verification-metric-clickthrough-review-v1/validation.json` |
| `reports/agent_jobs/verification-metric-clickthrough-review-v1/validation.json` | ignored | Reporting / Evaluation | Verification validation evidence | No direct overlap | already_superseded | Yes before delete/archive | same as above |
| `reports/agent_jobs/verification_lock_dirty_preserve_gate_20260506/README.md` | ignored | Evaluation | Verification dirty preserve gate | No direct Home BFF file overlap | already_superseded | Yes before delete/archive | `git add -f reports/agent_jobs/verification_lock_dirty_preserve_gate_20260506/README.md reports/agent_jobs/verification_lock_dirty_preserve_gate_20260506/diff-check.json` |
| `reports/agent_jobs/verification_lock_dirty_preserve_gate_20260506/diff-check.json` | ignored | Evaluation | generated evidence | No | already_superseded | Yes before delete/archive | same as above |
| `tenn_cockpit_home_design_export_20260506/**` | absent from worktree; stashed in `stash@{8}` | Reporting / Evaluation / Provenance | Cockpit Home design export and source refs | Yes, design/background input for Home work | archive_only | Yes before restore/delete/drop | `git archive --format=tar -o /tmp/tenn_cockpit_home_design_export_20260506.tar 'stash@{8}^3' tenn_cockpit_home_design_export_20260506` |
| `tenn_cockpit_home_design_export_20260506/.DS_Store` | stashed in `stash@{8}` | Reporting | local OS metadata | No | delete_candidate_needs_user_approval | Yes | `git restore --source='stash@{8}^3' -- tenn_cockpit_home_design_export_20260506/.DS_Store` then delete only after approval |
| `tenn_prompt_contracts_response_guidelines.zip` | absent from worktree; stashed in `stash@{8}` | Evaluation / Provenance | prompt/contracts export | Possible process guidance input, no runtime overlap | archive_only | Yes before restore/delete/drop | `git archive --format=tar -o /tmp/tenn_prompt_contracts_response_guidelines.tar 'stash@{8}^3' tenn_prompt_contracts_response_guidelines.zip` |
| Global ignored tool/cache/build dirs (`.venv*/`, `node_modules/`, `.next/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, screenshots, generated local reports) | ignored | Evaluation / local dev state | local runtime/tooling | No direct Home BFF file overlap | delete_candidate_needs_user_approval | Yes | create a separate ignored-artifact cleanup card before any `git clean -X` or `rm -rf` |
| Global ignored local env/data/secrets (`.env*`, `config/system.env`, `data/`, SQLite files, `integrations/*/secrets/`) | ignored | DATA_MISSING | local runtime/data/secrets | No direct Home BFF file overlap | DATA_MISSING | Yes | do not commit, archive, delete, or inspect further without a separate data/security-scoped task |

## Recommended Keep / Commit Set

Keep and commit now only if GPT decides to preserve this audit result:

```bash
git add docs/agent_tasks/dirty_preserve_worktree_classification_post_home_contract_20260507.md
git add -f reports/agent_jobs/dirty_preserve_worktree_classification_post_home_contract_20260507/README.md reports/agent_jobs/dirty_preserve_worktree_classification_post_home_contract_20260507/diff-check.json
git commit -m "milestone(evaluation): classify post-home preserve artifacts" -m "Working: Dirty/untracked/ignored preserve-worktree artifacts after Cockpit Home contract scaffold are classified without runtime changes." -m "Tested: task-card validate, required git preflight, git diff --check, and task-card check-diff."
```

Do not include the legacy-chat or marketplace task cards in the same commit. They are separate lane artifacts.

## Recommended Archive / Delete Candidates

Archive-only candidates:

- `tenn_cockpit_home_design_export_20260506/**`, currently in `stash@{8}`.
- `tenn_prompt_contracts_response_guidelines.zip`, currently in `stash@{8}`.
- Historical ignored report bundles that are superseded by later audits, especially `dirty_preserve_worktree_classification_20260506`, `preserve_merge_readiness_source_label_chat_20260506`, `query_legacy_chat_envelope_integration_status_20260506`, and `verification_lock_dirty_preserve_gate_20260506`.

Delete candidates needing explicit user approval:

- `tenn_cockpit_home_design_export_20260506/.DS_Store` inside `stash@{8}`.
- Global ignored cache/build directories only under a separate cleanup card.

Do not drop `stash@{8}` until the design export and prompt ZIP have been archived or intentionally discarded by the user.

## Files That Should Move To Separate Lane / Task

- Query Orchestration: `docs/agent_tasks/legacy_chat_envelope_merge_strategy_audit_v1.md` plus `reports/agent_jobs/legacy_chat_envelope_merge_strategy_audit_v1/**`.
- Reporting: `docs/agent_tasks/marketplace_matches_workflow_audit_v1.md` plus `reports/agent_jobs/marketplace_matches_workflow_audit_v1/**`.
- Provenance: `reports/agent_jobs/source_label_998d68e_integration_review/**`.
- Reporting/Provenance: `reports/agent_jobs/reporting_textual_sources_list_v1/diff-check.json`, pending DATA_MISSING review of its report status.

## Files That May Block Cockpit Home BFF Route V1

No final visible dirty file path directly overlaps a likely Home BFF implementation path. The blockers are governance and live-lane risk:

- The current audit card cannot be claimed because two unrelated task cards are dirty outside its `allowed_files`.
- A `Reporting` lane job, `backend-import-validity-companies-model-v1`, was active during the audit, then released before final status.
- A live shell watcher was trying to claim the Marketplace audit task card, then was absent in the final process check.
- `reports/agent_jobs/cockpit_home_backend_bff_contract_audit_v1/README.md` is missing from this worktree; only its ignored `diff-check.json` is present.
- The Cockpit Home design export and prompt ZIP are not in the current worktree, but remain preserved in `stash@{8}`.

Verdict: Cockpit Home BFF route v1 should wait in this preserve worktree. It can start in a clean isolated worktree only after a fresh `list-active`/`check-overlap` pass confirms no active same-lane or file overlap, and after GPT decides what to do with the current untracked task cards.

## Suggested Next Commands, Grouped By Option

Option A - preserve only this audit:

```bash
git add docs/agent_tasks/dirty_preserve_worktree_classification_post_home_contract_20260507.md
git add -f reports/agent_jobs/dirty_preserve_worktree_classification_post_home_contract_20260507/README.md reports/agent_jobs/dirty_preserve_worktree_classification_post_home_contract_20260507/diff-check.json
git commit -m "milestone(evaluation): classify post-home preserve artifacts" -m "Working: Post-Cockpit Home preserve artifacts are classified without runtime edits." -m "Tested: task-card validate, git preflight, git diff --check, and task-card check-diff."
```

Option B - preserve separate lane audits in separate commits:

```bash
git add docs/agent_tasks/legacy_chat_envelope_merge_strategy_audit_v1.md
git add -f reports/agent_jobs/legacy_chat_envelope_merge_strategy_audit_v1/README.md reports/agent_jobs/legacy_chat_envelope_merge_strategy_audit_v1/diff-check.json
git commit -m "milestone(query): preserve legacy chat envelope audit" -m "Working: Legacy chat envelope merge audit artifacts are preserved separately from Cockpit Home." -m "Tested: report-only artifact preservation."

git add docs/agent_tasks/marketplace_matches_workflow_audit_v1.md
git add -f reports/agent_jobs/marketplace_matches_workflow_audit_v1/README.md reports/agent_jobs/marketplace_matches_workflow_audit_v1/diff-check.json
git commit -m "milestone(reporting): preserve marketplace matches audit" -m "Working: Marketplace matches workflow audit artifacts are preserved separately from Cockpit Home." -m "Tested: report-only artifact preservation."
```

Option C - inspect stashed Cockpit Home export before archive/delete decisions:

```bash
git stash show --include-untracked --name-only 'stash@{8}'
git ls-tree -r --name-only 'stash@{8}^3' -- tenn_cockpit_home_design_export_20260506 tenn_prompt_contracts_response_guidelines.zip
```

Option D - archive stashed design/prompt artifacts after approval:

```bash
git archive --format=tar -o /tmp/tenn_cockpit_home_design_export_20260506.tar 'stash@{8}^3' tenn_cockpit_home_design_export_20260506
git archive --format=tar -o /tmp/tenn_prompt_contracts_response_guidelines.tar 'stash@{8}^3' tenn_prompt_contracts_response_guidelines.zip
```

Option E - start Cockpit Home BFF route v1 later from a clean worktree:

```bash
python3 scripts/agent_job_registry.py list-active --repo-root /mnt/sdb2/home/l4nd0/tenn
python3 scripts/agent_job_registry.py check-overlap <home-bff-task-card> --repo-root /mnt/sdb2/home/l4nd0/tenn
python3 scripts/agent_job_registry.py claim <home-bff-task-card> --repo-root /mnt/sdb2/home/l4nd0/tenn
```

Do not run any of these commands from this audit.

## Collision Risk

- Audit-only classification: MEDIUM. The report writes are narrow, but the preserve branch is live and active `Reporting` work exists.
- Any commit/archive/delete decision: MEDIUM until GPT chooses exact scope.
- Cockpit Home BFF implementation in this worktree: HIGH because current dirty files and active live work make task-card claim/check-diff fail.
- Cockpit Home BFF implementation in a clean isolated worktree after registry recheck: likely MEDIUM if scoped to Home BFF contract wiring only.

## DATA_MISSING

- Exact reason `47cb4c510cf5` is not the ancestor commit while `f7a7454` carries the same Cockpit Home contract scaffold file set on this branch.
- Whether `reports/agent_jobs/cockpit_home_backend_bff_contract_audit_v1/README.md` should be restored from another worktree, committed from a different task, or treated as absent.
- Whether the live Marketplace claim watcher should be stopped, left to time out, or allowed to claim after dirty files are resolved.
- Whether `tenn_cockpit_home_design_export_20260506/**` and `tenn_prompt_contracts_response_guidelines.zip` should be kept in git, archived outside git, or deleted after approval.
- Whether global ignored runtime/cache/data artifacts should be cleaned; this audit did not classify each of the about 1000 ignored entries individually.

## Can Cockpit Home BFF Route V1 Start Now?

Not in this preserve worktree.

It should wait until:

1. GPT decides the current three visible untracked task cards.
2. A fresh registry check confirms no active same-lane or file overlap for the new BFF card.
3. Any claim watcher or other live process is resolved or confirmed harmless.
4. A fresh Home BFF task card validates and claims cleanly in a clean isolated worktree.

## Validation Result

| Command | Result |
| --- | --- |
| `git diff --check` | passed with no output |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/dirty_preserve_worktree_classification_post_home_contract_20260507.md` | failed as expected; wrote `reports/agent_jobs/dirty_preserve_worktree_classification_post_home_contract_20260507/diff-check.json`; disallowed files were the pre-existing untracked `legacy_chat_envelope_merge_strategy_audit_v1.md` and `marketplace_matches_workflow_audit_v1.md` |
| `python3 scripts/agent_job_registry.py list-active --repo-root /mnt/sdb2/home/l4nd0/tenn` | final pass returned `active_jobs: []` |

No registry claim was created for this audit, so no release command was needed.

## Project Memory Save Recommendation

Save this memory:

`Post-Cockpit Home contract scaffold cleanup: current preserve worktree only shows three visible untracked task cards (current dirty classification, legacy chat envelope audit, marketplace matches audit). Cockpit Home design export and prompt-contract ZIP are no longer in the worktree but are preserved in stash@{8}. Do not start Home BFF wiring in the dirty preserve worktree; use a clean worktree after registry recheck.`

## Final Report Template

Files changed:
- `docs/agent_tasks/dirty_preserve_worktree_classification_post_home_contract_20260507.md`
- `reports/agent_jobs/dirty_preserve_worktree_classification_post_home_contract_20260507/README.md`
- `reports/agent_jobs/dirty_preserve_worktree_classification_post_home_contract_20260507/diff-check.json`

Files inspected:
- `CLAUDE.md`
- `AGENTS.md`
- `docs/architecture/SYSTEM_CONTRACT.md`
- `docs/entrypoints.md`
- `docs/architecture/13_security_and_secrets.md`
- `docs/claude/STATE.md`
- `/home/l4nd0/.claude/projects/-mnt-sdb2-home-l4nd0-tenn/memory/MEMORY.md`
- `graphify-out/GRAPH_REPORT.md`
- `.cursor/agents/repository_audit.md`
- `.codex/skills/repository-audit/SKILL.md`
- `docs/agent_tasks/dirty_preserve_worktree_classification_post_home_contract_20260507.md`
- `docs/agent_tasks/legacy_chat_envelope_merge_strategy_audit_v1.md`
- `docs/agent_tasks/marketplace_matches_workflow_audit_v1.md`
- selected `reports/agent_jobs/**/README.md` and `diff-check.json` artifacts listed above

Lane: Evaluation
Execution mode: AUDIT ONLY
Collision risk: MEDIUM for this audit, HIGH for Home BFF implementation in this dirty preserve worktree
Validation run:
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/dirty_preserve_worktree_classification_post_home_contract_20260507.md`
- required git preflight commands
- `python3 scripts/agent_job_registry.py list-active --repo-root /mnt/sdb2/home/l4nd0/tenn`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/dirty_preserve_worktree_classification_post_home_contract_20260507.md --repo-root /mnt/sdb2/home/l4nd0/tenn`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/dirty_preserve_worktree_classification_post_home_contract_20260507.md`

Validation result:
- task-card validation passed
- `git diff --check` passed
- final registry list-active returned no active jobs
- claim was skipped because check-overlap/check-diff identified pre-existing dirty files outside this audit card
- task-card check-diff failed as expected on the two unrelated untracked task cards

Files intentionally not touched:
- runtime backend/frontend code
- Cockpit Home BFF route wiring
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/app/services/cockpit_service.py`
- `financial-engine_v2/backend/app/services/query_orchestrator.py`
- `financial-engine_v2/cockpit/core/chat.py`
- `cockpit-ui/lib/api-client.ts`
- databases, Qdrant, news stores, memory stores, ingestion/reindex outputs
- stashes and ignored global runtime/cache/data artifacts

Remaining blockers:
- `docs/agent_tasks/legacy_chat_envelope_merge_strategy_audit_v1.md`
- `docs/agent_tasks/marketplace_matches_workflow_audit_v1.md`
- stashed `tenn_cockpit_home_design_export_20260506/**` and `tenn_prompt_contracts_response_guidelines.zip` need an archive/delete/defer decision
- `reports/agent_jobs/cockpit_home_backend_bff_contract_audit_v1/README.md` is DATA_MISSING in this worktree

Next safe step:
- Preserve this audit if desired, then decide legacy-chat and marketplace audit artifacts in separate lane commits or archives before any Home BFF implementation.
