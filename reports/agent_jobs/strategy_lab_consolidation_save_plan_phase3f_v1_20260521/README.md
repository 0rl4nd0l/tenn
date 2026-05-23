# Phase 3F Consolidation Save Plan

Job: `strategy_lab_consolidation_save_plan_phase3f_v1_20260521`

Mode: consolidation/save plan only, audit/report only.

Recommendation: `GO_PHASE3G_CONSOLIDATION_EXECUTION_TASK_CARD_DRAFT_ONLY`

## Confirmed Facts

- `/home/l4nd0/tenn` resolves to
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Current branch is `migration/clean-runtime-baseline-reconstruct-v1`.
- Current HEAD is `2bff733e2d7f8fadfde6d492a5ff48212b710f59`.
- The Phase 3F task card validates successfully.
- Registry `list-active` is available and currently shows one unrelated active
  Reporting job for `cockpit-ui`.
- Registry `check-overlap` for Phase 3F fails because pre-existing Phase 3D and
  Phase 3E task cards are untracked outside the Phase 3F allowlist.
- Registry claim was not attempted.
- Phase 3E report evidence is available and recommends
  `GO_PHASE3F_CONSOLIDATION_SAVE_PLAN_ONLY`.
- Phase 3D report evidence is available and recommends
  `GO_PHASE3E_OFFLINE_IMPLEMENTATION_PLAN_ONLY`.
- Phase 2, Phase 2B, Phase 3A, Phase 3B, and Phase 3C worktrees are available.
- Phase 2 has untracked authoritative schema/task/fixture files plus ignored
  report evidence.
- Phase 2B has untracked helper candidate doc/module/test/fixture files plus
  ignored report/raw/normalized helper outputs.
- Phase 3A has staged additions for task card, docs, mock payloads, and report
  files.
- Phase 3B has untracked docs/vectors/test, ignored report evidence, an older
  duplicate framework report bundle, and generated pycache.
- Phase 3C has untracked docs/vectors/mock transport docs/fixtures/test,
  ignored report evidence, an older duplicate framework report bundle, and
  generated pycache.
- Phase 3F did not merge, cherry-pick, commit, copy, stage, unstage, clean,
  stash, reset, remove, or edit Phase 2/2B/3A/3B/3C/3D/3E files.
- Phase 3F did not edit `docs/strategy_lab/**`, `tests/strategy_lab/**`,
  runtime/backend/product code, Cockpit, stores, dependency files, parser/gold
  files, source-registry files, services, tokens, production data, or
  paper/live/trading paths.

## Inferred Facts

- Phase 2 `strategy_lab_artifact_v1` should remain the authoritative schema
  candidate.
- Phase 2B helper output is useful only as pending-review helper evidence.
- Phase 3A, 3B, and 3C provide a coherent offline design/test/transport evidence
  chain, but the chain is not yet saved as baseline.
- A production-module implementation task card would be premature until the
  save/archive/exclude decisions are explicit.

## Speculative Ideas

- A future implementation plan could use a Tenn-owned sidecar client boundary,
  but only after consolidation and a separate task card.
- A later Project Memory save block would reduce the chance of confusing helper
  candidate evidence with authoritative baseline.

## DATA_MISSING

- Proof that Phase 2/2B/3A/3B/3C files are committed, merged, or otherwise
  preserved in an authoritative baseline.
- Approved destination for each candidate file group.
- Approved handling for Phase 3A staged additions.
- Approved handling for ignored report bundles under `reports/agent_jobs`.
- Approved handling for duplicate framework report bundles.
- Approved handling for generated pycache files.
- Real QuantDinger sidecar capability, auth, transport, retry, timeout,
  rate-limit, and unavailable behavior.
- Raw-output quarantine path and retention policy.
- Artifact persistence/store implementation plan.

## Inputs Inspected

- Phase 3E README, worktree readiness, go/no-go, and status.
- Phase 3D README, go/no-go, and status.
- Phase 2 README, go/no-go, status, git status, and report bundle list.
- Phase 2B README, status, git status, and report bundle list.
- Phase 3A README, go/no-go, status, git status, and report bundle list.
- Phase 3B README, go/no-go, status, git status, report bundle list, duplicate
  report search, and pycache search.
