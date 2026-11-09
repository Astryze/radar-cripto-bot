"""Consultas GraphQL documentadas, limitadas aos Spaces configurados."""
import json
import os
import re
from datetime import timedelta
from urllib.parse import urlsplit

import requests

from .integration_setup import integration_setup
from .utils import DeferredFetch, FetchError, MAX_BYTES, parse_date, retry_after_seconds, utcnow, validate_url

ENDPOINT = 'https://graphigo-business.prd.galaxy.eco/query'
HOST = urlsplit(ENDPOINT).hostname
LIST = """query GetSpaceQuests($input: ListQuestInput!) {
  quests(input: $input) {
    totalCount pageInfo { hasNextPage }
    list { id name type status participantsCount loyaltyPoints startTime endTime }
  }
}"""
DETAIL = """query GetQuest($id: ID!) {
  quest(id: $id) {
    id name type status startTime endTime cap participantsCount loyaltyPoints gasType chain
    description space { id }
  }
}"""
class GalxeAuthorizationError(FetchError):
    def __init__(self, status):
        self.status = status
        super().__init__('Acesso Galxe rejeitado')


FIELDS = ('id', 'name', 'type', 'status', 'startTime', 'endTime', 'cap',
          'participantsCount', 'loyaltyPoints', 'gasType', 'chain')


def _query(client, token, query, variables):
    last = client._last_request.get(HOST)
    if last is not None:
        client.sleep(max(0, 1 - (client.clock() - last)))
    client._last_request[HOST] = client.clock()
    try:
        with client.session.post(
            ENDPOINT, json={'query': query, 'variables': variables},
            headers={'access-token': token}, allow_redirects=False, stream=True, timeout=(5, 15),
        ) as response:
            status = response.status_code
            client.records.append({'url': ENDPOINT, 'status': status,
                                   'attempted_at': client.now().isoformat()})
            if status == 429:
                wait = retry_after_seconds(response.headers.get('Retry-After'), client.now())
                client._defer(ENDPOINT, 429, max(wait or 0, 900))
            if status != 200:
                raise FetchError(f'Galxe HTTP {status}')
            body = bytearray()
            for chunk in response.iter_content(65536):
                body.extend(chunk)
                if len(body) > MAX_BYTES:
                    raise FetchError('Resposta Galxe acima do limite')
    except requests.RequestException:
        raise FetchError('Falha de transporte Galxe') from None
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise FetchError('Resposta Galxe inválida')
    if payload.get('errors'):
        for error in payload['errors']:
            extensions = error.get('extensions') if isinstance(error, dict) else None
            status = extensions.get('http_status') if isinstance(extensions, dict) else None
            if status == 429:
                client._defer(ENDPOINT, 429, 900)
            if status in (401, 403):
                raise GalxeAuthorizationError(status)
        raise FetchError('Consulta Galxe rejeitada')
    if not isinstance(payload.get('data'), dict):
        raise FetchError('Resposta Galxe sem dados')
    return payload['data']


