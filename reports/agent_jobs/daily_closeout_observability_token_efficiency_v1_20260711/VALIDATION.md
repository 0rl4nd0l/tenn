# Validation

Validation status: `PASS_REPO_ONLY`

## Commands And Results

- `python3 scripts/tenn_dev_status.py`: exit 0; task worktree, guard/registry/
  ledger pass; final status correctly reports task-owned dirt.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/daily_closeout_observability_token_efficiency_v1_20260711.md`:
  exit 0; no issues.
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`:
  exit 0; zero active jobs.
- `python3 scripts/agent_task_ledger.py resolve-path` and
  `python3 scripts/agent_task_ledger.py validate`: exit 0; 311 entries, no
  issues or missing sources.
- Portable Git Guard preflight before edits: pass; `VALID_TASK_WORKTREE`,
  canonical/HEAD/merge base `2c9324a9`, no matching active work,
  `stop_reimplementation=false`.
- Portable Git Guard at closeout: command exit 0, but decision `block` and
  `stop_reimplementation=true` because the worktree now contains the expected
  `DIRTY_RELATED_WORKTREE` task diff. No duplicate or unrelated dirt found.
- `python3 -m json.tool` for all four V1 schemas: exit 0.
- `uv run --with jsonschema ...`: exit 0; four Draft 2020-12 schemas and four
  representative finalized fixtures validated.
- `uv run --with ruff ruff check scripts/codex_automation_observability.py scripts/codex_automation_runner.py scripts/test_codex_automation_observability.py scripts/test_codex_automation_runner.py`:
  exit 0, `All checks passed!`.
- `python3 -m py_compile scripts/codex_automation_observability.py scripts/codex_automation_runner.py`:
  exit 0.
- `python3 -m unittest scripts/test_codex_automation_observability.py scripts/test_codex_automation_runner.py`:
  exit 0; 34 tests passed.
- `python3 scripts/codex_automation_runner.py list`: exit 0; all existing jobs
  present and daily-closeout retains the small-model policy.
- `python3 scripts/codex_automation_observability.py --help`: exit 0; review and
  summarize commands present.
- Temp-root `python3 scripts/codex_automation_runner.py daily-closeout --dry-run`:
  exit 0; isolated read-only structured command rendered; only owner-mode temp
  directories created; zero run/evidence/model records and no child launch.
- Temp-root `python3 scripts/codex_automation_observability.py --output-root <tmp> summarize`:
  exit 0; seven-run empty-window JSON with zero model invocations/tokens and
  cost `DATA_MISSING`.
- `python3 scripts/agent_job_contract.py check-diff ...`: exit 0; no disallowed
  files; generated `diff-check.json`.
- `python3 scripts/agent_job_contract.py check-report-artifacts ...`: exit 0;
  all ten declared report artifacts exist and are non-empty.
- `python3 scripts/agent_job_contract.py check-closeout ...`: exit 0; no issues.
- `git diff --check`: exit 0.

## Focused Coverage

- owner-only atomic writes, finalized immutability, and symlink refusal
- lock contention, `SKIPPED_CONCURRENT`, and stale `RUNNING` recovery
- fixed allowlisted probes, timeouts, redaction, probe/pack caps
- normalized fact comparison, bootstrap, model-gate reasons, and usefulness
- native no-model path with zero tokens
- valid fake-child output and detailed token parsing
- invalid fake-child output, exact one attempt, preserved partial result
- oversized raw model output preserved and rejected before JSON load
- fact-reference/schema/unsafe-action validation
- hashes, report cap, immutable reviews, and seven-run aggregation
- non-daily command compatibility and health failure-shape recognition

## Failed Attempts And Corrections

- Host Python lacked `ruff`; validation moved to ephemeral `uv --with ruff`
  without changing repo dependencies.
- The first schema fixture used outdated helper argument names; the harness was
  corrected, then finalized fixtures passed.
- One exploratory summary command used unsupported `--limit`; the documented
  `--last`/default-seven contract was verified with the correct command.

## Runtime Functionality Proof

| Field | Required evidence |
| --- | --- |
| intended output | One scheduled daily-closeout joined run/evidence/report set, plus optional model output when gated. |
| live output location | Host automation output root under `~/.codex/automations/tenn` after approved deployment. |
| pre-run max timestamp or count | `DATA_MISSING`; live root access/write proof was forbidden. |
| post-run max timestamp or count | `DATA_MISSING`; no scheduled run occurred. |
| rows/files inserted or updated after run start | `DATA_MISSING`; temp test artifacts only. |
| readiness/gate status | Repo validation passed; publication, deployment, and scheduled-proof gates remain unapproved. |
| exact command/query used | No live command used. Temp dry-run and fake-child unittest commands are listed above. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | DATA_MISSING |
| remaining blocker | Explicit Group P, D, and S approvals in sequence, then intended-output proof. |

System functionality was not proven; only repo code, tests, schemas,
documentation, and temporary artifacts were proven.

## Publication Group P Refresh - 2026-07-11

- Live remote canonical, local origin canonical, task HEAD, and merge base all
  matched `2c9324a9e69d6c0a66d7a3f2090e39f5e6a5a35c`.
- Git Guard support, ledger, and registry passed; no duplicate work or missing
  source was found. Its `block` decision was solely the exact preserved
  `DIRTY_RELATED_WORKTREE` diff that the current owner goal approves publishing.
- GitHub auth passed and no existing PR matched this head branch or topic.
- The exact ten-file dirt set matched the handoff; there was no unexpected or
  missing path.
- Task-card, diff, report-artifact, closeout, JSON, Ruff, py_compile, 34 focused
  tests, runner list, CLI help, and `git diff --check` all passed again.
- Four schemas and four representative finalized fixtures passed again.
- A fresh temp-root dry-run returned exit 0, created zero run/evidence/model
  records, used only `0700` directories, and launched no Codex child.
