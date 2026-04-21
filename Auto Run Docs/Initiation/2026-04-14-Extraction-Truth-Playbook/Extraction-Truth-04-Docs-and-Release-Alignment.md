# Phase 04: Docs and Release Alignment

This phase removes the most damaging documentation drift after the product work is finished. It updates only the docs and release artifacts that are now provably stale, ties them to the implemented extraction-eval-review workflow, and leaves the repo with an accurate operator and engineering record of what was actually shipped in this sprint.

## Tasks

- [ ] Find and rank the stale docs that conflict with the shipped extraction state:
  - Search the repo for outdated claims about extraction status, multipass availability, evaluation coverage, Cockpit verification capabilities, and web-versus-future UI language before editing anything.
  - Prioritize files that users or future agents will trust first: `README.md`, `docs/architecture/01_system_overview.md`, `docs/architecture/12_evaluation_and_drift_monitoring.md`, `docs/architecture/14_roadmap_and_modules.md`, `docs/claude/STATE.md`, project sprint snapshots, and any extraction-specific runbooks changed by the earlier phases.
  - Write `docs/ops/extraction-truth/phase-04-doc-drift-audit.md` with YAML front matter (`type: analysis`, `tags: [docs, extraction, release]`) listing each stale claim, the code or artifact that disproves it, and the exact file that needs updating.

- [ ] Update the primary architecture and operator docs to match shipped behavior:
  - Reuse existing doc structure and wording patterns instead of inventing a new documentation taxonomy.
  - Align the docs with what now exists in code: current extraction entrypoints, synthetic and real-gold eval lanes, backend-owned verification and review surfaces, non-AUD truth handling, and any canonical report locations created during earlier phases.
  - Keep the system contract intact in prose: backend remains authoritative, Cockpit remains a client and orchestration layer, and extraction remains explicit-value only.

- [ ] Publish durable structured release artifacts for future reuse:
  - Write `docs/ops/extraction-truth/release-state.md` with YAML front matter (`type: report`, `related: ['[[phase-01-prototype-report]]', '[[phase-02-accuracy-report]]', '[[phase-03-review-workflow]]']`) summarizing the final shipped state, validation commands, remaining known risks, and where to find generated `reports/` outputs.
  - If the previous phases produced benchmark or eval summaries outside docs, link them with wiki-links instead of duplicating raw data.
  - Keep artifacts concise and operational; do not turn this phase into a narrative postmortem.

- [ ] Run a final release-readiness validation sweep:
  - Re-run the targeted test suites and the key prototype commands that now define the supported extraction workflow.
  - Verify that the canonical backend boot command, the limited real-gold eval path, and the review-session workflow still work after the doc and contract-alignment edits.
  - Confirm that any docs pointing to commands, endpoints, or report paths now match the implementation exactly.

- [ ] Package the sprint milestone cleanly:
  - Ensure the updated docs reference the correct artifacts, trust semantics, and contract boundaries without promising unbuilt FX conversion, broader Cockpit redesign, or analysis features outside this sprint.
  - If the release-readiness checks pass, create the required milestone commit using the repo’s `milestone(<subsystem>): ...` format and include the tested evidence from the final sweep.
