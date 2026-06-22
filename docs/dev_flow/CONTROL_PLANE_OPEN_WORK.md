# Control Plane Open Work Register

Status: control-plane follow-up after PR #383.

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
| P1 | Task ledger current-state drift | PARTIAL | Live ledger validates but contains a stale PR #380 `pr_opened` entry; current GitHub says PR #380 merged. | "What next?" flows can reason from stale ledger state. | Decide whether ledger should be append-only corrected or regenerated. | Add a ledger status-refresh entry and export a current committed summary. |
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
| P3 | Committed task ledger snapshot is empty | STALE | `agent_task_ledger.py validate` reported live ledger entries and zero committed snapshot entries. | Historical repo-only review is weaker than live registry review. | Decide whether committed snapshots should be maintained. | Export a current summary in a dedicated ledger task. |
| P3 | `tenn-improve-codebase-architecture` visibility | UNKNOWN | Skill exists in `.agents/skills`, but visible-surface docs focus on a smaller core set. | Operators may not know whether it is core or specialist. | Decide visible versus specialist placement. | Update `SKILLS_SURFACE.md` classification. |
| P3 | Old open Prompt Lab issue appears in broad control-plane search | UNKNOWN | PR/issue search surfaced open issue #167, not core Orlando control-plane flow. | Low risk unless confused with current audit. | No immediate decision. | Leave to normal issue triage. |

## Recommended Fix Order

1. Refresh the task ledger for PR #380/#382/#383 state and export a current summary.
2. Decide the `/goal monitor` contract: host-only documented command or repo-backed wrapper/report validator.
3. Repair and verify Git hook path behavior across Tenn worktrees.
4. Refresh `SKILLS_SURFACE.md` metadata and stale report-state references.
5. Watch the Runtime Functionality Proof closeout gate for false positives before widening enforcement.

None of these should be mixed into this audit unless separately approved. This audit is docs/report consolidation only.
