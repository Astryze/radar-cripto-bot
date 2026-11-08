"""Diagnóstico público, sem executar JavaScript ou consultar rotas internas."""
import json
from bs4 import BeautifulSoup
from .quiz_analyzer import public_soup


def diagnose(body, url):
    raw = BeautifulSoup(body, 'html.parser')
    visible = public_soup(body)
    rounds = [x.get_text(' ', strip=True) for x in visible.select('.missions-server-content__rounds li')]
    scripts = raw.select('script[type="application/json"], script[type="application/ld+json"]')
    malformed = 0
    for script in scripts:
        try:
            json.loads(script.string or '')
        except (ValueError, TypeError):
            malformed += 1
    shell = bool(raw.select_one('#missions-mount dashboard-layout'))
    login = bool(raw.select_one('form input[type="password"]'))
    return {'url': url, 'page_type': 'mission_spa_with_server_summary' if shell else 'public_html',
            'round_titles': rounds, 'embedded_json_blocks': len(scripts), 'invalid_json_blocks': malformed,
            'dynamic_shell_observed': shell, 'login_form_observed': login,
            'access_requirement': 'login_form_observed' if login else 'not_determined',
            'reason_code': 'login_form' if login else 'dynamic_shell_without_question_payload' if shell
            else 'no_supported_public_question_markup',
            'reason': 'HTML contém resumo e títulos de rodadas, sem payload público de perguntas; '
                      'JavaScript referenciado não demonstra acesso público nem exigência de login.' if shell
                      else 'Nenhuma pergunta reconhecida no HTML público; isso não prova ausência na plataforma.'}
