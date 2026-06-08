# AZJ/NSR Isolated Pass3a Replay

## Objective

Run one report-local isolated-cache pass3a replay for suspect AZJ
`488d6f1a-0180-4fca-8dcf-c4cdfc0f342e` and clean control NSR
`f2240712-9dde-41e0-88fa-29c1a0080dab` only.

Capture selected tables/pages, row refs, `metric_source_scales`,
`metric_scale_sources`, table-local/same-page/document scale evidence, and
`_common_metric_source_scale` input/output. Decide whether AZJ reproduces a
concrete metric-source-scale gap against the NSR control.

## Current State

`DONE_WITH_RISK`

Replay state is `DONE`. Repo closeout is `DONE_WITH_RISK` because task-card
`check-diff` exits 1 on two preserved pre-existing untracked sibling task cards:

- `docs/agent_tasks/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608.md`
- `docs/agent_tasks/extraction_cxo_runtime_provenance_capture_v1_20260608.md`

The replay-critical predicates passed.

## Decision

`DO_NOT_FIX_FROM_THIS_REPLAY`

The AZJ suspect did not reproduce the expected scale-source gap under an
isolated parser cache. AZJ returned `status=ok`, payload scale `millions`, and
all captured `metric_source_scales` were `millions`. NSR returned `status=ok`,
payload scale `thousands`, and all captured `metric_source_scales` were
`thousands`.

Recommendation: close this scale-table repair path. Do not run count-24,
count-32, random samples, broad extraction, or backfill from this evidence.

## Constraints And Unsafe Actions

Mode: `REPORT_LOCAL` / `audit_only`.

Hard stops honored:

- No count-24.
- No count-32.
- No random samples.
- No broad extraction, backfill, or full ticker-universe extraction.
- No production extraction repair.
- No DB, Qdrant, Redis, news, memory, source PDF, prompt, gold-label, runtime
  config, schema, normal parser cache, service, model/GPU, or production-data
  mutation.
- No GitHub mutation.
- No merge, rebase, reset, stash, branch deletion, or unrelated cleanup.

## Evidence Used

Target worktree:

`/home/l4nd0/tenn-extraction-cxo-runtime-provenance-capture-v1-20260608`

Target branch and HEAD:

`safe/extraction-cxo-runtime-provenance-capture-v1-20260608`

`1a1b1c2a7d7fec23d420a509b44dc5d18b59e0fb`

Baseline context:

`/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Baseline branch and HEAD:

`tmp/sloppy-fix-demo`

`dfa313aaa6c1b34696f4bf9a8bd430636e5792ce`

The baseline checkout was not used for the replay because its
`run_multipass_extraction` is stubbed and it lacks the matching
`docling_extract.py` source file needed for this pass3a debug-capture contract.

Exact PDFs:

- AZJ:
  `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/AZJ/financial_performance/2025-08-18_aurizon-network-pty-ltd-full-year-report_488d6f1a-0180-4fca-8dcf-c4cdfc0f342e.pdf`
- NSR:
  `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/NSR/financial_performance/2022-02-25_half-year-accounts_f2240712-9dde-41e0-88fa-29c1a0080dab.pdf`

Replay artifacts:

- `pass3a_debug_replay.json`
- `common_metric_source_scale_trace.json`
- `status.json`
- `validation.json`
- `logs/pass3a_debug_replay.log`
- `logs/validation.log`

## Replay Findings

AZJ:

- `status=ok`
- payload scale: `millions`
- `metric_source_scales`: all captured as `millions`
- `metric_scale_sources`: all captured as `table`
- selected tables present: `balance_sheet`, `cashflow_statement`,
  `income_statement`, `share_capital`
- common metric source scale output: `millions`

NSR:

- `status=ok`
- payload scale: `thousands`
- `metric_source_scales`: all captured as `thousands`
- `metric_scale_sources`: table for financial metrics, document for
  `shares_outstanding`
- selected tables present: `balance_sheet`, `cashflow_statement`,
  `income_statement`, `share_capital`
- common metric source scale output: `thousands`

This replay does not prove every metric value is correct. It only closes the
specific suspected scale-source gap path for these exact documents.

## Isolation Proof

Run root:

`/tmp/tenn-azj-nsr-isolated-pass3a-replay-v1-20260608-run-20260608064212`

Cache root:

`/tmp/tenn-azj-nsr-isolated-pass3a-replay-v1-20260608-run-20260608064212/reports/extraction_cache/docling_extract`

Validation predicates:

- isolated cache used: pass
- isolated cache before count: `0`
- isolated cache after count: `2`
- isolated run root contains only `.docling.json` parser-cache files: pass
- source PDFs unchanged before/after: pass
- normal parser caches unchanged before/after: pass
- production repair implemented: false

## Files Touched

- `docs/agent_tasks/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608.md`
- `reports/agent_jobs/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608/README.md`
- `reports/agent_jobs/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608/pass3a_debug_replay.py`
- `reports/agent_jobs/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608/pass3a_debug_replay.json`
- `reports/agent_jobs/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608/common_metric_source_scale_trace.json`
- `reports/agent_jobs/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608/status.json`
- `reports/agent_jobs/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608/validation.json`
- `reports/agent_jobs/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608/logs/task_card_validate.log`
- `reports/agent_jobs/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608/logs/pass3a_debug_replay.log`
- `reports/agent_jobs/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608/logs/validation.log`

## Files Intentionally Not Touched

- Source PDFs
- Normal parser caches
- DB, Qdrant, Redis, and news stores
- Prompts and gold labels
- Runtime config, services, schemas, model/GPU config
- Production extraction code
- GitHub issues or PRs
- The two pre-existing untracked sibling task cards listed above

## Commands Run

- `pwd -P` in baseline and sibling worktrees: exit 0.
- `git branch --show-current` in baseline and sibling worktrees: exit 0.
- `git rev-parse HEAD` in baseline and sibling worktrees: exit 0.
- `git remote -v` in sibling worktree: exit 0.
- `git status --short --untracked-files=all` in baseline and sibling worktrees:
  exit 0.
- `python3 scripts/agent_job_registry.py list-active --read-only`: exit 0.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608.md`:
  exit 0.
