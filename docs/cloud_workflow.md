# Cursor Cloud Workflow

This repo must treat local work as the source of truth.

Cursor Cloud does not see:

- your uncommitted local edits
- your local services and runtime state
- any commits that have not been pushed

That means Cloud work should be treated as branch and PR generation, not as the primary working copy.

## Rules

1. Start from the branch you actually want to extend.
   - For active recovery work, that is usually `recovery/reconstruction`.
2. Push the exact base state before opening a Cloud task.
   - If the state matters, make a small WIP commit and push it first.
3. Give Cloud a narrow task.
   - One subsystem or one bugfix per PR.
4. Require deterministic start and validation paths.
   - Run from repo root.
   - Start with `bash scripts/start_system.sh`
   - Validate with `bash scripts/validate_system.sh`
5. Bring Cloud work back through an isolated review branch or worktree.
   - Do not merge directly into a dirty local branch.

## Safe Workflow

### 1. Prepare locally

From repo root:

```bash
git switch recovery/reconstruction
git status --short
git add <intended files>
git commit -m "wip: checkpoint before cursor cloud"
git push origin recovery/reconstruction
git rev-parse HEAD
```

Use the printed commit SHA as the Cloud base.

Automated safe path:

```bash
bash scripts/prepare_cloud_worktree.sh
```

That helper does three things without touching the dirty working tree:

- creates a backup branch pinned to current `HEAD`
- creates a clean sibling worktree from current `HEAD` on a new `cloud/*` branch
- prints the exact branch, commit, and commands to hand off to Cursor Cloud

Optional local-noise suppression:

```bash
bash scripts/prepare_cloud_worktree.sh --apply-local-excludes
```

That only appends recommended local-only patterns to `.git/info/exclude`. It does not delete files, run `git clean`, or auto-commit anything.

### 2. Start the Cloud task

Tell Cursor Cloud exactly:

- branch name
- base commit SHA
- working directory: repo root
- canonical start command
- canonical validation command
- expected output: one PR only

### 3. Review locally

Fetch PR refs:

```bash
git fetch origin 'refs/pull/*/head:refs/remotes/origin/pr/*'
```

Review in an isolated worktree:

```bash
git worktree add -b integration/pr-review /tmp/tenn-pr-review recovery/reconstruction
cd /tmp/tenn-pr-review
git cherry-pick -x origin/pr/<PR_NUMBER>
```

If the cherry-pick conflicts, stop and review manually in the isolated worktree. Do not force the PR directly into your dirty main branch.

### 4. Promote back to your main branch

Only after the isolated review branch is clean:

```bash
cd /home/l4nd0/tenn
git cherry-pick <reviewed_commit_sha>
```

## What To Avoid

- Do not start Cloud work from a stale remote branch.
- Do not assume Cloud can see local uncommitted changes.
- Do not ask Cloud to clean up broad unrelated surfaces in one PR.
- Do not merge a Cloud PR straight into a dirty local tree.
- Do not run the wrapper scripts from inside `financial-engine_v2/`.
- Do not use `git clean -fdx` in this repo as a first step.

## Repo-Specific Notes

- Repo root is `/home/l4nd0/tenn`
- Canonical backend launcher: `financial-engine_v2/scripts/run_local_backend.sh`
- Wrapper start command: `scripts/start_system.sh`
- Wrapper validation command: `scripts/validate_system.sh`
- Machine-readable contract: `agent_contract.json`

The wrapper scripts are repo-root-relative. Run them from repo root:

```bash
cd /home/l4nd0/tenn
bash scripts/start_system.sh
bash scripts/validate_system.sh
```

## Cursor Cloud Handoff Prompt

Copy and paste this, then replace the placeholders.

```text
Work from branch <BRANCH_NAME> at commit <BASE_SHA>.

Repository root is the working directory.

Rules:
- Keep the task scoped to <TASK_DESCRIPTION>.
- Open one PR only.
- Do not refactor unrelated files.
- Do not rebase or broad-clean the repository.
- Preserve existing human edits when conflicts appear.

Canonical runtime:
- Start from repo root with: bash scripts/start_system.sh
- Validate from repo root with: bash scripts/validate_system.sh
- The backend is considered running only when /api/health is reachable.

Output requirements:
- Make the smallest correct change.
- Include tests only where they directly cover the task.
- Summarize changed files and validation performed.
- If blocked by missing local-only state or conflicting branch drift, stop and report the blocker instead of guessing.
```
