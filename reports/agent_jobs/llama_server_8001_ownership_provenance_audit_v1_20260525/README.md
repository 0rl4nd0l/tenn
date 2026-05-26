# Llama Server 8001 Ownership Provenance Audit

Issue: #82

Lane: Runtime / Reporting
Mode: audit_only
Decision: completed audit-only with follow-up #113

## Summary

The audit confirmed `llama-server` is listening on `0.0.0.0:8001`, with a
router child on an ephemeral localhost port. The parent process has PPID 996
(`systemd --user`), but the visible `llama-cpp-router.service` and
`llama-cpp-qwen25.service` units are inactive/dead with `MainPID=0`. Therefore
the audit reconciles current process/service evidence but does not prove the
definitive launcher beyond the parent process relationship.

No runtime process, service, GPU, model, or config mutation was performed.

## Outcome

Close gate: `COMPLETED_AUDIT_ONLY_WITH_FOLLOWUPS`

Root-cause classification: `AUDIT_ONLY_NO_REMEDIATION`, `NEEDS_FOLLOWUP`,
`READY_TO_CLOSE` as audit-only.

Follow-up: #113 tracks the remaining owner-evidence gap.
