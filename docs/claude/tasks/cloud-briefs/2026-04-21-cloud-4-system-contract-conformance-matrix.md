# Cloud-4: System-Contract Conformance Matrix Update

## Goal

Update the backend and cockpit conformance matrix against `SYSTEM_CONTRACT.md`, with explicit unresolved risks and evidence links.

## Scope

- Read:
  - `docs/architecture/SYSTEM_CONTRACT.md`
  - `docs/architecture/21_cockpit_client_contract.md`
  - `docs/architecture/19_backend_api_surface.md`
  - `docs/claude/STATE.md`
- Write:
  - Conformance matrix document update only.

## Invariants (Do Not Break)

- No contract weakening language.
- No claims without current-turn evidence.
- Do not mark unresolved surfaces as compliant.

## Validation

```bash
bash scripts/check_markdown_hygiene.sh
```

## Deliverable

- Updated matrix with:
  - contract clause
  - implemented surface
  - evidence (file paths and tests)
  - status (`compliant`, `partial`, `non-compliant`)
- Short prioritized list of highest-risk open contract gaps.
