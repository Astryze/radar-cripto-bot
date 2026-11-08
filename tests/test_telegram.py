from unittest.mock import Mock

import pytest
import requests

from src.telegram_bot import TelegramBot, split_message
from src.utils import FetchError


def test_send_splits_and_disables_previews(response):
    session = Mock()
    session.post.return_value = response()
    TelegramBot("test-placeholder", "test-chat", session, Mock()).send("a" * 5000)
    assert session.post.call_count == 2
    for call in session.post.call_args_list:
        payload = call.kwargs["json"]
        assert len(payload["text"]) <= 4096
        assert "parse_mode" not in payload
        assert payload["link_preview_options"]["is_disabled"]


def test_emoji_splitting():
    text = "🚀" * 6000
    chunks = split_message(text)
    assert "".join(chunks) == text
    assert all(len(s.encode("utf-16-le")) // 2 <= 4096 for s in chunks)


def test_429_retry_after(response):
    session, sleep = Mock(), Mock()
    session.post.side_effect = [response(status=429, payload={"ok": False, "error_code": 429,
        "parameters": {"retry_after": 3}}), response()]
    TelegramBot("test", "test", session, sleep).send("message")
    assert session.post.call_count == 2
    assert sleep.call_args_list[0].args == (3,)


def test_failed_delivery_raises(response):
    session = Mock()
    session.post.return_value = response(status=403, payload={"ok": False, "description": "token secret"})
    with pytest.raises(FetchError) as error:
        TelegramBot("test", "test", session, Mock()).send("message")
    assert "token secret" not in str(error.value)
    assert session.post.call_count == 1


def test_timeout_never_exposes_url_or_immediately_retries():
    session = Mock()
    session.post.side_effect = requests.Timeout("https://api.telegram.org/bot123:secret")
    with pytest.raises(FetchError) as error:
        TelegramBot("test", "test", session, Mock()).send("message")
    assert "secret" not in str(error.value)
    assert session.post.call_count == 1


def test_missing_credentials():
    with pytest.raises(ValueError):
        TelegramBot(None, None)


def test_pasted_secret_whitespace_is_trimmed(response):
    session = Mock()
    session.post.return_value = response()
    TelegramBot("  123:placeholder\n", " test-chat\r\n", session, Mock()).send("test")
    args, kwargs = session.post.call_args
    assert args[0] == "https://api.telegram.org/bot123:placeholder/sendMessage"
    assert kwargs["json"]["chat_id"] == "test-chat"


def test_token_cannot_inject_url_path():
    with pytest.raises(ValueError):
        TelegramBot("token/another-method", "test")


def test_chat_not_found_diagnostic(response):
    session = Mock()
    session.post.return_value = response(status=400, payload={"ok": False, "description": "Bad Request: chat not found"})
    with pytest.raises(FetchError, match="TELEGRAM_CHAT_ID"):
        TelegramBot("test", "test", session, Mock()).send("test")


def test_api_ok_false_even_with_http_200(response):
    session = Mock()
    session.post.return_value = response(payload={"ok": False, "error_code": 400})
    with pytest.raises(FetchError):
        TelegramBot("test", "test", session, Mock()).send("message")
