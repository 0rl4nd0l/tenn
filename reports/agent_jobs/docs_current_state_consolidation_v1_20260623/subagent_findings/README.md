# Subagent Findings

## A. Repo State and Worktree Scout

Completed read-only. Confirmed target worktree `/home/l4nd0/tenn-docs-current-state-consolidation-v1-20260623`, branch `docs/current-state-consolidation-v1-20260623`, HEAD `e402bf38e5b959f56c1bed6b35e18ba7371cd8f6`, and canonical branch `origin/migration/clean-runtime-baseline-reconstruct-v1` at the same commit. Confirmed default `origin/HEAD` is `main`, not this job's canonical branch. Identified PR #387 as an audit-time HIGH collision risk for `docs/dev_flow/CONTROL_PLANE_STATUS.md`, `docs/dev_flow/CONTROL_PLANE_OPEN_WORK.md`, and `docs/agent_registry/task_ledger/*`; publish preflight later found PR #387 merged.

## B. Documentation Inventory Scout

Completed read-only. Recommended keeping `AGENTS.md` canonical and concise, keeping `CLAUDE.md` as a narrow shim, adding one docs source map, refreshing `docs/dev_flow/SKILLS_SURFACE.md`, demoting stale current-state snapshots, and avoiding broad edits to task-card/report archives.

## C. Runtime / Topology Documentation Fact Checker

Completed read-only. Confirmed checked-in launcher/verifier/model-routing evidence for `/mnt/tenn-nvme2/...` paths and `Qwen3-30B-A3B-Instruct-2507-Q3_K_M`; observed `llama-cpp-router.service` active with listeners on `8001`, Redis on `6379`, and Ollama on `11434`. No live endpoint probes, store queries, or service mutations were performed. Backend/Cockpit/Qdrant/Postgres functionality remains `DATA_MISSING`, and a code/config inconsistency in `cockpit_api.py` default model path is out of scope for this docs job.

## D. Agent Navigation / Onboarding Scout

Completed read-only. Recommended the reading path `AGENTS.md` -> active task card -> source map -> relevant skill/runtime/architecture/report. Recommended demoting `docs/claude/current-state.md`, `docs/prompts/CODEX_MASTER_PROMPT.md`, stale control-plane status snapshots, and `docs/current_system.md` to reference/snapshot status.

## E. Evidence and Architecture Guard

Completed read-only. Warned not to promote stale March/April runtime snapshots into current state. Required volatile runtime claims to say configured/default/intended unless same-run commands prove observed working. Reaffirmed boundaries: runtime functionality proof table for runtime-like DONE claims; memory is not financial truth; architecture docs are policy, not runtime proof.

## F. Final Reviewer / Diff Guard

Completed read-only. The reviewer found three closeout blockers: stale report/status fields, untracked canonical `docs/README.md` and task-card files, and runtime wording that still implied live verification. Parent remediation: refreshed report/status artifacts, downgraded runtime wording to configured/documented unless runtime-proof evidence exists, and will stage the untracked canonical docs and report artifacts explicitly before commit. The reviewer confirmed no PR #387 collision-file edits, no forbidden runtime/product/data paths, JSON validity, markdown path sanity, `git diff --check`, task-card validation, and registry overlap checks.
