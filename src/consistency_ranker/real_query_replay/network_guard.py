"""Fail closed if any outbound network attempt is made during a replay."""

from __future__ import annotations

import socket
from typing import Any


class NetworkForbiddenError(RuntimeError):
    """Raised when a socket connection is attempted under the no-network guard."""


_guard_installed = False
_original_connect = socket.socket.connect


def _blocked_connect(self: socket.socket, address: Any) -> None:  # noqa: ANN401
    raise NetworkForbiddenError(
        f"Outbound network connection forbidden during real-query replay: {address!r}"
    )


def install_no_network_guard() -> None:
    """Monkeypatch ``socket.socket.connect`` to raise on any connection attempt."""
    global _guard_installed
    if _guard_installed:
        return
    socket.socket.connect = _blocked_connect  # type: ignore[assignment,method-assign]
    _guard_installed = True


def uninstall_no_network_guard() -> None:
    global _guard_installed
    if not _guard_installed:
        return
    socket.socket.connect = _original_connect  # type: ignore[assignment,method-assign]
    _guard_installed = False


def assert_no_network() -> None:
    """Install the guard (idempotent). Call at the start of every replay entrypoint."""
    install_no_network_guard()
