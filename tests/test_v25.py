"""Verificação offline. Respostas HTTP simuladas não são consultas reais."""
import json
from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.galxe import ENDPOINT, galxe_catalog
from src.multiplatform import classify, financial_classification, integration_diagnostic, run, zealy_catalog
from src.platform_permissions import load_platforms
from src.state import State
from src.utils import DeferredFetch, FetchError, HttpClient, utcnow


def observations():
    return json.loads(Path('config/campaign_observations.json').read_text())['campaigns']


def test_binance_october_does_not_confirm_november():
    btc, trading = observations()
    assert btc['registration_cutoff'] is None
    assert btc['monthly_cap'] == 5000
    assert btc['kyc'].startswith('obrigatório')
    assert btc['reward_form'] == 'voucher de token' and btc['redeemable'] is None
    assert financial_classification(btc) == 'GRATUIDADE_NAO_CONFIRMADA'
    assert financial_classification(trading) == 'EXIGE_CAPITAL'
    assert classify(btc, {'name': 'Binance', 'permission': 'AUTORIZACAO_NECESSARIA'})['availability'] == 'não confirmada'


def test_unconfirmed_binance_only_reports_empty_summary(tmp_path):
    state = State(tmp_path / 'state.json')
    bot = Mock()
    for _ in range(2):
        assert run(load_platforms(), observations(), state, Mock(records=[]), bot,
                   tmp_path, send_empty_summary=True) == 0
    bot.send.assert_called_once()
    assert 'Nenhuma oportunidade que atenda a todos os critérios de gratuidade e resgate foi confirmada nesta execução.' in bot.send.call_args.args[0]
    report = json.loads((tmp_path / 'multiplatform.json').read_text())
    assert report['api_http_responses'] == report['verified_zero_investment'] == 0


@pytest.fixture
def galxe(monkeypatch):
    monkeypatch.setenv('GALXE_ACCESS_TOKEN', 'TESTE_OFFLINE')
    monkeypatch.setattr('src.galxe.validate_url', Mock())
    session = Mock(headers={})
    client = HttpClient(session=session, sleep=Mock())
    platform = {'enabled': True, 'permission': 'API_OFICIAL', 'space_ids': ['123'],
                'last_audit': utcnow().date().isoformat()}
    return platform, client


def response(payload, status=200, headers=None):
    result = Mock(status_code=status, headers=headers or {})
    result.iter_content.return_value = [json.dumps(payload).encode()]
    manager = Mock()
    manager.__enter__ = Mock(return_value=result)
    manager.__exit__ = Mock(return_value=False)
    return manager


def test_galxe_discovery_and_details(galxe):
    platform, client = galxe
    client.session.post.side_effect = [
        response({'data': {'quests': {'list': [{'id': 'quest1', 'name': 'Teste', 'status': 'Active'}],
                                      'pageInfo': {'hasNextPage': True}}}}),
        response({'data': {'quest': {'id': 'quest1', 'gasType': 'Gasless', 'loyaltyPoints': 25}}}),
    ]
    rows, status = galxe_catalog(platform, client)
    assert status == 'collected_api_catalog_partial'
    assert rows[0]['loyaltyPoints'] == 25 and rows[0]['reward_verified'] is False
    assert rows[0]['financial_classification'] == 'GRATUIDADE_NAO_CONFIRMADA'
    assert rows[0]['brazil'] == 'desconhecido'
    for call in client.session.post.call_args_list:
        assert call.args == (ENDPOINT,)
        assert call.kwargs['allow_redirects'] is False
        assert call.kwargs['json']['query'].startswith('query ')
    assert 'TESTE_OFFLINE' not in json.dumps(client.records)


@pytest.mark.parametrize('reason', ['missing', 'expired', 'disabled'])
def test_galxe_skips_without_authorization(galxe, monkeypatch, reason):
    platform, client = galxe
    if reason == 'missing':
        monkeypatch.delenv('GALXE_ACCESS_TOKEN')
    elif reason == 'disabled':
        platform['enabled'] = False
    else:
        platform['last_audit'] = (utcnow() - timedelta(days=31)).isoformat()
    assert galxe_catalog(platform, client)[1].startswith('skipped')
    client.session.post.assert_not_called()


@pytest.mark.parametrize('http_status', [302, 401, 403])
def test_galxe_stops_on_redirect_and_auth_failure(galxe, http_status):
    platform, client = galxe
    client.session.post.return_value = response({}, http_status)
    with pytest.raises(FetchError, match=f'Galxe HTTP {http_status}'):
        galxe_catalog(platform, client)
    client.session.post.assert_called_once()


