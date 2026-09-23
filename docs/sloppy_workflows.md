# Sloppy Scan and Fix

Operator notes for the GitHub Actions workflows in this repo. Trigger, credential, artifact, and fail-closed behavior come from the workflow YAML. `.sloppy.yml` is a checked-in Sloppy reference and still contains generic Node/Next fields (`test-command: "npm run test:ci"`, `framework: next.js`, `runtime: node-20`). Do not treat those fields as TENN's Python test or runtime contract.

Source of truth:

- `.github/workflows/sloppy-scan.yml`
- `.github/workflows/sloppy-fix.yml`
- `scripts/test_sloppy_fix_workflow.py`

There is no `schedule` / cron trigger on either workflow.

## Scan

| | |
|---|---|
| Workflow | `Sloppy Scan` (`.github/workflows/sloppy-scan.yml`) |
| Triggers | every `pull_request`; manual `workflow_dispatch` |
| Default provider | `github-models` |
| Manual provider choice | `github-models` or `agent` |
| Agent model | `CODEX_MODEL` default `gpt-5.2-codex` |
| Issue file | `/tmp/sloppy-scan-issues.json` |
| Artifact | `sloppy-scan-issues` (`if-no-files-found: error`) |

`pull_request` runs always use `github-models`. The `agent` provider is only selected on manual dispatch.

`agent` mode requires a non-empty `OPENAI_API_KEY` secret (whitespace stripped, length at least 20). The job then calls OpenAI `GET /v1/models` and a short `codex exec` preflight. Either check failing stops the scan before Sloppy runs.

Permissions on the scan job are `contents: read`, `pull-requests: write`, and `models: read`.

## Fix

| | |
|---|---|
| Workflow | `Sloppy Fix` (`.github/workflows/sloppy-fix.yml`) |
| Triggers | manual `workflow_dispatch`; automatic `workflow_run` after `Sloppy Scan` completes |
| Fix agent | Claude (`claude-sonnet-4-5-20250929`) via `braedonsaunders/sloppy@main` |
| Credentials | `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN` |
| Permissions | fix job: `actions: read`, `contents: write`, `pull-requests: write` |

Automatic runs start only when the scan conclusion is `success` and `workflow_run.head_repository.full_name` equals this repository. Fork scan runs do not start the fix job.

Checkout uses the scan head repository and SHA on `workflow_run`, and `github.ref_name` on manual dispatch.

### Automatic issue handoff

On `workflow_run`, the fix job downloads artifact `sloppy-scan-issues` from the triggering scan (`continue-on-error: true`) and reads `/tmp/sloppy-scan/sloppy-scan-issues.json`.

| Scan handoff | `found_count` | Fix step |
|---|---|---|
| Artifact missing or empty | `missing_artifact` | skipped |
| JSON `issues` array has no objects with `status == "found"` | `0` | skipped |
| One or more `status == "found"` issues | integer count | Claude fix runs when credentials exist |
| JSON has no `issues` array | job fails in the select step | no fix |

Manual dispatch does not download the scan artifact. It sets `found_count=manual` and points Sloppy at `/tmp/sloppy-fix-issues.json`.

Missing Claude credentials skip the fix step on both triggers. The skip is a successful step, not a failed job.

### Fail closed

The fail-closed step runs only on automatic `workflow_run` when Claude credentials exist and `found_count` is neither `0` nor `missing_artifact`.

It reads Sloppy's `issues-fixed` output:

- missing or non-numeric values fail the job
- `0` fails the job
- a positive integer is success

Manual dispatch does not run this check.

### PR comment

The comment job runs only for automatic same-repo scans whose conclusion was `success`. Its `if` includes `always()`, so it still comments when the fix job fails closed.

It comments on `workflow_run.pull_requests[0]` when that pull request exists. Comment text covers skipped (no credentials, missing artifact, or zero findings), success with the fixed count, and fail-closed with both seeded and fixed counts. Comment API errors are warnings; they do not fail the job.

Manual dispatch does not comment.

## Local check

```bash
python3 -m unittest scripts/test_sloppy_fix_workflow.py
```

The tests load `.github/workflows/sloppy-fix.yml` with a YAML loader that keeps GitHub Actions booleans as strings, then execute the fail-closed shell step with sample counts.
