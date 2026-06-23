# Control Plane Open Work Register

Status: control-plane follow-up after merged PR #388 and live task-ledger current-state refresh.

Priority meanings:

- P0: causes incorrect or unsafe Codex behavior;
- P1: blocks useful automation;
- P2: confusing but not blocking;
- P3: cleanup or nice-to-have.

## Register

| Priority | Item | Status | Evidence | Impact | Owner decision needed | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| P0 | Runtime Functionality Proof can still be skipped by agent behavior | IMPLEMENTED | `scripts/agent_job_contract.py check-closeout` enforces runtime-like closeout proof against report artifacts; `scripts/agent_job_hook.py` runs it on Stop/SessionEnd for active task cards. | Runtime/product/data `DONE` claims now get a control-plane warning/failure when proof fields are missing, unless the task is explicitly report-only, docs-only, or control-plane only. | No immediate decision for this control-plane gate. | After merge, monitor for false positives and only tune the runtime-like keyword/exemption list with focused tests. |
| P1 | Repo `/goal monitor` implementation | NOT_FOUND | No repo command, script, hook, daemon, or timer was found. Host `codex-goal-monitor` exists only outside the repo. | Orlando can be misled into thinking `/goal monitor` is a Tenn feature. | Decide whether host-only monitor is enough or a repo wrapper/report protocol is needed. | Either document HOST_ONLY permanently or approve a repo-backed monitor wrapper task. |
| P1 | Task ledger current-state drift | PARTIAL | Current worktree resolves the live ledger path as present with 2 raw entries for `task_ledger_current_state_refresh_v1_20260623`; latest state is `done`, and the committed snapshot was exported from that live ledger after PR #388. | "What next?" flows now have a live branch-independent current-state entry for this task, but older hand-curated PR #380/#382/#383/#385/#386 snapshot entries are not present in the live ledger. | Decide whether historical control-plane work should be backfilled into the live ledger or left to GitHub/task-card/report evidence. | Continue appending future mutable tasks to the live ledger; backfill older verified work only through a separate approved task. |
| P1 | Git hook installation check is stale or misconfigured | PARTIAL | `scripts/check_agent_hooks.py` reports configured path `/home/l4nd0/tenn/.git/hooks` missing while common-dir hooks exist under `/mnt/sdb2/...`. | Local pre-commit/pre-push expectations may not match actual hook execution. | Decide whether to standardize hooks path across worktrees. | Run a dedicated hook repair/verification task. |
| P1 | Repo skills are not guaranteed visible in host autocomplete | HOST_ONLY | `scripts/sync_codex_skills.sh` dry-run would link 10 skills; `--apply` was not run. | Orlando may see host/global skills and miss Tenn repo skills. | Decide whether to keep path-forcing workflow or approve host sync. | Prefer explicit `.agents/skills/<skill>/SKILL.md` reads; sync only in a separate approved task. |
| P1 | OpenCode worker usability is proven only to probe/test level | PARTIAL | Probe succeeded and unit tests passed, but no actual worker was run in this audit. | Worker scouting is available, but every task still needs per-result proof. | No decision if evidence-only scouting is acceptable. | For first real use, run one read-only scout and preserve task/result/validation artifacts. |
| P2 | `SKILLS_SURFACE.md` freshness metadata is stale | STALE | File still references `pending-pr-380`; canonical audit is after PR #382. | Operators may distrust current skill-surface docs. | No product decision. | Tiny docs update to current commit/PR metadata. |
| P2 | Old report states conflict with live PR state | STALE | Reports for PR #378, #380, #373, and #367 contain old statuses; GitHub shows merged or superseded outcomes. | Report search can surface stale readiness claims. | Decide whether to append refresh notes to old reports or rely on new status docs. | Add a report-state refresh index or stale-report banner task. |
| P2 | PR #367 report lineage | SUPERSEDED | PR #367 was closed and superseded by PR #375; older report still says PR open. | Duplicate closeout work risk. | No if current docs mark it superseded. | Keep supersession note in operator docs and ledger refresh. |
| P2 | `.codex/skills/cockpit-flag-orchestrator` legacy skill | STALE | `docs/agents/skill-registry.md` classifies `.codex/skills` as legacy/custom; file references older runtime concerns. | Autocomplete or local browsing can confuse Orlando. | Decide whether to archive, keep grandfathered, or remove. | Add explicit legacy warning or remove in a separate cleanup task. |
| P2 | `.claude/monitors` legacy monitor scripts | STALE | Scripts reference Claude CLI and older paths; not Codex `/goal monitor`. | "Monitor" searches can mislead operators. | Decide whether Claude monitors are still used. | Mark legacy or remove in a separate cleanup task. |
| P2 | Docs impact check lacks standalone validator | PARTIAL | Template and skill requirements exist; no universal docs-impact script found. | Docs-impact omissions may be missed. | Decide if this should be enforced. | Add a small validator only if omissions recur. |
| P2 | Review-board output lacks schema gate | PARTIAL | Templates exist, but no board-output validator was found. | Board decisions can drift in shape. | Decide if board output should be machine-validated. | Add JSON/schema validation for `BOARD_DECISION.json`. |
| P2 | `tenn-goal-report` has no report-state validator | PARTIAL | Skill describes state conventions; no dedicated validator was found. | Long-goal reports can become incomplete or stale. | Decide whether to enforce report fields. | Add report validator for long-goal README/state files. |
| P2 | Host systemd Tenn timers are invisible to repo operators | HOST_ONLY | Host timers exist for Tenn Codex automation; no repo ownership proof. | Orlando may rely on automation not available elsewhere. | Decide whether host automation inventory belongs in repo docs. | Keep host-only label; add host inventory report if needed. |
| P3 | Committed task ledger snapshot fallback | IMPLEMENTED | `docs/agent_registry/task_ledger/LEDGER.jsonl` contains live-exported entries for `task_ledger_current_state_refresh_v1_20260623` and validates with `agent_task_ledger.py`; `LEDGER.md` summarizes the live source. | Repo-only review now has a committed snapshot matching the live ledger, but historical PR state must still be verified from GitHub, task cards, reports, or memory. | No immediate decision for committed snapshot maintenance. | Refresh after future live ledger appends; backfill older control-plane entries only if explicitly approved. |
| P3 | `tenn-improve-codebase-architecture` visibility | UNKNOWN | Skill exists in `.agents/skills`, but visible-surface docs focus on a smaller core set. | Operators may not know whether it is core or specialist. | Decide visible versus specialist placement. | Update `SKILLS_SURFACE.md` classification. |
| P3 | Old open Prompt Lab issue appears in broad control-plane search | UNKNOWN | PR/issue search surfaced open issue #167, not core Orlando control-plane flow. | Low risk unless confused with current audit. | No immediate decision. | Leave to normal issue triage. |

## Recommended Fix Order

1. Decide the `/goal monitor` contract: host-only documented command or repo-backed wrapper/report validator.
2. Repair and verify Git hook path behavior across Tenn worktrees.
3. Refresh `SKILLS_SURFACE.md` metadata and stale report-state references.
4. Watch the Runtime Functionality Proof closeout gate for false positives before widening enforcement.
5. Decide whether to backfill older verified control-plane entries into the live task ledger, or leave historical state to GitHub/task-card/report evidence.

None of these should be mixed into this status refresh unless separately approved. This task is ledger/status current-state refresh only.
