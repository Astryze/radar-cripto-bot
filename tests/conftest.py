import socket
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from src.models import Candidate, Source


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Testes não podem usar rede nem Telegram real")
    monkeypatch.setattr("requests.sessions.Session.request", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **kw: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))])


@pytest.fixture
def now():
    return datetime(2026, 11, 8, 12, tzinfo=timezone.utc)


@pytest.fixture
def source():
    return Source("official", "Projeto Exemplo", "https://example.org/feed", "feed", ["example.org"])


@pytest.fixture
def candidate(source):
    def make(text, verified=True, title="Example Learn & Earn Mission"):
        return Candidate(title, "https://example.org/mission", source,
                         "Join now. Complete the quiz to earn 100 points.\n" + text,
                         verified=verified)
    return make


@pytest.fixture
def response():
    def make(data=b"", status=200, content_type="text/html", payload=None, headers=None):
        r = Mock(status_code=status)
        r.headers = {"Content-Type": content_type, **(headers or {})}
        r.iter_content.return_value = [data]
        r.json.return_value = payload if payload is not None else {"ok": True}
        return r
    return make
