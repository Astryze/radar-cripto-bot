"""API Zealy para consultas autorizadas. Resultados de usuários são minimizados."""
import json
import os
import re
from datetime import timedelta
from urllib.parse import urlencode
from uuid import UUID

from .integration_setup import integration_setup
from .utils import FetchError, parse_date, utcnow

HOST = 'api-v2.zealy.io'
BASE = f'https://{HOST}/public/communities'
UUID_PATTERN = r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}'
USER_ROUTE = re.compile(rf'users(?:/{UUID_PATTERN}(?:/invites)?)?|reviews/users/{UUID_PATTERN}')
LOOKUP_FIELDS = {'discordId', 'discordHandle', 'twitterId', 'twitterUsername', 'ethAddress', 'email'}
INVITE_STATES = ('active', 'pending', 'consumed')


def user_id(value):
    try:
        return str(UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise ValueError('Identificador Zealy deve ser um UUID') from None


def profile(payload):
    if not isinstance(payload, dict):
        raise FetchError('Perfil Zealy inválido')
    user_id(payload.get('id'))
    banned = payload.get('isBanned')
    if type(banned) is not bool:
        raise FetchError('Perfil Zealy sem situação de banimento')
    role = payload.get('role')
    roles = ('admin', 'editor', 'reviewer', 'guest', 'banned')
    return {
        **{field: payload.get(field) if type(payload.get(field)) in (int, float) else None
           for field in ('xp', 'level', 'rank')},
        'banned': banned or role == 'banned',
        'role': role if role in roles else None,
        'membership': ('confirmada' if role in roles and payload.get('deletedAt') is None
                       else 'não confirmada'),
        'verified_wallets': wallet_count(payload, 'verifiedBlockchainAddresses'),
        'unverified_wallets': wallet_count(payload, 'unVerifiedBlockchainAddresses'),
    }


def wallet_count(payload, field):
    addresses = payload.get(field)
    if not isinstance(addresses, dict):
        return None
    return sum(
        sum(isinstance(address, str) and bool(address.strip()) for address in value)
        if isinstance(value, list) else int(isinstance(value, str) and bool(value.strip()))
        for value in addresses.values()
    )


class ZealyIntegration:
    def __init__(self, platform, client):
        self.platform = platform
        self.client = client
        self.cache = {}

    def _read(self, community, route, label, normalize, *, query=None, payload=None):
        setup = integration_setup(self.platform, 'zealy')
        audit = parse_date(self.platform.get('last_audit'))
        now = utcnow()
        if (not self.platform.get('enabled') or self.platform.get('permission') != 'API_OFICIAL'
                or not audit or not now - timedelta(days=30) <= audit <= now
                or not setup['scope_configured'] or community not in self.platform['communities']):
            raise PermissionError('Comunidade Zealy sem escopo auditado')
        key = os.getenv('ZEALY_API_KEY', '').strip()
        if not key:
            raise PermissionError('ZEALY_API_KEY indisponível')
        if payload is not None:
            if self.platform.get('allow_member_post') is not True or setup['read_only_declared']:
                raise PermissionError('POST de associação requer habilitação e chave compatível')
        elif not setup['read_only_declared']:
            raise PermissionError('Chave Zealy somente leitura não declarada')
        url = f'{BASE}/{community}/{route}'
        if query:
            url += '?' + urlencode(query)
        cache_key = (url, payload['userId'] if payload else None)
        if cache_key in self.cache:
            return self.cache[cache_key]
        body, _, kind = self.client._request(
            url, [HOST], method='POST' if payload is not None else 'GET',
            payload=payload, headers={'x-api-key': key}, record_url=f'{BASE}/{community}/{label}',
            cache=False,
        )
        if payload is not None:
            result = {'membership': 'confirmada'}
        else:
            if 'json' not in kind:
                raise FetchError('Zealy não retornou JSON')
            try:
                result = normalize(json.loads(body))
            except (ValueError, TypeError, KeyError):
                raise FetchError('Resposta Zealy inválida') from None
        self.cache[cache_key] = result
        return result

    def get_user(self, community, identifier):
        identifier = user_id(identifier)

        def normalize(payload):
            if not isinstance(payload, dict) or user_id(payload.get('id')) != identifier:
                raise FetchError('Perfil Zealy divergente')
            return profile(payload)

        return self._read(community, f'users/{identifier}', 'users/{userId}', normalize)

    def lookup_user(self, community, field, value):
        if field not in LOOKUP_FIELDS or not isinstance(value, str) or not 1 <= len(value.strip()) <= 200:
            raise ValueError('Filtro de usuário Zealy inválido')
        return self._read(community, 'users', 'users', profile, query={field: value.strip()})

    def invites(self, community, identifier, *, status=None, max_pages=3, page_size=50):
        identifier = user_id(identifier)
        if status not in (*INVITE_STATES, None) or not 1 <= max_pages <= 5 or not 1 <= page_size <= 100:
            raise ValueError('Filtros de convites inválidos')

        def normalize(payload):
            if not isinstance(payload, list) or len(payload) > page_size:
                raise FetchError('Página de convites Zealy inválida')
            counts = dict.fromkeys(INVITE_STATES, 0)
            for item in payload:
                if not isinstance(item, dict) or item.get('status') not in INVITE_STATES:
                    raise FetchError('Status de convite Zealy inválido')
                counts[item['status']] += 1
            return counts

        counts = dict.fromkeys(INVITE_STATES, 0)
        for page in range(1, max_pages + 1):
            query = {'page': page, 'page_size': page_size}
            if status is not None:
                query['status'] = status
            batch = self._read(community, f'users/{identifier}/invites', 'users/{userId}/invites',
                               normalize, query=query)
            for state, count in batch.items():
                counts[state] += count
            if sum(batch.values()) < page_size:
                return {'counts': counts, 'pages': page, 'partial': False}
        return {'counts': counts, 'pages': max_pages, 'partial': True}

    def reviews(self, community, identifier):
        identifier = user_id(identifier)

        def normalize(payload):
            if not isinstance(payload, dict) or any(type(payload.get(field)) is not int
                                                     for field in ('flags', 'stars')):
                raise FetchError('Avaliações Zealy inválidas')
            return {field: payload[field] for field in ('flags', 'stars')}

        return self._read(community, f'reviews/users/{identifier}', 'reviews/users/{id}', normalize)

    def membership(self, community, identifier):
        return self._read(community, 'member', 'member', None, payload={'userId': user_id(identifier)})
