# Dev Flow Skills Bloat Audit V1

State: DONE_WITH_RISK

## Objective

Run a report-only audit of Tenn skills, rules, hooks, templates, docs, and
development-flow ergonomics. Decide what should be kept, merged, renamed,
rehomed, deprecated, or trimmed later. Design docs freshness and model/subagent
routing additions for a later implementation PR.

## Executive Verdict

Tenn does not need more user-facing skills. It needs a smaller operator command
surface and a stronger backend routing layer.

Recommended daily command set for Orlando:

1. `/issue` for turning vague work into an executable packet.
2. `/fix` for one approved bounded implementation.
3. `/review-board` for high-risk decisions, merge readiness, or owner-boundary
   calls.
4. `/explain` for plain-language status and architecture explanations.
5. `/goal` for long report-producing or multi-step work.
6. `/handoff` or `/save` only after a repo-native handoff convention exists.

Everything else should be backend-only, wrapped, or explicitly domain-specialty.

## Current Evidence

- Repo: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Branch: `control-plane/dev-flow-agent-task-ledger-v1-20260616`
- HEAD at audit start after the YAML fix commit:
  `137535b81a5b60d1f94ca630605caadccc4e1b99`
- Upstream: `origin/control-plane/dev-flow-agent-task-ledger-v1-20260616`
- Canonical base fetched:
  `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Current branch status before report edits: clean, ahead of upstream by 2
  local commits.
- Selected comparison base: `origin/migration/clean-runtime-baseline-reconstruct-v1`.
- Merge-base with canonical base: `a74e88a422eb5390c399893ee97832407a06d9e5`.
- Read-only registry: `ok: true`, `read_only: true`, `lock_acquired: false`,
  `active_jobs: []`.
- Live task ledger: `DATA_MISSING`.
- Committed task ledger JSONL: `DATA_MISSING`.

## Duplicate-Work Classification

Classification: `WARNING_PROCEED_REPORT_ONLY`.

No exact active duplicate for this skills-bloat audit was found in read-only
GitHub PR/issue checks, task-card/report searches, branch names, or worktree
names.

Adjacent work exists:

- `/home/l4nd0/tenn-agent-ledger-runtime-handoff-v1-20260617` is an active-looking
  dirty sibling worktree for Agent Task Ledger runtime and handoff workflow.
  This audit treats its files as `OWNER_BOUNDARY` and does not edit them.
- `reports/agent_jobs/agent_flow_combined_audit_v1_20260616/COMBINED_AUDIT.md`
  already identified broad agent-flow bloat. This report extends that work into
  a per-skill inventory, operator command set, docs freshness design, and
  model/subagent routing design.

## Main Findings

1. The useful Tenn core is clear: task cards, `.agents/skills`, read-only
   registry, task ledger, exact allowed files, report bundles, and owner gates.
2. The operator-facing surface is too large. Several skills should be backend
   guards or internal phases, not commands Orlando has to choose manually.
3. Host skills are valuable but should remain host-only unless wrapped by a
   Tenn skill that injects task-card, registry, issue-tracker, and forbidden
   surface rules.
4. Legacy `.codex/skills/cockpit-flag-orchestrator` is powerful but unsafe as a
   default active Codex surface because it assumes service/API/commit/resolve
   behavior that conflicts with current report-first gates.
5. `tenn-git-guard` and `tenn-git-hygiene` are the highest-overlap pair. Keep
   `tenn-git-guard` as the backend preflight. Convert most `tenn-git-hygiene`
   content into reference/autonomy templates unless Orlando explicitly asks for
   cleanup planning.
6. `tenn-auto-progress` should stop being a day-to-day visible skill. Its issue
   ranking logic belongs inside `/issue` as an internal candidate-ranking phase.
7. `tenn-frame-design` is useful, but the durable value is the artifact schema.
   Rehome most of it into `docs/dev_flow/templates/FRAME.md`,
   `OPERATOR_NOTES.md`, and an optional `/goal` frame mode.
8. Docs freshness is not yet a first-class closeout gate. `/fix`,
   `tenn-code-reviewer`, and handoff should all record docs impact.
9. Model/subagent routing is implicit. Task cards, worker briefs, and review
   board decisions should record task tier and who is allowed to make final
   decisions.

## Report Files

- `SKILLS_INVENTORY.md`
- `SKILL_RECOMMENDATIONS.md`
- `OVERLAPS_AND_BLOAT.md`
- `USER_FACING_COMMAND_SET.md`
- `BACKEND_GUARDRAILS.md`
- `DOCS_FRESHNESS_DESIGN.md`
- `MODEL_ROUTING_DESIGN.md`
- `SUBAGENT_DELEGATION_DESIGN.md`
- `HOST_SKILLS_REVIEW.md`
- `OWNER_DECISIONS.md`
- `NEXT_IMPLEMENTATION_PROMPT.md`
- `VALIDATION.md`

## Files Touched

- `docs/agent_tasks/dev_flow_skills_bloat_audit_v1_20260617.md`
- `reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/*`

## Files Intentionally Not Touched

- `.agents/skills/**`
- `.codex/skills/**`
- `.codex/hooks.json`
- `scripts/agent_job_hook.py`
- `scripts/agent_job_contract.py`
- `scripts/agent_job_registry.py`
- `scripts/agent_task_ledger.py`
- `docs/dev_flow/templates/**`
- `docs/agent_registry/**`
- `AGENTS.md`
- product/runtime/data/extraction/count-24 paths
- host-global files under `/home/l4nd0/.codex` or `/home/l4nd0/.agents`

## Unsafe Actions Avoided

- No skill edits, deletes, renames, or rehomes.
- No hook, script, template, runtime, product, extraction, data, DB, Qdrant,
  Redis, news, memory, source-PDF, gold-label, prompt, service, model, GPU, or
  count-24 mutation.
- No host-global mutation.
- No GitHub write.
- No branch/worktree cleanup, merge, rebase, reset, stash, cherry-pick, prune,
  push, or force-push.

## Next Action

Use `NEXT_IMPLEMENTATION_PROMPT.md` after the active ledger-runtime/handoff
work is either merged, parked, or explicitly classified. The next PR should be a
small control-plane implementation PR, not another broad audit.

## Remaining Risk

- The live and committed task ledger files were `DATA_MISSING` in this checkout.
- A sibling worktree is actively changing Agent Task Ledger runtime and handoff
  surfaces; next implementation must re-check and avoid overwriting it.
- Plugin-cache skills were counted and classified as plugin-domain only, not
  expanded into Tenn operator-facing rows because they are not repo or host
  Tenn workflow truth.
