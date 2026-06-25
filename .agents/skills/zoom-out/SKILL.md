---
name: zoom-out
description: Tenn zoom-out mode for stepping up one abstraction layer and mapping relevant modules, callers, evidence, risks, and next actions.
---

# Zoom Out

Use this when Orlando asks to zoom out, asks whether the current work is solving
the right problem, or needs a higher-level map before continuing.

## Workflow

1. State the current local problem in one sentence.
2. Step up one layer: name the broader Tenn workflow, subsystem, or operator
   control-plane concern.
3. Map relevant files, modules, callers, reports, task cards, branches, PRs, and
   docs using Tenn domain language.
4. Separate `VERIFIED`, `INFERRED`, `UNKNOWN`, and `DATA_MISSING`.
5. Identify the highest-leverage next action and the stop condition.

For code architecture, use `tenn-improve-codebase-architecture` when the ask is
about module depth, seams, adapters, locality, leverage, or refactoring.
