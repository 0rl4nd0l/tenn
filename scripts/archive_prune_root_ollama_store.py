#!/usr/bin/env python3
import json
import os
import shutil
from glob import glob


SRC_ROOT = "/usr/share/ollama/.ollama/models"
MANIFEST_BASE = os.path.join(SRC_ROOT, "manifests", "registry.ollama.ai", "library")
ARCHIVE_ROOT = "/mnt/sdb2/home/l4nd0/tenn/.archives/ollama-root-store-2026-04-07"
KEEP_MODELS = {
    "qwen2.5:32b": os.path.join(MANIFEST_BASE, "qwen2.5", "32b"),
    "gpt-oss:20b-cloud": os.path.join(MANIFEST_BASE, "gpt-oss", "20b-cloud"),
}


def manifest_digests(path: str) -> list[str]:
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    digests: list[str] = []
    config = data.get("config") or {}
    if config.get("digest"):
        digests.append(config["digest"])
    for layer in data.get("layers") or []:
        if layer.get("digest"):
            digests.append(layer["digest"])
    return digests


def ensure_root() -> None:
    if os.geteuid() != 0:
        raise SystemExit("Run this script with sudo.")


def main() -> None:
    ensure_root()

    keep_paths = set(KEEP_MODELS.values())
    all_manifests = sorted(glob(os.path.join(MANIFEST_BASE, "*", "*")))
    archive_manifests = [path for path in all_manifests if path not in keep_paths]

    keep_digests: set[str] = set()
    archive_digests: set[str] = set()

    for path in keep_paths:
        if not os.path.exists(path):
            raise SystemExit(f"Missing keep manifest: {path}")
        keep_digests.update(manifest_digests(path))

    for path in archive_manifests:
        archive_digests.update(manifest_digests(path))

    archive_only = sorted(digest for digest in archive_digests if digest not in keep_digests)

    os.makedirs(os.path.join(ARCHIVE_ROOT, "models", "manifests", "registry.ollama.ai", "library"), exist_ok=True)
    os.makedirs(os.path.join(ARCHIVE_ROOT, "models", "blobs"), exist_ok=True)

    archived_manifest_paths: list[str] = []
    archived_blobs: list[dict[str, object]] = []

    for path in archive_manifests:
        relative_path = os.path.relpath(path, SRC_ROOT)
        destination = os.path.join(ARCHIVE_ROOT, "models", relative_path)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        shutil.copy2(path, destination)
        archived_manifest_paths.append(relative_path)

    for digest in archive_only:
        source = os.path.join(SRC_ROOT, "blobs", digest.replace(":", "-"))
        if not os.path.exists(source):
            continue
        destination = os.path.join(ARCHIVE_ROOT, "models", "blobs", os.path.basename(source))
        shutil.copy2(source, destination)
        archived_blobs.append(
            {
                "digest": digest,
                "size": os.path.getsize(source),
                "path": os.path.relpath(destination, ARCHIVE_ROOT),
            }
        )

    summary = {
        "archived_at": "2026-04-07",
        "source_root": SRC_ROOT,
        "archive_root": ARCHIVE_ROOT,
        "kept_models": list(KEEP_MODELS.keys()),
        "archived_manifests": archived_manifest_paths,
        "archived_blob_count": len(archived_blobs),
        "archived_blob_bytes": sum(int(blob["size"]) for blob in archived_blobs),
        "archived_blobs": archived_blobs,
    }
    with open(os.path.join(ARCHIVE_ROOT, "archive-summary.json"), "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    for path in archive_manifests:
        if os.path.exists(path):
            os.remove(path)

    for digest in archive_only:
        source = os.path.join(SRC_ROOT, "blobs", digest.replace(":", "-"))
        if os.path.exists(source):
            os.remove(source)

    for root, _dirs, _files in os.walk(MANIFEST_BASE, topdown=False):
        if root == MANIFEST_BASE:
            continue
        try:
            if not os.listdir(root):
                os.rmdir(root)
        except OSError:
            pass

    print(json.dumps(
        {
            "archive_root": ARCHIVE_ROOT,
            "archived_manifests": len(archived_manifest_paths),
            "archived_blob_count": len(archived_blobs),
            "archived_blob_gib": round(sum(int(blob["size"]) for blob in archived_blobs) / 1024 / 1024 / 1024, 2),
            "kept_models": list(KEEP_MODELS.keys()),
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