def test_galxe_cooldown(galxe):
    platform, client = galxe
    client.session.post.return_value = response({}, 429, {'Retry-After': '3600'})
    with pytest.raises(DeferredFetch):
        galxe_catalog(platform, client)
    assert galxe_catalog(platform, client)[1] == 'skipped_api_cooldown'
    client.session.post.assert_called_once()


def test_zealy_deleted_quests_excluded(monkeypatch):
    monkeypatch.setenv('ZEALY_API_KEY', 'TESTE_OFFLINE')
    client = Mock()
    client.session.headers = {}
    client.get.return_value = (b'[{"published":true,"deleted":true,"id":"q","name":"Teste"}]',
                               'https://api-v2.zealy.io', 'application/json')
    platform = {'enabled': True, 'permission': 'API_OFICIAL', 'communities': ['example'], 'read_only_key': True}
    assert zealy_catalog(platform, client)[0] == []
    platform['permission'] = 'AUTORIZACAO_NECESSARIA'
    assert zealy_catalog(platform, client)[1] == 'skipped_permission'
    client.get.assert_called_once()


def test_galxe_empty_list_is_a_successful_observation(galxe):
    platform, client = galxe
    client.session.post.return_value = response({'data': {'quests': {'list': []}}})
    assert galxe_catalog(platform, client) == ([], 'collected_api_catalog')
    assert client.records[0]['attempted_at']


def test_galxe_missing_list_is_an_error(galxe):
    platform, client = galxe
    client.session.post.return_value = response({'data': {'quests': None}})
    with pytest.raises(FetchError, match='Listagem Galxe inválida'):
        galxe_catalog(platform, client)


def test_galxe_graphql_quota_error_sets_cooldown(galxe):
    platform, client = galxe
    client.session.post.return_value = response({'errors': [{'extensions': {'http_status': 429}}]})
    with pytest.raises(DeferredFetch):
        galxe_catalog(platform, client)
    assert galxe_catalog(platform, client)[1] == 'skipped_api_cooldown'
    client.session.post.assert_called_once()


@pytest.mark.parametrize('change', [
    {'distribution': 'sorteio'}, {'redeemable': None}, {'brazil': 'desconhecido'},
    {'availability': 'encerrada'}, {'financial_classification': 'GRATUIDADE_NAO_CONFIRMADA'},
])
def test_verified_opportunity_requires_all_criteria(change):
    from src.multiplatform import verified_opportunity

    eligible = {
        'official': True, 'reward_verified': True, 'evidence': [{'url': ENDPOINT}],
        'reward_type': 'BTC', 'redeemable': True, 'brazil': 'confirmado', 'availability': 'aberta',
        'financial_classification': 'ZERO_INVESTIMENTO',
        'verification_status': 'revisão manual recente; sem reconsulta automática',
    }
    assert verified_opportunity(eligible)
    assert not verified_opportunity({**eligible, **change})


def test_report_keeps_http_evidence_without_headers(tmp_path, monkeypatch):
    client = Mock(records=[])

    def collect(platform, http, *, space_checks):
        http.records.append({'url': ENDPOINT, 'status': 403, 'attempted_at': utcnow().isoformat(),
                             'headers': {'access-token': 'SOMENTE_TESTE'}})
        raise FetchError('Galxe HTTP 403')

    monkeypatch.setattr('src.multiplatform.galxe_catalog', collect)
    assert run(load_platforms(), [], State(tmp_path / 'state'), client, None, tmp_path, True) == 2
    output = (tmp_path / 'multiplatform.json').read_text()
    evidence = next(source for source in json.loads(output)['sources'] if source['id'] == 'galxe')
    assert evidence['http_responses'][0]['status'] == 403
    assert 'SOMENTE_TESTE' not in output


def test_diagnostic_distinguishes_missing_secret_and_scope(monkeypatch):
    from src.multiplatform import integration_diagnostic

    monkeypatch.delenv('GALXE_ACCESS_TOKEN', raising=False)
    platform = {'id': 'galxe', 'space_ids': []}
    health = {'status': 'skipped_missing_access_token_or_spaces', 'campaigns_found': []}
    result = integration_diagnostic(platform, health)
    assert result['credential_available'] is False and result['scope_configured'] is False
    monkeypatch.setenv('GALXE_ACCESS_TOKEN', 'SOMENTE_TESTE')
    result = integration_diagnostic(platform, health)
    assert result['credential_available'] is True
    assert result['message'] == 'escopo autorizado não configurado (space_ids)'
    assert 'SOMENTE_TESTE' not in json.dumps(result)


def test_galxe_graphql_denial_is_not_empty_catalog(galxe, tmp_path):
    platform, client = galxe
    platform.update(id='galxe', limitations='')
    client.session.post.return_value = response({'errors': [{'extensions': {'http_status': 403}}]})
    assert run([platform], [], State(tmp_path / 'state'), client, None, tmp_path, True) == 2
    report = json.loads((tmp_path / 'multiplatform.json').read_text())
    source = report['sources'][0]
    assert source['http_status'] == 200
    assert source['integration']['message'] == 'autorização negada pela API (403)'


