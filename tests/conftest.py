"""Prevent accidental real API calls or developer credential use in tests."""

import socket
import pytest


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("MAILO_MODEL", raising=False)
    original_connect = socket.socket.connect

    def local_only(sock, address):
        # Windows asyncio implements socketpair with a loopback connection.
        if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1"):
            return original_connect(sock, address)
        raise AssertionError("Tests must not open external network connections")

    def blocked(*args, **kwargs):
        raise AssertionError("Tests must not open network connections")

    monkeypatch.setattr(socket.socket, "connect", local_only)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
