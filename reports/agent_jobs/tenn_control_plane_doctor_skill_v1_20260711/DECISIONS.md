# Decisions

## First-Class Entry Point

Add a visible skill rather than a mode of `tenn-explain` or `tenn-fix` because
the operator intent is distinct and safety-sensitive: run one deterministic
read-only diagnostic and stop before repair. The entrypoint makes that boundary
discoverable without adding another implementation.

## Reuse The Backend

Keep all control-plane checks in `scripts/control_plane_doctor.py`. The skill
contains workflow, interpretation, and safety rules only. It has no `scripts/`,
`references/`, or `assets/` directory.

## Proof Boundary

A valid JSON document and matching exit code prove that the doctor ran. They do
not prove that automation, ingestion, extraction, services, or other inspected
systems produced fresh intended output. Require the `AGENTS.md` Runtime
Functionality Proof table for those broader claims.

## Output Discipline

Explain all checks, prioritize `FAIL`, `DATA_MISSING`, and `WARN`, and rank at
most three separately approved follow-up actions. Do not write durable reports
for ordinary invocation unless requested or required by an active `/goal`.

## Skeptical Review

- critical findings: none
- warnings: none
- suggestion: host picker/autocomplete visibility can only be proven after a
  separately approved publication and host-skill synchronization workflow
- duplication check: passed; no bundled executable or copied doctor logic
- scope check: only the exact task-card files are intended
- safety check: the skill explicitly forbids implicit fetch/retarget and all
  remediation or protected mutation
