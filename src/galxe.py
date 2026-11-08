"""Consultas GraphQL documentadas, limitadas aos Spaces configurados."""
import json
import os
import re
from datetime import timedelta
from urllib.parse import urlsplit

import requests

from .utils import FetchError, MAX_BYTES, parse_date, retry_after_seconds, utcnow, validate_url

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
  }
}"""
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
            client.records.append({'url': ENDPOINT, 'status': status})
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
            if isinstance(error, dict) and (error.get('extensions') or {}).get('http_status') == 429:
                client._defer(ENDPOINT, 429, 900)
        raise FetchError('Consulta Galxe rejeitada')
    if not isinstance(payload.get('data'), dict):
        raise FetchError('Resposta Galxe sem dados')
    return payload['data']


def galxe_catalog(platform, client):
    token = os.getenv('GALXE_ACCESS_TOKEN', '').strip()
    spaces = platform.get('space_ids', [])
    if not platform['enabled'] or platform['permission'] != 'API_OFICIAL':
        return [], 'skipped_permission'
    if not token or not spaces:
        return [], 'skipped_missing_access_token_or_spaces'
    audit = parse_date(platform.get('last_audit'))
    now = utcnow()
    if not audit or not now - timedelta(days=30) <= audit <= now:
        return [], 'skipped_expired_audit'
    if len(spaces) > 3 or len(set(spaces)) != len(spaces) or any(
        not isinstance(space, str) or not re.fullmatch(r'[0-9]{1,20}', space) for space in spaces
    ):
        raise ValueError('Spaces Galxe inválidos')
    until = parse_date(client.cooldowns.get(HOST, {}).get('until'))
    if until and until > now:
        return [], 'skipped_api_cooldown'
    validate_url(ENDPOINT, [HOST])
    catalog = []
    truncated = False
    for space in spaces:
        listing = _query(client, token, LIST, {'input': {
            'spaceId': space, 'statuses': ['Active', 'NotStarted'], 'first': 20,
        }})['quests']
        items = listing['list']
        if not isinstance(items, list):
            raise FetchError('Listagem Galxe inválida')
        truncated |= bool(listing.get('pageInfo', {}).get('hasNextPage')) or len(items) > 20
        for index, item in enumerate(items[:20]):
            quest_id = item['id']
            if not isinstance(quest_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', quest_id):
                raise FetchError('Identificador Galxe inválido')
            if index < 2:
                detail = _query(client, token, DETAIL, {'id': quest_id})['quest']
                if not isinstance(detail, dict) or detail.get('id') != quest_id:
                    raise FetchError('Detalhe Galxe indisponível')
                item = {**item, **detail}
            row = {key: item[key] for key in FIELDS if isinstance(item.get(key), (str, int, float))}
            row.update(space_id=space, brazil='desconhecido', reward_verified=False,
                       financial_classification='GRATUIDADE_NAO_CONFIRMADA',
                       quiz='não confirmado', educational_content='não confirmado',
                       requirements='não confirmados',
                       verification='Metadados oficiais. Gasless cobre gas indicado, não comprova custo total.')
            catalog.append(row)
    return catalog, 'collected_api_catalog_partial' if truncated else 'collected_api_catalog'
