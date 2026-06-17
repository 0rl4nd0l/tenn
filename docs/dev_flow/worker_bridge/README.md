# OpenCode Worker Bridge

This bridge lets Codex delegate bounded read-only scout tasks to OpenCode,
including DeepSeek-backed OpenCode models, without making workers owners of the
repo diff or final decision.

Tenn is the project under development. Codex, OpenCode, and DeepSeek are
development tools. Project-specific policy remains in `AGENTS.md`, task cards,
and local guard scripts.

## Commands

Probe local OpenCode:

```bash
python3 scripts/opencode_worker_bridge.py probe
```

Run a read-only worker:

```bash
python3 scripts/opencode_worker_bridge.py run \
  --job-dir reports/agent_jobs/<job_id>/workers \
  --worker-id evidence-scout-1 \
  --agent evidence-scout \
  --model deepseek/deepseek-chat \
  --task-file reports/agent_jobs/<job_id>/workers/evidence-scout-1-task.md \
  --workdir "$PWD" \
  --decision-limit evidence_only \
  --permission-profile readonly \
  --task-tier small \
  --timeout-seconds 600
```

Validate, summarize, and emit ledger-compatible JSON:

```bash
python3 scripts/opencode_worker_bridge.py validate-result \
  reports/agent_jobs/<job_id>/workers/evidence-scout-1/WORKER_RESULT.md

python3 scripts/opencode_worker_bridge.py summarize \
  --job-dir reports/agent_jobs/<job_id>/workers

python3 scripts/opencode_worker_bridge.py ledger-entry \
  --job-dir reports/agent_jobs/<job_id>/workers \
  --worker-id evidence-scout-1
```

## Result Contract

`WORKER_RESULT.md` must include:

- `worker_id`
- `task_tier`
- `model`
- `decision_limit`
- `summary`
- `findings`
- `evidence_paths`
- `confidence`
- `risks`
- `recommended_next_action`

For `decision_limit=evidence_only`, result validation rejects final-authority
claims such as merge approval or no-review-needed conclusions.

Evidence-only runs also require verified permission-enforcement metadata in
`WORKER_META.json`.

## Safety

The bridge refuses obvious secret and raw-data paths before invoking OpenCode.
For `evidence_only`, it injects a restrictive OpenCode config with
`OPENCODE_CONFIG_CONTENT`, verifies the resolved config with
`opencode debug config`, and fails closed if enforcement cannot be proven. The
readonly profile denies edit/write/patch, external-directory access, subagents,
web tools, and shell commands by default. Only minimal safe git inspection
commands are allowed through bash.

The bridge also avoids dangerous permission bypass flags when constructing
`opencode run`.

Workers are still tool-assisted model processes, not a security sandbox. Keep
tasks small, file-scoped, and non-sensitive. Codex must review worker output
before applying any change.

## Worker Agents

Recommended first agents:

- `evidence-scout`
- `docs-scout`
- `validation-scout`

This PR does not create host-global OpenCode agents. If host agent creation is
approved later, use:

```bash
opencode agent create evidence-scout
opencode agent create docs-scout
opencode agent create validation-scout
```

## Model Routing

- `small`: DeepSeek/OpenCode evidence, docs, logs, and report work.
- `medium`: DeepSeek/OpenCode may propose bounded docs/template patches, but
  Codex applies and reviews them.
- `large`: Codex high reasoning; DeepSeek evidence only.
- `critical`: Codex high reasoning plus review-board; DeepSeek strategy-bid
  only.
