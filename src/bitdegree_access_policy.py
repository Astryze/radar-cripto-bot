"""Barreira explícita: a solicitação manda interromper se a plataforma proibir coleta."""
POLICY = {
    'status': 'blocked_by_platform_terms',
    'source': 'https://www.bitdegree.org/terms-of-service',
    'section': '10',
    'reviewed_at': '2026-11-08',
    'reason': 'A seção 10 proíbe cópia com tecnologia de robôs/crawlers. '
              'Leitura autenticada automatizada não foi habilitada. '
              'É necessária autorização específica da BitDegree para reavaliar esta integração.',
}


def require_authorized_access():
    raise PermissionError(POLICY['reason'])
