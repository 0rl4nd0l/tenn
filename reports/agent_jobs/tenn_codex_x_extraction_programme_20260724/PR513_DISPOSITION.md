# PR #513 Disposition

## Objective

Resolve draft PR #513 without merging its stale branch, preserve merged PR #517
behavior, and refresh the extraction supervisor package without starting ticket
01 or launching a Codex X child.

## Current state

`DONE_WITH_RISK`

The disposition is `ADOPT_SUCCESSOR`.

- Extraction canonical:
  `migration/clean-runtime-baseline-reconstruct-v1` at
  `2f5a8aac38cf31ecbed3bcb50420fbd5b32ec8d7`, tree
  `cba105b2ff945fb0279158c7f54de2bcf4517e5d`.
- Old PR #513: closed as superseded at head
  `12ecb02fee3eebe9fd19527bc55a444502ec26d4`.
- Replacement draft PR #521:
  <https://github.com/0rl4nd0l/tenn/pull/521>.
- Replacement head:
  `7c421ad9e7721796e07dd6427f4caf584a577155`.
- Replacement tree:
  `17eecd8c81c3deb8c57c0565fbd13e9d31954bcc`.
- PR #521 remains draft, open, mergeable, and unmerged.

Residual risk is explicit: the accepted authority is not on canonical until a
separately authorized exact-head merge. Ticket 01 is therefore
`DEPENDS_ON_SUCCESSOR_INTEGRATION`, not launchable.

## Intended delta retained

The successor retains nine product, documentation, and test paths:

- `docs/extraction/metric_extraction_contract.md`
- `financial-engine_v2/backend/app/services/extraction_gold_eval.py`
- `financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py`
- `financial-engine_v2/backend/app/services/extraction_review.py`
- `financial-engine_v2/backend/app/services/financial_metric_contract.py`
- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/app/services/pipeline.py`
- `financial-engine_v2/backend/tests/test_extraction_capability_guards.py`
- `financial-engine_v2/backend/tests/test_financial_metric_contract.py`

The registry centralizes existing field and persistence order, evaluation-only
aliases, production relevance, metric family/status rows, source/provenance
requirements, and derivation declarations. Existing caller names remain
compatibility exports.

## Delta rejected

- The stale V2 task card
  `docs/agent_tasks/extraction_metric_contract_authority_v1_20260715.md`.
- Any old-base control-plane, `AGENTS.md`, `.codex`, hook, workflow, or report
  difference.
- Any extraction-correctness, scorecard-policy, source-selection, prompt,
  gold-label, PDF, runtime, data, deployment, or ticket 01 implementation.

## Metric safety

- Canonical and persistence field order is unchanged.
- Evaluation aliases are not production matching rules.
- `net_debt` is direct-source-required.
- `net_debt.authorized_derivations` is empty.
- The registry does not authorize
  `net_debt = total_debt - cash_end`.
- The only authorized derivation remains the existing Appendix 5B sum of
  explicit capex sub-items.
- Existing derived-net-debt runtime behavior remains a described contract
  mismatch and was not changed or approved.

## Validation

- Exact-commit focused suites: `464 passed`, 14 existing warnings.
- Included suites: contract/parity, PR #517 Docling and multipass, extraction
  eval/scorecard, extraction review service/routes, and pipeline.
- Parity digest:
  `cc042df11e1743d9cf3085020991bd6dd8f73da835a7ece2efb48edf1c9f51ce`.
- Changed-file Ruff `0.15.6`: pass.
- Changed-file `py_compile`: pass.
- `git diff --check`: pass.
- Fresh read-only review bound to the exact commit and tree: `SUCCESS`, with
  zero critical findings, warnings, or suggestions.
- PR #521 exact-head checks: `lint-and-test=SUCCESS`, `scan=SUCCESS`, stable
  across two terminal snapshots.

Raw waiter evidence:

- `/tmp/tenn-pr513-validation.d0cg4F/pytest-exact-commit.json`
- `/tmp/tenn-pr513-validation.d0cg4F/pytest-exact-commit.json.log`
- `/tmp/tenn-pr513-validation.d0cg4F/pr521-checks.json`

## Commands and exit status

- Live `git ls-remote`, `gh pr view`, PR diff/check inspection: exit `0`.
- Portable Tenn Git Guard preflight: exit `0`, no non-stale ownership block.
- Two clean `git cherry-pick --no-commit` transplants: exit `0`.
- Disposable tracked-requirements validation environment: exit `0` after
  selecting Python 3.12 and uv all-index resolution.
- Initial focused pytest: exit `1`, only because two edited registry notes
  changed the parity digest; the notes were reverted.
- Exact baseline/candidate digest comparison: exit `0`, canonical digest
  restored.
- Final exact-commit pytest waiter: exit `0`.
- Ruff, compile, and diff checks: exit `0`.
- Push and draft PR creation: exit `0`.
- First combined `gh pr close --comment` attempt: rejected before mutation
  because that installed CLI lacks the flag.
- Supported comment and close calls for PR #513: exit `0`.
- Exact-head PR #521 check waiter: exit `0`.

## Files intentionally not touched

Outside this supervisor package and the nine-file successor commit, no product,
control-plane, source, prompt, fixture, PDF, runtime, data, service, deployment,
or Codex X workspace file was changed. Commit
`d5dd1dd476a496d74a5e0cf77ca26f00e03f4fb9` remains the immutable parent
report-only package revision.

## Unsafe actions avoided

- No merge.
- No runtime, service, queue, DB, Qdrant, GPU, model, extraction, backfill, or
  production-data action.
- No source PDF, gold label, prompt, scorecard denominator, or ticket 01
  implementation.
- No launch-checkout cleanup, reset, stash, or ignored-file dependency.
- No Codex X child launch.

## Ignored and untracked artifacts

The launch checkout's pre-existing ignored caches and reports were not used.
Validation created disposable Python tooling under `/tmp` and ignored test
caches in the clean successor worktree; the exact commit contains only tracked
source. The reviewer confirmed no untracked source dependency.

## Updated ticket 01 classification

`ASXFP_01_SCORECARDS` is now `DEPENDS_ON_SUCCESSOR_INTEGRATION`.

The old ambiguous overlap is resolved, but canonical
`2f5a8aac38cf31ecbed3bcb50420fbd5b32ec8d7` does not yet contain the accepted
registry. Ticket 01 must use the final canonical metric authority for its
precision/recall denominator.

Exact next action: obtain separate authorization to merge draft PR #521 at
exact head `7c421ad9e7721796e07dd6427f4caf584a577155`; after merge, refresh canonical,
create a new run revision, verify the authority/parity digest on that canonical
SHA, and then reclassify only the residual ticket 01 scorecard gap. Do not reuse
or launch the old held prompt.
