---
job_id: youtube_intake_quality_gates_v1_20260526
lane: Evaluation
supporting_lanes:
  - Memory
  - Provenance
  - Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/youtube_intake_quality_gates_v1_20260526.md
  - docs/evaluation_spine_youtube_intake_quality.md
  - scripts/evaluate_youtube_intake_quality.py
  - financial-engine_v2/backend/tests/fixtures/youtube_intake_quality/matrix.json
  - financial-engine_v2/backend/tests/test_youtube_intake_quality_gates.py
  - reports/agent_jobs/youtube_intake_quality_gates_v1_20260526/
  - reports/agent_jobs/youtube_intake_quality_gates_v1_20260526/README.md
  - reports/agent_jobs/youtube_intake_quality_gates_v1_20260526/status.json
  - reports/agent_jobs/youtube_intake_quality_gates_v1_20260526/validation.json
  - reports/agent_jobs/youtube_intake_quality_gates_v1_20260526/diff-check.json
  - reports/agent_jobs/youtube_intake_quality_gates_v1_20260526/youtube_intake_quality_eval.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/youtube_intake_quality_gates_v1_20260526
mutation_mode: safe_extension
production_data_access: false
---

# YouTube Intake Quality Gates

Issue: https://github.com/0rl4nd0l/tenn/issues/102

## Objective

Add a repo-native offline evaluation matrix for autonomous YouTube intake quality
decisions so low-signal and speculative transcripts cannot be treated as factual
memory candidates without explicit review semantics.

## Allowed Scope

- Add synthetic, non-production YouTube intake fixtures.
- Add a local deterministic eval script that classifies fixture rows into
  explicit intake decisions.
- Add focused pytest coverage for the matrix, CLI report output, and
  speculative-as-factual failure behavior.
- Add focused docs/report artifacts describing the quality matrix.

## Forbidden Scope

- No product behavior changes.
- No production DB, Qdrant, news, or memory writes.
- No canonical financial truth, parser routing, extraction prompts, gold labels,
  runtime/model/GPU/service config, or unrelated dirty work.
- No automatic strategy-memory commits or approval bypass.

## Acceptance Criteria

- Fixture matrix covers no transcript, members-only video, short/incomplete
  transcript, generic low-signal commentary, ticker-bearing factual discussion,
  ticker-bearing speculative thesis, and mixed factual/speculative claims.
- Gate reports explicit decisions: `reject`, `quarantine`,
  `factual_candidate`, `speculative_candidate`, and `requires_user_review`.
- Each decision includes evidence fields for downstream memory routing.
- Eval fails loudly when speculative takeaways are treated as factual memory
  candidates.
- Eval is runnable locally without production data access.
- Result links back to #100 as the quality gate for autonomous YouTube intake.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/youtube_intake_quality_gates_v1_20260526.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/youtube_intake_quality_gates_v1_20260526.md --repo-root .`
- `PYTHONPATH=financial-engine_v2/backend uv run --python 3.10 --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest financial-engine_v2/backend/tests/test_youtube_intake_quality_gates.py -q`
- `PYTHONPATH=financial-engine_v2/backend uv run --python 3.10 --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m ruff check scripts/evaluate_youtube_intake_quality.py financial-engine_v2/backend/tests/test_youtube_intake_quality_gates.py`
- `python3 scripts/evaluate_youtube_intake_quality.py --fixtures financial-engine_v2/backend/tests/fixtures/youtube_intake_quality/matrix.json --out-json reports/agent_jobs/youtube_intake_quality_gates_v1_20260526/youtube_intake_quality_eval.json`
- `python3 -m json.tool reports/agent_jobs/youtube_intake_quality_gates_v1_20260526/youtube_intake_quality_eval.json`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/youtube_intake_quality_gates_v1_20260526.md`
