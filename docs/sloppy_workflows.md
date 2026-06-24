# Sloppy scan/fix workflows

This page documents the repository's Sloppy GitHub Actions control plane. It is
for operators and maintainers who need to understand how PR scans, seeded fixes,
and failure signals move between the two workflows.

Source of truth:

- `.github/workflows/sloppy-scan.yml`
- `.github/workflows/sloppy-fix.yml`
- `.sloppy.yml`
- `scripts/test_sloppy_fix_workflow.py`

## Workflow map

| Workflow | Trigger | Writes? | Provider path | Main output |
| --- | --- | --- | --- | --- |
| `Sloppy Scan` | `pull_request`, manual `workflow_dispatch` | PR comments only | `github-models` by default; manual `agent` option uses Codex/OpenAI | `sloppy-scan-issues` artifact |
| `Sloppy Fix` | manual `workflow_dispatch`, completed `Sloppy Scan` `workflow_run` | Yes, contents and PRs | Claude (`ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN`) | fix result plus best-effort PR comment |

The automatic path is:

1. `Sloppy Scan` runs on a PR or by manual dispatch.
2. Scan mode writes `/tmp/sloppy-scan-issues.json`.
3. The scan workflow uploads that file as the `sloppy-scan-issues` artifact.
4. A completed same-repository `Sloppy Scan` can trigger `Sloppy Fix`.
5. `Sloppy Fix` downloads the triggering scan artifact, checks out the scan
   `head_sha`, and runs fix mode only when there are seeded found issues.
6. The fix workflow comments on the PR when a PR is associated with the
   triggering scan run.

## Sloppy Scan interface

`Sloppy Scan` supports two scan providers:

- `github-models` (default): used for PR runs and manual runs unless overridden.
- `agent`: available only through manual dispatch. This path normalizes
  `OPENAI_API_KEY`, performs a models API preflight, installs a Codex CLI
  compatibility shim, and runs Sloppy scan mode with `agent: codex`.

Scan mode always passes `output-file: /tmp/sloppy-scan-issues.json` to Sloppy and
uploads that path as the `sloppy-scan-issues` artifact. Artifact upload uses
`if-no-files-found: error`, so a scan that does not create the JSON handoff
should fail instead of silently triggering an unseeded automatic fix.

## Sloppy Fix interface

`Sloppy Fix` is write-capable. It is intentionally unscheduled and has only two
entrypoints:

- manual `workflow_dispatch`
- automatic `workflow_run` after `Sloppy Scan` completes

Automatic runs are gated to same-repository scan runs:

```text
github.event.workflow_run.conclusion == 'success'
github.event.workflow_run.head_repository.full_name == github.repository
```

For automatic runs, the workflow checks out the triggering scan's `head_sha` and
downloads `sloppy-scan-issues` from that scan run. The selector step then applies
these rules:

| Selector outcome | Behavior |
| --- | --- |
| Missing or empty artifact file | Set `found_count=missing_artifact`; skip fix mode successfully. |
| Malformed JSON or missing `issues` array | Hard error from the selector step. |
| Valid artifact with zero `status: found` issues | Set `found_count=0`; skip fix mode successfully. |
| Valid artifact with one or more `status: found` issues | Run Sloppy fix mode with the artifact path as `output-file`. |

Manual runs set `found_count=manual` and pass `/tmp/sloppy-fix-issues.json` as
the Sloppy `output-file` path.

## Fail-closed contract

When all of the following are true, `Sloppy Fix` must not finish green unless it
fixes at least one issue:

- the run is automatic (`workflow_run`)
- Claude auth is enabled
- the scan artifact was present
- the artifact contained a positive count of `status: found` issues

After Sloppy fix mode runs, the workflow reads `steps.sloppy_fix.outputs['issues-fixed']`.
It fails closed when that value is missing, non-numeric, or `0`.

This prevents a seeded scan with found issues from producing a green automatic
fix run when the action made no fixes.

## PR comments

The comment job is best-effort and runs for same-repository automatic runs after
a successful triggering scan. It reports one of these states:

- no Claude credentials were available
- the scan artifact was missing
- the scan reported no found issues
- Sloppy Fix completed and fixed `N` issue(s)
- Sloppy Fix failed closed after seeded issues produced zero or invalid fixes
- Sloppy Fix attempted and ended with another result

If the triggering workflow run has no associated PR, the comment step returns
without posting.

## Configuration notes

- Workflow YAML is the source of truth for trigger, provider, model, permission,
  artifact, and fail-closed behavior.
- `.sloppy.yml` remains a repository-level Sloppy configuration reference. It
  currently includes generic fields such as `test-command: "npm run test:ci"`,
  `framework: next.js`, and `runtime: node-20`; verify those values before using
  them as Python/TENN runtime guidance.
- `Sloppy Fix` preserves the Claude provider shape:
  - `agent: claude`
  - `model: claude-sonnet-4-5-20250929`
  - credentials from `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN`
- `Sloppy Scan` manual `agent` mode uses `CODEX_MODEL=gpt-5.2-codex`.

## Troubleshooting

| Symptom | Likely cause | What to check |
| --- | --- | --- |
| Automatic fix does not run after a scan | Scan failed, scan came from a fork, or workflow condition rejected it | `Sloppy Scan` conclusion and `head_repository.full_name` |
| Fix run is green but no fix happened | No Claude credentials, zero found issues, or missing artifact skip path | `auth_enabled`, `seeded_issue_count`, and skip step logs |
| Fix run fails after Sloppy runs | Positive seeded findings with zero, missing, or invalid `issues-fixed` output | `Fail Sloppy fix when seeded issues remain unfixed` step |
| Fix selector fails before Sloppy runs | Malformed artifact JSON or missing `issues` array | Downloaded `/tmp/sloppy-scan/sloppy-scan-issues.json` |
| Manual agent scan fails early | OpenAI secret missing, too short, or auth preflight failed | `Normalize OpenAI API key` and `Codex preflight` steps |
| No PR comment appears | The triggering run has no PR association, or GitHub comment API failed | `Comment on PR` step warnings |

## Local verification

Run the focused workflow tests after editing either Sloppy workflow:

```bash
python -m unittest scripts/test_sloppy_fix_workflow.py
```

These tests parse `.github/workflows/sloppy-fix.yml` with a GitHub Actions-safe
YAML loader and assert:

- seeded automatic runs fail when Sloppy reports zero fixes
- Claude provider, auth, action, model, and output-file wiring are preserved
- seeded and fixed issue counts propagate into the PR comment job
- the fix workflow remains unscheduled
