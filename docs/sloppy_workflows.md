# Sloppy Scan and Fix Workflows

This runbook documents the repository's Sloppy quality-control automation. The
source of truth is the GitHub Actions YAML in `.github/workflows/`; use this page
as the operator map for triggers, handoffs, skip conditions, and local checks.

## Workflow map

| Workflow | File | Trigger | Provider shape | Output contract |
| --- | --- | --- | --- | --- |
| Sloppy Scan | `.github/workflows/sloppy-scan.yml` | `pull_request` and manual `workflow_dispatch` | default `github-models`; manual `agent` option uses Codex with `CODEX_MODEL=gpt-5.2-codex` | uploads required artifact `sloppy-scan-issues` from `/tmp/sloppy-scan-issues.json` |
| Sloppy Fix | `.github/workflows/sloppy-fix.yml` | manual `workflow_dispatch` and completed `Sloppy Scan` `workflow_run` | Claude fix mode via `braedonsaunders/sloppy@main`, `agent: claude`, `model: claude-sonnet-4-5-20250929` | consumes the selected issues JSON path as Sloppy `output-file` |

Neither workflow is scheduled. Do not add `schedule` or `cron` triggers without
explicit project approval.

## Scan behavior

Sloppy Scan runs on PRs and can be manually dispatched with one of two providers:

- `github-models` (default): uses the GitHub Models path exposed by the Sloppy
  action.
- `agent`: normalizes `OPENAI_API_KEY`, performs a Codex preflight, then runs the
  Sloppy scan through Codex.

The scan action writes issues to `/tmp/sloppy-scan-issues.json`; the upload step
publishes that file as artifact `sloppy-scan-issues` and fails if the file is
missing. Automatic Sloppy Fix depends on this artifact when the scan completes.

## Automatic fix handoff

For `workflow_run` events, Sloppy Fix only proceeds for successful Sloppy Scan
runs from the same repository:

```text
github.event.workflow_run.conclusion == 'success'
github.event.workflow_run.head_repository.full_name == github.repository
```

The fix job checks out the triggering scan's repository and SHA, then attempts to
download artifact `sloppy-scan-issues` from the triggering run ID. The selector
step expects `/tmp/sloppy-scan/sloppy-scan-issues.json` to contain an `issues`
array and counts entries where `status == "found"`.

Automatic outcomes:

| Condition | Result |
| --- | --- |
| Missing or empty scan artifact | skip Sloppy Fix successfully, with `found_count=missing_artifact` |
| Malformed artifact or missing `issues` array | hard workflow error before fix mode |
| Valid artifact with zero `found` issues | skip Sloppy Fix successfully |
| Valid artifact with one or more `found` issues | run Sloppy Fix in Claude mode against the downloaded JSON |
| Positive seeded issue count but invalid or zero `issues-fixed` output | fail closed |
| Positive seeded issue count and positive numeric `issues-fixed` output | allow the fix job to pass |

The fail-closed guard checks that Sloppy Fix fixed at least one seeded finding; it
does not assert that every seeded finding was fixed.

## Manual fix dispatch

Manual `workflow_dispatch` keeps the fallback output path
`/tmp/sloppy-fix-issues.json` and does not require a downloaded scan artifact.
Claude credentials are still required through either `ANTHROPIC_API_KEY` or
`CLAUDE_CODE_OAUTH_TOKEN`; if neither secret is present, the workflow skips fix
mode instead of running unauthenticated.

## PR comment behavior

For same-repository automatic runs, the `comment` job is best-effort:

- It reports whether Sloppy Fix skipped because credentials, artifacts, or found
  issues were missing.
- It reports successful automatic fixes with the `issues-fixed` count.
- It reports fail-closed automatic fixes when seeded findings existed but the fix
  result did not include a positive fixed count.
- Comment creation failures are warnings and should not mask the fix job result.

## Local validation

Run the focused workflow tests after editing `.github/workflows/sloppy-fix.yml`:

```bash
python3 -m unittest scripts/test_sloppy_fix_workflow.py
```

Useful source checks:

```bash
rg -n "workflow_dispatch|workflow_run|schedule:|cron:" .github/workflows/sloppy-fix.yml
rg -n "output-file|sloppy-scan-issues|upload-artifact" .github/workflows/sloppy-scan.yml .github/workflows/sloppy-fix.yml
git diff --check
```

## Configuration caveat

`.sloppy.yml` is a broad Sloppy configuration reference, not a complete TENN
runtime guide. In particular, it still includes generic Node-oriented examples
such as `test-command: "npm run test:ci"`, `framework: next.js`, and
`runtime: node-20`. Prefer the workflow YAML and this runbook for repository
automation behavior, and prefer `AGENTS.md` / `financial-engine_v2/README.md`
for Python runtime and test commands.
