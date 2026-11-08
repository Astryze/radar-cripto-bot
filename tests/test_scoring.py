import pytest

from src.models import Cost, Opportunity
from src.scoring import actionable, score


def ideal(**kwargs):
    values = dict(title="Test", project="Test", url="https://example.org/quest", cost=Cost.FREE,
                  reward_status="confirmada", effort="baixo", official=True,
                  deadline="aberto", eligibility="Brasil confirmado")
    return Opportunity(**(values | kwargs))


def test_ideal():
    op = score(ideal())
    assert op.score == 100 and op.priority == "alta" and actionable(op)


@pytest.mark.parametrize("cost", [Cost.REQUIRED, Cost.POSSIBLE, Cost.UNKNOWN, Cost.GAS])
def test_only_zero_cost_alerts(cost):
    op = score(ideal(cost=cost))
    assert op.priority != "alta"
    assert not actionable(op)


@pytest.mark.parametrize("kwargs", [{"deadline": "encerrado"}, {"eligibility": "Brasil não elegível"},
                                    {"evidence": {"pausa": ["paused"]}}])
def test_unavailable(kwargs):
    op = score(ideal(**kwargs))
    assert op.score == 0 and not actionable(op)


def test_unknown_brazil_not_high_priority():
    assert score(ideal(eligibility="desconhecida")).priority == "média"
