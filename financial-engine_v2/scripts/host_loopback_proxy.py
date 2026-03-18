#!/usr/bin/env python3
from __future__ import annotations

import argparse
import socket
from contextlib import suppress
from threading import Thread
from urllib.parse import urlsplit


BUFFER_SIZE = 65536


def _forward(src: socket.socket, dst: socket.socket) -> None:
    try:
        while True:
            chunk = src.recv(BUFFER_SIZE)
            if not chunk:
                break
            dst.sendall(chunk)
    except OSError:
        pass
    finally:
        with suppress(OSError):
            dst.shutdown(socket.SHUT_WR)


def _handle_client(client_sock: socket.socket, upstream_host: str, upstream_port: int) -> None:
    with client_sock:
        upstream_sock = socket.create_connection((upstream_host, upstream_port))
        with upstream_sock:
            upstream_thread = Thread(target=_forward, args=(client_sock, upstream_sock), daemon=True)
            downstream_thread = Thread(target=_forward, args=(upstream_sock, client_sock), daemon=True)
            upstream_thread.start()
            downstream_thread.start()
            upstream_thread.join()
            downstream_thread.join()


def main() -> int:
    parser = argparse.ArgumentParser(description="Expose a host-loopback TCP service on a bridge-reachable port.")
    parser.add_argument("--listen-host", default="0.0.0.0")
    parser.add_argument("--listen-port", type=int, required=True)
    parser.add_argument("--upstream-base-url", required=True)
    args = parser.parse_args()

    upstream = urlsplit(args.upstream_base_url)
    if upstream.scheme not in {"http", "https", ""}:
        raise ValueError("upstream-base-url must use http, https, or no scheme")
    if not upstream.hostname:
        raise ValueError("upstream-base-url must include a hostname")
    upstream_port = upstream.port or (443 if upstream.scheme == "https" else 80)

    with socket.create_server((args.listen_host, args.listen_port), reuse_port=False) as server:
        while True:
            client_sock, _ = server.accept()
            Thread(
                target=_handle_client,
                args=(client_sock, upstream.hostname, upstream_port),
                daemon=True,
            ).start()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
