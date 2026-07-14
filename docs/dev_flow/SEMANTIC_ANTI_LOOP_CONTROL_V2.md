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
python3 scripts/agent_decision_ledger.py summarize --repo-root <repo>
```

A claimed run does not call the ledger's standalone `append` command. It writes
exactly one `<output_dir>/DECISION_ENTRY.json` candidate; normal registry
`release` validates `RUN_OUTCOME.json` and that candidate, appends it while
holding the shared registry lock, then records the release receipt. Standalone
append is reserved for an explicitly authorized, unclaimed seed and refuses a
seed that matches any active claim:

```bash
python3 scripts/agent_decision_ledger.py append --repo-root <repo> \
  --entry-file <seed.json> --authorize-unclaimed-seed
```

Each entry records the semantic scope, task/run identity, phase transition,
decision (`PASS`, `FAIL`, `DATA_MISSING`, `CONFLICT`, or `PARKED`), outcome
status, decision delta, evidence, transition-specific `blocks` and
`does_not_block`, validation time, invalidation conditions, and exact reopen
conditions. Completing a task never implies that its proof question changed.

Live append rejects a semantic replay even when a reclaimed run changes its
task ID, run ID, outcome status, timestamp, or report/evidence references.
Those fields are provenance only and do not create a decision delta. A
material decision change within the same fingerprint and program track must set
`supersedes_decision_id` to the current chain head, carry a real decision
delta, and continue from that head's `phase_after`. This keeps legitimate
`PASS` to `CONFLICT` evolution possible while preventing duplicate closeout
entries. Historical rows without explicit lineage remain valid.

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
Within the same program track, evidence hash, and hypothesis, the two-outcome
no-delta count is evaluated before `does_not_block`; that annotation cannot
bypass `LOOP_GUARD_STOP` for a third continuation.

Portable repo-local hooks may invoke only the installed guard surface:

```bash
python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py \
  hook --repo-root <repo> --platform codex --event Stop
```

The dispatcher selects a V2-capable Tenn control plane and runs its hook
against the target repo; the target does not vendor Tenn helper scripts.

Repositories that require V2 for every non-trivial run set
`TENN_V2_REQUIRED=1` on portable `BeforeTool` and terminal hook commands and
retain the matching repository instruction. The hook mechanically gates
mutations and unclassified tools; it cannot distinguish a short read probe from
an arbitrarily long read-only diagnosis, so operators must create the card once
the diagnosis becomes non-trivial. In that mode, a narrow single-file
`docs/agent_tasks/*.md` bootstrap, validation,
explicit live-ledger initialization, the exact registry claim, and conservative
read-only shell probes are admitted before a claim. The claim itself validates
and classifies the shared decision ledger while holding the registry lock.
Missing/invalid ledger state, exact
resolved scope, active duplicate scope, a transition-specific decision block,
or the third unchanged no-delta continuation stops before work is claimed.

With an active V2 claim, source/report tool paths must exactly match
`allowed_files`. Shell commands use a conservative classifier: known operations
request their declared capability and unknown, compound, redirected, spoofed,
destructive Git, recursive, or otherwise unbounded filesystem commands fail
closed. Repo-local Python entrypoints are trusted code, not an operating-system
sandbox: diagnostic/research/report verbs classify their declared intent,
explicit output-bearing arguments are path- and capability-checked, and read
inputs do not imply persistence. Pytest is admitted only with bytecode writes
and plugin autoload disabled plus its cache provider removed; `uv run` must also
be frozen and no-sync. Those controls prevent incidental tool writes but cannot
constrain side effects authored inside a test, `conftest.py`, or repo script.
Admission classifies visible tool arguments and trusts reviewed repo-local
Python/test bodies; it is not OS syscall confinement, so hostile or nested side
effects require a separate sandbox. Do not execute untrusted repo code under
this contract.

V2 Git publication is equally narrow. Commit admission requires exact staged
paths plus `core.hooksPath=/dev/null`, `core.fsmonitor=false`, `--no-verify`,
`--no-gpg-sign`, and an explicit message; push requires `--no-verify`, a
configured named remote, and the explicit current `HEAD`.
`git add -f` is admitted only for exact task-card paths so ignored report
artifacts can be made durable without broad staging.
Run required validation explicitly before publication because these admitted
forms suppress repository hooks.

The claim records `claim_head_sha`; release walks every committed path
in `claim_head_sha..HEAD`, including paths changed and later reverted, and
rejects any path outside the exact `allowed_files`. A clean final worktree or
commit therefore cannot bypass `check-diff`. A no-card terminal event confirms
only that no active target-worktree
V2 claim remains and relies on the configured pre-tool coverage; it does not
independently prove what earlier read-only work occurred. When an unclaimed V2
card remains explicitly selected, the
terminal hook admits only a report-free semantic stop (`REUSED_COMPLETE`,
`ACTIVE_DUPLICATE`, `LOOP_GUARD_STOP`, or a recorded evidence/decision block)
or a validated successful-release receipt. Repositories that do not opt in
preserve legacy V1 terminal warning-compatible behavior. A selected V1 card's
`BeforeTool` contract or diff violation may still block the proposed tool.

## Closeout

Every claimed V2 run admitted to substantive work writes `RUN_OUTCOME.json`
and exactly one `DECISION_ENTRY.json` candidate under its task-card
`output_dir`. The outcome contains:

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

Successful V2 registry release is also a closeout and publication gate. It
leaves the active claim intact unless the recorded task card still matches,
`RUN_OUTCOME.json` passes, and exactly one `DECISION_ENTRY.json` candidate
matches the current run, fingerprint, transition, status, and decision delta.
While holding the registry lock, release validates the live ledger, appends the
candidate (or recognizes an identical retry), writes a receipt, and only then
removes the active record. Immediately before append, it reclassifies the scope
against the current live ledger. Concurrent resolved, missing-data, conflict,
or explicit blocking decisions always stop release; a material candidate may
override only `LOOP_GUARD_STOP`. An identical latest-head candidate is reused
solely for an idempotent retry after a receipt-write failure. Release rejects a
third unchanged no-delta outcome and keeps the claim active. An explicitly selected terminal hook can
recheck the receipt after release. V1 release remains backward compatible.

`release --abandon-reason` is administrative recovery only for a stale/corrupt
claim or task-card/semantic-identity drift; it is never the closeout path for a
normal terminal/no-progress result. A valid `DATA_MISSING`,
`BLOCKED_NO_NEW_INPUT`, or other terminal run still writes its outcome and
decision candidate and uses normal release so no-delta history counts toward
the two-run loop guard. Pre-claim semantic stops create no `RUN_OUTCOME.json`,
`DECISION_ENTRY.json`, report, or new continuation goal.
