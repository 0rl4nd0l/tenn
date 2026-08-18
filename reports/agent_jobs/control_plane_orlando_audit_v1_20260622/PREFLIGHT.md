# Preflight Evidence

## Initial Cwd

The user supplied cwd was:

```text
/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1
```

That path was not a Git repository in this environment. It contained `docs`, `financial-engine_v2`, and `reports`, but no `.git`.

## Canonical Selection

The audit used `/home/l4nd0/tenn-fast-dev-storage-v1` only as a read/fetch anchor, then created a clean sibling worktree from the requested canonical Tenn branch:

```text
origin/migration/clean-runtime-baseline-reconstruct-v1
```

Merged PR evidence:

- PR #380: merged into `migration/clean-runtime-baseline-reconstruct-v1` at `4d62fec4e855b313ae89136e947510c627b9bcde`.
- PR #382: merged into `migration/clean-runtime-baseline-reconstruct-v1` at `154888ecca6220ab598efcd140a2c2b62fca3da7`.

## Working Tree

```text
pwd: /home/l4nd0/tenn-control-plane-orlando-audit-v1-20260622
branch: control-plane/orlando-control-plane-audit-v1-20260622
HEAD: 154888ecca6220ab598efcd140a2c2b62fca3da7
upstream: origin/migration/clean-runtime-baseline-reconstruct-v1
status before docs/report writes: clean
origin/HEAD symbolic ref: refs/remotes/origin/main
origin/HEAD commit: cc99cec1bfc4ee79aac407a8caeed8d4baec2f6b
canonical Tenn branch commit: 154888ecca6220ab598efcd140a2c2b62fca3da7
merge-base with canonical: 154888ecca6220ab598efcd140a2c2b62fca3da7
```

Important ambiguity: Git remote `origin/HEAD` points at `main`, but this audit followed the user-requested current canonical Tenn branch after PR #380 and #382: `origin/migration/clean-runtime-baseline-reconstruct-v1`.

## Required Reads

Read fully:

- `AGENTS.md`
- `docs/dev_flow/SKILLS_SURFACE.md`
- all `.agents/skills/*/SKILL.md`
- relevant control-plane scripts and templates
- recent control-plane reports related to PR #345, #367, #370, #373, #375, #378, #380, and #382

## Registry And Ledger

Registry read-only:

```bash
python3 scripts/agent_job_registry.py list-active --read-only --repo-root .
```

Result:

```text
ok: true
active_jobs: []
lock_acquired: false
read_only: true
```

Ledger validation:

```bash
python3 scripts/agent_task_ledger.py validate
```

Result:

```text
ok: true
entry_count: 15
issues: []
data_missing: []
```

Ledger caveat: the live ledger validates, but its summary still contains a stale PR #380 `pr_opened` entry even though PR #380 is merged.
