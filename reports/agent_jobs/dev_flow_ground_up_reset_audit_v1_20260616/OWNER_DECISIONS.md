# Owner Decisions

These need Orlando's decision before implementation or cleanup.

| Decision | Options | Recommendation |
| --- | --- | --- |
| `/diagnose` vs `/issue` | Replace diagnose, rename diagnose, or wrap diagnose. | Wrap diagnose with `/issue`; keep diagnose. |
| Add `/explain` | Host-only, repo skill, or no first-class skill. | Add repo `tenn-explain`. |
| Architecture command | Use host skill directly or Tenn wrapper. | Add Tenn wrapper around host `improve-codebase-architecture`. |
| Git Hygiene | Standalone command or backend guard. | Backend guard for every command. |
| Scribe | Keep separate or fold into state/decisions. | Fold into `STATE.md`, `DECISIONS.md`, and operator notes. |
| Auto-progress | Standalone or candidate engine. | Candidate engine inside `/issue`. |
| Generic `triage` | Use directly or deprecate. | Deprecate direct use for Tenn. |
| Host `post_apply_patch.py` | Keep broad, exempt report-only, or disable for Tenn. | Decide separately; likely exempt report-only paths. |
| Worktree cleanup | Start cleanup now or separate approved wave. | Separate approved wave only. |
| Dirty `.githooks/pre-push` in current checkout | Adopt, revert, park, or preserve. | Preserve and review in a dedicated hook task. |
