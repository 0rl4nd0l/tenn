from __future__ import annotations

import json
import os
import shlex
import signal
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class RouterCapabilityState:
    active_mode: str
    router_supported: bool
    router_configured: bool
    router_api_reachable: bool
    candidate_server_count: int
    selected_server_port: str
    selected_server_pid: int | None
    reason: str = ""

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class LlamaServerTopology:
    selected_process: dict | None
    candidate_processes: list[dict]
    ambiguous: bool
    reason: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "selected_process": dict(self.selected_process or {}),
            "candidate_processes": [dict(proc) for proc in self.candidate_processes],
            "ambiguous": self.ambiguous,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ModelSwitchResult:
    ok: bool
    path: str
    target_model: str
    fallback_used: bool
    message: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def find_llama_server_process() -> dict | None:
    """
    Locate the running llama-server process via /proc.
    Returns dict with: pid, binary, model_path, model_alias, raw_args,
    router_mode (bool), models_dir (str).

    NOTE: Returns only the FIRST match. For multi-server topologies,
    use find_all_llama_server_processes() instead.
    """
    procs = find_all_llama_server_processes()
    return procs[0] if procs else None


def resolve_llama_server_topology(processes: list[dict] | None = None) -> LlamaServerTopology:
    discovered = list(processes if processes is not None else find_all_llama_server_processes())
    if not discovered:
        return LlamaServerTopology(
            selected_process=None,
            candidate_processes=[],
            ambiguous=False,
            reason="no_llama_server_processes",
        )

    chat_candidates = [proc for proc in discovered if str(proc.get("port") or "") == "8001"]
    extraction_candidates = [proc for proc in discovered if str(proc.get("port") or "") == "8002"]

    if len(chat_candidates) == 1:
        reason = ""
        if extraction_candidates:
            reason = "chat_runtime_selected_with_extraction_runtime_present"
        return LlamaServerTopology(
            selected_process=chat_candidates[0],
            candidate_processes=discovered,
            ambiguous=False,
            reason=reason,
        )

    if len(chat_candidates) > 1:
        return LlamaServerTopology(
            selected_process=None,
            candidate_processes=chat_candidates,
            ambiguous=True,
            reason="multiple_chat_runtime_candidates",
        )

    if len(discovered) == 1:
        return LlamaServerTopology(
            selected_process=None,
            candidate_processes=discovered,
            ambiguous=True,
            reason="only_extraction_runtime_detected",
        )

    return LlamaServerTopology(
        selected_process=None,
        candidate_processes=discovered,
        ambiguous=True,
        reason="no_unique_chat_runtime",
    )


def resolve_llama_server_port_topology(
    port: str,
    processes: list[dict] | None = None,
) -> LlamaServerTopology:
    discovered = list(processes if processes is not None else find_all_llama_server_processes())
    target_port = str(port or "8001").strip() or "8001"
    matches = [proc for proc in discovered if str(proc.get("port") or "") == target_port]

    if len(matches) == 1:
        return LlamaServerTopology(
            selected_process=matches[0],
            candidate_processes=matches,
            ambiguous=False,
            reason=f"runtime_selected_for_port_{target_port}",
        )

    if len(matches) > 1:
        return LlamaServerTopology(
            selected_process=None,
            candidate_processes=matches,
            ambiguous=True,
            reason=f"multiple_runtime_candidates_on_port_{target_port}",
        )

    return LlamaServerTopology(
        selected_process=None,
        candidate_processes=[],
        ambiguous=False,
        reason=f"no_runtime_on_port_{target_port}",
    )


