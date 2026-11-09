"""Verificação offline do contrato e do transporte Zealy."""
import json
from unittest.mock import Mock

import pytest
import requests

from src.multiplatform import zealy_catalog
from src.utils import DeferredFetch, FetchError, HttpClient, utcnow
from src.zealy_integration import BASE, ZealyIntegration

USER = '123e4567-e89b-12d3-a456-426614174000'


def response(payload=None, status=200, headers=None):
    result = Mock(status_code=status, headers={'Content-Type': 'application/json', **(headers or {})})
    result.iter_content.return_value = [] if payload is None else [json.dumps(payload).encode()]
    return result


@pytest.fixture
def integration(monkeypatch):
    monkeypatch.setenv('ZEALY_API_KEY', 'SOMENTE_TESTE')
    monkeypatch.setattr('src.utils.validate_url', Mock())
    platform = {'id': 'zealy', 'enabled': True, 'permission': 'API_OFICIAL',
                'communities': ['example'], 'last_audit': utcnow().date().isoformat(),
                'read_only_key': True}
    monkeypatch.setattr('src.platform_permissions.load_platforms', lambda: [platform])
    return ZealyIntegration(platform, HttpClient(session=Mock(headers={}), sleep=Mock()))


def test_profile_lookup_and_cache_are_sanitized(integration):
    client = integration.client
    client.session.get.return_value = response({
        'id': USER, 'xp': 12, 'level': 2, 'rank': 3, 'role': 'guest', 'isBanned': False,
        'email': 'pessoa@example.org', 'verifiedBlockchainAddresses': {'eth-mainnet': ['private-address']},
        'unVerifiedBlockchainAddresses': {'eth-mainnet': []},
    })
    result = integration.get_user('example', USER)
    assert result['xp'] == 12 and result['level'] == 2 and result['rank'] == 3
    assert result['membership'] == 'confirmada' and not result['banned']
    assert result['verified_wallets'] == 1 and result['unverified_wallets'] == 0
    assert integration.get_user('example', USER) == result
    client.session.get.assert_called_once()
    assert client.session.get.call_args.kwargs['headers'] == {'x-api-key': 'SOMENTE_TESTE'}
    assert client.records[0]['url'].endswith('users/{userId}')
    assert client.cache == {}
    assert 'private-address' not in json.dumps(result)


def test_users_is_filtered_lookup_not_member_listing(integration):
    client = integration.client
    client.session.get.return_value = response({'id': USER, 'isBanned': True, 'role': 'banned'})
    assert integration.lookup_user('example', 'email', 'pessoa@example.org')['banned']
    assert client.session.get.call_args.args[0] == f'{BASE}/example/users?email=pessoa%40example.org'
    assert client.records[0]['url'] == f'{BASE}/example/users'


def test_invites_uses_documented_pagination_and_aggregates(integration):
    client = integration.client
    client.session.get.side_effect = [
        response([{'status': 'active'}, {'status': 'pending'}]),
        response([{'status': 'consumed'}]),
    ]
    assert integration.invites('example', USER, page_size=2) == {
        'counts': {'active': 1, 'pending': 1, 'consumed': 1}, 'pages': 2, 'partial': False}
    assert [call.args[0].split('?')[1] for call in client.session.get.call_args_list] == [
        'page=1&page_size=2', 'page=2&page_size=2']


def test_reviews_uses_only_flags_and_stars(integration):
    integration.client.session.get.return_value = response({'flags': 1, 'stars': 2, 'extra': 'privado'})
    assert integration.reviews('example', USER) == {'flags': 1, 'stars': 2}
    assert integration.client.records[0]['url'].endswith('reviews/users/{id}')


def test_membership_post_requires_explicit_compatible_access(integration):
    client = integration.client
    integration.platform['allow_member_post'] = True
    with pytest.raises(PermissionError):
        integration.membership('example', USER)
    client.session.post.assert_not_called()
    integration.platform['read_only_key'] = False
    client.session.post.return_value = response()
    assert integration.membership('example', USER) == {'membership': 'confirmada'}
    assert client.session.post.call_args.args[0] == f'{BASE}/example/member'
    assert client.session.post.call_args.kwargs['json'] == {'userId': USER}
    assert client.session.post.call_args.kwargs['allow_redirects'] is False


def test_missing_key_and_out_of_scope_block_before_network(integration, monkeypatch):
    with pytest.raises(PermissionError):
        integration.get_user('other', USER)
    monkeypatch.delenv('ZEALY_API_KEY')
    with pytest.raises(PermissionError, match='indisponível'):
        integration.get_user('example', USER)
    integration.client.session.get.assert_not_called()


@pytest.mark.parametrize('status', [401, 403, 404])
def test_terminal_http_errors_are_not_retried(integration, status):
    client = integration.client
    client.session.get.return_value = response({'private': 'corpo sensível'}, status)
    with pytest.raises(FetchError, match=f'HTTP {status}') as error:
        integration.get_user('example', USER)
    assert 'corpo sensível' not in str(error.value)
    client.session.get.assert_called_once()


def test_invalid_profile_is_not_cached(integration):
    integration.client.session.get.return_value = response({'id': USER})
    with pytest.raises(FetchError, match='banimento'):
        integration.get_user('example', USER)
    assert integration.cache == {}


def test_rate_limit_preserves_retry_after(integration):
    client = integration.client
    client.session.get.return_value = response({}, 429, {'Retry-After': '3600'})
    with pytest.raises(DeferredFetch) as error:
        integration.invites('example', USER)
    assert error.value.status == 429
    with pytest.raises(DeferredFetch):
        integration.invites('example', USER)
    client.session.get.assert_called_once()


def test_network_failure_retries_and_sanitizes(integration):
    client = integration.client
    client.session.get.side_effect = requests.ConnectionError('SOMENTE_TESTE')
    with pytest.raises(FetchError, match='Falha de transporte') as error:
        integration.get_user('example', USER)
    assert 'SOMENTE_TESTE' not in str(error.value)
    assert client.session.get.call_count == client.attempts


def test_catalog_uses_optional_profile_but_keeps_eligibility_unconfirmed(integration, monkeypatch):
    monkeypatch.setenv('ZEALY_USER_ID', USER)
    client = integration.client
    client.session.get.side_effect = [
        response([{'id': 'quest', 'name': 'Teste', 'published': True, 'conditionOperator': 'AND',
                   'conditions': [{'type': 'date', 'operator': '<', 'value': '2024-01-01'}],
                   'rewards': [{'type': 'xp', 'value': 20}]}]),
        response({'id': USER, 'role': 'guest', 'isBanned': False, 'xp': 10}),
    ]
    rows, status = zealy_catalog(integration.platform, client)
    assert status == 'collected_api_catalog'
    row = rows[0]
    assert row['availability'] == 'encerrada' and row['participation']['membership'] == 'confirmada'
    assert row['xp_rewards'] == [20]
    assert row['brazil'] == 'desconhecido' and row['financial_classification'] == 'GRATUIDADE_NAO_CONFIRMADA'
    assert USER not in json.dumps(rows + client.records)
