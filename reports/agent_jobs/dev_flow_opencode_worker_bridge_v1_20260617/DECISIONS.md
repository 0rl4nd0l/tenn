# Decisions

## Continue Without PR #367

PR #367 is open and contains task-ledger runtime work. The bridge does not
depend on that PR because the requested `ledger-entry` subcommand can emit
compatible JSON without importing or invoking `scripts/agent_task_ledger.py`.

Decision: continue on canonical base.

## Avoid PR #368 Template Collisions

PR #368 is open and edits docs-freshness/model-routing templates, including
`MODEL_ROUTING.md` and `WORKER_RESULT.md`.

Decision: do not edit those two files in this branch. Enforce the result
contract in the bridge and tests, and document model routing in the bridge
README/report.

## No Host-Global OpenCode Agents

Creating OpenCode agents would mutate host/global tool configuration outside
the approved file scope.

Decision: document exact `opencode agent create` commands only.

## Read-Only Worker Boundary

The bridge captures OpenCode stdout and writes artifacts itself. Workers are
prompted to read and report only; Codex owns file writes, validation, commits,
pushes, and PRs.

Decision: no write-worker implementation in this slice.

## PR #370 Review Follow-Up

Codex Review found that prompt-only read-only behavior was insufficient because
OpenCode defaults can permit edits or shell commands. The follow-up patch now
requires `--permission-profile readonly` for `decision_limit=evidence_only`,
injects restrictive permissions through `OPENCODE_CONFIG_CONTENT`, verifies the
resolved config with `opencode debug config`, and records the enforcement method
in `WORKER_META.json`.
