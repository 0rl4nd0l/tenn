# Cockpit Prompt Lab Operator Gate

Issue: #147
Lane: Reporting
Mode: SAFE EXTENSION
Worktree: `/home/l4nd0/tenn-reporting-prompt-lab-operator-gate-v1-20260601`
Branch: `safe/reporting-prompt-lab-operator-gate-v1-20260601`

## Summary

This job gates Cockpit Prompt Lab route inventory, prompt preview, and LLM
dry-run access behind explicit operator access. Normal Settings does not render
Prompt Lab by default. The backend also rejects Prompt Lab requests unless
`COCKPIT_PROMPT_LAB_OPERATOR_ACCESS` is enabled and the request includes
`X-Cockpit-Prompt-Lab-Intent: inspect-prompts`.

No production data, memory store, retrieval, financial truth, prompt semantics,
GPU/runtime configuration, or live LLM dry-run was changed.

## Evidence

- Backend disabled-by-default route access returns HTTP 403.
- Backend dry-run without the operator intent header returns HTTP 403 before
  reaching the fake LLM client.
- Existing Prompt Lab preview and dry-run behavior still passes when backend
  operator access and intent are present.
- Normal Settings hides the Prompt Lab tab when
  `NEXT_PUBLIC_COCKPIT_PROMPT_LAB_OPERATOR_ACCESS` is unset.
- Operator UI mode shows Prompt Lab and sends the Prompt Lab intent header for
  route inventory, preview, and dry-run requests.

See `operator_gate_evidence.md` and `validation.json` for command-level
validation.
