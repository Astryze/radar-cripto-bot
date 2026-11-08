import json
from datetime import timedelta
from unittest.mock import Mock

from src.main import run
from src.models import Cost, Opportunity
from src.state import State
from src.utils import DeferredFetch, utcnow

PAGE = b'<article><h1>Quiz Mission</h1>Join now. Complete the quiz to earn 20 USDC. No purchase or deposit required. Brazil is eligible.</article>'


def source_page(source):
    source.kind = "page"
    source.url = "https://example.org/mission"
    return source


def test_summary_is_first_and_new_campaigns_are_tracked(source, tmp_path):
    source_page(source)
    client, bot = Mock(), Mock()
    client.get.return_value = PAGE, source.url, "text/html"
    state = State(tmp_path / "state.json")
    assert run([source], client, state, bot, tmp_path / "reports") == 0
    assert bot.send.call_args_list[0].args[0].startswith("RADAR CRIPTO — RELATÓRIO DIÁRIO")
    assert "NOVA OPORTUNIDADE" in bot.send.call_args_list[1].args[0]
    assert source.url in state.data["campaigns"]
    assert json.loads((tmp_path / "reports/run.json").read_text())["new_campaigns"] == 1


def test_202_is_pending_not_permanent_failure(source, tmp_path):
    client, bot = Mock(), Mock()
    retry = (utcnow() + timedelta(minutes=15)).isoformat()
    client.get.side_effect = DeferredFetch(202, retry, "https://example.org/results/1")
    state = State(tmp_path / "state.json")
    assert run([source], client, state, bot, tmp_path / "reports") == 0
    result = json.loads((tmp_path / "reports/run.json").read_text())
    assert result["pending_sources"] == 1 and result["errors"] == []
    assert result["sources"][0]["http_status"] == 202
    assert state.data["pending_sources"][source.id]["url"] == "https://example.org/results/1"


def test_202_monitor_result_is_used_next_run(source, tmp_path):
    source_page(source)
    client, bot = Mock(), Mock()
    state = State(tmp_path / "state.json")
    state.data["pending_sources"][source.id] = {"url": "https://example.org/result"}
    client.get.return_value = PAGE, "https://example.org/result", "text/html"
    assert run([source], client, state, bot, tmp_path / "reports") == 0
    assert client.get.call_args_list[0].args[0] == "https://example.org/result"
    assert source.id not in state.data["pending_sources"]


def test_recorded_deadline_closes_even_when_source_unavailable(source, tmp_path):
    source_page(source)
    state = State(tmp_path / "state.json")
    op = Opportunity("Quiz Mission", "Test", source.url, cost=Cost.FREE, official=True,
                      deadline="aberto", deadline_at=(utcnow() - timedelta(days=1)).isoformat(), source_id=source.id)
    state.mark(op)
    client, bot = Mock(), Mock()
    client.get.side_effect = RuntimeError("network unavailable")
    assert run([source], client, state, bot, tmp_path / "reports") == 2
    assert any("CAMPANHA ENCERRADA" in c.args[0] for c in bot.send.call_args_list)
    assert state.data["campaigns"][source.url]["latest"]["deadline"] == "encerrado"


def test_tracked_closed_page_does_not_need_reward_keywords(source, tmp_path):
    source_page(source)
    state = State(tmp_path / "state.json")
    op = Opportunity("Quiz Mission", "Test", source.url, cost=Cost.FREE, official=True, deadline="aberto", source_id=source.id)
    state.mark(op)
    client, bot = Mock(), Mock()
    client.get.return_value = (b'<article><h1>Quiz Mission</h1>This campaign has ended. Registration is closed. Thank you for your participation in our educational event.</article>', source.url, "text/html")
    assert run([source], client, state, bot, tmp_path / "reports") == 0
    assert any("CAMPANHA ENCERRADA" in c.args[0] for c in bot.send.call_args_list)
