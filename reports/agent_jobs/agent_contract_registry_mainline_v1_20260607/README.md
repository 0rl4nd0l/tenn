# Agent Contract Registry Mainline V1 Report

Status: DONE_WITH_RISK
Date: 2026-06-07
Task card: `docs/agent_tasks/agent_contract_registry_mainline_v1_20260607.md`
Worktree: `/home/l4nd0/tenn-agent-contract-registry-main-v1-20260607`
Branch: `safe/agent-contract-registry-main-v1-20260607`
Baseline: `origin/main` at `7443d9f248346210ada834e1fd19ab923ace192f`

## Scope

Restored mainline Tenn task-card validation and read-only registry inspection
tooling without touching the dirty live checkout.

## Current Evidence

- Current `origin/main` did not contain:
  - `scripts/agent_job_contract.py`
  - `scripts/agent_job_registry.py`
  - `scripts/test_agent_job_contract.py`
  - `scripts/test_agent_job_registry.py`
- PR #300 was merged, but its base was
  `migration/clean-runtime-baseline-reconstruct-v1`, not `main`, so the
  control-plane scripts were still absent from current mainline.
- The dirty live checkout under
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` was preserved and not
  edited.

## Code Changes

- `scripts/agent_job_contract.py`
  - Restores YAML frontmatter task-card validation.
  - Restores `check-diff` allowlist enforcement.
  - Keeps CLI JSON output safe when optional YAML metadata is parsed into
    native date/datetime values.
  - Keeps `audit_only` code changes blocked unless
    `allow_audit_code_changes=true`.
  - Accepts current and near-current mutation modes:
    `audit_only`, `blocked`, `code_and_report_only`,
    `controlled_artifact_provisioning`, `report_only`, and `safe_extension`.
  - Treats `production_data_access` as explicit boolean risk metadata:
    `true` requires `approval_required=true` and is rejected for `audit_only`.
- `scripts/agent_job_registry.py`
  - Restores active task-card registry operations.
  - Adds/keeps `list-active --read-only` with no registry lock acquisition and
    explicit `read_only` / `lock_acquired` fields.
- `scripts/test_agent_job_contract.py`
  - Covers supported mutation modes and the production-data approval guard.
- `scripts/test_agent_job_registry.py`
  - Covers missing-root and existing-record `list-active --read-only`
    no-write behavior.

## Validation

Task-card validation:

```bash
python3 scripts/agent_job_contract.py validate \
  docs/agent_tasks/agent_contract_registry_mainline_v1_20260607.md
```

Result: `ok: true`.

Focused tests:

```bash
/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python \
  -m pytest scripts/test_agent_job_contract.py scripts/test_agent_job_registry.py
```

Result: `51 passed in 1.66s`.

Focused read-only registry tests:

```bash
/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python \
  -m pytest scripts/test_agent_job_registry.py -k 'read_only'
```

Result: `5 passed, 14 deselected`.

The read-only tests cover:

- missing registry root is not created,
- existing active records are read without file or mtime mutation,
- pre-existing `.lock/owner.json` is ignored and preserved,
- `RegistryLock.__enter__` is not called in read-only mode,
- corrupt active JSON returns a warning without rewriting the file.

Manual missing-root read-only probe:

```bash
TENN_AGENT_REGISTRY_ROOT=/tmp/tenn-registry-readonly-missing-*/missing-registry \
  python3 scripts/agent_job_registry.py list-active --read-only --repo-root .
```

Result:

```text
ok: true
read_only: true
lock_acquired: false
active_jobs: []
registry_exists: no
lock_exists: no
```

Mainline task-card corpus validation:

```bash
for card in docs/agent_tasks/*.md; do
  python3 scripts/agent_job_contract.py validate "$card" >/tmp/tenn-card-validate-one.json
done
```

Result: all current mainline task cards validated cleanly.

Read-only list-active against this clean worktree:

```bash
python3 scripts/agent_job_registry.py list-active --read-only --repo-root .
```

Result:

```text
ok: true
read_only: true
lock_acquired: false
active_jobs: []
```

Diff and syntax checks:

```bash
python3 -m py_compile \
  scripts/agent_job_contract.py \
  scripts/agent_job_registry.py \
  scripts/test_agent_job_contract.py \
  scripts/test_agent_job_registry.py
python3 scripts/agent_job_contract.py check-diff \
  docs/agent_tasks/agent_contract_registry_mainline_v1_20260607.md \
  --repo-root . \
  --no-write-report
git diff --check
```

Result: passed before this report was written; rerun after report preservation
is required before merge.

Independent subagent review:

- A read-only subagent reviewed the candidate source branches and recommended
  porting exact blobs/hunks from
  `repo-hygiene/registry-readonly-list-active-v1-20260606` rather than using
  the dirty live untracked scripts or merging the whole branch.
- The review specifically warned that the dirty live untracked
  `scripts/agent_job_registry.py` lacks `--read-only`, enters `RegistryLock`,
  and omits `read_only` / `lock_acquired` proof fields.
- The review also recommended the added lock-contention, no-`RegistryLock`, and
  corrupt-active-record tests now present in
  `scripts/test_agent_job_registry.py`.

Dependency note:

- System `python3 -m pytest ...` returned `No module named pytest`.
- The repaired project/runtime venv already has `pytest 9.0.3` and
  `PyYAML 6.0.3`, so no additional dependency install was needed.

## Unsafe Actions Avoided

- Did not edit, clean, reset, stash, or absorb dirty live-checkout files.
- Did not run lock-writing registry commands against the live shared checkout.
- Did not mutate product runtime, Cockpit, news, extraction, parser, Qdrant,
  Redis, DBs, source PDFs, model/GPU state, cron, timers, services, or GitHub
  issues.

## Remaining Risk

This restores mainline validation and read-only registry inspection, but it does
not claim that every future task-card schema is settled. New mutation modes or
lanes should be added deliberately with tests rather than bypassing validation
or treating `DATA_MISSING` as acceptable.