def test_empty_catalog_diagnostic_differs_from_success_with_results():
    from src.multiplatform import integration_diagnostic

    platform = {'id': 'zealy'}
    health = {'status': 'collected_api_catalog', 'campaigns_found': []}
    assert integration_diagnostic(platform, health)['message'] == 'consulta concluída sem resultados'
    health['campaigns_found'].append({'id': 'example'})
    assert integration_diagnostic(platform, health)['message'] == 'conectada e consultada, 1 resultado(s)'


@pytest.mark.parametrize(('connector', 'source', 'field', 'entries'), [
    (galxe_catalog, 'galxe', 'space_ids', '123'),
    (galxe_catalog, 'galxe', 'space_ids', ['123', '123']),
    (zealy_catalog, 'zealy', 'communities', ['../outro']),
    (zealy_catalog, 'zealy', 'communities', [42]),
])
def test_invalid_scope_stops_before_network(connector, source, field, entries):
    platform = {'id': source, 'enabled': True, 'permission': 'API_OFICIAL', field: entries}
    client = Mock()
    rows, status = connector(platform, client)
    assert rows == [] and status == 'skipped_invalid_scope'
    assert not client.mock_calls
    diagnostic = integration_diagnostic(platform, {'status': status, 'campaigns_found': []})
    assert f'configuração inválida em {field}' in diagnostic['issues']


def test_zealy_requires_read_only_declaration(monkeypatch):
    monkeypatch.setenv('ZEALY_API_KEY', 'SOMENTE_TESTE')
    platform = {'enabled': True, 'permission': 'API_OFICIAL', 'communities': ['example']}
    client = Mock()
    assert zealy_catalog(platform, client) == ([], 'skipped_read_only_not_declared')
    client.get.assert_not_called()


def test_zealy_sanitizes_catalog_and_flags_local_truncation(monkeypatch):
    monkeypatch.setenv('ZEALY_API_KEY', 'SOMENTE_TESTE')
    platform = {'enabled': True, 'permission': 'API_OFICIAL', 'communities': ['example'], 'read_only_key': True}
    item = {'id': 'example', 'name': 'Exemplo', 'published': True,
            'rewards': [{'type': 'xp'}, {'type': 'token'}, {'type': 'nft'}],
            'tasks': [{'type': 'api', 'settings': {'apiKey': 'CHAVE_PRIVADA_EXEMPLO'}}],
            'conditions': [{'type': 'date', 'operator': '<', 'value': '2026-12-31T00:00:00Z'}]}
    client = Mock()
    client.session.headers = {}
    client.get.return_value = (json.dumps([item] * 51).encode(), 'url', 'application/json')
    rows, status = zealy_catalog(platform, client)
    assert status.endswith('_partial') and len(rows) == 50
    assert rows[0]['reward_types'] == ['nft', 'token', 'xp']
    assert rows[0]['date_conditions'][0]['operator'] == '<'
    assert rows[0]['financial_classification'] == 'GRATUIDADE_NAO_CONFIRMADA'
    assert 'CHAVE_PRIVADA_EXEMPLO' not in json.dumps(rows)


def test_zealy_never_follows_redirect_to_another_scope(monkeypatch):
    monkeypatch.setattr('src.utils.validate_url', Mock())
    monkeypatch.setattr('src.platform_permissions.guard_request', Mock())
    session = Mock(headers={})
    session.get.return_value = Mock(
        status_code=302, headers={'Location': '/public/communities/other/quests'}
    )
    with pytest.raises(FetchError, match='Redirecionamento Zealy'):
        HttpClient(session=session).get(
            'https://api-v2.zealy.io/public/communities/example/quests', ['api-v2.zealy.io'])
    session.get.assert_called_once()


def test_galxe_rejects_detail_from_another_space(monkeypatch):
    from src.utils import utcnow

    monkeypatch.setenv('GALXE_ACCESS_TOKEN', 'SOMENTE_TESTE')
    monkeypatch.setattr('src.galxe.validate_url', Mock())
    platform = {'enabled': True, 'permission': 'API_OFICIAL', 'space_ids': ['123'],
                'last_audit': utcnow().date().isoformat()}
    client = HttpClient(session=Mock(headers={}), sleep=Mock())
    client.session.post.side_effect = [
        response({'data': {'quests': {'list': [{'id': 'quest1'}]}}}),
        response({'data': {'quest': {'id': 'quest1', 'space': {'id': '999'}}}}),
    ]
    with pytest.raises(FetchError, match='fora do Space autorizado'):
        galxe_catalog(platform, client)
