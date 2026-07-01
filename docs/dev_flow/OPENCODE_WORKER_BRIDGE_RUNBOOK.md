# OpenCode Worker Bridge Runbook

Status: report-only audit. The bridge is repo-backed and probeable in this environment, but each worker result still needs task-specific validation.

Verified from commit `154888ecca6220ab598efcd140a2c2b62fca3da7`.

## What OpenCode Is Used For

OpenCode is used as a bounded worker scout for Tenn. It can gather evidence, compare files, inspect docs, and return a structured result. It must not become final authority for scope, correctness, readiness, owner decisions, PR readiness, or Runtime Functionality Proof.

Use it when the main Codex session benefits from parallel scouting, especially:

- read-only code or docs inventory;
- validation evidence collection;
- risk review before a change;
- narrow candidate implementation only when the task card explicitly permits bounded implementation.

## What `scripts/opencode_worker_bridge.py` Does

The bridge script provides these commands:

| Command | Purpose |
| --- | --- |
| `probe` | Checks whether OpenCode is installed, which agents/models are visible, and whether provider/model config is usable. |
| `run` | Creates a worker run directory, writes worker metadata, builds a restrictive OpenCode config, runs `opencode run`, and captures raw output. |
| `validate-result` | Validates a worker result JSON against required Tenn worker fields and decision-limit rules. |
| `summarize` | Produces a compact summary across worker result files. |
| `ledger-entry` | Produces a task-ledger entry shape for a worker run. |

The bridge is intentionally fail-closed. It rejects unsafe task references, unproven read-only enforcement, invalid worker results, and unsupported decision claims.

## Probe Result From This Audit

Command:

```bash
python3 scripts/opencode_worker_bridge.py probe
```

Result:

- exit status: 0;
- `available: true`;
- command: `/home/l4nd0/.opencode/bin/opencode`;
- version: `1.3.17`;
- visible agent summary: `build (primary)`;
- DeepSeek provider available: true;
- DeepSeek models visible included `deepseek/deepseek-chat`, `deepseek/deepseek-reasoner`, `deepseek/deepseek-v4-flash`, and `deepseek/deepseek-v4-pro`;
- JSON list attempts for agents/models failed, but plain text list commands worked.

This proves OpenCode is visible on this host. It does not prove any specific worker result is correct.

## What The `codex-worker-bridge` Skill Requires

Before using OpenCode workers:

1. Read `.agents/skills/codex-worker-bridge/SKILL.md`.
2. Work under a Tenn task card.
3. Keep worker scope inside task-card permissions.
4. Prefer `evidence_only` workers with `readonly` permissions.
5. Use the bridge script rather than ad hoc OpenCode commands.
6. Validate every worker result with `validate-result`.
7. Have Codex decide integration, risk, and next action.

## How To Run `probe`

```bash
python3 scripts/opencode_worker_bridge.py probe
```

If it fails, record the exact output in the report and classify OpenCode status as `PARTIAL` or `DATA_MISSING`. Do not fall back to unconstrained OpenCode usage.

## How To Create A Worker Task

Use the template:

```text
docs/dev_flow/templates/WORKER_TASK.md
```

Minimum fields to include in the task:

- worker id;
- parent job id;
- task tier;
- decision limit;
- permission profile;
- allowed files or directories;
- denied files or directories;
- exact questions to answer;
- required evidence paths;
- stop condition.

For a read-only scout, use:

```text
decision_limit: evidence_only
permission_profile: readonly
```

## How To Run A Read-Only Worker

The exact CLI flags may vary by bridge version. Use the bridge help before running:

```bash
python3 scripts/opencode_worker_bridge.py run --help
```

The safe pattern is:

```bash
python3 scripts/opencode_worker_bridge.py run \
  --task <path-to-worker-task.md> \
  --worker-id <worker-id> \
  --task-tier scout \
  --decision-limit evidence_only \
  --permission-profile readonly
```

If the bridge rejects the run, treat that as the correct outcome until the task card, worker task, or environment is fixed.

## How To Validate Worker Results

After a worker returns a result JSON:

```bash
python3 scripts/opencode_worker_bridge.py validate-result <path-to-result.json>
```

Required result fields include:

- `worker_id`;
- `task_tier`;
- `model`;
- `decision_limit`;
- `summary`;
- `findings`;
- `evidence_paths`;
- `confidence`;
- `risks`;
- `recommended_next_action`;
- `stop_condition_hit`.

For `stop_condition_hit`, valid values are exactly:

```text
yes
no
DATA_MISSING
```

The validator rejects final-authority claims in evidence-only mode, mismatched decision limits, invalid stop-condition values, and missing permission metadata.
It tolerates one surrounding markdown fence around the whole worker result, but
workers should still return the bare `WORKER_RESULT.md` body.

## How To Summarize Worker Outputs

Use:

```bash
python3 scripts/opencode_worker_bridge.py summarize <worker-result-dir>
```

The summary is an input to Codex judgment. It is not a readiness decision.

## Permission Model

The bridge writes restrictive OpenCode configuration through `OPENCODE_CONFIG_CONTENT` and verifies it with `opencode debug config --pure`. The safety model includes:

- read-only permission profiles for evidence workers;
- denied secret and raw-database path references;
- no automatic trust in `OPENCODE_SERVER_URL` attach mode without remote read-only proof;
- narrow allowed command behavior;
- structured result validation before using outputs.

## Fail-Closed Behavior

Expected fail-closed cases include:

- OpenCode binary missing;
- provider or model unavailable;
- read-only enforcement cannot be proven;
- remote attach mode active without proof of remote permissions;
- worker task references denied paths;
- worker result JSON missing required fields;
- worker claims final authority under `evidence_only`;
- worker uses invalid `stop_condition_hit`;
- worker result lacks permission metadata.

If any of these occurs, record `DATA_MISSING` or `PARTIAL` and stop the worker path.

## Expected Agents And Models

This host currently shows `build (primary)` as the visible agent summary and DeepSeek models as available. The bridge and skill are compatible with worker roles such as evidence scout, docs scout, validation scout, and bounded implementation worker, but those roles are task contracts, not proof that host OpenCode agents are preconfigured.

Use the model that the task card permits. If no model is specified, prefer the default model surfaced by the bridge and record it in worker metadata.

## What Codex Must Decide

Codex, not OpenCode, decides:

- whether the task card permits the work;
- whether evidence is sufficient;
- whether a finding is actionable;
- whether to mutate files;
- whether validation passed;
- whether Runtime Functionality Proof is satisfied;
- whether to open a PR;
- whether to stop with `WAITING_ON_USER`.

## Debugging Missing OpenCode, Provider, Or Model Config

Use this sequence:

```bash
command -v opencode
python3 scripts/opencode_worker_bridge.py probe
opencode agent list
opencode models
opencode debug config --pure
```

Then check:

- whether `OPENCODE_SERVER_URL` is set;
- whether required providers are logged in;
- whether the desired model appears in `probe`;
- whether the task card permits worker use;
- whether the worker task references only allowed paths.

Do not bypass the bridge because `probe` failed.

## Evidence Needed Before Using A Worker Result

For each worker result, preserve:

- worker task file;
- worker metadata file;
- raw OpenCode output;
- structured result JSON;
- `validate-result` output;
- Codex summary of what was accepted, rejected, or left undecided.

Only after that can a worker result support a Tenn report, review board, or implementation decision.
