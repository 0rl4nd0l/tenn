# Validation

## Passed

- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-sloppy-automation-repair-v1-20260629 --topic "sloppy automation scan artifact and model config" --json`
  - result: pass
  - path ownership: `VALID_TASK_WORKTREE`
  - registry: no active jobs
  - ledger: live and committed sources validated
- `python3 scripts/tenn_dev_status.py`
  - result: pass before edits, `STATE: CLEAN`
  - result after edits: guard still passes; dirty set is this task's files
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/sloppy_automation_scan_artifact_repair_v1_20260629.md`
  - result: pass
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
  - result: pass, no active jobs
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
  - result: pass, 276 entries checked across live and committed sources
- YAML/config parse and value sanity for `.sloppy.yml`,
  `.github/workflows/sloppy-scan.yml`, and `.github/workflows/sloppy-fix.yml`
  - result: pass
  - confirmed `github-models-model: openai/gpt-4o-mini`
  - confirmed `output-file: /tmp/sloppy-scan-issues.json`
  - confirmed no action-consumed `.sloppy.yml` scalar values contain `#`
- Workflow structure check
  - result: pass
  - confirmed Sloppy Scan uploads `sloppy-scan-issues`
  - confirmed Sloppy Fix has `workflow_run`, artifact download, seeded issue
    outputs, `actions: read`, and PR comment permissions
- `bash -n` over shell `run:` bodies extracted from both Sloppy workflows
  - result: pass
- `git diff --check`
  - result: pass
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/sloppy_automation_scan_artifact_repair_v1_20260629.md --repo-root . --no-write-report`
  - result: pass before and after report artifacts
  - disallowed files: none
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/sloppy_automation_scan_artifact_repair_v1_20260629.md --repo-root .`
  - result: pass, all listed report artifacts exist
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/sloppy_automation_scan_artifact_repair_v1_20260629.md --repo-root .`
  - result: pass
- `python3 scripts/agent_task_ledger.py validate --entry-file reports/agent_jobs/sloppy_automation_scan_artifact_repair_v1_20260629/TASK_LEDGER_ENTRY.json`
  - result: pass after schema-status correction
- `python3 -m json.tool reports/agent_jobs/sloppy_automation_scan_artifact_repair_v1_20260629/TASK_LEDGER_ENTRY.json`
  - result: pass
- initial commit and push
  - result: commit `a64bbee07f66392114a00eabcc94ba5d217663f6` pushed to
    `origin/control-plane/sloppy-automation-repair-v1-20260629`
  - note: the pre-push hook reported missing local
    `financial-engine_v2/.venv/bin/ruff` and
    `financial-engine_v2/.venv/bin/pytest`; with
    `TENN_ALLOW_MISSING_HOOK_TOOLS=1`, markdown hygiene passed and the hook
    skipped only the unavailable local lint/test binaries
- Draft PR creation
  - result: pass
  - PR: https://github.com/0rl4nd0l/tenn/pull/469
  - base: `migration/clean-runtime-baseline-reconstruct-v1`
  - head: `control-plane/sloppy-automation-repair-v1-20260629`
- `gh api -X GET repos/0rl4nd0l/tenn/actions/runs/28356577058`
  - result: pass
  - workflow: `Sloppy Scan`
  - event: `pull_request`
  - conclusion: `success`
  - head SHA: `a64bbee07f66392114a00eabcc94ba5d217663f6`
- `gh api -X GET repos/0rl4nd0l/tenn/actions/runs/28356577058/artifacts`
  - result: pass
  - artifact: `sloppy-scan-issues`
  - artifact ID: `7945513532`
  - created at: `2026-06-29T07:45:07Z`
- `gh run download 28356577058 --repo 0rl4nd0l/tenn --name sloppy-scan-issues --dir /tmp/sloppy-scan-proof-28356577058`
  - result: pass
  - downloaded file:
    `/tmp/sloppy-scan-proof-28356577058/sloppy-scan-issues.json`
  - payload summary: `mode: scan`, `score: 100`, `issues: []`
- `gh api -X GET repos/0rl4nd0l/tenn/actions/runs/28356591800`
  - result: pass
  - workflow: `Sloppy Fix`
  - event: `workflow_run`
  - conclusion: `success`
- `gh run view 28356591800 --repo 0rl4nd0l/tenn --log`
  - result: pass
  - confirmed `actions/download-artifact@v4` used `run-id: 28356577058`
  - confirmed artifact `sloppy-scan-issues` ID `7945513532` downloaded
  - confirmed Sloppy Fix skipped because the triggering Sloppy Scan reported no
    found issues
  - confirmed PR comment environment:
    `FIX_ENABLED=true`, `FIX_RESULT=success`, `SEEDED_ISSUE_COUNT=0`
- `gh api -X GET repos/0rl4nd0l/tenn/issues/469/comments`
  - result: pass
  - confirmed Sloppy Scan score comment and Sloppy Fix automatic skip comment
    were both posted by `github-actions[bot]`

## Not Run

- `actionlint`
  - result: not available in this environment (`command -v actionlint` returned
    no path)
- Product/runtime/data/extraction tests
  - result: not applicable; this task changed only GitHub automation config and
    report/task-card artifacts
