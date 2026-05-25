# Graphify Instruction Conditionality Safe Extension

## Scope

- Follow-up to GitHub issue #67 and `graphify_artifact_contract_audit_v1_20260525`.
- Lane: Reporting.
- Execution mode: SAFE EXTENSION MODE.
- Target system layer: agent instruction and report-artifact contract only.
- Contract boundary: no backend, Cockpit product, financial truth, provenance, memory, runtime, Docker, env, Graphify artifact generation, or data-store changes.

## Preflight Declaration

- Agent: Codex.
- Branch: `audit/repo-hygiene-safe-audits-v1-20260525`.
- Worktree: `/home/l4nd0/tenn-repo-hygiene-audits-v1-20260525`.
- Intended files: task card, `AGENTS.md`, `CLAUDE.md`, and this report directory.
- Contested surfaces touched: none.
- Collision risk: LOW.
- Decision: proceed.

## Result

The stale literal Graphify requirement is now conditional in both instruction files:

- `AGENTS.md` now says `graphify-out/` may be absent in clean worktrees.
- `CLAUDE.md` now says the same.
- Agents are instructed to read `graphify-out/GRAPH_REPORT.md` when present; when absent, they must report Graphify evidence as `DATA_MISSING` and continue from current repo evidence.
- Agents are explicitly told not to generate or commit `graphify-out` artifacts without user approval.

No `graphify update` command was run. No generated `graphify-out/` artifacts were created or committed.

## Evidence

- The #67 audit reported `graphify-out/GRAPH_REPORT.md` and `graphify-out/wiki/index.md` absent in this clean audit worktree, ignored by `.gitignore`, and not tracked in git.
- Current absence checks for `graphify-out`, `graphify-out/GRAPH_REPORT.md`, and `graphify-out/wiki/index.md` returned missing.
- `docs/architecture/SYSTEM_CONTRACT.md` contains no Graphify invariant; this is an agent-instruction wording fix only.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/graphify_instruction_conditionality_safe_extension_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py list-active`: passed, no active jobs before claim.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/graphify_instruction_conditionality_safe_extension_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/graphify_instruction_conditionality_safe_extension_v1_20260525.md`: passed.
- `test -e graphify-out`: missing, expected for this fix.
- `test -f graphify-out/GRAPH_REPORT.md`: missing, expected for this fix.
- `test -f graphify-out/wiki/index.md`: missing, expected for this fix.
- Graphify instruction content inspection: passed.
- `python3 -m json.tool reports/agent_jobs/graphify_instruction_conditionality_safe_extension_v1_20260525/status.json`: passed.
- `python3 -m json.tool reports/agent_jobs/graphify_instruction_conditionality_safe_extension_v1_20260525/validation.json`: passed.
- `git diff --check`: passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/graphify_instruction_conditionality_safe_extension_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py release graphify_instruction_conditionality_safe_extension_v1_20260525`: passed.
