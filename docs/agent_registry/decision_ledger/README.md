# Agent Decision Ledger

The Agent Decision Ledger records whether a proof question changed. It is
append-only and separate from the Agent Task Ledger: completing a task does not
mean that its claim, evidence, or phase changed.

## Live source and path resolution

The live ledger is `<registry_root>/decision-ledger.jsonl`, beside
`task-ledger.jsonl`. `scripts/agent_decision_ledger.py` resolves the same shared
registry root as `scripts/agent_job_registry.py`:

1. `TENN_AGENT_REGISTRY_ROOT`
2. `git config tenn.agentRegistryRoot`
3. the Git common directory plus `tenn-agent-registry`
4. the repo-local `.tenn/agent_jobs` fallback when Git metadata is unavailable

Linked worktrees therefore see one decision ledger. Never construct a path from
a worktree's literal `.git` entry.

Read-only commands do not create a missing ledger. For a V2 run, a missing live
ledger is reported as `DATA_MISSING` and must be initialized only by the
authorization-explicit `initialize` command.

## Entry contract

Every JSONL object contains:

- identity: `decision_id`, `scope_fingerprint`, `task_id`, and `run_id`
- semantic scope: `project_id`, `claim_id`, `hypothesis_id`, `program_track`,
  `source_class`, `dataset_version`, `evidence_hash`, and `target_transition`
- transition: `phase_before` and `phase_after`
- result: `decision`, `outcome_status`, and `decision_delta`
- evidence and effect: `evidence_refs`, `blocks`, and `does_not_block`
- validity: `validated_at`, `invalidation_conditions`, and `reopen_conditions`

`decision` is one of `PASS`, `FAIL`, `DATA_MISSING`, `CONFLICT`, or `PARKED`.
`outcome_status` uses the V2 `RUN_OUTCOME.json` statuses. `program_track` is
`offline_development` or `prospective_readiness`.

The `scope_fingerprint` is the lowercase 64-character SHA-256 value computed
from the V2 task contract. The helper recomputes it from the seven semantic
scope fields and rejects mismatches. It is recorded here, never supplied
manually to the task card. Input `evidence_hash` values may use an optional
`sha256:` prefix or uppercase hex, but fingerprinting canonicalizes them to
lowercase `sha256:<64-hex>`.

`decision_delta` may be a string, list, or object. Empty values and the markers
`NONE`, `NO_CHANGE`, `NO_DELTA`, and `UNCHANGED` are recognized as no delta.
An `ADVANCED` entry must contain a semantic delta. Search results expose
`has_decision_delta` and `is_no_delta` so callers do not need to reinterpret
free text.

Decision IDs are unique. Validation rejects duplicate IDs, and append checks
the existing ledger under the shared registry lock before writing one complete
JSONL line. Existing records are never rewritten or deleted.

Example entry:

```json
{
  "decision_id": "greyhound-floor-663-v1",
  "scope_fingerprint": "9e339d70e0a5590fd7db29faddbfa60a52920c57f77de9be62d994594f6a36ce",
  "task_id": "greyhound_historical_floor_review_v1",
  "run_id": "run-20260713T010000Z",
  "project_id": "greyhound_racing_collector",
  "claim_id": "historical_source_floor",
  "hypothesis_id": "thedogs_history_clears_floor",
  "program_track": "offline_development",
  "source_class": "thedogs_published_market_history",
  "dataset_version": "663-race-snapshot-20260709",
  "evidence_hash": "sha256:2222222222222222222222222222222222222222222222222222222222222222",
  "target_transition": "historical_sample_floor_cleared",
  "phase_before": "historical_floor_unproven",
  "phase_after": "historical_floor_cleared",
  "decision": "PASS",
  "outcome_status": "ADVANCED",
  "decision_delta": "The verified snapshot contains 663 eligible races.",
  "evidence_refs": ["reports/weekly/rolling_model_comparison.json"],
  "blocks": [],
  "does_not_block": ["prospective Sportsbet capture"],
  "validated_at": "2026-07-13T01:00:00Z",
  "invalidation_conditions": ["The recorded evidence hash is disproved."],
  "reopen_conditions": ["A new dataset version or evidence hash is supplied."]
}
```

## Commands

All commands accept `--repo-root` after the command, which is the portable
preflight integration form:

```bash
python3 scripts/agent_decision_ledger.py resolve-path --repo-root .
python3 scripts/agent_decision_ledger.py initialize --repo-root . --authorize-create-empty-ledger
python3 scripts/agent_decision_ledger.py validate --repo-root .
python3 scripts/agent_decision_ledger.py search --repo-root . --project-id greyhound_racing_collector --claim-id historical_source_floor
python3 scripts/agent_decision_ledger.py summarize --repo-root . --format json
```

Validate a proposed entry without touching the live registry:

```bash
python3 scripts/agent_decision_ledger.py validate --repo-root . --entry-file reports/agent_jobs/<job_id>/DECISION_ENTRY.json
```

Append only when the task card or owner explicitly permits registry mutation:

```bash
python3 scripts/agent_decision_ledger.py append --repo-root . --entry-file reports/agent_jobs/<job_id>/DECISION_ENTRY.json
```

An authorized pilot may initialize an absent ledger explicitly:

```bash
python3 scripts/agent_decision_ledger.py initialize --repo-root . --authorize-create-empty-ledger
```

Initialization takes the shared registry lock, creates only an absent empty
file, and is idempotent. It validates an existing ledger and never truncates
it. The authorization flag is mandatory so validation or search cannot create
registry state implicitly.

Tests and local fixtures may select an isolated file with `--ledger-path`.
Search also supports exact scope fields, `--text`, and `--no-delta-only`.
