#!/usr/bin/env bash
set -euo pipefail

script_path="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/gpu_process_guard.sh"

workdir="$(mktemp -d)"
trap 'rm -rf "${workdir}"' EXIT

cat >"${workdir}/nvidia-smi" <<'EOT'
#!/usr/bin/env bash
sleep 3
EOT
chmod +x "${workdir}/nvidia-smi"

SECONDS=0
PATH="${workdir}:${PATH}" \
  GPU_GUARD_NVIDIA_SMI_TIMEOUT_SECONDS=1 \
  "${script_path}" --check >"${workdir}/out.txt" 2>"${workdir}/err.txt" || true
runtime=${SECONDS}

grep -q "nvidia-smi query timed out" "${workdir}/err.txt" || {
  echo "ASSERT FAIL: expected nvidia-smi timeout warning" >&2
  exit 1
}

if (( runtime > 7 )); then
  echo "ASSERT FAIL: guard did not complete within expected timeout guard window (runtime=${runtime}s)" >&2
  exit 1
fi

echo "PASS: gpu_process_guard timeout wrapper bounded check (${runtime}s)"