- First replay launch: exit 126 due an interpreter path typo; no replay ran.
- Correct isolated replay command with `PYTHONDONTWRITEBYTECODE=1`,
  `DATA_ROOT=/tmp/tenn-azj-nsr-isolated-pass3a-replay-v1-20260608-run-20260608064212`,
  `DATABASE_URL=sqlite:///:memory:`, `TASK_MODE=sync`,
  `AUTO_CREATE_TABLES=false`, `ENABLE_EMBEDDINGS=false`,
  `ENABLE_QDRANT=false`, and `PYTHONPATH=financial-engine_v2/backend`: exit 0.
- `json_and_replay_predicates`: exit 0.
- `runner_syntax_compile_no_bytecode`: exit 0.
- `git diff --check`: exit 0.
- `python3 scripts/agent_job_contract.py check-diff --no-write-report docs/agent_tasks/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608.md`:
  exit 1 due preserved pre-existing untracked sibling task cards.
- `git status --short --ignored --untracked-files=all reports/agent_jobs/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608`:
  exit 0.

## Validation Status

Replay-critical validation: pass.

Task-card validation: pass.

Whitespace/conflict-marker check: pass.

Task-card diff gate: blocked by unrelated pre-existing untracked task cards.

`DATA_MISSING`: none for the requested replay fields.

## Raw Logs

- `reports/agent_jobs/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608/logs/task_card_validate.log`
- `reports/agent_jobs/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608/logs/pass3a_debug_replay.log`
- `reports/agent_jobs/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608/logs/validation.log`

## Approvals Needed

None for this report-local replay closeout.

Explicit approval is still required for any production repair, GitHub mutation,
broad extraction, count-24/count-32/random sample, backfill, service start, or
data-store mutation.

## Blocked Items And DATA_MISSING

- `DATA_MISSING`: none for the requested replay fields.
- `check-diff`: blocked by preserved pre-existing untracked task cards outside
  this task card's `allowed_files`.

## Ignored Or Untracked Artifact Note

The `reports/` tree is ignored by git, so report artifacts appear as `!!` under
`git status --ignored`. The task card is untracked and visible under normal
`git status`.

The two pre-existing sibling task cards remain untracked and outside this
task's allowlist. They were not modified or deleted.

## Remaining Risk

This replay only tests the exact AZJ suspect and NSR control documents. It does
not validate broad extraction behavior, corpus-level rates, every metric value,
or a production repair. No such wider claim should be made from this report.

## Next Recommended Prompt

Review `reports/agent_jobs/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608`
and close the AZJ/NSR scale-table repair path as
`DO_NOT_FIX_FROM_THIS_REPLAY`. Do not run count-24, count-32, random sampling,
broad extraction, or backfill from this evidence.
