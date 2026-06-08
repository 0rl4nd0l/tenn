# Scale Table Candidate Selector

## Objective

Build a report-only fixed-harness candidate selector for the scale-table
provenance cases. Use only existing fixed harness artifacts, count summaries,
and prior exact-doc replay artifacts. Rank exact documents where scale or
provenance evidence still shows a concrete mismatch or `DATA_MISSING`.
Recommend at most one suspect document plus one clean control for a future
isolated-cache pass3a replay.

## Current State

`DONE_WITH_RISK`

One suspect exists, so I do not recommend closing the scale-table repair path
yet. The recommendation is limited to one future approval-gated isolated-cache
pass3a replay: AZJ as suspect and NSR as clean control.

No count-24, count-32, random sample, broad extraction, backfill, production
repair, GitHub mutation, or production-data mutation was run.

## Evidence Used

- Current checkout: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
  - branch: `tmp/sloppy-fix-demo`
  - HEAD: `dfa313aaa6c1b34696f4bf9a8bd430636e5792ce`
  - status: dirty before this job; unrelated dirt preserved
- Count-24 bounded summary:
  `/home/l4nd0/tenn-count24-bounded-validation-v1-20260607/reports/agent_jobs/extraction_count24_bounded_validation_v1_20260607/`
- Count-24 failure taxonomy:
  `/home/l4nd0/tenn-count24-bounded-validation-v1-20260607/reports/agent_jobs/extraction_count24_failure_taxonomy_v1_20260607/`
- Scale source evidence:
  `/home/l4nd0/tenn-count24-bounded-validation-v1-20260607/reports/agent_jobs/extraction_scale_table_source_evidence_after_count24_v1_20260607/`
- Selected-table provenance diagnostic:
  `/home/l4nd0/tenn-count24-bounded-validation-v1-20260607/reports/agent_jobs/extraction_selected_table_provenance_diagnostic_v1_20260607/`
- AZJ/EDU pass3a provenance capture:
  `/home/l4nd0/tenn-azj-edu-pass3a-provenance-v1-20260607/reports/agent_jobs/extraction_azj_edu_pass3a_provenance_capture_v1_20260607/`
- CXO/NSR isolated-cache pass3a replay:
  `/home/l4nd0/tenn-extraction-cxo-runtime-provenance-capture-v1-20260608/reports/agent_jobs/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608/`

## Ranked Candidates

1. AZJ `488d6f1a-0180-4fca-8dcf-c4cdfc0f342e`: suspect recommended.
   Count-24 failed `validation_gate:scale_unknown` with non-null metrics.
   Selected formal-statement pages have same-page `$m` evidence, but exact
   pass3a capture still has empty `metric_source_scales`, empty
   `metric_scale_sources`, fallback `unknown`, and common scale output
   `unknown`.
2. WHC `9640d9f1-a45b-492d-8df5-9bad0f46431c`: not recommended for the next
   pass3a scale-control replay. It has visual `$'000` source scale, but no
   selected statement tables and zero extracted metrics, making it primarily a
   parser/table coverage gap.
3. EDU `ac3c9ab0-e01a-4996-95f9-6466388ddc9c`: not recommended. It has
   scale/provenance `DATA_MISSING`, but source evidence is mixed between
   `$'000` summary sections and raw-dollar main statements, and selected
   income/highlight/share-capital surfaces are unclean.
4. NIC `50398d3d-27f7-4d9e-8a26-a2d69f128a1c`: excluded. It is a one-page
   webcast-details noncandidate policy gap, not a scale-table repair case.

## Recommendation

Future isolated-cache pass3a replay, if approved:

- suspect: AZJ `488d6f1a-0180-4fca-8dcf-c4cdfc0f342e`
- clean control: NSR `f2240712-9dde-41e0-88fa-29c1a0080dab`

NSR is the best control because the prior isolated-cache replay finished `ok`
with row refs, table/document metric scale sources, `metric_source_scales` all
`thousands`, fallback `thousands`, and common-scale output `thousands` across
income, balance, cash-flow, and share-capital tables.

## Decision

Do not close the scale-table repair path yet. Keep it open only for one future
AZJ-vs-NSR isolated-cache replay. If AZJ does not reproduce a concrete
metric-source-scale gap against the NSR control, recommend closing this repair
path rather than running more samples.

## Files Touched

- `docs/agent_tasks/extraction_scale_table_candidate_selector_v1_20260608.md`
- `reports/agent_jobs/extraction_scale_table_candidate_selector_v1_20260608/README.md`
- `reports/agent_jobs/extraction_scale_table_candidate_selector_v1_20260608/selection.json`
- `reports/agent_jobs/extraction_scale_table_candidate_selector_v1_20260608/status.json`
- `reports/agent_jobs/extraction_scale_table_candidate_selector_v1_20260608/validation.json`

## Files Intentionally Not Touched

- extraction runtime code and tests
- source PDFs
- parser caches outside ignored report artifacts
- DB, Qdrant, Redis, news stores, memory, prompts, gold labels, runtime config,
  services, model/GPU config, and production data
- GitHub issues and PRs
- unrelated dirty or untracked workspace files

## Validation Status

Static validation is recorded in `validation.json`:

- task-card validation: passed, exit status `0`
- JSON parse for generated artifacts: passed, exit status `0`
- `git diff --check`: passed, exit status `0`
- task-card `check-diff --no-write-report`: failed, exit status `1`

Runtime validation was not required because this is a report-only selector over
existing artifacts. Running extraction, samples, backfills, or services would
violate the task constraints.

The `check-diff` failure is caused by pre-existing dirty tracked and untracked
files outside this task card allowlist in the shared checkout. I preserved that
unrelated dirt instead of widening the task card or cleaning it.

## Unsafe Actions Avoided

- no count-24 rerun
- no count-32 run
- no random sample
- no broad extraction or backfill
- no production repair
- no DB, Qdrant, Redis, news, memory, source PDF, prompt, gold label, runtime
  config, normal parser-cache, service, model/GPU, or production-data mutation
- no GitHub mutation
- no cleanup of unrelated dirty files

## Next Recommended Prompt

```text
/goal Run one approval-gated isolated-cache pass3a replay for suspect AZJ 488d6f1a-0180-4fca-8dcf-c4cdfc0f342e and clean control NSR f2240712-9dde-41e0-88fa-29c1a0080dab only. Do not run count-24, count-32, random samples, broad extraction, backfill, or production repair. Capture selected tables/pages, row_refs, metric_source_scales, metric_scale_sources, table-local/same-page/document scale evidence, and _common_metric_source_scale input/output. If AZJ no longer reproduces a concrete metric-source-scale gap against the NSR control, recommend closing the scale-table repair path.
```