def _binary_supports_models_dir(binary: str) -> bool:
    try:
        result = subprocess.run(
            [binary, "--help"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return False
    return "models-dir" in f"{result.stdout}\n{result.stderr}"


def probe_router_capability(
    proc_info: dict | None,
    *,
    host: str = "127.0.0.1",
    port: str = "8001",
    api_key: str = "",
    candidate_processes: list[dict] | None = None,
) -> RouterCapabilityState:
    processes = list(candidate_processes if candidate_processes is not None else find_all_llama_server_processes())
    router_configured = str(os.getenv("LLAMA_SERVER_ROUTER_MODE", "0")).strip() == "1"
    selected_port = str((proc_info or {}).get("port") or port or "8001")
    selected_pid = (proc_info or {}).get("pid")
    topology = resolve_llama_server_topology(processes)

    if proc_info is None:
        return RouterCapabilityState(
            active_mode="router_mode_unavailable" if topology.ambiguous else "router_mode_unavailable",
            router_supported=False,
            router_configured=router_configured,
            router_api_reachable=False,
            candidate_server_count=len(processes),
            selected_server_port=selected_port,
            selected_server_pid=None,
            reason=topology.reason or "llama_server_not_running",
        )

    binary = str(proc_info.get("binary") or "").strip()
    router_api_reachable = is_router_mode(host, selected_port, api_key)
    router_supported = bool(proc_info.get("router_mode")) or (bool(binary) and _binary_supports_models_dir(binary))

    if proc_info.get("router_mode"):
        if router_api_reachable:
            active_mode = "router_mode_active"
            reason = ""
        else:
            active_mode = "router_mode_degraded"
            reason = "router_process_detected_but_api_shape_missing"
    elif router_supported:
        active_mode = "router_mode_available_not_active"
        reason = "router_supported_but_single_model_running"
    else:
        active_mode = "single_model_active"
        reason = "binary_missing_models_dir_support"

    return RouterCapabilityState(
        active_mode=active_mode,
        router_supported=router_supported,
        router_configured=router_configured,
        router_api_reachable=router_api_reachable,
        candidate_server_count=len(processes),
        selected_server_port=selected_port,
        selected_server_pid=int(selected_pid) if selected_pid is not None else None,
        reason=reason,
    )


def find_all_llama_server_processes() -> list[dict]:
    """
    Locate ALL running llama-server processes via /proc.

    Returns list of dicts, each with: pid, binary, model_path, model_alias,
    raw_args, router_mode (bool), models_dir (str), port (str).
    """
    results: list[dict] = []
    try:
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit():
                continue
            try:
                cmdline = (entry / "cmdline").read_bytes().split(b"\x00")
                parts = [c.decode("utf-8", errors="replace") for c in cmdline if c]
                if not parts:
                    continue
                binary = parts[0]
                if "llama-server" not in binary:
                    continue
                args = parts[1:]
                model_path = _extract_arg(args, ("-m", "--model"))
                model_alias = _extract_arg(args, ("-a", "--alias"))
                models_dir = _extract_arg(args, ("--models-dir",))
                port = _extract_arg(args, ("--port",)) or "8001"
                router_mode = bool(models_dir and not model_path)
                results.append({
                    "pid": int(entry.name),
                    "binary": binary,
                    "model_path": model_path,
                    "model_alias": model_alias,
                    "raw_args": args,
                    "router_mode": router_mode,
                    "models_dir": models_dir,
                    "port": port,
                })
            except (PermissionError, ValueError, FileNotFoundError):
                continue
    except Exception:
        pass
    return results


# Authorised llama-server ports (SYSTEM_CONTRACT.md §9.4).
AUTHORISED_PORTS = frozenset({"8001", "8002"})


def _read_proc_cmdline(pid: int) -> str:
    try:
        return Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\x00", b" ").decode()
    except Exception:
        return ""


def _read_parent_pid(pid: int) -> int | None:
    try:
        for line in Path(f"/proc/{pid}/status").read_text(encoding="utf-8").splitlines():
            if line.startswith("PPid:"):
                return int(line.split(":", 1)[1].strip())
    except Exception:
        return None
    return None


def _is_router_owned_child_process(pid: int) -> bool:
    """Return True when *pid* descends from the canonical router on 8001/8002.

    In router mode, llama.cpp keeps the public HTTP server on an authorised port
    and may spawn per-model child workers on ephemeral localhost ports. Those
    children belong to the canonical runtime and must not be treated as rogue.
    """
    current = pid
    for _ in range(6):
        parent = _read_parent_pid(current)
        if not parent:
            return False
        cmdline = _read_proc_cmdline(parent)
        if "llama-server" not in cmdline:
            return False
        args = shlex.split(cmdline)
        port = _extract_arg(args[1:], ("--port",)) or "8001"
        if port in AUTHORISED_PORTS and "--models-dir" in args[1:]:
            return True
        current = parent
    return False


def check_gpu_process_topology() -> dict:
    """Check running llama-server processes against the authorised manifest.

    Returns dict with:
        authorised: list of process dicts on canonical ports or router-owned child ports
        rogue: list of independent process dicts on non-canonical ports
        clean: bool — True if no rogues detected
    """
    procs = find_all_llama_server_processes()
    authorised = [p for p in procs if p["port"] in AUTHORISED_PORTS or _is_router_owned_child_process(p["pid"])]
    rogue = [p for p in procs if p not in authorised]
    return {
        "authorised": authorised,
        "rogue": rogue,
        "clean": len(rogue) == 0,
    }


def discover_models(models_dir: str) -> list[dict]:
    """
    Scan a directory for .gguf files.
    Returns list of {path, name, stem} dicts, sorted by name.
    """
    path = Path(models_dir).expanduser()
    if not path.is_dir():
        return []
    return sorted(
        [{"path": str(f), "name": f.name, "stem": f.stem} for f in path.glob("*.gguf")],
        key=lambda d: d["name"],
    )


def _ollama_model_roots() -> list[Path]:
    """
    Return all candidate Ollama model root directories to search.
    Ollama may store models under the service user's home (/usr/share/ollama),
    the current user's home (~/.ollama), or a custom OLLAMA_MODELS path.
    """
    candidates = [
        Path.home() / ".ollama" / "models",
        Path("/usr/share/ollama/.ollama/models"),
        Path("/var/lib/ollama/.ollama/models"),
    ]
    env_override = os.environ.get("OLLAMA_MODELS")
    if env_override:
        candidates.insert(0, Path(env_override))
    return [p for p in candidates if p.is_dir()]


def discover_ollama_models() -> list[dict]:
    """
    Read Ollama's manifest store(s) and return usable models as GGUF blob paths.
    Returns list of {path, name, stem} dicts — compatible with discover_models output.

    Ollama stores model weights as plain GGUF files named by their SHA256 digest
    (sha256-<hex>) in <root>/blobs/.  The manifests map model:tag names to digests.
    Checks all known Ollama model roots (user home + system service dir).
    """
    results: list[dict] = []
    seen_digests: set[str] = set()

    for root in _ollama_model_roots():
        blobs_dir = root / "blobs"
        manifests_root = root / "manifests"
        if not manifests_root.is_dir() or not blobs_dir.is_dir():
            continue

        for manifest_path in manifests_root.rglob("*"):
            if not manifest_path.is_file():
                continue
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                continue

            # Derive human-readable name: library/<model>/<tag> → <model>:<tag>
            parts = manifest_path.parts
            try:
                lib_idx = list(parts).index("library")
                display = f"{parts[lib_idx + 1]}:{parts[lib_idx + 2]}"
            except (ValueError, IndexError):
                display = manifest_path.name

            for layer in (manifest.get("layers") or []):
                if layer.get("mediaType") != "application/vnd.ollama.image.model":
                    continue
                digest = layer.get("digest", "")
                if not digest or digest in seen_digests:
                    continue
                blob_name = digest.replace("sha256:", "sha256-", 1)
                blob_path = blobs_dir / blob_name
                if not blob_path.exists():
                    continue
                seen_digests.add(digest)
                results.append({
                    "path": str(blob_path),
                    "name": f"{display}  (ollama)",
                    "stem": display,
                })

    return sorted(results, key=lambda d: d["stem"])


def models_dir_from_process(proc_info: dict) -> str:
    """Derive the models directory from the running process."""
    # Router mode: --models-dir is explicit.
    models_dir = proc_info.get("models_dir", "")
    if models_dir:
        return models_dir
    # Single-model mode: derive from the -m path's parent.
    model_path = proc_info.get("model_path", "")
    if model_path:
        parent = str(Path(model_path).parent)
        if parent and parent != ".":
            return parent
    return os.environ.get("LLAMACPP_MODELS_DIR", str(Path.home() / "tenn" / "models"))


_KNOWN_SYSTEMD_SERVICES = [
    "llama-cpp-qwen25",
    "llama-cpp",
    "llama-server",
]


def _stop_systemd_service(on_status: object) -> str | None:
    """
    Stop the systemd user service managing llama-server, if one is active.
    Returns the service name if stopped, else None.
    """
    for svc in _KNOWN_SYSTEMD_SERVICES:
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", svc],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                if callable(on_status):
                    on_status(f"Stopping systemd service {svc}...")
                subprocess.run(
                    ["systemctl", "--user", "stop", svc],
                    capture_output=True, timeout=15,
                )
                return svc
        except Exception:
            continue
    return None


def has_no_mmap(raw_args: list[str]) -> bool:
    """Return True if --no-mmap is present in the process arg list."""
    return "--no-mmap" in raw_args


def _warm_page_cache(model_path: str, on_status: object = None) -> None:
    """Read the model file sequentially to populate the OS page cache.

    With mmap (the default), llama-server memory-maps the GGUF file. If the
    pages are already in the page cache from a prior read, the mmap is
    satisfied from RAM instead of hitting NVMe — cutting load time for a
    previously-used model from seconds to near-instant.

    This is a no-op for models already cached (the kernel skips re-reading).
    """
    p = Path(model_path)
    if not p.is_file():
        return
    total_bytes = p.stat().st_size
    size_gb = total_bytes / (1024 ** 3)
    if callable(on_status):
        on_status(f"Warming page cache for {p.name} ({size_gb:.1f} GB)...")
    chunk_size = 8 * 1024 * 1024  # 8 MB
    read_bytes = 0
    last_pct = -1
    try:
        with open(model_path, "rb") as f:
            while True:
                data = f.read(chunk_size)
                if not data:
                    break
                read_bytes += len(data)
                pct = int(read_bytes * 100 / total_bytes)
                # Report progress every 10%.
                if callable(on_status) and pct >= last_pct + 10:
                    last_pct = pct
                    on_status(
                        f"Warming page cache: {pct}%  "
                        f"({read_bytes / (1024**3):.1f} / {size_gb:.1f} GB)"
                    )
    except OSError:
        pass  # Non-fatal — server will just read from disk at mmap time.
    if callable(on_status):
        on_status(f"Page cache warm complete ({size_gb:.1f} GB)")


def restart_with_model(
    proc_info: dict,
    new_model_path: str,
    new_model_alias: str,
    startup_timeout: float = 600.0,
    on_status: object = None,
    mmap_disabled: bool | None = None,
) -> bool:
    """
    Kill the current llama-server and relaunch it with a different model.
    All other startup args (GPU layers, context size, host, port, etc.) are preserved.
    If a systemd user service is managing the process, it is stopped first to
    prevent auto-restart interference.

    on_status: optional callable(str) called with progress messages.
    Returns True if the new server becomes ready within startup_timeout seconds.
    """
    def _status(msg: str) -> None:
        if callable(on_status):
            on_status(msg)

    # Stop any systemd service that would respawn the old model.
    _stop_systemd_service(_status)

    pid = proc_info["pid"]
    binary = proc_info["binary"]
    raw_args = proc_info["raw_args"]

    # Rebuild args, replacing -m/-a values and toggling --no-mmap if requested.
    new_args: list[str] = []
    i = 0
    while i < len(raw_args):
        if raw_args[i] in ("-m", "--model") and i + 1 < len(raw_args):
            new_args += [raw_args[i], new_model_path]
            i += 2
        elif raw_args[i] in ("-a", "--alias") and i + 1 < len(raw_args):
            new_args += [raw_args[i], new_model_alias]
            i += 2
        elif raw_args[i] == "--no-mmap" and mmap_disabled is not None:
            # Handled below — skip original value.
            i += 1
        else:
            new_args.append(raw_args[i])
            i += 1

    # If no -a in original args, append it.
    if "-a" not in raw_args and "--alias" not in raw_args:
        new_args += ["-a", new_model_alias]

    # Apply mmap override.
    if mmap_disabled is True:
        new_args.append("--no-mmap")
    # mmap_disabled=False means remove --no-mmap (already stripped above).

    # Graceful shutdown: SIGTERM then SIGKILL.
    _status("Stopping current model...")
    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(20):
            time.sleep(0.5)
            try:
                os.kill(pid, 0)  # probe: raises if process is gone
            except ProcessLookupError:
                break
        else:
            _status("Server slow to stop — forcing shutdown")
            os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass  # already gone

    # Warm the OS page cache so mmap doesn't block on disk I/O during startup.
    # Reading the file populates the cache; subsequent mmap access hits RAM instead of NVMe.
    _warm_page_cache(new_model_path, _status)

    # Use alias (human-readable) if the path is an Ollama blob (no .gguf suffix).
    model_label = new_model_alias if Path(new_model_path).suffix != ".gguf" else Path(new_model_path).name
    _status(f"Starting server with {model_label}...")
    proc = subprocess.Popen(
        [binary] + new_args,
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    # Poll until the new server is ready, aborting early if the process dies.
    host = _extract_arg(raw_args, ("--host",)) or "127.0.0.1"
    port = _extract_arg(raw_args, ("--port",)) or "8001"
    ready_url = f"http://{host}:{port}/v1/models"
    deadline = time.monotonic() + startup_timeout
    elapsed = 0
    while time.monotonic() < deadline:
        time.sleep(5)
        elapsed += 5

        # Check if llama-server died before becoming ready.
        if proc.poll() is not None:
            stderr_tail = ""
            if proc.stderr:
                try:
                    raw = proc.stderr.read(4096)
                    stderr_tail = raw.decode("utf-8", errors="replace").strip()
                except Exception:
                    pass
            reason = f"exit code {proc.returncode}"
            if stderr_tail:
                # Show last meaningful line for context.
                last_lines = [l for l in stderr_tail.splitlines() if l.strip()]
                reason += f": {last_lines[-1]}" if last_lines else ""
            _status(f"Server crashed during startup ({reason})")
            return False

        remaining = int(deadline - time.monotonic())
        _status(f"Loading model... {elapsed}s elapsed  ({remaining}s timeout)")
        try:
            urllib.request.urlopen(ready_url, timeout=3)
            return True
        except Exception:
            continue
    return False


def _extract_arg(args: list[str], flags: tuple[str, ...]) -> str:
    """Return the value after the first matching flag, or empty string."""
    for i, a in enumerate(args):
        if a in flags and i + 1 < len(args):
            return args[i + 1]
    return ""


# ---------------------------------------------------------------------------
# Router mode API — zero-downtime model switching via /models/load|unload
# ---------------------------------------------------------------------------

def _api_request(
    url: str,
    api_key: str = "",
    method: str = "GET",
    body: dict | None = None,
    timeout: float = 10.0,
) -> dict | list | None:
    """Make an authenticated HTTP request to the llama-server API."""
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _is_loading_stalled(
    host: str, port: str, model_name: str, api_key: str = "",
) -> bool:
    """Detect if a model stuck in 'loading' state actually has a dead child.

    The llama.cpp router has a known issue where a crashed child process may
    not be detected, leaving the model in 'loading' state indefinitely with
    failed=false.  We check the raw /v1/models response for the child's
    assigned port, then probe it.  If the port is unreachable, the child is
    dead and the load has stalled.
    """
    import socket as _socket

    result = _api_request(f"http://{host}:{port}/v1/models", api_key=api_key)
    if not result:
        return False

    for entry in (result.get("data") or []):
        entry_name = entry.get("id") or entry.get("model") or ""
        if entry_name != model_name:
            continue
        status = entry.get("status")
        if not isinstance(status, dict):
            continue
        if status.get("value") != "loading":
            continue
        # Extract the child port from the args list in the status object.
        child_args = status.get("args") or []
        child_port = _extract_arg(child_args, ("--port",))
        if not child_port:
            continue
        # Probe the child port — if unreachable, child is dead.
        try:
            s = _socket.create_connection(
                (host or "127.0.0.1", int(child_port)), timeout=2,
            )
            s.close()
            return False  # child port is reachable — still loading normally
        except (OSError, ValueError):
            return True  # port unreachable — child is dead

    return False


def is_router_mode(host: str, port: str, api_key: str = "") -> bool:
    """Detect if the server is running in router mode.

    In router mode, the /v1/models response includes a 'status' object
    per model (with 'value' field). In single-model mode, models have no
    'status' field. This is the most reliable detection method.
    """
    result = _api_request(f"http://{host}:{port}/v1/models", api_key=api_key)
    if not result:
        return False
    for entry in (result.get("data") or []):
        if isinstance(entry.get("status"), dict):
            return True
    return False


def list_models_api(
    host: str, port: str, api_key: str = "",
) -> list[dict]:
    """List all models known to the router with their load status.

    Returns list of dicts with at minimum: name, state (loaded/unloaded/loading).
    Falls back to /v1/models for single-model mode.
    """
    result = _api_request(
        f"http://{host}:{port}/v1/models",
        api_key=api_key,
    )
    if not result:
        return []

    models = []
    # Router mode returns {"data": [...]} with status.value fields.
    # Single-model mode returns {"data": [...]} with no status field.
    for entry in (result.get("data") or result.get("models") or []):
        name = entry.get("id") or entry.get("model") or entry.get("name") or ""
        status = entry.get("status")
        if isinstance(status, dict):
            state = status.get("value", "loaded")
            # Router reports failed=true when child process crashed but may
            # still show state as "loading" — surface the real state.
            if status.get("failed"):
                state = "failed"
        elif isinstance(status, str):
            state = status
        else:
            state = "loaded"  # single-model mode has no status field
        models.append({"name": name, "state": state})
    return models


def load_model_api(
    host: str,
    port: str,
    model_name: str,
    api_key: str = "",
    timeout: float = 600.0,
    on_status: object = None,
) -> bool:
    """Load a model via the router API. With --models-max 1, the currently
    loaded model is auto-evicted before loading the new one.

    Sends POST /models/load, then polls GET /v1/models until the target
    model state is 'loaded' or timeout expires.

    Returns True on success.
    """
    def _status(msg: str) -> None:
        if callable(on_status):
            on_status(msg)

    _status(f"Requesting load of {model_name}...")
    url = f"http://{host}:{port}/models/load"
    req = urllib.request.Request(
        url,
        data=json.dumps({"model": model_name}).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    try:
        urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        _status(f"Load request failed: HTTP {e.code} — {body[:200]}")
        return False
    except Exception as exc:
        _status(f"Load request failed: {exc}")
        return False

    # Poll until loaded, bailing early on terminal failure states.
    # The router has a known issue where a crashed child process may be
    # reported as "loading" (failed=false) indefinitely. We detect this by
    # checking the raw /v1/models response for the failed flag and child
    # process args, then probing the child port directly.
    _TERMINAL_STATES = {"failed", "error"}
    _LOADING_STALL_SECONDS = 60  # if "loading" for this long, probe child
    deadline = time.monotonic() + timeout
    elapsed = 0
    loading_since: float | None = None

    while time.monotonic() < deadline:
        time.sleep(1)
        elapsed += 1
        models = list_models_api(host, port, api_key)
        target = next((m for m in models if m["name"] == model_name), None)
        if target is None:
            state = "not found"
            loading_since = None
        else:
            state = target["state"]
            if state == "loaded":
                _status(f"{model_name} loaded successfully ({elapsed}s)")
                return True
            if state in _TERMINAL_STATES:
                _status(f"{model_name} failed to load (state: {state} after {elapsed}s)")
                return False
            if state == "loading":
                if loading_since is None:
                    loading_since = time.monotonic()
                elif time.monotonic() - loading_since > _LOADING_STALL_SECONDS:
                    # Stall detected — probe child health via raw API.
                    if _is_loading_stalled(host, port, model_name, api_key):
                        _status(
                            f"{model_name} child process appears dead "
                            f"(stuck in 'loading' for {int(time.monotonic() - loading_since)}s)"
                        )
                        return False
            else:
                loading_since = None

        remaining = int(deadline - time.monotonic())
        _status(f"Loading {model_name}... {state} ({elapsed}s elapsed, {remaining}s timeout)")

    _status(f"Timed out waiting for {model_name} to load ({timeout:.0f}s)")
    return False


def unload_model_api(
    host: str, port: str, model_name: str, api_key: str = "",
) -> bool:
    """Unload a model via the router API."""
    result = _api_request(
        f"http://{host}:{port}/models/unload",
        api_key=api_key,
        method="POST",
        body={"model": model_name},
    )
    return result is not None


def generate_preset_ini(
    models_dir: str,
    output_path: str | None = None,
    global_opts: dict[str, str] | None = None,
) -> Path:
    """Generate a preset INI file for router mode.

    The INI uses llama.cpp's native format: section names are model names
    (filename without .gguf), keys are CLI flag names without leading dashes.
    A [*] section applies to all models.

    Returns the path to the generated file.
    """
    if output_path is None:
        output_path = str(Path.home() / ".config" / "tenn" / "llamacpp-presets.ini")

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    defaults: dict[str, str] = {}
    if global_opts:
        defaults.update(global_opts)

    lines = ["# Auto-generated by cockpit — per-model presets for router mode", ""]

    # Global section — keep it minimal.  Do NOT add embeddings/pooling here:
    # those flags change the CUDA memory layout and stall model loading on
    # older GPUs (e.g. Tesla M40, compute 5.2).  They belong only on models
    # that actually serve embeddings (e.g. nomic-embed-text).
    if defaults:
        lines.append("[*]")
        for key, val in sorted(defaults.items()):
            lines.append(f"{key} = {val}")
        lines.append("")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def switch_model(
    proc_info: dict,
    new_model_name: str,
    new_model_path: str,
    api_key: str = "",
    host: str = "127.0.0.1",
    port: str = "8001",
    startup_timeout: float = 600.0,
    on_status: object = None,
    mmap_disabled: bool | None = None,
) -> ModelSwitchResult:
    """High-level model switch: uses router API if available, falls back to restart.

    Returns a structured result describing the chosen switch path and outcome.
    """
    def _status(msg: str) -> None:
        if callable(on_status):
            on_status(msg)

    # Detect mode.
    router = proc_info.get("router_mode", False)
    if not router:
        # Double-check via HTTP in case process detection missed it.
        router = is_router_mode(host, port, api_key)

    if router:
        _status("Router mode detected — switching via API (zero downtime)")
        # Warm page cache for the new model before asking the server to load it.
        _warm_page_cache(new_model_path, _status)
        ok = load_model_api(
            host, port, new_model_name, api_key, startup_timeout, on_status,
        )
        message = (
            f"Router hot-switch loaded {new_model_name}"
            if ok
            else f"Router hot-switch failed for {new_model_name}"
        )
        return ModelSwitchResult(
            ok=ok,
            path="router_hot_switch",
            target_model=new_model_name,
            fallback_used=False,
            message=message,
        )

    # Fallback: single-model mode — kill and restart.
    _status("Single-model mode — restarting server")
    ok = restart_with_model(
        proc_info, new_model_path, new_model_name,
        startup_timeout, on_status, mmap_disabled,
    )
    message = (
        f"Restarted server with {new_model_name}"
        if ok
        else f"Restart path failed for {new_model_name}"
    )
    return ModelSwitchResult(
        ok=ok,
        path="restart",
        target_model=new_model_name,
        fallback_used=False,
        message=message,
    )


def build_router_args(proc_info: dict, models_dir: str, preset_path: str) -> list[str]:
    """Convert single-model launch args to router-mode args.

    Strips -m/--model, -a/--alias, --pooling, --embeddings.
    Adds --models-dir, --models-max 1, --models-preset.
    """
    raw = proc_info["raw_args"]
    skip_next = False
    new_args: list[str] = []

    # Flags that take a value and should be removed for router mode.
    strip_value_flags = {"-m", "--model", "-a", "--alias", "--pooling"}
    # Flags that are standalone booleans and should be removed.
    strip_bool_flags = {"--embeddings"}

    for i, arg in enumerate(raw):
        if skip_next:
            skip_next = False
            continue
        if arg in strip_value_flags and i + 1 < len(raw):
            skip_next = True
            continue
        if arg in strip_bool_flags:
            continue
        new_args.append(arg)

    new_args += [
        "--models-dir", models_dir,
        "--models-max", "1",
        "--models-preset", preset_path,
    ]
    return new_args


def restart_into_router_mode(
    proc_info: dict,
    models_dir: str,
    startup_timeout: float = 600.0,
    on_status: object = None,
) -> bool:
    """Kill the current single-model server and relaunch in router mode.

    Generates a preset INI, rebuilds args, and starts the server.
    Returns True when the router server is ready.
    """
    def _status(msg: str) -> None:
        if callable(on_status):
            on_status(msg)

    # Generate preset INI for per-model config.
    preset_path = str(generate_preset_ini(models_dir))
    _status(f"Generated preset file: {preset_path}")

    # Stop systemd service if managed.
    _stop_systemd_service(_status)

    # Kill current process.
    pid = proc_info["pid"]
    binary = proc_info["binary"]
    _status("Stopping single-model server...")
    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(10):
            time.sleep(0.5)
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
        else:
            os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass

    # Build router-mode args and launch.
    new_args = build_router_args(proc_info, models_dir, preset_path)
    _status(f"Starting router server (models-dir: {models_dir})...")
    proc = subprocess.Popen(
        [binary] + new_args,
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    # Poll until ready.
    host = _extract_arg(proc_info["raw_args"], ("--host",)) or "127.0.0.1"
    port = _extract_arg(proc_info["raw_args"], ("--port",)) or "8001"
    ready_url = f"http://{host}:{port}/v1/models"
    deadline = time.monotonic() + startup_timeout
    elapsed = 0
    while time.monotonic() < deadline:
        time.sleep(1)
        elapsed += 1
        if proc.poll() is not None:
            stderr_tail = ""
            if proc.stderr:
                try:
                    raw = proc.stderr.read(4096)
                    stderr_tail = raw.decode("utf-8", errors="replace").strip()
                except Exception:
                    pass
            reason = f"exit code {proc.returncode}"
            if stderr_tail:
                last_lines = [l for l in stderr_tail.splitlines() if l.strip()]
                reason += f": {last_lines[-1]}" if last_lines else ""
            _status(f"Router server crashed during startup ({reason})")
            return False
        remaining = int(deadline - time.monotonic())
        _status(f"Starting router... {elapsed}s elapsed ({remaining}s timeout)")
        try:
            urllib.request.urlopen(ready_url, timeout=3)
            _status("Router server ready")
            return True
        except Exception:
            continue
    _status("Router server startup timed out")
    return False
