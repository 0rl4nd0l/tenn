---
job_id: extraction_azj_nsr_isolated_pass3a_replay_v1_20260608
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608.md
  - reports/agent_jobs/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608/README.md
  - reports/agent_jobs/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608/pass3a_debug_replay.py
  - reports/agent_jobs/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608/pass3a_debug_replay.json
  - reports/agent_jobs/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608/common_metric_source_scale_trace.json
  - reports/agent_jobs/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608/status.json
  - reports/agent_jobs/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608/validation.json
  - reports/agent_jobs/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608/logs/task_card_validate.log
  - reports/agent_jobs/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608/logs/pass3a_debug_replay.log
  - reports/agent_jobs/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608/logs/validation.log
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608
mutation_mode: audit_only
production_data_access: false
github_mutation_allowed: false
allow_audit_code_changes: true
---

# AZJ/NSR Isolated Pass3a Replay

## Objective

Run one report-local isolated-cache pass3a replay for suspect AZJ
`488d6f1a-0180-4fca-8dcf-c4cdfc0f342e` and clean control NSR
`f2240712-9dde-41e0-88fa-29c1a0080dab` only.

Capture selected tables/pages, row refs, `metric_source_scales`,
`metric_scale_sources`, table-local/same-page/document scale evidence, and
`_common_metric_source_scale` input/output. If AZJ does not reproduce a concrete
metric-source-scale gap against the NSR control, recommend closing the
scale-table repair path.

## Scope

Mode: REPORT_LOCAL. No production extraction repair.

Target worktree:

`/home/l4nd0/tenn-extraction-cxo-runtime-provenance-capture-v1-20260608`

Reason: the baseline checkout
`/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` currently has a stubbed
`run_multipass_extraction` and lacks the matching `docling_extract.py` source
file. This sibling worktree has the full pass3a/debug-capture contract already
used by prior exact-doc replay artifacts.

## Hard Stops

- Do not run count-24.
- Do not run count-32.
- Do not run random samples.
- Do not run broad extraction, backfill, or full ticker-universe extraction.
- Do not implement production repair.
- Do not mutate DB, Qdrant, Redis, news stores, memory, source PDFs, prompts,
  gold labels, runtime config, schemas, normal parser caches, services,
  model/GPU config, or production data.
- Do not create, edit, label, comment on, close, or reopen GitHub issues.
- Do not clean, stash, reset, merge, rebase, cherry-pick, delete branches, or
  delete unrelated dirt.

## Required Output

- Exact-doc replay artifact for AZJ and NSR.
- Isolated-cache proof.
- Source PDF and normal parser-cache unchanged checks.
- Captured pass3a tables, row refs, metric source scales, scale sources, and
  common-scale traces.
- Decision on whether AZJ reproduces a concrete gap against NSR.
- Static validation and explicit no-sample/backfill statement.
