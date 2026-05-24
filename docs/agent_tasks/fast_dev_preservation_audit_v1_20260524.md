---
job_id: fast_dev_preservation_audit_v1_20260524
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/fast_dev_preservation_audit_v1_20260524.md
  - reports/agent_jobs/fast_dev_preservation_audit_v1_20260524/README.md
  - reports/agent_jobs/fast_dev_preservation_audit_v1_20260524/status.json
  - reports/agent_jobs/fast_dev_preservation_audit_v1_20260524/validation.json
  - reports/agent_jobs/fast_dev_preservation_audit_v1_20260524/diff-check.json
approval_required: false
allow_audit_code_changes: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/fast_dev_preservation_audit_v1_20260524
mutation_mode: audit_only
production_data_access: false
---

# Fast Dev Preservation Audit

Audit `/home/l4nd0/tenn-fast-dev-storage-v1` tracked and untracked work before any runtime topology rebind away from fast-dev.

## Scope

- Compare canonical `/home/l4nd0/tenn` to `/home/l4nd0/tenn-fast-dev-storage-v1`.
- Classify tracked and untracked fast-dev files by lane and preservation status.
- Produce a report-only safe integration/discard plan.

## Hard Boundaries

- Do not edit fast-dev files.
- Do not stage, commit, delete, move, archive, or clean fast-dev files.
- Do not rebind Docker, systemd, cron, symlinks, data mounts, runtime services, models, memory, parser routing, financial truth, or production data.
- Stop if the canonical path does not resolve to the expected NVMe clean baseline, fast-dev is missing, registry overlap blocks the lane, or classification would require runtime or production DB mutation.
