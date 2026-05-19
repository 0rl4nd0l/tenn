#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1"
REPORT_DIR="$REPO_ROOT/reports/agent_jobs/nvme_full_system_functionality_v1_20260518"
APPLY_SCRIPT="$REPORT_DIR/host_alias_apply_commands.sh"
VERIFY_SCRIPT="$REPO_ROOT/scripts/verify_nvme_runtime_endpoints.sh"
STAMP="$(date --iso-8601=seconds)"
RESULT="$REPORT_DIR/post_sudo_alias_completion.txt"
STATUS="$REPORT_DIR/status.json"

cd "$REPO_ROOT"

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: run with sudo so /data and /reports can be created safely." >&2
  echo "Example: sudo $0" >&2
  exit 2
fi

{
  echo "### post_sudo_alias_completion"
  echo "$STAMP"
  echo "## applying host aliases"
  bash "$APPLY_SCRIPT"
  echo "## alias resolutions"
  readlink -f /data || true
  readlink -f /reports || true
  ls -ld /data /reports || true
  echo "## endpoint verifier"
  if bash "$VERIFY_SCRIPT"; then
    echo "POST_SUDO_COMPLETION_OK=1"
  else
    echo "POST_SUDO_COMPLETION_OK=0"
    exit 1
  fi
} | tee "$RESULT"

if grep -q 'NVME_RUNTIME_ENDPOINTS_OK=1' "$RESULT"; then
  cat > "$STATUS" <<JSON
{
  "job_id": "nvme_full_system_functionality_v1_20260518",
  "verdict": "IMPLEMENTED_AND_VALIDATED_AFTER_SUDO",
  "goal_complete": true,
  "completion_artifact": "reports/agent_jobs/nvme_full_system_functionality_v1_20260518/post_sudo_alias_completion.txt",
  "runtime_root": "/home/l4nd0/tenn-runtime",
  "runtime_root_resolved": "/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1",
  "data_root": "/mnt/tenn-nvme2/tenn/financial-engine_v2/data",
  "reports_root": "/mnt/tenn-nvme2/tenn/financial-engine_v2/reports",
  "models_root": "/mnt/tenn-nvme2/tenn/models",
  "host_aliases": {
    "/data": "/mnt/tenn-nvme2/tenn/financial-engine_v2/data",
    "/reports": "/mnt/tenn-nvme2/tenn/financial-engine_v2/reports"
  },
  "verifier_result": "NVME_RUNTIME_ENDPOINTS_OK=1",
  "updated_at": "$STAMP"
}
JSON
fi
