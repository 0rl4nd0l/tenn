# Next Implementation Prompt

Use this after the active Agent Task Ledger runtime/handoff worktree is merged,
parked, or explicitly classified.

```text
/goal Implement the first narrow dev-flow skills-bloat cleanup PR.

Context:
Use the report bundle at
reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/.
Another agent may have recently implemented Agent Task Ledger runtime and
handoff workflow. Re-check that work first and do not overwrite it.

Objective:
Make the Tenn dev-flow easier for future agents by shrinking the operator-facing
skill surface and adding docs/model routing fields. This is control-plane docs,
skill, template, and optional validation-script work only.

Required preflight:
1. Fetch origin/migration/clean-runtime-baseline-reconstruct-v1.
2. Verify repo, branch, HEAD, upstream, dirty status, and canonical base.
3. Run registry read-only check.
4. Check live and committed task ledger.
5. Search task cards, reports, worktrees, branches, open/closed PRs, and issues
   for active work touching skills-bloat, docs freshness, model routing,
   subagent routing, handoff, and task ledger runtime.
6. If active overlapping work exists, classify ADOPT/CONTINUE/PRESERVE/
   SUPERSEDED/OWNER_BOUNDARY/UNKNOWN before editing.

Allowed scope:
- Create a task card for the implementation.
- Update only exact allowlisted control-plane files.
- Prefer a clean sibling worktree from current
  origin/migration/clean-runtime-baseline-reconstruct-v1 if the shared checkout
  is dirty or stale.

Implementation slice:
1. Update docs/agents/skill-registry.md with:
   - six-command daily operator surface
   - backend-only skill list
   - plugin skills are explicit-domain only
   - .codex/skills remains legacy/custom unless task-card-grandfathered
2. Update repo skills narrowly:
   - tenn-issue: owns auto-progress candidate ranking internally
   - tenn-goal-report or future handoff wrapper: requires Docs Impact Check
   - tenn-code-reviewer: reviews docs impact and model/subagent fields
   - tenn-worker: records task_tier/model_tier/decision_limit
   - tenn-git-guard: stays canonical backend preflight
3. Add or update templates:
   - FRAME.md if frame-design is rehomed
   - OPERATOR_NOTES.md if still needed
   - HANDOFF.md only if not already created by the ledger/handoff work
   - add docs_impact and task_tier fields to relevant templates
4. Do not implement docs_impact.py unless Orlando explicitly approves that
   script in this run. If not implemented, create a DOCS_FOLLOWUP section.

Hard boundaries:
- Do not touch product/runtime/data/extraction/count-24.
- Do not mutate host-global files.
- Do not delete or rename skills.
- Do not edit .codex/skills/cockpit-flag-orchestrator except to document legacy
  status elsewhere.
- Do not clean branches/worktrees.
- Do not mutate GitHub unless explicitly approved after validation.

Validation:
- task-card validate
- registry list-active read-only
- parse changed SKILL.md frontmatter/H1
- JSON validation for changed JSON templates
- git diff --check
- task-card check-diff --no-write-report
- changed-path guard
- product/runtime/data/extraction/count-24 guard
- host-global guard
- final status

Definition of done:
- Operator-facing command set is documented.
- Backend-only skill list is documented.
- Auto-progress/frame/git-hygiene overlap is reduced in descriptions or docs.
- Docs Impact Check fields exist in the right templates/skills.
- Model/subagent routing fields exist in the right templates/skills.
- Next follow-up is implementation, PR/merge, or owner decision, not another
  broad audit.
```
