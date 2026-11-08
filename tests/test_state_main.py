import json
from unittest.mock import Mock

import pytest

from src.main import run
from src.opportunity_filter import classify
from src.state import State

PAGE = b'''<html><article><h1>Learn &amp; Earn Mission</h1><p>Join now.
Complete the quiz to earn 100 points. No purchase or deposit required.
Brazil is eligible. Deadline: December 31, 2099.</p></article></html>'''


def test_persistent_dedup_updates_only_relevant_fields(tmp_path, candidate, now):
    path = tmp_path / "state.json"
    state = State(path)
    op = classify(candidate("No purchase or deposit required."), now)
    assert state.changed(op)
    state.mark(op)
    assert not State(path).changed(op)
    op.score += 1
    assert not state.changed(op)
    op.deadline_at = "2026-11-30"
    assert state.changed(op)


def test_corrupted_state_fails_closed(tmp_path):
    path = tmp_path / "state.json"
    path.write_text('{"sent": []}')
    with pytest.raises(ValueError):
        State(path)


def setup_run(source):
    source.kind = "page"
    source.url = "https://example.org/mission"
    client = Mock()
    client.get.return_value = PAGE, source.url, "text/html"
    return client


def test_full_pipeline_and_second_run_not_repeated(source, tmp_path):
    client, bot = setup_run(source), Mock()
    state = State(tmp_path / "state.json")
    assert run([source], client, state, bot, tmp_path / "reports") == 0
    assert bot.send.call_count == 2  # Campanha + resumo diário.
    result = json.loads((tmp_path / "reports/run.json").read_text())
    assert result["sent"] == 1 and len(result["opportunities"]) == 1
    assert run([source], client, State(state.path), bot, tmp_path / "reports") == 0
    assert bot.send.call_count == 2


def test_failed_delivery_not_marked(source, tmp_path):
    client, bot = setup_run(source), Mock()
    bot.send.side_effect = RuntimeError("Telegram unavailable")
    state = State(tmp_path / "state.json")
    assert run([source], client, state, bot, tmp_path / "reports") == 2
    assert state.data["sent"] == {} and state.data["summaries"] == []


def test_dry_run_never_sends_or_writes_state(source, tmp_path):
    client, bot = setup_run(source), Mock()
    state = State(tmp_path / "state.json")
    assert run([source], client, state, bot, tmp_path / "reports", dry_run=True) == 0
    bot.send.assert_not_called()
    assert not state.path.exists()


def test_failed_source_is_visible(source, tmp_path):
    client, bot = Mock(), Mock()
    client.get.side_effect = RuntimeError("HTTP 403")
    assert run([source], client, State(tmp_path / "state.json"), bot, tmp_path / "reports") == 2
    result = json.loads((tmp_path / "reports/run.json").read_text())
    assert not result["sources"][0]["ok"] and result["errors"]
    assert "Cobertura parcial" in (tmp_path / "reports/summary.txt").read_text()
