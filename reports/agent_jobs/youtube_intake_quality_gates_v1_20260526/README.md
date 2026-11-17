# YouTube Intake Quality Gates

Issue: https://github.com/0rl4nd0l/tenn/issues/102

## Outcome

Added a local, deterministic evaluation gate for autonomous YouTube intake quality.
The gate uses synthetic fixtures only and produces explicit decisions before any
future memory workflow can treat YouTube commentary as factual or speculative
candidate evidence.

## Matrix

- `no_transcript` -> `reject`
- `members_only` -> `reject`
- `short_incomplete` -> `quarantine`
- `generic_low_signal` -> `requires_user_review`
- `ticker_factual` -> `factual_candidate`
- `ticker_speculative` -> `speculative_candidate`
- `mixed_factual_speculative` -> `requires_user_review`

All output rows include evidence fields for transcript availability, transcript
length, duration, ticker extraction, factual signals, speculative signals, and
fail-closed memory-routing posture.

## Safety

- No production data access.
- No DB, Qdrant, news, or memory writes.
- No product behavior change.
- No strategy-memory automatic commit path; `may_write_memory` is always false.
- Speculative signal rows fail validation if classified as factual candidates.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/youtube_intake_quality_gates_v1_20260526.md` - passed
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/youtube_intake_quality_gates_v1_20260526.md --repo-root .` - passed
- `PYTHONPATH=financial-engine_v2/backend uv run --python 3.10 --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest financial-engine_v2/backend/tests/test_youtube_intake_quality_gates.py -q` - 5 passed
- `PYTHONPATH=financial-engine_v2/backend uv run --python 3.10 --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m ruff check scripts/evaluate_youtube_intake_quality.py financial-engine_v2/backend/tests/test_youtube_intake_quality_gates.py` - passed
- `python3 scripts/evaluate_youtube_intake_quality.py --fixtures financial-engine_v2/backend/tests/fixtures/youtube_intake_quality/matrix.json --out-json reports/agent_jobs/youtube_intake_quality_gates_v1_20260526/youtube_intake_quality_eval.json` - passed
- `python3 -m json.tool reports/agent_jobs/youtube_intake_quality_gates_v1_20260526/youtube_intake_quality_eval.json` - passed
