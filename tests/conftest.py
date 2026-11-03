"""Bütün testler sentetiktir; yanlışlıkla gerçek servise erişimi de engelle."""

import socket

import pytest


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Testlerde gerçek ağ erişimi yasak; MockTransport kullanın")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
