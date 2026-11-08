import socket
from unittest.mock import Mock

import pytest
import requests

from src.utils import FetchError, HttpClient, canonical_url, validate_url


@pytest.mark.parametrize("url", [
    "http://example.org/", "https://user:pass@example.org", "https://example.org:8080/",
    "https://127.0.0.1/", "https://[::1]/", "https://169.254.169.254/", "https://10.0.0.1/",
    "https://localhost/", "https://metadata.internal/", "https://example.org\\@evil.test",
    "https://example.org/%0a".replace("%0a", "\n"), "file:///etc/passwd",
    "https://example.org.evil.test/", "https://example.org@evil.test/",
])
def test_url_security(url):
    with pytest.raises(ValueError):
        validate_url(url, ["example.org"])


def test_dns_private(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **kw: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.1", 443))])
    with pytest.raises(ValueError):
        validate_url("https://example.org", ["example.org"])


def test_canonical_retains_campaign_identifier():
    assert canonical_url("https://example.org/a/?utm_source=x&id=2#prize") == "https://example.org/a?id=2"


def test_transient_retry(response):
    session, sleep = Mock(), Mock()
    session.get.side_effect = [response(status=503), response(data=b"ok")]
    data, final, kind = HttpClient(session, sleep).get("https://example.org", ["example.org"])
    assert data == b"ok" and session.get.call_count == 2
    sleep.assert_called_once_with(1)


def test_transport_attempts_bounded():
    session, sleep = Mock(), Mock()
    session.get.side_effect = requests.Timeout("unsafe credential-bearing URL")
    with pytest.raises(FetchError, match="Falha de transporte"):
        HttpClient(session, sleep).get("https://example.org", ["example.org"])
    assert session.get.call_count == 3


def test_404_not_retried(response):
    session = Mock()
    session.get.return_value = response(status=404)
    with pytest.raises(FetchError, match="HTTP 404"):
        HttpClient(session).get("https://example.org", ["example.org"])
    assert session.get.call_count == 1


def test_redirect_cannot_escape_allowlist(response):
    session = Mock()
    session.get.return_value = response(status=302, headers={"Location": "https://evil.test/phish"})
    with pytest.raises(ValueError):
        HttpClient(session).get("https://example.org", ["example.org"])
    assert session.get.call_count == 1


def test_content_limit(response):
    session = Mock()
    session.get.return_value = response(data=b"x" * 2_000_001)
    with pytest.raises(FetchError, match="2 MB"):
        HttpClient(session).get("https://example.org", ["example.org"])
