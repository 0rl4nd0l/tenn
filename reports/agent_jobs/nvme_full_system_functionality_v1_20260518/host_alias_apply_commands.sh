#!/usr/bin/env bash
set -euo pipefail
cd /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1
sudo ./scripts/setup_nvme2_host_aliases.sh
./scripts/verify_nvme_runtime_endpoints.sh
