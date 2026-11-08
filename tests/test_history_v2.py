import json

from src.models import Cost
from src.opportunity_filter import classify
from src.state import State, fingerprint


def test_migrate_v1_without_losing_delivery_or_summary(tmp_path, candidate, now):
    op = classify(candidate("No purchase or deposit required."), now)
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"version": 1, "sent": {op.url: fingerprint(op, legacy=True)}, "summaries": ["2026-11-08"]}))
    state = State(path)
    assert state.data["version"] == 2 and not state.changed(op)
    assert state.data["summaries"] == ["2026-11-08"]
    state.save()
    assert State(path).data["sent"] == state.data["sent"]


def test_possible_to_free_then_closed(tmp_path, candidate, now):
    state = State(tmp_path / "state.json")
    op = classify(candidate("Rules to be confirmed."), now)
    assert state.event(op) is None
    state.observe(op)
    op.cost = Cost.FREE
    assert state.event(op) == "gratuidade confirmada após investigação"
    state.observe(op, state.event(op))
    state.mark(op)
    assert state.event(op) is None
    op.deadline = "encerrado"
    assert state.event(op) == "campanha encerrada"
    state.observe(op, state.event(op))
    state.mark(op)
    assert state.event(op) is None


def test_failed_transition_survives_next_execution(tmp_path, candidate, now):
    state = State(tmp_path / "state.json")
    op = classify(candidate("No purchase or deposit required."), now)
    event = state.event(op)
    state.observe(op, event)
    state.save()  # Envio falhou: não marcar entregue.
    assert State(state.path).event(op) == event


def test_changed_reward_or_deadline_alerts_once(tmp_path, candidate, now):
    state = State(tmp_path / "state.json")
    op = classify(candidate("No purchase or deposit required."), now)
    state.mark(op)
    op.reward = "Earn 200 points"
    assert state.event(op)
    state.mark(op)
    assert state.event(op) is None
    op.deadline_at = "2099-12-30"
    assert state.event(op)
