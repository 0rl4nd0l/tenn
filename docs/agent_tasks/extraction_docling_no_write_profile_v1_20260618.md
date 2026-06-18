---
job_id: extraction_docling_no_write_profile_v1_20260618
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_docling_no_write_profile_v1_20260618.md
  - scripts/extraction_no_write_replay.py
  - scripts/test_extraction_no_write_replay.py
  - reports/agent_jobs/extraction_docling_no_write_profile_v1_20260618/README.md
  - reports/agent_jobs/extraction_docling_no_write_profile_v1_20260618/status.json
  - reports/agent_jobs/extraction_docling_no_write_profile_v1_20260618/validation.json
  - reports/agent_jobs/extraction_docling_no_write_profile_v1_20260618/diff-check.json
  - reports/agent_jobs/extraction_docling_no_write_profile_v1_20260618/docling_preflight/input_manifest.json
  - reports/agent_jobs/extraction_docling_no_write_profile_v1_20260618/docling_preflight/replay_results.json
  - reports/agent_jobs/extraction_docling_no_write_profile_v1_20260618/docling_preflight/side_effect_audit.json
  - reports/agent_jobs/extraction_docling_no_write_profile_v1_20260618/docling_preflight/validation.json
  - reports/agent_jobs/extraction_docling_no_write_profile_v1_20260618/docling_preflight/logs/replay.log
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_docling_no_write_profile_v1_20260618
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: false
---

# Certified Docling No-Write Profile

## Objective

Extend `scripts/extraction_no_write_replay.py` with a certified
`docling-no-write` profile that lets future agents use docling and an approved
existing repo/backend venv without asking for fresh approval.

## Scope

- Preserve the current default baseline no-write profile.
- Add explicit profile selection for `baseline-no-write` and
  `docling-no-write`.
- Let `docling-no-write` use only an approved existing venv Python, never
  install or repair dependencies.
- Return `DATA_MISSING` with report artifacts when no approved venv or docling
  import is available.
- Keep all no-write guarantees from the existing harness.

## Hard Stops

- Do not install dependencies, modify lockfiles, mutate venvs, or use
  host-global package managers.
- Do not start services, download models, change runtime/model/GPU config, or
  modify production data.
- Do not mutate DB, Qdrant, Redis, news stores, memory, source PDFs, prompts,
  gold labels, registry state, or GitHub.
- Do not run broad extraction, count samples, or backfills.

## Validation

- Task-card validate.
- Focused unit tests for profile selection, approved venv checks, no-install
  behavior, and `DATA_MISSING` preflight handling.
- `py_compile`.
- `docling-no-write --preflight-only` against a small certified case. On this
  host it may correctly return `DATA_MISSING` if no approved docling-capable
  venv exists.
- `git diff --check`.
- Task-card `check-diff`.
- Report artifact check.

## Autonomy Rule

Future agents may run the `docling-no-write` profile without fresh approval
only when:

1. the task card allows the exact report artifacts,
2. every selected case is certified by the manifest,
3. the profile uses an approved existing venv Python or the current Python is
   already an approved repo venv,
4. docling imports successfully before extraction starts,
5. the runner verifies isolated cache/runtime roots and report-only writes, and
6. no dependency install, GitHub, broad extraction, backfill, production data,
   or non-loopback service boundary is crossed.

Otherwise the runner must fail closed as `DATA_MISSING` or `FAIL`; agents must
not improvise environment setup.
