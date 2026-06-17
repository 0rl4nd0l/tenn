---
name: codex-worker-bridge
description: Delegate bounded read-only scout tasks from Codex to OpenCode workers, usually DeepSeek-backed, while keeping Codex as the final decision-maker.
---

# Codex Worker Bridge

Use this skill when Codex needs a small or medium read-only scout to gather
evidence, inspect docs, summarize logs, or run bounded validation through
OpenCode.

This is generic development tooling. Project-specific policy should come from
the current repo constitution, task card, and guard scripts.

## Boundaries

- Default to `decision_limit=evidence_only`.
- Workers may read, grep, glob, and summarize.
- Workers may write only their own bridge artifacts under the worker job
  directory.
- Workers must not edit repo source, docs, templates, config, runtime files, or
  host-global files.
- Workers must not run git mutation commands.
- Workers must not inspect secrets, credentials, API keys, `.env` files,
  private tokens, raw DB dumps, production data, or runtime state.
- Workers must not make final decisions on critical work.
- Codex remains responsible for applying, reviewing, validating, committing,
  pushing, and opening PRs.

## Probe

Check local OpenCode availability before delegation:

```bash
python3 scripts/opencode_worker_bridge.py probe
```

The probe emits JSON with command availability, version, any locally listable
agents/models, and whether a DeepSeek provider/model appears available.

## Run A Worker

Create a narrow task file first. Keep it file-scoped and evidence-only.

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

The bridge writes:

- `WORKER_TASK.md`
- `WORKER_RESULT.md`
- `WORKER_META.json`
- `raw_output.txt`

OpenCode stdout becomes the result artifact. The bridge records failure in
metadata if OpenCode is missing, times out, exits nonzero, or emits an invalid
result.

For `evidence_only`, the bridge fails closed unless it can inject and verify a
restrictive OpenCode permission config through `OPENCODE_CONFIG_CONTENT`.
`WORKER_META.json` records the profile, method, config hash, and sanitized
verification summary.

## Validate And Summarize

```bash
python3 scripts/opencode_worker_bridge.py validate-result \
  reports/agent_jobs/<job_id>/workers/evidence-scout-1/WORKER_RESULT.md

python3 scripts/opencode_worker_bridge.py summarize \
  --job-dir reports/agent_jobs/<job_id>/workers

python3 scripts/opencode_worker_bridge.py ledger-entry \
  --job-dir reports/agent_jobs/<job_id>/workers \
  --worker-id evidence-scout-1
```

## Suggested Worker Agents

Do not create host-global agents unless the current task explicitly permits it.
If host agent creation is approved, these are the recommended starting points:

```bash
opencode agent create evidence-scout
opencode agent create docs-scout
opencode agent create validation-scout
```

Recommended intent:

- `evidence-scout`: find and summarize file-backed evidence.
- `docs-scout`: inspect docs/templates/runbooks and report drift.
- `validation-scout`: inspect validation commands and summarize results.

## Model Routing

- `small`: DeepSeek/OpenCode evidence, docs, logs, and report work.
- `medium`: DeepSeek/OpenCode may propose bounded docs/template patches, but
  Codex applies and reviews them.
- `large`: Codex high reasoning; DeepSeek evidence only.
- `critical`: Codex high reasoning plus review-board; DeepSeek strategy-bid
  only.
