#!/usr/bin/env bash
set -euo pipefail
if [[ -L /data && "$(readlink -f /data)" == "/mnt/tenn-nvme2/tenn/financial-engine_v2/data" ]]; then
  sudo rm /data
else
  echo "SKIP /data: missing or not the expected Tenn NVMe2 symlink"
fi
if [[ -L /reports && "$(readlink -f /reports)" == "/mnt/tenn-nvme2/tenn/financial-engine_v2/reports" ]]; then
  sudo rm /reports
else
  echo "SKIP /reports: missing or not the expected Tenn NVMe2 symlink"
fi
