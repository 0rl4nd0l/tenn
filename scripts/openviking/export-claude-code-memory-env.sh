#!/usr/bin/env bash
# Source this file before launching Claude Code to enable persistent dev-session memory.
# Usage:  source scripts/openviking/export-claude-code-memory-env.sh
#         # then launch: claude  (or your IDE integration)
#
# First-time setup:
#   cp financial-engine_v2/config/openviking/claude-code.ov.conf.example \
#      ~/.openviking/claude-code.ov.conf
#   # Edit ~/.openviking/claude-code.ov.conf — set vlm.model and api_base to match
#   # your running llama.cpp instance (default: http://127.0.0.1:8001/v1).
#   # Workspace is isolated from cockpit: ~/.openviking/workspaces/claude-code
export OPENVIKING_CONFIG_FILE="${HOME}/.openviking/claude-code.ov.conf"
echo "[openviking] claude-code workspace: ${OPENVIKING_CONFIG_FILE}"
