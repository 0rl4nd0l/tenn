# Sloppy CI Workflows

This runbook documents the repository's Sloppy scan/fix control plane. It is
derived from `.github/workflows/sloppy-scan.yml`,
`.github/workflows/sloppy-fix.yml`, `.sloppy.yml`, and
`scripts/test_sloppy_fix_workflow.py`.

Task cards under `docs/agent_tasks/` record the evaluation work that landed
this behavior. Use this page as the durable operator contract.

## What runs when

| Workflow | Trigger | Writes to repo? | Primary purpose |
| --- | --- | --- | --- |
| Sloppy Scan | `pull_request`, `workflow_dispatch` | No | Find issues and upload the scan JSON artifact. |
| Sloppy Fix | `workflow_dispatch`, successful same-repo `workflow_run` from Sloppy Scan | Yes, when Claude auth is available | Attempt fixes from a manual run or from scan findings. |

`Sloppy Fix` is intentionally unscheduled. Do not add a cron trigger without
explicit approval because it is write-capable automation.

Fork pull requests do not start automatic fix runs: the `workflow_run` job
requires `head_repository.full_name == github.repository`. Manual
`workflow_dispatch` still works from this repository.

## Scan workflow contract

`Sloppy Scan` runs `braedonsaunders/sloppy@main` in `scan` mode with:

- `scan-scope: auto`
- default `scan-provider: github-models`
- optional manual `scan_provider=agent`
- `agent: codex`
- `model: gpt-5.2-codex`
- `output-file: /tmp/sloppy-scan-issues.json`

The job requests `contents: read`, `pull-requests: write`, and `models: read`
(needed for the GitHub Models scan provider). It always attempts to upload the
output as artifact `sloppy-scan-issues` and uses `if-no-files-found: error`.
Automatic fix runs depend on that artifact containing an `issues` array whose
found entries have `status: "found"`.

When the manual `agent` scan provider is selected, the workflow requires
`OPENAI_API_KEY`, normalizes newlines out of the secret, performs an OpenAI auth
preflight, and installs a Codex CLI compatibility shim before invoking Sloppy.

## Fix workflow contract

Automatic Sloppy Fix runs only after a successful same-repo Sloppy Scan:

```text
workflow_run.conclusion == success
workflow_run.head_repository.full_name == github.repository
```

For these automatic runs, the workflow checks out the scan run's `head_sha`,
downloads the `sloppy-scan-issues` artifact, counts findings with
`status: "found"`, and passes the artifact path back to Sloppy Fix.

Manual `workflow_dispatch` runs do not use a scan artifact. They invoke Sloppy
Fix directly with the temporary output path `/tmp/sloppy-fix-issues.json`.
The fail-closed gate and PR comment job apply only to automatic `workflow_run`
invocations, not to manual dispatch.

The fix step uses `braedonsaunders/sloppy@main` in `fix` mode with:

- `agent: claude`
- `model: claude-sonnet-4-5-20250929`
- `output-file: ${{ steps.sloppy_issues.outputs.path }}`
- `custom-prompt-file: /dev/null`

Claude auth is enabled when either `ANTHROPIC_API_KEY` or
`CLAUDE_CODE_OAUTH_TOKEN` is present. The job sets
`FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` and requests `actions: read`,
`contents: write`, and `pull-requests: write`.

## Outcomes and operator signals

| Condition | Result | Notes |
| --- | --- | --- |
| No Claude credentials | Skips fix | The workflow emits a skip message instead of attempting writes. |
| Automatic run, missing `sloppy-scan-issues` artifact | Skips fix | The artifact download is best-effort, then the selector records `missing_artifact`. |
| Automatic run, scan reports zero found issues | Skips fix | No write-capable fix attempt is made. |
| Automatic run, scan reports found issues and Sloppy Fix reports an invalid or zero `issues-fixed` count | Fails closed | This is intentional so seeded findings do not silently pass as fixed. |
| Automatic run, scan reports found issues and Sloppy Fix reports one or more fixes | Succeeds | The gate only checks that the fixed count is a positive integer. |
| Automatic run associated with a PR | Best-effort PR comment | Comment text distinguishes skip, success, and fail-closed outcomes. |

The comment job uses `always()` so it still posts after a fail-closed fix job,
as long as the triggering scan succeeded and the run is same-repo. Failure to
create the PR comment is reported as a workflow warning and does not mask the
fix job result.

## Local verification

Use the focused unittest when changing `.github/workflows/sloppy-fix.yml`:

```bash
python3 -m unittest scripts/test_sloppy_fix_workflow.py
```

The test suite verifies that:

- `Sloppy Fix` remains unscheduled.
- Claude provider, model, and auth environment are preserved.
- seeded/fixed issue counts flow into the PR comment job.
- automatic seeded issue runs fail when the fix reports zero fixes.

For YAML-only checks, parse both workflow files before pushing changes:

```bash
python3 - <<'PY'
from pathlib import Path
import yaml

class GitHubActionsYamlLoader(yaml.SafeLoader):
    pass

GitHubActionsYamlLoader.yaml_implicit_resolvers = {
    key: [
        (tag, regexp)
        for tag, regexp in resolvers
        if tag != "tag:yaml.org,2002:bool"
    ]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}

for path in [
    Path(".github/workflows/sloppy-scan.yml"),
    Path(".github/workflows/sloppy-fix.yml"),
]:
    yaml.load(path.read_text(encoding="utf-8"), Loader=GitHubActionsYamlLoader)
    print(f"ok: {path}")
PY
```

## Configuration caveat

`.sloppy.yml` is a repository-level Sloppy configuration reference, but the
GitHub workflow files are the source of truth for this repository's trigger,
provider, model, artifact, and credential behavior. Treat generic values in
`.sloppy.yml` such as `test-command: "npm run test:ci"`, `framework: next.js`,
and `runtime: node-20` as Sloppy reference defaults, not TENN Python runtime
instructions.
