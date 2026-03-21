from __future__ import annotations

import json
import os
import signal
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


def find_llama_server_process() -> dict | None:
    """
    Locate the running llama-server process via /proc.
    Returns dict with: pid, binary, model_path, model_alias, raw_args
    or None if not found.
    """
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
                return {
                    "pid": int(entry.name),
                    "binary": binary,
                    "model_path": model_path,
                    "model_alias": model_alias,
                    "raw_args": args,
                }
            except (PermissionError, ValueError, FileNotFoundError):
                continue
    except Exception:
        pass
    return None


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
    """Derive the models directory from the running process's -m path."""
    model_path = proc_info.get("model_path", "")
    if model_path:
        parent = str(Path(model_path).parent)
        if parent and parent != ".":
            return parent
    return os.environ.get("LLAMACPP_MODELS_DIR", str(Path.home() / "tenn" / "models"))


def restart_with_model(
    proc_info: dict,
    new_model_path: str,
    new_model_alias: str,
    startup_timeout: float = 90.0,
    on_status: object = None,
) -> bool:
    """
    Kill the current llama-server and relaunch it with a different model.
    All other startup args (GPU layers, context size, host, port, etc.) are preserved.

    on_status: optional callable(str) called with progress messages.
    Returns True if the new server becomes ready within startup_timeout seconds.
    """
    def _status(msg: str) -> None:
        if callable(on_status):
            on_status(msg)

    pid = proc_info["pid"]
    binary = proc_info["binary"]
    raw_args = proc_info["raw_args"]

    # Rebuild args, replacing -m/-a values.
    new_args: list[str] = []
    i = 0
    while i < len(raw_args):
        if raw_args[i] in ("-m", "--model") and i + 1 < len(raw_args):
            new_args += [raw_args[i], new_model_path]
            i += 2
        elif raw_args[i] in ("-a", "--alias") and i + 1 < len(raw_args):
            new_args += [raw_args[i], new_model_alias]
            i += 2
        else:
            new_args.append(raw_args[i])
            i += 1

    # If no -a in original args, append it.
    if "-a" not in raw_args and "--alias" not in raw_args:
        new_args += ["-a", new_model_alias]

    # Graceful shutdown: SIGTERM then SIGKILL.
    _status("Sending SIGTERM to llama-server...")
    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(20):
            time.sleep(0.5)
            try:
                os.kill(pid, 0)  # probe: raises if process is gone
            except ProcessLookupError:
                break
        else:
            _status("Graceful shutdown timed out — sending SIGKILL")
            os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass  # already gone

    _status(f"Starting llama-server with {Path(new_model_path).name}...")
    subprocess.Popen(
        [binary] + new_args,
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Poll until the new server is ready.
    host = _extract_arg(raw_args, ("--host",)) or "127.0.0.1"
    port = _extract_arg(raw_args, ("--port",)) or "8001"
    ready_url = f"http://{host}:{port}/v1/models"
    deadline = time.monotonic() + startup_timeout
    dots = 0
    while time.monotonic() < deadline:
        time.sleep(2)
        dots += 1
        _status(f"Waiting for server{'.' * (dots % 4)}  ({int(deadline - time.monotonic())}s left)")
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
