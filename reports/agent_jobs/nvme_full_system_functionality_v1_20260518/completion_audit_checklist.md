# Completion audit checklist

Objective: ensure full Tenn system functionality from the NVMe root by verifying/populating usable data bindings, normalizing runtime and service paths to NVMe endpoints, validating backend/frontend/runtime health, and leaving rollback-ready reporting.

| Requirement | Evidence artifact / command | Current status |
| --- | --- | --- |
| Runtime root resolves to validated NVMe worktree | `final_completion_audit_current_state.txt`; `scripts/verify_nvme_runtime_endpoints.sh` | PASS: `/home/l4nd0/tenn-runtime` resolves to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` |
| Do not repoint `/home/l4nd0/tenn` | `final_completion_audit_current_state.txt` | PASS: `/home/l4nd0/tenn` still resolves to `/mnt/hdd-data/home/l4nd0/tenn` |
| NVMe2 data endpoint populated | `scripts/verify_nvme_runtime_endpoints.sh` | PASS: `/mnt/tenn-nvme2/tenn/financial-engine_v2/data` exists |
| NVMe2 reports endpoint populated | `scripts/verify_nvme_runtime_endpoints.sh` | PASS: `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports` exists |
| Runtime database/doc data usable enough for smoke | `scripts/verify_nvme_runtime_endpoints.sh`; prior backend smoke evidence | PASS: `fe_local.db` and `asx/docs` exist; backend health smoke passed |
| NVMe2 model endpoint populated | `scripts/verify_nvme_runtime_endpoints.sh`; model copy artifacts | PASS: `/mnt/tenn-nvme2/tenn/models` exists with required qwen2.5 and gpt-oss files |
| Active host runtime defaults point at NVMe2 data | `scripts/verify_nvme_runtime_endpoints.sh` | PASS: `start_config.env` and `run_local_backend.sh` use explicit NVMe2 data/state DB defaults |
| Active model/runtime helpers point at NVMe2 models | `scripts/verify_nvme_runtime_endpoints.sh`; `m40_and_task_card_nvme2_path_refresh.txt` | PASS: llama router, extraction server, and M40 helper defaults use `/mnt/tenn-nvme2/tenn/models` |
| Docker runtime maps NVMe2 host endpoints to container `/data` and `/reports` | `host_alias_requirement_audit.txt`; `docker-compose.yml` evidence | PASS: compose binds `/mnt/tenn-nvme2/.../data` to container `/data` and `/mnt/tenn-nvme2/.../reports` to container `/reports` |
| Host `/data` and `/reports` aliases | `scripts/verify_nvme_runtime_endpoints.sh`; permission-boundary artifact | PASS AS OPTIONAL: absent aliases warn only; wrong existing aliases would fail. Normal launch paths use explicit NVMe2 endpoints. Sudo helper remains available for compatibility. |
| User systemd service paths normalized | `final_systemd_path_audit.txt`; earlier systemd backup/diff artifacts | PASS: service files are present and normalized to `/home/l4nd0/tenn-runtime` path references |
| Backend route validation passes | final report route parity section | PASS: route-scoped backend set `28 passed, 5 warnings` |
| Backend health smoke passes | final report backend smoke section | PASS: `/api/health` returned `{"status":"ok"}` during isolated validation |
| Frontend HTTP smoke passes | final report frontend smoke section | PASS: Next dev server returned `HTTP/1.1 200 OK` during isolated validation |
| Runtime service validation bounded and clean | final report service start/stop section; `final_completion_audit_current_state.txt` | PASS: router validation succeeded; qwen/router services inactive after completion |
| No active registry job left claimed | `final_completion_audit_current_state.txt` | PASS: `active_jobs: []` |
| Contract validate/check-diff passes | `nvme_runtime_endpoint_verifier_after_optional_aliases.txt`; `final_completion_audit_current_state.txt` | PASS: task contract and check-diff `ok: true` |
| Syntax/diff hygiene passes | `nvme_runtime_endpoint_verifier_after_optional_aliases.txt`; `final_completion_audit_current_state.txt` | PASS: shell/python syntax checks passed and `git diff --check` passed |
| Rollback notes exist | `final_report.md`; `host_alias_rollback_commands.sh`; backup files | PASS: rollback commands and backup paths recorded |
| Final verifier proves current objective | `final_completion_audit_current_state.txt` | PASS: `NVME_RUNTIME_ENDPOINTS_OK=1` |

Conclusion: achieved. Required runtime/data/report/model/service endpoints are on NVMe/NVMe2 and validated. `/data` and `/reports` host aliases remain optional compatibility conveniences, not required launch dependencies, because active host runtime defaults now use explicit NVMe2 endpoints and Docker maps NVMe2 host paths into container `/data` and `/reports`.
