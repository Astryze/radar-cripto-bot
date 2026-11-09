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
    credential = os.getenv(secret, '').strip()
    present = bool(credential)
    credential_valid = present and all(33 <= ord(char) <= 126 for char in credential)
    scope_variable = {'galxe': 'GALXE_SPACE_IDS', 'zealy': 'ZEALY_COMMUNITIES'}[source]
    entries = platform.get(scope, [])
    valid = (isinstance(entries, list) and len(entries) <= (20 if source == 'zealy' else 3)
             and all(isinstance(entry, str) and re.fullmatch(pattern, entry) for entry in entries)
             and len(set(entries)) == len(entries))
    configured = valid and bool(entries)
    issues = []
    if not present:
        issues.append(f'credencial indisponível nesta execução ({secret})')
    elif not credential_valid:
        issues.append(f'formato inválido em {secret}')
    if not valid:
        issues.append(f'configuração inválida em {scope}')
    elif not configured:
        issues.append(f'escopo autorizado não configurado ({scope})')
    read_only = platform.get('read_only_key') is True if source == 'zealy' else None
    if source == 'zealy' and not read_only:
        if 'read_only_key' in platform and type(platform['read_only_key']) is not bool:
            issues.append('declaração inválida em ZEALY_READ_ONLY_KEY/read_only_key')
        else:
            issues.append('chave somente leitura não declarada (ZEALY_READ_ONLY_KEY/read_only_key)')
    return {
        'credential_available': present,
        'credential_format_valid': credential_valid,
        'scope_configured': configured,
        'scope_valid': valid,
        'read_only_declared': read_only,
        'issues': issues,
        'pending_variables': ([secret] if not credential_valid else [])
        + ([scope_variable] if not configured else [])
        + (['ZEALY_READ_ONLY_KEY'] if source == 'zealy' and not read_only else []),
    }
