# Remaining Gaps

- Legacy `/api/chat` taxonomy audit remains open. This task explicitly did not touch legacy `/api/chat`.
- The web source drawer/source UI was not touched. This task only changed local Textual `/sources` display.
- `financial-engine_v2/cockpit/core/sources.py` still contains the legacy generic formatter. It remains safe for this task because `chat.py` now prefers envelope rendering for `/sources list/show`; the legacy formatter is only used with explicit non-verified fallback wording.
- Task-card registry claim was blocked by unrelated dirty files in the shared worktree. No active job lock was present, but the claim could not be written.
- DATA_MISSING: architecture-check `.cursor/rules/*` files referenced by the skill were unavailable in this checkout; `SYSTEM_CONTRACT.md` and `21_cockpit_client_contract.md` were used instead.

No remaining blocker for G003 Textual `/sources list` v1 behavior was found after focused validation.
