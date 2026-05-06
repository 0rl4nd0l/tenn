# Remaining Gaps

No high-risk blocker remains for G008/G009 in the Cockpit chat/API paths covered
by this patch.

Known remaining gaps:

- Legacy `/api/chat` and non-Cockpit direct response envelopes were not redesigned.
- QueryOrchestrator direct-result envelope taxonomy remains a separate broader
  task; this patch handles emitted evidence/source metadata at the Cockpit API
  boundary.
- Deep research internal per-subsource failure accounting is still limited; this
  patch surfaces failed/degraded final deep-research state.
- Textual/local TUI source rendering was not changed.
- Cockpit source drawer UI was not changed because existing components already
  consume the metadata fields.
- Broader selectors still surface unrelated SQLite invariant failures and
  unrelated subagent event-loop failures.

Unrelated dirty files intentionally not touched:

- Cockpit UI files under `cockpit-ui/components/cockpit/...`
- `tenn_prompt_contracts_response_guidelines.zip`
