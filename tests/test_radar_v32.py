"""Fixtures sintéticas para regressão. Nenhum catálogo ou campanha real."""
import json
from unittest.mock import Mock

from src.main import run
from src.models import Cost, Opportunity, Source
from src.multiplatform import zealy_catalog
from src.opportunity_filter import cost_evidence
from src.scoring import verified_alert
from src.state import State
from src.utils import DeferredFetch, FetchError


def test_fallback_preserves_primary_rate_limit(tmp_path):
    primary = 'https://example.org/news'
    fallback = 'https://example.net/SECURITY.md'
    source = Source('solana', 'Exemplo Bug Bounty', primary, 'page',
                    ['example.org', 'example.net'], rate_limit_fallback=fallback)
    client = Mock()
    body = b'# Example\nSubmit findings through the official form. The portal requires a non-refundable SOL burn per submission.'
    client.get.side_effect = [DeferredFetch(429, '2026-11-09T03:00:00Z'),
                              (body, fallback, 'text/plain'), (body, fallback, 'text/plain')]
    assert run([source], client, State(tmp_path / 'state'), None, tmp_path, dry_run=True) == 0
    row = json.loads((tmp_path / 'integrations/solana.json').read_text())
    assert row['primary_http_status'] == 429
    assert row['fallback_collected'] and row['primary_next_retry_at']
    assert cost_evidence(body.decode(), True)[0] == Cost.REQUIRED


def test_zealy_retains_catalog_after_one_community_fails(monkeypatch):
    monkeypatch.setenv('ZEALY_API_KEY', 'TESTE_OFFLINE')
    monkeypatch.delenv('ZEALY_USER_ID', raising=False)
    client = Mock()
    client.session.headers = {}
    client.get.side_effect = [FetchError('API recusou'), (b'[]', 'url', 'application/json')]
    scopes = {'enabled': True, 'permission': 'API_OFICIAL', 'read_only_key': True,
              'communities': ['first', 'second']}
    checks = []
    assert zealy_catalog(scopes, client, community_checks=checks) == ([], 'collected_api_catalog_partial')
    assert [(c['community'], c['status']) for c in checks] == [('first', 'failed'), ('second', 'catalog_read')]
    assert client.session.headers == {}


def test_alert_requires_redeemable_token_and_brazil():
    op = Opportunity('Exemplo', 'Teste', 'https://example.org', cost=Cost.FREE, deadline='aberto',
                     official=True, reward_status='confirmada', eligibility='Brasil confirmado',
                     investigation_status='concluída com material público',
                     conclusion='GRATUITA CONFIRMADA', reward_assets=[{'kind': 'token'}],
                     evidence={'gratuidade': ['rules'], 'recompensa': ['rules']})
    assert not verified_alert(op)
    op.evidence['resgate'] = ['rules']
    op.withdrawability = 'possibilidade de saque/negociação declarada pela fonte; requisitos pessoais não verificados'
    assert verified_alert(op)
    op.eligibility = 'desconhecida'
    assert not verified_alert(op)
