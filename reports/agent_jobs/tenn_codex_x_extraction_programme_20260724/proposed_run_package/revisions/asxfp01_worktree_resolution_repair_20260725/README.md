# ASXFP 01 Codex X Worktree Resolution Repair

## Objective

Repair the Codex X isolated-checkout Git admission contract exposed by
`ASXFP_01_SCORECARDS`, preserve the failed launch evidence, restore the ticket
to `READY` with zero product implementation attempts, and stop before another
implementer or reviewer launch.

## Current state

`DONE`

The launcher repair is committed locally at
`263dc65b7be87e47c4ed761a8c63bc89333e100b`. The launcher repository has no
configured remote, so that commit cannot be pushed from the repaired checkout.
The corrected supervisor package is report-only and is based on canonical Tenn
commit `107c926930ef5a14783a8293bac9b47c9046bfed`, tree
`9e43e6380c357e1a40a23bff6d4a07522c86ff98`.

No product file, product test, runtime, data store, model worker, reviewer,
merge, or deployment was touched.

## Root cause

Codex X cloned the Tenn product repository into the writable source and then
moved the clone's `.git` directory to launcher-owned `git-metadata`. It did not
leave a `.git` indirection file in the source. The launcher admission path used
ambient `GIT_DIR` and `GIT_WORK_TREE`, but the child was told to run ordinary
`git -C <source>` commands. Without standalone product metadata, Git walked
upward and resolved the enclosing per-run launcher control repository. Its
`SOURCE.md` and `manifest.json` therefore appeared as untracked product files.

The product checkout itself was independently clean at the pinned HEAD and
tree. The failure was repository-context admission, not product implementation.

## Repair

The launcher now:

- leaves a regular `.git` indirection at the writable source pointing to the
  launcher-owned Git directory;
- records the exact expected source root, Git directory, HEAD, tree, remote,
  normalized repository identity, and launcher-owned Git wrapper;
- puts the wrapper first on the child `PATH`, strips ambient Git context, binds
  every operation to the recorded `--git-dir` and `--work-tree`, and rejects
  repository-context override arguments;
- compares ordinary and explicitly bound `rev-parse --show-toplevel` and
  `--absolute-git-dir` results before model execution;
- checks pinned HEAD/tree and product-only status, staged diff, and unstaged
  diff; and
- fails closed for external roots, wrong or broken metadata, wrong repository
  identity, dirty product worktrees, symlinked source roots, and baseline drift
  on continuation.

The child prompt gives the exact wrapper and repository-binding commands. It no
longer asks the model to infer its repository context.

## Failed-launch accounting

Run `20260725T041849Z-107c926930-e0e992`, session
`019f978e-6163-77f3-b30c-4b124d4a029f`, is reclassified as
`ORCHESTRATION_WORKTREE_RESOLUTION_FAILURE`.

The child executed only its mandatory checkout preflight. It read no ticket
code, changed no product file, ran no product test, and produced no patch,
commit, scorecard, or reviewable delta. Ticket `ASXFP_01_SCORECARDS` is
therefore `READY`, with `implementation_attempts: 0` and `retry_count: 0`.
Reviewer launch remains prohibited because there is no reviewable delta.

## Corrected no-launch proof

Prepared run `20260725T050234Z-107c926930-7bfbc3` was created with
`--prepare-only`; its transport preflight was then executed with `--dry-run`.
No child session identity exists and `would_start_child` was false.

- expected and resolved source root:
  `/home/l4nd0/codex-x-pilot/.state/runs/20260725T050234Z-107c926930-7bfbc3/workspace/source`
- expected and resolved Git directory:
  `/home/l4nd0/codex-x-pilot/.state/runs/20260725T050234Z-107c926930-7bfbc3/git-metadata`
- launcher-owned wrapper:
  `/home/l4nd0/codex-x-pilot/.state/runs/20260725T050234Z-107c926930-7bfbc3/bin/git`
- remote identity: `github.com/0rl4nd0l/tenn`
- HEAD: `107c926930ef5a14783a8293bac9b47c9046bfed`
- tree: `9e43e6380c357e1a40a23bff6d4a07522c86ff98`
- status: empty
- staged and unstaged diff checks: pass
- prepared manifest SHA-256:
  `f97e23e264d5b525f253641775887da3ba9a203f51cbdccf0963adfeb4404777`
- wrapper SHA-256:
  `a6183a9e194c9269564bb78897eb5c2b0b106630ca88f1f56a0375798f1bd001`

## Changed files

Launcher checkout `/home/l4nd0/codex-x-pilot-transport-contract-v1-20260725`:

- `README.md`
- `src/codex_x.py`
- `src/child_transport.py`
- `templates/config.toml`
- `templates/project-AGENTS.md`
- `tests/test_codex_x.py`

This report revision:

- `README.md`
- `CODE_REVIEW.json`
- `allowed_scope.json`
- `artifact_hashes.json`
- `attempt_validation.json`
- `incident_classification.json`
- `launcher_preflight.json`
- `proposed_launch_command.sh`
- `repository_resolution_reproduction.json`
- `revision_summary.json`
- `schema_bindings.json`
- `schema_validation.json`
- `prompts/ASXFP_01_SCORECARDS-implementer-transport-v4.txt`
- `schemas/child_result.schema.json`
- `schemas/model_output.schema.json`
- `schemas/ticket_state.schema.json`
- `ticket_state/ASXFP_01_SCORECARDS.json`

## Validation

All commands exited zero:

- focused launcher tests:
  `83 passed in 5.05s`
- full launcher tests:
  `113 passed, 3 subtests passed in 7.69s`
- Python compilation for launcher modules
- shell syntax for launcher entrypoints and the proposed launch command
- Draft 2020-12 schema validation and strict output-schema validation
- artifact hash inventory validation
- launcher and supervisor `git diff --check`
- read-only launcher dry run
- prepare-only run plus no-launch child transport preflight
- ordinary, explicitly bound, and wrapper-bound exact Tenn top-level checks

Regression coverage includes a workspace nested in a dirty parent repository,
parent untracked files, missing or broken product Git metadata, a wrong Git
directory, valid clean and dirty product worktrees, wrong repository identity,
symlinked source roots, wrapper context overrides, and continuation drift.

## Evidence and constraints

The failed run and session evidence remain under launcher state:

- `/home/l4nd0/codex-x-pilot/.state/runs/20260725T041849Z-107c926930-e0e992`
- `/home/l4nd0/codex-x-pilot/.state/user-home/codex-home/sessions/2026/07/25/rollout-2026-07-25T14-35-18-019f978e-6163-77f3-b30c-4b124d4a029f.jsonl`

The pre-existing supervisor checkout was stale relative to current canonical and
was preserved without edits. This revision was built in a clean sibling
worktree. The launcher control checkout and the user's Tenn checkout were also
preserved.

The proposed launch command is sealed in `proposed_launch_command.sh`. It was
syntax-checked and dry-run validated but was not executed. A fresh implementer
launch is the next safe action only after separate owner authorization.
