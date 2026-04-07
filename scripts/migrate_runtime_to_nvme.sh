#!/usr/bin/env bash
set -euo pipefail

SRC_ROOT="/mnt/sdb2/home/l4nd0/tenn"
DST_ROOT="/mnt/nvme/tenn"
SRC_DATA="${SRC_ROOT}/financial-engine_v2/data"
SRC_MODELS="${SRC_ROOT}/models"
DST_DATA="${DST_ROOT}/runtime-data"
DST_MODELS="${DST_ROOT}/models"

echo "[migrate-runtime] source data:   ${SRC_DATA}"
echo "[migrate-runtime] source models: ${SRC_MODELS}"
echo "[migrate-runtime] target data:   ${DST_DATA}"
echo "[migrate-runtime] target models: ${DST_MODELS}"

mkdir -p "${DST_DATA}" "${DST_MODELS}"

echo "[migrate-runtime] syncing runtime data..."
rsync -aHAX --info=progress2 "${SRC_DATA}/" "${DST_DATA}/"

echo "[migrate-runtime] syncing gguf models..."
rsync -aHAX --info=progress2 "${SRC_MODELS}/" "${DST_MODELS}/"

echo "[migrate-runtime] validating expected targets..."
test -d "${DST_DATA}/asx/docs"
test -f "${DST_MODELS}/qwen2.5-14b-instruct-q4_k_m.gguf"

echo "[migrate-runtime] complete"
echo "[migrate-runtime] next checks:"
echo "  df -h ${DST_ROOT}"
echo "  ls -lh ${DST_MODELS}"
echo "  test -d ${DST_DATA}/asx/docs && echo docs_ok"
echo "  grep -E 'DATA_ROOT|DOCS_ROOT|DATABASE_URL' ${SRC_ROOT}/financial-engine_v2/.env.local"
