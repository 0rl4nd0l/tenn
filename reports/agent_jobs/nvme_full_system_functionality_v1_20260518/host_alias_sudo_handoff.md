# Host-root NVMe2 alias sudo handoff

The remaining incomplete objective item is host-root aliases for `/data` and `/reports`.

Apply and verify:

```bash
/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/reports/agent_jobs/nvme_full_system_functionality_v1_20260518/host_alias_apply_commands.sh
```

Expected final verifier line:

```text
NVME_RUNTIME_ENDPOINTS_OK=1
```

Rollback if needed:

```bash
/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/reports/agent_jobs/nvme_full_system_functionality_v1_20260518/host_alias_rollback_commands.sh
```

Safety notes:

- The apply helper refuses to overwrite existing non-symlinks.
- The rollback helper removes `/data` and `/reports` only if each resolves to the expected Tenn NVMe2 target.
- Docker/container `/data` and `/reports` are already mapped to NVMe2; this is only for host-root aliases.
