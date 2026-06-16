---
name: tenn-improve-codebase-architecture
description: Tenn wrapper around the host improve-codebase-architecture skill. Report-only by default; execution requires task card, exact allowlist, Git guard, and focused validation.
---

# Tenn Improve Codebase Architecture

Use this wrapper when Orlando asks for Tenn architecture improvement,
architecture debt discovery, subsystem shape, or structural refactor planning.

Default mode is report/plan only. Do not mutate source code from architecture
discovery alone.

## Workflow

1. Run `tenn-git-guard`.
2. Read live repo architecture evidence before applying host assumptions.
3. Use the host `improve-codebase-architecture` skill for deepening analysis,
   but route outputs into Tenn report artifacts.
4. Avoid stale `.cursor/rules` assumptions unless live repo files prove they
   apply to this checkout.
5. Prefer deletion, simplification, and removal of unused layers over adding
   new layers.
6. Produce recommendations, risks, and candidate task cards.

## Execution Mode

Execution mode requires:

- explicit owner request or approved board decision
- task card
- exact scope and `allowed_files`
- focused validation plan
- `tenn-code-reviewer` before PR preparation

Stop before broad refactors, product/runtime/data/extraction mutation, schema or
prompt changes, dependency changes, host-global config, or cleanup unless those
actions are explicitly approved and allowlisted.
