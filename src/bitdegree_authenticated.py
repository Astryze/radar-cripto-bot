"""Etapa bloqueada pelos termos: não abre navegador nem lê credenciais de sessão."""
import argparse
import json
from pathlib import Path
from .bitdegree_access_policy import POLICY
from .utils import atomic_json, utcnow


def blocked_report(missions):
    return {'version': '2.3-blocked', 'at': utcnow().isoformat(), 'policy': POLICY,
            'session_loaded': False, 'chromium_started': False, 'telegram_sent': 0,
            'missions': [{'title': mission['title'], 'url': mission['url'],
                          'authentication_state': 'not_checked', 'loading_status': 'not_attempted_policy_block',
                          'http_status': None, 'content_type': None, 'questions_found': None,
                          'alternatives_found': None, 'reason': POLICY['reason']} for mission in missions]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports', type=Path, default=Path('reports'))
    args = parser.parse_args()
    missions = json.loads(Path('config/bitdegree_diagnostic_missions.json').read_text())
    atomic_json(args.reports / 'bitdegree-authenticated.json', blocked_report(missions))
    print('BitDegree autenticada ignorada: acesso automatizado bloqueado pelos termos. '
          'Sessão não lida; demais fontes preservadas.')
    return 0  # Etapa explicitamente ignorada, não uma análise executada com sucesso.


if __name__ == '__main__':
    raise SystemExit(main())
