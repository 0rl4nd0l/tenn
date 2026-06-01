# Patch Recommendations

## Recommended Follow-Up Patch

Create a narrow safe-extension docs/control-plane patch for #78 or a child issue
with this write scope:

- `AGENTS.md`
- `CODEX.md`
- `GEMINI.md`
- `docs/process/github_issue_system_protocol.md`
- possibly `scripts/agent_job_contract.py` and focused tests, only if the chosen
  resolution is to expand task-card lane validation instead of documenting a
  label-to-lane mapping.

## Patch Items

1. Resolve lane vocabulary mismatch.
   - Option A: extend task-card lanes to include Repo Hygiene, Runtime, and
     Cockpit, with focused validator tests.
   - Option B: keep six architecture lanes and add an explicit GitHub-label to
     task-card-lane mapping table.
   - Do not leave the current implicit proxy-lane workaround undocumented.

2. Make `docs/claude/STATE.md` updates conditional.
   - Keep STATE as a useful current-state tracker.
   - Clarify that agents must not write it when the task card does not allow it
     or another active job owns it; they should report `DATA_MISSING` or a
     follow-up instead.

3. Align graphify guidance.
   - Update `GEMINI.md` to match AGENTS/CLAUDE: read graphify reports when
     present; do not run `graphify update .` after every code edit; refresh at
     most once per day or on explicit request.

4. Clarify default-load order without adding more default content.
   - Agent-specific identity first for identity only.
   - Shared AGENTS/CLAUDE/SYSTEM_CONTRACT rules govern repo behavior.
   - `SYSTEM_CONTRACT.md` wins conflicts.

5. Document hook non-equivalence.
   - Claude, Codex, and Gemini hooks differ by platform.
   - Do not copy hook behaviors across tools unless a task explicitly updates
     that tool's config and docs together.

6. Replace stale hardcoded Codex skill inventory in AGENTS.md.
   - Prefer session-provided skill discovery and the active runtime skill list.
   - Keep repo-local skill paths only where files exist, or describe them as
     examples that may be `DATA_MISSING` in a given checkout.

7. Normalize mandatory command examples.
   - Use `python3` for `scripts/agent_job_*` examples where no venv is assumed.
   - Keep venv-specific `python` only inside explicitly activated venv examples.

## Explicit Non-Recommendations

- Do not broadly rewrite `AGENTS.md` or `CLAUDE.md` in one patch.
- Do not move task-specific skill content into default-loaded files.
- Do not close #78 from this audit-only report alone.
- Do not mutate `docs/claude/STATE.md` while the active Financial Truth job owns
  it in the shared registry.
- Do not refresh graphify unless explicitly requested or separately task-carded.

## Follow-Up Policy

This audit has `FOLLOWUP_REQUIRED`: the lane vocabulary mismatch and graphify
policy conflict are actionable. #78 should stay open, or the eventual patch PR
should link a narrower follow-up issue if only part of the patch is accepted.
