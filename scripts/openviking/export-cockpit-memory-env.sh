#!/usr/bin/env bash
# Source this file to point OpenViking at the cockpit-specific workspace.
# Usage:  source scripts/openviking/export-cockpit-memory-env.sh
#
# First-time setup:
#   cp financial-engine_v2/config/openviking/cockpit.ov.conf.example \
#      ~/.openviking/cockpit.ov.conf
#   # Edit ~/.openviking/cockpit.ov.conf — set vlm.model and api_base to match
#   # your running llama.cpp instance (default: http://127.0.0.1:8001/v1).
#   # Ollama embeddings (nomic-embed-text) are used for semantic memory search.
export OPENVIKING_CONFIG_FILE="${HOME}/.openviking/cockpit.ov.conf"
echo "[openviking] cockpit workspace: ${OPENVIKING_CONFIG_FILE}"
