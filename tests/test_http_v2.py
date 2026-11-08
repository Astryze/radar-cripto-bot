from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from src.utils import DeferredFetch, FetchError, HttpClient, retry_after_seconds

NOW = datetime(2026, 11, 8, 13, tzinfo=timezone.utc)


@pytest.mark.parametrize("value,expected", [("10", 10), ("-1", None), ("invalid", None),
    ("Sun, 08 Nov 2026 13:00:15 GMT", 15), ("Sun, 08 Nov 2026 12:00:00 GMT", 0), ("inf", None)])
def test_retry_after_formats(value, expected):
    assert retry_after_seconds(value, NOW) == expected


def test_429_respects_header_and_jitter(response):
    session, sleep = Mock(), Mock()
    session.get.side_effect = [response(status=429, headers={"Retry-After": "7"}), response(data=b"ok")]
    client = HttpClient(session, sleep, jitter=lambda: 0.5, now=lambda: NOW)
    assert client.get("https://example.org/mission", ["example.org"])[0] == b"ok"
    sleep.assert_called_once_with(7)
    assert [r["status"] for r in client.records] == [429, 200]


def test_long_retry_after_defers_without_early_retry(response):
    session, sleep = Mock(), Mock()
    session.get.return_value = response(status=429, headers={"Retry-After": "3600"})
    client = HttpClient(session, sleep, now=lambda: NOW)
    with pytest.raises(DeferredFetch) as exc:
        client.get("https://example.org/a", ["example.org"])
    assert exc.value.next_retry_at == "2026-11-08T14:00:00+00:00"
    with pytest.raises(DeferredFetch):
        client.get("https://example.org/b", ["example.org"])
    assert session.get.call_count == 1
    sleep.assert_not_called()


def test_429_never_hammers_source(response):
    session = Mock()
    session.get.return_value = response(status=429)
    client = HttpClient(session, Mock(), jitter=lambda: 0)
    with pytest.raises(DeferredFetch):
        client.get("https://example.org/a", ["example.org"])
    assert session.get.call_count == 2


@pytest.mark.parametrize("status", [403, 404])
def test_unavailable_not_retried(status, response):
    session = Mock()
    session.get.return_value = response(status=status)
    with pytest.raises(FetchError, match=str(status)):
        HttpClient(session, Mock()).get("https://example.org/a", ["example.org"])
    assert session.get.call_count == 1


@pytest.mark.parametrize("status", [500, 501, 502, 503, 504, 599])
def test_server_failure_bounded(status, response):
    session, sleep = Mock(), Mock()
    session.get.return_value = response(status=status)
    with pytest.raises(DeferredFetch):
        HttpClient(session, sleep, jitter=lambda: 0.25).get("https://example.org/a", ["example.org"])
    assert session.get.call_count == 3
    assert [c.args[0] for c in sleep.call_args_list] == [1.25, 2.25]


def test_202_pending_and_explicit_monitor_only(response):
    session = Mock()
    session.get.return_value = response(status=202, headers={"Location": "/jobs/123", "Retry-After": "60"})
    client = HttpClient(session, Mock(), now=lambda: NOW)
    with pytest.raises(DeferredFetch) as exc:
        client.get("https://example.org/campaigns", ["example.org"])
    assert exc.value.status == 202
    assert exc.value.monitor_url == "https://example.org/jobs/123"
    assert session.get.call_count == 1


def test_202_never_invents_endpoint(response):
    session = Mock()
    session.get.return_value = response(status=202)
    with pytest.raises(DeferredFetch) as exc:
        HttpClient(session, Mock()).get("https://example.org/a", ["example.org"])
    assert exc.value.monitor_url is None


def test_202_monitor_cannot_escape_allowlist(response):
    session = Mock()
    session.get.return_value = response(status=202, headers={"Location": "https://evil.test/job"})
    with pytest.raises(ValueError):
        HttpClient(session, Mock()).get("https://example.org/a", ["example.org"])
    assert session.get.call_count == 1


def test_cache_reuses_successful_official_policy(response):
    session = Mock()
    session.get.return_value = response(data=b"policy")
    client = HttpClient(session, Mock())
    assert client.get("https://example.org/faq", ["example.org"]) == client.get("https://example.org/faq", ["example.org"])
    assert session.get.call_count == 1
