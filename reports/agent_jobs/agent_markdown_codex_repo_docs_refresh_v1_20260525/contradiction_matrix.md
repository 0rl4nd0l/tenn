# Contradiction And Bloat Matrix

Collected: 2026-06-01T08:05:25Z

## Findings

| ID | Severity | Evidence | Finding | Proposed action |
| --- | --- | --- | --- | --- |
| C1 | high | `AGENTS.md:117-126` defines six lanes; `scripts/agent_job_contract.py:22-29` validates the same six; `.github/ISSUE_TEMPLATE/tenn_task.yml:19-27`, `tenn_audit_finding.yml:19-27`, and `tenn_branch_merge_review.yml:36-44` include `repo-hygiene`, `runtime`, and `cockpit`. | GitHub issue labels and task-card validation use incompatible lane vocabularies. This blocks literal task-card validation for repo-hygiene/runtime/cockpit issue work and forces proxy lanes such as Reporting. | Safe-extension follow-up should either add these lanes to the task-card validator and AGENTS lane model, or explicitly document that GitHub labels can be finer-grained than task-card lanes and require a mapping table. |
| C2 | medium | `CLAUDE.md:140-145` requires updating `docs/claude/STATE.md` at the end of every session; `AGENTS.md:134-143` stops on unresolved HIGH overlap; current registry has active Financial Truth ownership of `docs/claude/STATE.md`. | The unconditional STATE update instruction conflicts with exact task-card allowlists and active-file ownership in live multi-agent mode. | Update standing guidance to make STATE updates conditional on task-card allowlist and registry ownership; otherwise record `DATA_MISSING` or report-only closeout instead of touching the file. |
| C3 | medium | `AGENTS.md:57` tells Codex to read `CLAUDE.md` first; `CLAUDE.md:1-7` imports `AGENTS.md`; `CODEX.md:6-10` says Codex must read AGENTS and CLAUDE; `GEMINI.md:3-4` says Gemini reads GEMINI first, then CLAUDE and AGENTS. | Default read order is circular and tool-specific. The intended behavior is recoverable, but it increases default instruction load and ambiguity. | Add a short load-order note: agent-specific identity first only for identity, then shared contract surfaces; SYSTEM_CONTRACT controls conflicts. Do not duplicate full rules. |
| C4 | medium | `AGENTS.md:342-348` and `CLAUDE.md:367-373` say not to run graphify update after every milestone; `GEMINI.md:86-93` says after modifying code files, run `graphify update .`; `.codex/hooks.json:9` and `.claude/settings.json:35` only warn if `graphify-out/graph.json` exists. | Gemini graphify maintenance instruction conflicts with shared AGENTS/CLAUDE graphify throttling policy. | Align GEMINI.md to the shared rule: read graphify reports when present; refresh at most once per day or on explicit request. |
| C5 | medium | `docs/process/github_issue_system_protocol.md:75-83` says audit-only PRs should not auto-close issues; issue #78 asks for audit/report or bounded refresh. | Audit-only PR title/body must use refs/audit wording, not `fixes #78`, unless all issue acceptance criteria are completed. | Keep #78 open after this audit PR unless a later safe-extension docs patch resolves every accepted finding or links follow-ups. |
| C6 | low | `docs/process/codex_skill_sources/github_issue_system/README.md:9-17` says repo skill copies are mirrors of local Codex skills. | Skill guidance exists in both repo-visible mirrors and local Codex skills; drift is expected unless mirror sync is explicit. | Treat repo copies as reference evidence only. Add version/sync timestamp in a follow-up if live issue mutation depends on mirror text. |
| C7 | low | `.claude/settings.json:72-99` has Claude stop hooks for task-card, milestone, doc coverage, and memory; `.codex/hooks.json:14-24` has only a task-card stop hook; `.gemini/settings.json:13-21` enforces task-card BeforeTool for write/shell tools. | Hook lifecycle behavior is intentionally non-equivalent, but docs can tempt agents to copy behavior between tools. | Keep hook differences tool-specific. Document non-equivalence in load map rather than copying all hooks into every agent file. |
| C8 | low | `graphify-out/GRAPH_REPORT.md` is required by AGENTS/CLAUDE/GEMINI when graphify exists, but `find graphify-out` returned no files in this worktree. | Current graphify context is `DATA_MISSING`; agents must not claim graph-derived architecture evidence in this checkout. | Leave as `DATA_MISSING` unless a user explicitly requests a graph refresh. |
| C9 | medium | `AGENTS.md:10-29` lists many Codex skills under `/home/l4nd0/tenn/.codex/skills/...`; `find /home/l4nd0/tenn/.codex/skills -maxdepth 2 -name SKILL.md` returned only `cockpit-flag-orchestrator/SKILL.md`; current session skill discovery is broader and external to this repo file. | The repo-root AGENTS skill list is stale for this worktree and can send agents to missing paths. | Replace the static repo-local Codex skill inventory with a smaller rule: use session-provided skill discovery first, treat listed paths as examples only, and mark missing paths `DATA_MISSING`. |
| C10 | medium | `command -v python` failed with `python: command not found`; `python3 --version` returned `Python 3.10.12`; `AGENTS.md:264-268` and `GEMINI.md:48` include bare `python scripts/agent_job_*` examples. | Some mandatory command examples are not executable in this host shell without changing `python` to `python3` or using the repo venv. | Normalize task-card/registry command examples in default docs to `python3`, or explicitly say `python` means an activated environment where `python` exists. |

## Non-Findings

- GitHub issue-system protocol correctly distinguishes GitHub Issues as live
  backlog, task cards as execution contracts, reports as evidence, and Project
  Memory as durable coordination/search hints (`docs/process/github_issue_system_protocol.md:5-22`).
- Issue forms correctly keep labels/milestones as recommendations unless a task
  card permits live GitHub mutation (`.github/ISSUE_TEMPLATE/tenn_task.yml:10-12`
  and branch review template lines 10-13).
- The task-card registry rules in AGENTS are consistent with the current
  `agent_job_registry.py` workflow for list-active, claim, check-overlap, and
  release.