- Phase 3C README, go/no-go, status, git status, report bundle list, duplicate
  report search, and pycache search.
- Current checkout branch, HEAD, status, symlink resolution, worktree list,
  recent commits, task-card validation, registry status, and registry overlap
  output.

## Files Written

- `docs/agent_tasks/strategy_lab_consolidation_save_plan_phase3f_v1_20260521.md`
- `reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/README.md`
- `reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/preflight.md`
- `reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/input_inventory.md`
- `reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/worktree_file_classification.md`
- `reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/preservation_model.md`
- `reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/future_action_matrix.md`
- `reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/phase3g_recommendation.md`
- `reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/status.json`
- `reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/diff-check.json` if generated by supported validation

## Worktree / File Classification

- Active authoritative candidate inputs: Phase 2 schema/fixtures, Phase 3A
  adapter docs/mock payloads, Phase 3B vectors/test, and Phase 3C mock
  transport docs/fixtures/test.
- Report-only evidence: Phase 2, 2B, 3A, 3B, 3C, 3D, 3E, and Phase 3F report
  bundles.
- Pending-review helper candidate: Phase 2B helper doc/module/test/fixtures/raw
  summaries/normalized outputs.
- Archive-only or duplicate/superseded: older
  `strategy_lab_quantdinger_framework_v1_20260520` bundles under Phase 3B and
  Phase 3C, and helper semantics that conflict with
  `strategy_lab_artifact_v1`.
- Generated/exclude: Phase 3B and Phase 3C pycache.
- DATA_MISSING: committed baseline proof and approved save destinations.

## Preservation Model

Preserve the Strategy Lab evidence by separating:

- authoritative candidates to save only under future approval;
- report/task-history evidence to force-add only if desired;
- helper evidence to keep pending-review;
- duplicate framework material to archive;
- generated pycache to exclude.

No preservation action was performed in Phase 3F.

## Future Action Matrix

The main future actions are:

- `COMMIT_TO_BASELINE_CANDIDATE` for Phase 2 authoritative schema/fixtures,
  Phase 3A design docs/mock payloads, Phase 3B unique vectors/test, and Phase
  3C unique transport docs/fixtures/test.
- `FORCE_ADD_REPORT_EVIDENCE_CANDIDATE` for selected ignored report bundles if
  the project wants report evidence in git.
- `KEEP_PENDING_REVIEW` for Phase 2B helper candidate material.
- `SUPERSEDE_WITH_AUTHORITATIVE_SCHEMA` for helper or copied schema material
  that conflicts with Phase 2 authoritative schema.
- `ARCHIVE_ONLY` for duplicate older framework bundles.
- `EXCLUDE_GENERATED` for pycache.
- `DATA_MISSING_REVIEW_REQUIRED` for proof of consolidated baseline and Phase
  3A staged-addition handling.

## Risks

- Dirty or staged worktrees could be mistaken for committed baseline.
- Helper artifacts could be mistaken for authoritative Strategy Lab artifacts.
- Ignored report bundles could disappear from future checkouts if not explicitly
  preserved.
- Phase 3A staged additions need a separate handling decision.
- Future runtime work could accidentally absorb helper/backend candidate files
  before the authoritative schema boundary is settled.
- Generated pycache could be preserved accidentally if a later task uses broad
  copy/add rules.

## Validation Summary

- `jq empty` on `status.json`: passed.
- Markdown hygiene: passed.
- `git diff --check`: passed.
- `git diff --cached --check`: passed.
- `agent_job_contract.py check-diff`: failed only on the pre-existing unrelated
  Phase 3D and Phase 3E task cards outside the Phase 3F allowlist.
- Final registry `list-active`: passed with two unrelated active jobs, one
  Reporting job for `cockpit-ui` and one Evaluation job for
  `sloppy_fix_manual_only_v1`.
- Final ordinary git status shows the Phase 3F task card plus the pre-existing
  Phase 3D and Phase 3E task cards; the Phase 3F report bundle is ignored under
  `reports/agent_jobs`.
- Targeted status for `docs/strategy_lab`, `tests/strategy_lab`,
  `financial-engine_v2`, `cockpit-ui`, `scripts`, dependency files, Docker
  files, and env files had no entries.
- QuantDinger process scan found no `quantdinger` or `tenn_quantdinger`
  process.