def galxe_catalog(platform, client, *, space_checks=None):
    token = os.getenv('GALXE_ACCESS_TOKEN', '').strip()
    spaces = platform.get('space_ids', [])
    if not platform['enabled'] or platform['permission'] != 'API_OFICIAL':
        return [], 'skipped_permission'
    setup = integration_setup(platform, 'galxe')
    if not setup['scope_valid']:
        return [], 'skipped_invalid_scope'
    if not token or not spaces:
        return [], 'skipped_missing_access_token_or_spaces'
    if not setup['credential_format_valid']:
        return [], 'skipped_invalid_credential'
    audit = parse_date(platform.get('last_audit'))
    now = utcnow()
    if not audit or not now - timedelta(days=30) <= audit <= now:
        return [], 'skipped_expired_audit'
    until = parse_date(client.cooldowns.get(HOST, {}).get('until'))
    if until and until > now:
        return [], 'skipped_api_cooldown'
    validate_url(ENDPOINT, [HOST])
    catalog = []
    truncated = False
    failures = []
    successful = 0
    for space in spaces:
        before, row_start = len(client.records), len(catalog)
        check = {'space_id': space, 'endpoint': ENDPOINT, 'attempted_at': client.now().isoformat()}
        if space_checks is not None:
            space_checks.append(check)
        try:
            truncated |= _read_space(client, token, space, catalog)
        except (FetchError, ValueError) as exc:
            failures.append(exc)
            check.update(status='failed', error=type(exc).__name__, api_status=getattr(exc, 'status', None))
        else:
            successful += 1
            check['status'] = 'catalog_read' if len(catalog) > row_start else 'empty'
        check.update(http_statuses=[row['status'] for row in client.records[before:]],
                     results=len(catalog) - row_start)
        if failures and isinstance(failures[-1], DeferredFetch):
            for remaining in spaces[spaces.index(space) + 1:]:
                if space_checks is not None:
                    space_checks.append({'space_id': remaining, 'status': 'cooldown', 'results': 0})
            break
    if failures and not successful and not catalog:
        raise failures[0]
    return catalog, 'collected_api_catalog_partial' if truncated or failures else 'collected_api_catalog'


def _read_space(client, token, space, catalog):
    listing = _query(client, token, LIST, {'input': {
        'spaceId': space, 'statuses': ['Active', 'NotStarted'], 'first': 20,
    }}).get('quests')
    if not isinstance(listing, dict) or not isinstance(listing.get('list'), list):
        raise FetchError('Listagem Galxe inválida')
    items = listing['list']
    truncated = bool(listing.get('pageInfo', {}).get('hasNextPage')) or len(items) > 20
    for index, item in enumerate(items[:20]):
        quest_id = item.get('id') if isinstance(item, dict) else None
        if not isinstance(quest_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', quest_id):
            raise FetchError('Identificador Galxe inválido')
        if index < 2:
            detail = _query(client, token, DETAIL, {'id': quest_id}).get('quest')
            if not isinstance(detail, dict) or detail.get('id') != quest_id:
                raise FetchError('Detalhe Galxe indisponível')
            detail_space = detail.get('space')
            if detail_space is not None and (
                not isinstance(detail_space, dict) or detail_space.get('id') != space
            ):
                raise FetchError('Detalhe Galxe fora do Space autorizado')
            item = {**item, **detail}
        row = {key: item[key] for key in FIELDS if isinstance(item.get(key), (str, int, float))}
        description = item.get('description')
        description = description if isinstance(description, str) else ''
        signals = [term for term, pattern in {
            'depósito': r'\b(deposit|depósito)\b',
            'compra': r'\b(buy|purchase|compra)\b',
            'trade': r'\b(trade|trading|swap)\b',
            'staking': r'\b(stake|staking)\b',
            'gas': r'\b(gas|network fee)\b',
            'carteira': r'\b(wallet|carteira)\b',
            'KYC': r'\b(kyc|identity verification)\b',
            'geografia': r'\b(country|countries|residents|brazil|brasil)\b',
        }.items() if re.search(pattern, description, re.I)]
        reward_hint = {'Points': 'pontos', 'MysteryBox': 'recompensa aleatória',
                       'Airdrop': 'distribuição anunciada de token'}.get(item.get('type'), 'não identificado')
        points = item.get('loyaltyPoints')
        row.update(financial_mentions=signals, reward_hint=reward_hint,
                   loyalty_reward={'quantity': points, 'unit': 'loyalty_points', 'conversion_verified': False}
                   if type(points) is int and points > 0 else None,
                   pagination_available=listing.get('pageInfo', {}).get('hasNextPage'),
                   space_id=space, queried_at=client.now().isoformat(), source=ENDPOINT, brazil='desconhecido', reward_verified=False,
                   financial_classification='GRATUIDADE_NAO_CONFIRMADA',
                   quiz='não confirmado', educational_content='não confirmado',
                   requirements='não confirmados', official_verification='INSUFFICIENT_EVIDENCE',
                   verification='Metadados oficiais. Gasless cobre gas indicado, não comprova custo total.')
        catalog.append(row)
    return truncated
