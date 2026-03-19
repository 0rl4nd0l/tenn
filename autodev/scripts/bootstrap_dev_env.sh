#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv-autodev"

python3 -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip
python -m pip install -r "${ROOT_DIR}/autodev/docker/requirements-dev.txt"

echo ""
echo "Autodev dev environment bootstrapped."
echo "Activate with: source ${VENV_DIR}/bin/activate"
echo "Run once with: python -m autodev.runtime.autodev_loop --once"

