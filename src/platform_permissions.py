"""Cadastro central: página pública não implica autorização de coleta."""
import json
from pathlib import Path
from urllib.parse import urlsplit

PERMISSIONS = {'AUTOMACAO_PERMITIDA','API_OFICIAL','ACESSO_PUBLICO_MANUAL',
               'AUTORIZACAO_NECESSARIA','AUTOMACAO_PROIBIDA'}
REGISTRY = Path(__file__).resolve().parents[1] / 'config/platforms.json'


def load_platforms(path=REGISTRY):
    platforms = json.loads(Path(path).read_text())['platforms']
    if len({p['id'] for p in platforms}) != len(platforms):
        raise ValueError('Plataformas duplicadas')
    for p in platforms:
        if p['permission'] not in PERMISSIONS or not isinstance(p['enabled'], bool):
            raise ValueError('Permissão inválida')
    return platforms


def guard_request(url):
    """Protege também coletores legados e redirects antes de qualquer GET."""
    host = urlsplit(url).hostname or ''
    roots = {'binance.com','coinmarketcap.com','galxe.com','galaxy.eco','layer3.xyz',
             'zealy.io','intract.io','questn.com','revolut.com','bitdegree.org'}
    if any(host == root or host.endswith('.' + root) for root in roots):
        # Somente endpoint GET auditado da Zealy. Não libera o resto do site.
        if host == 'api-v2.zealy.io':
            import re
            if re.fullmatch(r'/public/communities/[a-z0-9-]{1,80}/quests', urlsplit(url).path):
                platform = next(p for p in load_platforms() if p['id']=='zealy')
                from .utils import parse_date, utcnow
                from datetime import timedelta
                audited = parse_date(platform.get('last_audit'))
                if (platform['enabled'] and platform['permission']=='API_OFICIAL' and audited
                        and utcnow()-timedelta(days=30) <= audited <= utcnow()):
                    return
        raise PermissionError('Coleta da plataforma não autorizada pelo cadastro central')
