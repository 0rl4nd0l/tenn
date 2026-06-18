---
job_id: extraction_no_write_replay_harness_v1_20260618
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_no_write_replay_harness_v1_20260618.md
  - scripts/extraction_no_write_replay.py
  - scripts/test_extraction_no_write_replay.py
  - financial-engine_v2/data/extraction_no_write_cases/guard_cases_v1.json
  - reports/agent_jobs/extraction_no_write_replay_harness_v1_20260618/README.md
  - reports/agent_jobs/extraction_no_write_replay_harness_v1_20260618/status.json
  - reports/agent_jobs/extraction_no_write_replay_harness_v1_20260618/validation.json
  - reports/agent_jobs/extraction_no_write_replay_harness_v1_20260618/diff-check.json
  - reports/agent_jobs/extraction_no_write_replay_harness_v1_20260618/subagents/safety_contract_WORKER_RESULT.md
  - reports/agent_jobs/extraction_no_write_replay_harness_v1_20260618/subagents/case_corpus_WORKER_RESULT.md
  - reports/agent_jobs/extraction_no_write_replay_harness_v1_20260618/subagents/review_WORKER_RESULT.md
  - reports/agent_jobs/extraction_no_write_replay_harness_v1_20260618/no_write_replay/input_manifest.json
  - reports/agent_jobs/extraction_no_write_replay_harness_v1_20260618/no_write_replay/replay_results.json
  - reports/agent_jobs/extraction_no_write_replay_harness_v1_20260618/no_write_replay/side_effect_audit.json
  - reports/agent_jobs/extraction_no_write_replay_harness_v1_20260618/no_write_replay/validation.json
  - reports/agent_jobs/extraction_no_write_replay_harness_v1_20260618/no_write_replay/logs/replay.log
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 14400
output_dir: reports/agent_jobs/extraction_no_write_replay_harness_v1_20260618
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: false
---

# Certified No-Write Extraction Replay Harness

## Objective

Create a repo-native command that Codex agents can run without fresh approval
when a task card allows the report outputs and the selected cases are in the
certified manifest.

The command must run only fixed local cases, isolate parser/cache writes under
`/tmp`, write durable artifacts only under the selected report directory, and
emit side-effect evidence that protected surfaces were not changed.

## Certified V1 Corpus

- WHC `9640d9f1-a45b-492d-8df5-9bad0f46431c`
- CTN `dec0b5f1-e6d2-48d8-ad9d-16ffd540ee39`
- HUB `419bcca8-213e-4706-8962-8e3bd8adf091`
- LBL `551c6b84-1053-405c-a833-4ecc018e2045` as the repaired companion-period guard
- AZJ `488d6f1a-0180-4fca-8dcf-c4cdfc0f342e`
- NSR `f2240712-9dde-41e0-88fa-29c1a0080dab`

## Hard Stops

- Do not mutate DB, Qdrant, Redis, news stores, memory, source PDFs, prompts,
  gold labels, runtime/service/model/GPU config, schemas, registry state, or
  production data.
- Do not run count-24, count-32, random samples, broad extraction, backfill, or
  full ticker-universe extraction.
- Do not fetch missing source artifacts; mark them `DATA_MISSING`.
- Do not push, open PRs, comment on GitHub, merge, rebase, reset, stash, clean,
  or delete branches/worktrees.

## Required Runner Contract

- Refuse non-certified cases.
- Refuse missing source files.
- Require loopback-only LLM URLs; do not start services.
- Use a disposable `DATA_ROOT` under `/tmp`.
- Verify docling/parser cache root is under that disposable `DATA_ROOT`.
- Write durable outputs only inside `--report-dir`.
- Record before/after git status, source PDF fingerprints, normal parser-cache
  snapshots, isolated cache contents, and forbidden-surface booleans.

## Validation

- Task-card validate.
- Registry `list-active --read-only`.
- Focused unit tests for manifest/case selection/report-dir/env safety.
- `py_compile` for the runner.
- Smoke replay over HUB and LBL if local LLM/runtime prerequisites are present;
  otherwise record the exact missing prerequisite as `DATA_MISSING`.
- Full v1 corpus replay if the smoke passes and remains within no-write safety.
- `git diff --check`.
- Task-card `check-diff`.
- Report artifact check.

## Autonomy Rule

Future agents may run `scripts/extraction_no_write_replay.py` without fresh
approval only when:

1. the task card allows the exact report artifacts,
2. every selected case is present in the certified manifest,
3. the runner verifies isolated cache and report-only durable writes, and
4. no GitHub, broad extraction, backfill, production data, or non-loopback
   service boundary is crossed.

All other extraction runs still require explicit approval.
