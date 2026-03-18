#!/usr/bin/env python3
"""
GPU runtime status: query nvidia-smi, parse memory and processes, print summary.
Exit non-zero if GPU not detected or memory usage > 95%.
Read-only, no external dependencies.
"""

import csv
import io
import subprocess
import sys


def run_nvidia_smi(*query_args: str) -> tuple[int, str]:
    """Run nvidia-smi with optional query args. Returns (returncode, stdout)."""
    cmd = ["nvidia-smi"] + list(query_args)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode, result.stdout or ""
    except FileNotFoundError:
        return -1, ""
    except subprocess.TimeoutExpired:
        return -2, ""


def parse_csv_lines(output: str) -> list[dict[str, str]]:
    """Parse nvidia-smi CSV output into list of dicts (first line = headers)."""
    output = output.strip()
    if not output:
        return []
    reader = csv.reader(io.StringIO(output))
    rows = []
    header = None
    for row in reader:
        row = [c.strip() for c in row]
        if header is None:
            header = row
            continue
        if len(row) == len(header):
            rows.append(dict(zip(header, row)))
    return rows


def parse_memory_mib(s: str) -> int:
    """Parse '1234 MiB' -> 1234."""
    s = (s or "").strip()
    if not s:
        return 0
    parts = s.split()
    try:
        return int(parts[0])
    except (ValueError, IndexError):
        return 0


def main() -> int:
    # Query GPU memory and name
    rc, out = run_nvidia_smi(
        "--query-gpu=memory.used,memory.total,name,uuid",
        "--format=csv,noheader,nounits",
    )
    if rc != 0 or not out.strip():
        print("gpu_runtime_status: GPU not detected (nvidia-smi failed or no output)")
        return 1

    gpus = parse_csv_lines(
        "memory.used [MiB],memory.total [MiB],name,uuid\n" + out
    )
    if not gpus:
        print("gpu_runtime_status: GPU not detected (no GPU entries)")
        return 1

    # Query compute processes
    rc_proc, out_proc = run_nvidia_smi(
        "--query-compute-apps=pid,process_name,used_memory",
        "--format=csv,noheader,nounits",
    )
    processes = []
    if rc_proc == 0 and out_proc.strip():
        processes = parse_csv_lines(
            "pid,process_name,used_memory [MiB]\n" + out_proc
        )

    # Build and print summary
    total_used_mib = 0
    total_mib = 0
    max_pct = 0.0

    print("=== GPU runtime status ===\n")
    for i, gpu in enumerate(gpus):
        used = parse_memory_mib(gpu.get("memory.used [MiB]", "0"))
        total = parse_memory_mib(gpu.get("memory.total [MiB]", "0"))
        name = gpu.get("name", "N/A")
        uuid = gpu.get("uuid", "N/A")

        total_used_mib += used
        total_mib += total
        pct = (used / total * 100) if total else 0
        if pct > max_pct:
            max_pct = pct

        print(f"GPU {i}: {name}")
        print(f"  UUID: {uuid}")
        print(f"  Memory: {used} / {total} MiB ({pct:.1f}%)")
        print()

    if processes:
        print("Active processes:")
        for p in processes:
            pid = p.get("pid", "?")
            name = p.get("process_name", "?")
            mem = p.get("used_memory [MiB]", "?")
            print(f"  PID {pid}  {name}  {mem} MiB")
        print()
    else:
        print("Active processes: none\n")

    # Aggregate if multiple GPUs
    if gpus:
        agg_pct = (total_used_mib / total_mib * 100) if total_mib else 0
        print(f"Total memory: {total_used_mib} / {total_mib} MiB ({agg_pct:.1f}%)")
        if max_pct > 95 or agg_pct > 95:
            print("\ngpu_runtime_status: memory usage > 95%")
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
