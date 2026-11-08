"""Preflight local. Só retorna estados de configuração e nunca a credencial."""
import os
import re

SOURCES = {
    'galxe': ('GALXE_ACCESS_TOKEN', 'space_ids', r'[0-9]{1,20}'),
    'zealy': ('ZEALY_API_KEY', 'communities', r'[a-z0-9-]{1,80}'),
}


def integration_setup(platform, source=None):
    source = source or platform['id']
    secret, scope, pattern = SOURCES[source]
    present = bool(os.getenv(secret, '').strip())
    entries = platform.get(scope, [])
    valid = (isinstance(entries, list) and len(entries) <= 3
             and all(isinstance(entry, str) and re.fullmatch(pattern, entry) for entry in entries)
             and len(set(entries)) == len(entries))
    configured = valid and bool(entries)
    issues = []
    if not present:
        issues.append(f'credencial indisponível nesta execução ({secret})')
    if not valid:
        issues.append(f'configuração inválida em {scope}')
    elif not configured:
        issues.append(f'escopo autorizado não configurado ({scope})')
    read_only = platform.get('read_only_key') is True if source == 'zealy' else None
    if source == 'zealy' and not read_only:
        issues.append('chave somente leitura não declarada (read_only_key)')
    return {
        'credential_available': present,
        'scope_configured': configured,
        'scope_valid': valid,
        'read_only_declared': read_only,
        'issues': issues,
    }
