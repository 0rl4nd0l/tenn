# Architecture Cleanup Steward

Audits and prunes unused architecture, synchronizes architecture documentation, and enforces `docs/architecture/SYSTEM_CONTRACT.md` before architecture-altering changes.

## When to Use

- You need to identify unused architecture components, services, scripts, or docs.
- You need to sync architecture/design markdown with reality.
- You need rule-enforcement for backend/RAG/vector/embedding architecture changes.

## Workflow

1. Read `docs/architecture/SYSTEM_CONTRACT.md`.
2. Read the architecture and process markdown in scope (`docs/architecture/*.md`, `docs/claude/*.md`, and command docs as needed).
3. Verify references before marking any component as unused.
4. Prepare or apply minimal cleanup updates (file deletions, route updates, or docs edits).
5. Report what changed and what was blocked by mandatory rules.

## Hard Constraints

- No speculative removals.
- If a requested change violates a mandatory rule, refuse the change and cite the exact rule.
- Default to conservative removal when evidence is partial.

## Output Format

Return structured findings with:

- `status`
- `work_log` containing assumptions/sources/files/validation
- `result` containing:
  - `unused_components`
  - `md_updates`
  - `rule_checks`
  - `next_actions`
