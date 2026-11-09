"""Testes offline com respostas simuladas e sem credenciais reais."""
from unittest.mock import Mock

import pytest

from src.galxe import galxe_catalog
from src.models import Cost, Opportunity
from src.scoring import opportunity_classification
from src.telegram_bot import TEST_MESSAGE, delivery_test
from src.utils import HttpClient, utcnow
from test_v25 import response


@pytest.mark.parametrize("status", [401, 403, 404, 429, 503])
def test_galxe_scope_failure_retains_other_scope(monkeypatch, status):
    monkeypatch.setenv("GALXE_ACCESS_TOKEN", "EXEMPLO")
    monkeypatch.setattr("src.galxe.validate_url", Mock())
    client = HttpClient(session=Mock(), sleep=Mock())
    client.session.post.side_effect = [
        response({"data": {"quests": {"list": [{"id": "qid", "name": "Teste"}]}}}),
        response({"data": {"quest": {"id": "qid", "space": {"id": "123"}}}}),
        response({}, status),
    ]
    config = {"enabled": True, "permission": "API_OFICIAL", "space_ids": ["123", "456"],
              "last_audit": utcnow().date().isoformat()}
    checks = []
    rows, result = galxe_catalog(config, client, space_checks=checks)
    assert [row["space_id"] for row in rows] == ["123"]
    assert result == "collected_api_catalog_partial"
    assert checks[1]["http_statuses"] == [status]


def test_telegram_sends_only_labeled_test():
    session = Mock()
    reply = session.post.return_value
    reply.status_code = 200
    reply.json.return_value = {"ok": True}
    assert delivery_test("123:fake_token", "-100200", session=session)["status"] == "telegram_api_accepted"
    assert session.post.call_args.kwargs["json"]["text"] == TEST_MESSAGE


def test_telegram_invalid_config_never_connects():
    session = Mock()
    result = delivery_test("https://example.com", "", session=session)
    assert result["status"] == "invalid_configuration"
    assert len(result["issues"]) == 2
    session.post.assert_not_called()


def test_free_label_requires_official_redemption_evidence():
    op = Opportunity("Exemplo", "Rede", "https://example.com", cost=Cost.FREE, official=True,
                     eligibility="Brasil confirmado", deadline="aberto")
    assert opportunity_classification(op) == "ZERO_INVESTMENT_UNCONFIRMED"
    op.eligibility = "Brasil não elegível"
    assert opportunity_classification(op) == "BRAZIL_INELIGIBLE"
    op.deadline = "encerrado"
    assert opportunity_classification(op) == "EXPIRED"
