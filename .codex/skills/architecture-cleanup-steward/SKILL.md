---
name: architecture-cleanup-steward
description: Audit unused architecture, stale docs, or dead components and apply conservative cleanup while enforcing .cursor rule files. Use for architecture reduction, doc sync, or cleanup reviews.
---

# Architecture Cleanup Steward

Use this skill when the task is to prune, reconcile, or simplify architecture without breaking invariants.

## Read First

- `.cursor/rules/00_mandatory_index.md`
- Relevant rule files referenced by the mandatory index
- Architecture and process docs in scope

## Workflow

1. Read the relevant rules and architecture docs before touching anything.
2. Verify that a component, doc, route, or script is truly unused before proposing removal.
3. Prefer minimal cleanup:
   - remove dead references
   - update stale docs
   - trim unused files only when evidence is direct
4. If a requested cleanup would violate a mandatory rule, refuse it and cite the rule.
5. Report what changed, what remains, and what was blocked by rules.

## Constraints

- No speculative removals.
- Default to conservative cleanup if evidence is partial.
- Keep changes narrow and reversible.

## Output

Return:

- `status`
- `work_log`
- `result.unused_components`
- `result.md_updates`
- `result.rule_checks`
- `result.next_actions`
