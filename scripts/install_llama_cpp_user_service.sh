#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="llama-cpp-router.service"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_FILE="${ROOT_DIR}/systemd/${SERVICE_NAME}"
DST_DIR="${HOME}/.config/systemd/user"
DST_FILE="${DST_DIR}/${SERVICE_NAME}"
ENV_DIR="${HOME}/.config/tenn"
ENV_FILE="${ENV_DIR}/llama-server.env"

mkdir -p "${DST_DIR}" "${ENV_DIR}"
cp "${SRC_FILE}" "${DST_FILE}"

if [[ ! -f "${ENV_FILE}" ]]; then
  cat > "${ENV_FILE}" <<'EOF'
# Optional overrides for scripts/run_llama_server.sh
# LLAMA_SERVER_MODEL=/absolute/path/to/model.gguf
# LLAMA_SERVER_ALIAS=qwen2.5-coder-14b
# LLAMA_SERVER_API_KEY=local-openai-key
# LLAMA_SERVER_PROFILE=interactive
# valid profiles: interactive, balanced, throughput
# LLAMA_SERVER_HOST=127.0.0.1
# LLAMA_SERVER_PORT=8001
# LLAMA_SERVER_MMAP=0
EOF
fi

systemctl --user daemon-reload
systemctl --user enable "${SERVICE_NAME}"
systemctl --user restart "${SERVICE_NAME}"
systemctl --user status "${SERVICE_NAME}" --no-pager -n 30
