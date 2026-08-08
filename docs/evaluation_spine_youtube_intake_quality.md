# YouTube Intake Quality Matrix

This matrix is an offline evaluation gate for autonomous YouTube/commentary intake.
It does not approve transcripts, write memory, write Qdrant, or change product
behavior. It classifies synthetic fixture rows into review decisions that future
channel-watch automation can use before any memory workflow sees a transcript.

## Decisions

| Decision | Meaning | Memory routing posture |
| --- | --- | --- |
| `reject` | No usable transcript or inaccessible video. | No memory candidate. |
| `quarantine` | Transcript exists but is incomplete or otherwise unsafe for intake. | No memory candidate until re-ingested or reviewed. |
| `factual_candidate` | Ticker-bearing factual discussion is present. | Candidate only; explicit approval still required. |
| `speculative_candidate` | Ticker-bearing thesis/speculation is present. | Candidate only; must remain speculative and approval-gated. |
| `requires_user_review` | Mixed or low-signal content needs an operator decision. | Review item only; no automatic memory write. |

## Required Fixture Classes

- no transcript
- members-only video
- short/incomplete transcript
- generic low-signal commentary
- ticker-bearing factual discussion
- ticker-bearing speculative thesis
- mixed factual/speculative claims

## Fail-Closed Rules

- `may_write_memory` is always `false` in this eval output.
- Any row with speculative signals must not be classified as
  `factual_candidate`.
- Any expected/actual decision mismatch fails the eval.
- Missing required fixture classes fail the eval.

## Local Command

```bash
python3 scripts/evaluate_youtube_intake_quality.py \
  --fixtures financial-engine_v2/backend/tests/fixtures/youtube_intake_quality/matrix.json \
  --out-json reports/agent_jobs/youtube_intake_quality_gates_v1_20260526/youtube_intake_quality_eval.json
```

This is the evaluation gate linked to the broader YouTube strategy-memory audit
tracked by #100.
