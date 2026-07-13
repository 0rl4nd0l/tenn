# Semantic Anti-Loop Control V2

## Purpose

V2 prevents semantically duplicate agent work without conflating task state,
decision state, offline experimentation, and prospective promotion. It applies
only when a task card declares `control_contract_version: 2`. Legacy cards
remain V1-compatible and receive a migration warning.

## Run Contract

In addition to the existing task-card fields, V2 requires:

- `project_id`, `claim_id`, `proof_question`, and `hypothesis_id`
- `program_track`: `offline_development` or `prospective_readiness`
- `entry_state`, `target_transition`, and `exit_predicate`
- `source_class`, `dataset_version`, and a SHA-256 `evidence_hash`
- explicit `capabilities`
- `resume_only_if`

Capabilities are limited to `READ`, `REPORT_WRITE`, `RESEARCH_FIT`,
`DATASET_MATERIALIZE`, `CODE_EDIT`, `MODEL_PERSIST`, `DB_COPY_WRITE`,
`CANONICAL_DB_WRITE`, `RUNTIME_CHANGE`, and `PUBLISH`.

The validator rejects a supplied `scope_fingerprint`. It strips surrounding
whitespace from these fields, canonicalizes `evidence_hash` to a lowercase
`sha256:<64-hex>` value, encodes the values in fixed order as a compact JSON
array, and hashes it with SHA-256:

```text
project_id
claim_id
hypothesis_id
source_class
dataset_version
evidence_hash
target_transition
```

## Decision Ledger

Decision state is append-only in `<registry_root>/decision-ledger.jsonl`, beside
the task ledger. Resolve `<registry_root>` through the same environment,
Git-config, Git-common-directory, and repo-local fallback order as the active
job registry. Linked worktrees therefore share one decision history.

Use:

```bash
python3 scripts/agent_decision_ledger.py resolve-path --repo-root <repo>
python3 scripts/agent_decision_ledger.py initialize --repo-root <repo> --authorize-create-empty-ledger
python3 scripts/agent_decision_ledger.py validate --repo-root <repo>
python3 scripts/agent_decision_ledger.py search --repo-root <repo> --project-id <id> --claim-id <id>
python3 scripts/agent_decision_ledger.py append --repo-root <repo> --entry-file <entry.json>
python3 scripts/agent_decision_ledger.py summarize --repo-root <repo>
```

Each entry records the semantic scope, task/run identity, phase transition,
decision (`PASS`, `FAIL`, `DATA_MISSING`, `CONFLICT`, or `PARKED`), outcome
status, decision delta, evidence, transition-specific `blocks` and
`does_not_block`, validation time, invalidation conditions, and exact reopen
conditions. Completing a task never implies that its proof question changed.

`initialize` is an authorization-explicit bootstrap action. It takes the
shared registry lock, creates only an absent empty ledger, validates an
existing ledger, and never truncates data. Validation, search, and portable
preflight remain read-only and never initialize registry state.

## Portable Preflight

For V2, pass the task card:

```bash
python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py \
  preflight --repo-root <repo> --topic "<topic>" --task-card <card> --json
```

The semantic result is:

- `REUSED_COMPLETE` for an exact resolved fingerprint.
- `ACTIVE_DUPLICATE` for another non-stale active job with the fingerprint.
- `LOOP_GUARD_STOP` before a third same-claim, unchanged-evidence no-delta
  continuation.
- `DATA_MISSING` or `EVIDENCE_CONFLICT` when the requested transition is still
  blocked.
- `ALLOW_CHANGED_EVIDENCE`, `ALLOW_NEW_HYPOTHESIS`, or another `ALLOW_*`
  result for a materially changed scope.

Missing V2 decision-ledger evidence is `DATA_MISSING` and blocks substantive
work. A prospective decision blocks only transitions named in its `blocks`;
it cannot block an offline transition without an explicit dependency.

Portable repo-local hooks may invoke only the installed guard surface:

```bash
python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py \
  hook --repo-root <repo> --platform codex --event Stop
```

The dispatcher selects a V2-capable Tenn control plane and runs its hook
against the target repo; the target does not vendor Tenn helper scripts.

## Closeout

Every V2 run writes `RUN_OUTCOME.json` under its task-card `output_dir` with:

- `status`, computed `scope_fingerprint`, `state_before`, and `state_after`
- `decision_delta`, `reused_claims`, and `changed_claims`
- `new_evidence`, `produced_artifacts`, and `used_capabilities`
- `resume_only_if`, `new_goal_permitted`, and optional `blocked_by`

Allowed statuses are `ADVANCED`, `REUSED_COMPLETE`, `ACTIVE_DUPLICATE`,
`WAITING_ON_AUTHORIZATION`, `DATA_MISSING`, `EVIDENCE_CONFLICT`,
`BLOCKED_NO_NEW_INPUT`, and `LOOP_GUARD_STOP`.

`ADVANCED` requires a real decision delta plus a state or claim change; created
files alone are not progress. Used capabilities must be declared by the card.
All other statuses are terminal/no-progress: they require an exact
`resume_only_if`, set `new_goal_permitted=false`, and must not create or list
`NEXT_GOAL.md`. An advanced goal is permitted only for a materially different
target transition.

V2 review boards use `tenn_review_board_decision_v2` and follow the same
conditional-goal rule. V1 board decisions retain their existing concrete
`next_goal` contract.
