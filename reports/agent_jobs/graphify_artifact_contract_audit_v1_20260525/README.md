# Graphify Artifact Contract Audit

## Scope

- GitHub issue: #67.
- Lane: Reporting, mapped from the issue's repo-hygiene audit intent because the task-card validator does not define a Repo Hygiene lane.
- Execution mode: AUDIT MODE.
- Target system layer: agent instruction and report-artifact contract only.
- Contract boundary: no backend, Cockpit product, financial truth, provenance, memory, runtime, Docker, env, or data-store changes.

## Findings

1. `AGENTS.md` and `CLAUDE.md` both state that the project has a graphify knowledge graph at `graphify-out/` and instruct agents to read `graphify-out/GRAPH_REPORT.md` before architecture or codebase answers. Evidence: `AGENTS.md:340-348`, `CLAUDE.md:365-373`.
2. `docs/architecture/SYSTEM_CONTRACT.md` has no Graphify references in the current checkout. The Graphify rule is an agent-instruction contract, not a backend system invariant.
3. `graphify-out/`, `graphify-out/GRAPH_REPORT.md`, and `graphify-out/wiki/index.md` are absent in this clean audit worktree. `git ls-files graphify-out` and `git log --all -- graphify-out` returned no tracked artifact evidence.
4. `.gitignore:67` ignores `graphify-out/`, and `git check-ignore -v` confirms both expected artifact paths are ignored by that rule.
5. Generation tooling is partial: `scripts/build_architecture_graph_scope.py` can materialize a curated architecture corpus and optionally run `graphify update <scope>`, but the `graphify` executable is not on `PATH` in this shell. A prior spec note also records `graphify` as `command not found`.

## Classification

- Missing artifact status: Confirmed.
- Contract breach status: Confirmed for the literal AGENTS/CLAUDE claim in clean checkouts, because agents cannot read a required missing file.
- System-contract breach status: Not confirmed. No Graphify rule appears in `SYSTEM_CONTRACT.md`, and no backend authority or data invariant is affected.
- Root cause: stale or over-strong agent instructions plus intentionally ignored/external generated artifact expectations.

## Recommendation

Open a safe child docs task to either:

- update AGENTS/CLAUDE to make Graphify reading conditional: read `graphify-out/GRAPH_REPORT.md` when present; otherwise report `DATA_MISSING` and continue from raw repo evidence, or
- add an approved Graphify generation runbook and artifact manifest that explains where `graphify-out/` is generated, why it remains ignored, and when a user-approved `graphify update` is allowed.

Do not generate or commit `graphify-out/` artifacts without explicit user approval.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/graphify_artifact_contract_audit_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/graphify_artifact_contract_audit_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/graphify_artifact_contract_audit_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py release graphify_artifact_contract_audit_v1_20260525`: passed.
- `python3 -m json.tool reports/agent_jobs/graphify_artifact_contract_audit_v1_20260525/graphify_contract_matrix.json`: passed.
- `python3 -m json.tool reports/agent_jobs/graphify_artifact_contract_audit_v1_20260525/status.json`: passed.
- `git diff --check`: passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/graphify_artifact_contract_audit_v1_20260525.md`: passed.
