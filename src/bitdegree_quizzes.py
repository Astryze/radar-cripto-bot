"""Monitor público e assistente de estudo BitDegree. Somente GET; nunca submete avaliações."""
import argparse
import logging
import os
import re
import time
from http.cookiejar import DefaultCookiePolicy
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from .feed_reader import load_sources, read_source
from .quiz_analyzer import ANALYZER_VERSION, analyze_question, extract_public_questions, public_soup, study_text
from .quiz_diagnostics import diagnose
from .public_questions import inconclusive
from .state import State
from .telegram_bot import TelegramBot
from .utils import (FetchError, HttpClient, atomic_json, canonical_url, digest, normalize,
                    setup_logging, utcnow, validate_url)

LOG = logging.getLogger(__name__)
DEFAULT_LIMITS = {"max_requests": 18, "max_missions": 6, "max_related_pages": 2,
                  "max_questions": 12, "budget_seconds": 120}


class NoCookies(DefaultCookiePolicy):
    def set_ok(self, cookie, request):
        return False

    def return_ok(self, cookie, request):
        return False


def public_client():
    client = HttpClient(attempts=2, max_retry_wait=5, min_interval=1)
    client.session.cookies.clear()
    client.session.cookies.set_policy(NoCookies())
    return client


class Budget:
    def __init__(self, client, limits, clock=time.monotonic):
        self.client, self.limits, self.clock = client, limits, clock
        self.started, self.requests = clock(), 0

    def metadata(self, url):
        records = getattr(self.client, 'records', [])
        entries = [r for r in records if r.get('url') == url]
        latest = entries[-1] if entries else {}
        return {'http_status': latest.get('status'), 'content_type': latest.get('content_type')}

    def get(self, url, domains):
        if (self.requests >= self.limits['max_requests'] or
                self.clock() - self.started >= self.limits['budget_seconds']):
            raise FetchError('Orçamento de coleta BitDegree atingido')
        validate_url(url, domains)
        self.requests += 1
        body, final, content_type = self.client.get(url, domains)
        validate_url(final, domains)
        if 'html' not in content_type.lower():
            raise FetchError('BitDegree: conteúdo não é HTML público')
        return body, final, content_type


def mission_url(url):
    p = urlsplit(url)
    return p.hostname == 'www.bitdegree.org' and bool(re.fullmatch(r'/guilds/[^/]+/[^/]+/?', p.path))


def related_links(body, mission, domains):
    """Segue somente links publicados, ligados ao estudo/quiz; não descobre APIs privadas."""
    prefix = urlsplit(mission).path.rstrip('/')
    links, seen = [], {canonical_url(mission)}
    for link in public_soup(body).select('a[href]'):
        label = normalize(link.get_text(' ', strip=True))
        href = urljoin(mission, link.get('href', ''))
        try:
            validate_url(href, domains, resolve=False)
        except ValueError:
            continue
        parsed = urlsplit(href)
        # Nenhum endpoint de conta, login ou ações; nem missões de outra guilda.
        if re.search(r'login|sign.?in|register|wallet|submit|claim|api/|logout|captcha', normalize(href)):
            continue
        if parsed.hostname == 'www.bitdegree.org' and not (
                parsed.path.startswith(prefix + '/') or parsed.path == prefix
                or parsed.path.startswith('/crypto/')):
            continue
        if not re.search(r'quiz|round|lesson|study|material|learn|curso|estud|li[cç][aã]o', label + ' ' + parsed.path):
            continue
        key = canonical_url(href)
        if key not in seen:
            seen.add(key)
            links.append(key)
    return links


def inspect_mission(candidate, budget, domains, previous, limits):
    body, final, _ = budget.get(candidate.url, candidate.source.domains)
    if canonical_url(final).split('?', 1)[0] != canonical_url(candidate.url).split('?', 1)[0]:
        raise FetchError('Missão redirecionada para outra página; não atribuir conteúdo de terceiros')
    pages = [(final, body)]
    partial = []
    for url in related_links(body, final, domains)[:limits['max_related_pages']]:
        try:
            extra, resolved, _ = budget.get(url, domains)
            if canonical_url(resolved) != canonical_url(url):
                raise FetchError('Material redirecionado: requer revisão do vínculo com a missão')
            pages.append((resolved, extra))
        except (FetchError, ValueError) as exc:
            partial.append(type(exc).__name__)
    questions, seen = [], set()
    materials = []
    for url, content in pages:
        for q in extract_public_questions(content, url):
            key = digest([q['question'], q['options']])
            if key not in seen:
                seen.add(key)
                questions.append(q)
        materials.append({'url': url, 'text': study_text(content), 'official': True})
    questions = questions[:limits['max_questions']]
    # Uma falha temporária não vira desaparecimento de perguntas nem invalida cache anterior.
    if partial:
        raise FetchError('Coleta de material incompleta; histórico anterior preservado')
    source_hash = digest({'version': ANALYZER_VERSION, 'questions': questions,
                          'materials': materials if questions else []})
    if previous.get('source_hash') == source_hash:
        results = previous['results']
    else:
        results = []
        for q in questions:
            answer = (inconclusive(q) if q.get('question_type') in {'multiple', 'written'}
                      else analyze_question(q['question'], q['options'], materials))
            answer['question_source'] = q['question_source']
            results.append(answer)
    status = 'quiz público analisado' if questions else 'perguntas não disponíveis publicamente'
    visible = normalize(public_soup(body).get_text(' ', strip=True))
    if not questions and re.search(r'captcha|sign in to|log in to|login para|entre para', visible):
        status = 'acesso a perguntas depende de login ou verificação; nenhuma tentativa de acesso'
    record = {'title': candidate.title, 'url': canonical_url(candidate.url), 'status': status,
              'results': results, 'source_hash': source_hash, 'checked_at': utcnow().isoformat(),
              'analyzed_at': previous.get('analyzed_at') if previous.get('source_hash') == source_hash
              else utcnow().isoformat(), 'analyzer_version': ANALYZER_VERSION,
              'materials': [{'url': m['url'], 'content_hash': digest(m['text'])} for m in materials]}
    record.update(budget.metadata(final))
    record['diagnostic'] = diagnose(body, final)
    record['questions_extracted'] = len(questions)
    record['questions_analyzed'] = len(results)
    record['conclusive_answers'] = sum(r['probable_answer'] is not None for r in results)
    record['diagnostic']['reason_code'] = 'public_questions_extracted' if questions else record['diagnostic']['reason_code']
    record['notification_hash'] = digest({k: record[k] for k in ('title', 'url', 'status', 'results')})
    record['delivered_hash'] = previous.get('delivered_hash')
    return record


def quiz_message(record, updated=False):
    lines = ['RADAR CRIPTO — BITDEGREE', 'Quiz/missão atualizada' if updated else 'Nova missão monitorada',
             f"Missão: {record['title']}", f"Status: {record['status']}", f"Página pública: {record['url']}",
             'Monitoramento de estudo: não confirma gratuidade, elegibilidade ou recompensa da campanha.',
             'Somente apoio ao estudo. Revise e envie manualmente; nenhuma resposta é submetida pelo bot.']
    if not record['results']:
        lines.append('Nenhuma pergunta/alternativa pública identificada no HTML consultado. '
                     'Conteúdo privado, dinâmico ou outro layout pode exigir revisão manual.')
    for i, result in enumerate(record['results'], 1):
        lines.extend([f"\nPergunta {i}: {result['question']}"])
        lines.extend(f"{j}. {option}" for j, option in enumerate(result['options'], 1))
        lines.extend([f"Resposta sugerida: {result['probable_answer'] or 'não determinado'}",
                      f"Confiança: {result['confidence']}", f"Justificativa: {result['reasoning']}"])
        support = result.get('support')
        if support:
            lines.extend([f"Trecho de apoio: {support['excerpt']}", f"Fonte oficial: {support['url']}"])
        lines.extend([f"Perguntas: {result['question_source']}",
                      'Limitações: ' + ' '.join(result.get('limitations', []))])
    return '\n'.join(lines)


def run(sources, client, state, bot, report_dir, dry_run=False, limits=None, notify_diagnostics=True):
    limits = {**DEFAULT_LIMITS, **(limits or {})}
    for key, default in DEFAULT_LIMITS.items():
        if not isinstance(limits[key], int) or not 1 <= limits[key] <= default:
            raise ValueError('Limites BitDegree inválidos ou acima do teto de segurança')
    budget = Budget(client, limits)
    history = state.data['quizzes']
    if any(not isinstance(v, dict) or not isinstance(v.get('results'), list)
           or 'source_hash' not in v for v in history.values()):
        raise ValueError('Histórico de quizzes inválido; não substituir dados anteriores')
    if isinstance(client, HttpClient):
        client.cooldowns.update(state.data['cooldowns'])
    domains = {d for s in sources if s.official for d in s.domains}
    candidates, errors, seen = [], [], set()
    health = []
    for source in [s for s in sources if s.enabled and s.kind == 'bitdegree'][:3]:
        try:
            found = read_source(source, budget)
            health.append({'source': source.id, 'checked_at': utcnow().isoformat(), 'status': 'coletada'})
            for candidate in found:
                key = canonical_url(candidate.url)
                if (candidate.source.official and mission_url(key) and key not in seen
                        and candidate.listing_status != 'encerrado'):
                    seen.add(key)
                    candidates.append(candidate)
        except (FetchError, ValueError) as exc:
            errors.append({'source': source.id, 'error_type': type(exc).__name__})
    # Mais antigas primeiro: uma missão não monopoliza todas as execuções.
    checks = state.data['quiz_checks']
    if any(not isinstance(value, str) for value in checks.values()):
        raise ValueError('Histórico de coletas BitDegree inválido')
    candidates.sort(key=lambda c: checks.get(canonical_url(c.url),
                    history.get(canonical_url(c.url), {}).get('checked_at', '')))
    observed, failed, sent = [], [], 0
    for candidate in candidates[:limits['max_missions']]:
        key = canonical_url(candidate.url)
        prior = history.get(key, {})
        if not dry_run:
            checks[key] = utcnow().isoformat()
        try:
            record = inspect_mission(candidate, budget, domains, prior, limits)
            observed.append(record)
            if dry_run:
                continue
            history[key] = record
            state.save()  # Cache sobrevive inclusive a uma falha de Telegram.
            if (record['results'] or notify_diagnostics) and record['notification_hash'] != record.get('delivered_hash'):
                bot.send(quiz_message(record, bool(prior)))
                record['delivered_hash'] = record['notification_hash']
                state.save()
                sent += 1
        except (FetchError, ValueError) as exc:
            errors.append({'mission': key, 'error_type': type(exc).__name__})
            failed.append({'title': candidate.title, 'url': key, **budget.metadata(key),
                           'questions_extracted': 0, 'questions_analyzed': 0, 'conclusive_answers': 0,
                           'diagnostic': {'reason_code': 'technical_collection_failure', 'error_type': type(exc).__name__}})
    if not dry_run:
        if isinstance(client, HttpClient):
            state.data['cooldowns'] = client.cooldowns
        state.save()
    report = {'version': '2.2', 'at': utcnow().isoformat(), 'dry_run': dry_run,
              'requests': budget.requests, 'http': getattr(client, 'records', []), 'sources': health,
              'discovered_missions': len(candidates), 'checked_missions': len(observed),
              'public_quizzes': sum(bool(r['results']) for r in observed), 'sent': sent,
              'errors': errors, 'missions': observed + failed,
              'limitations': 'HTML público estático; nenhuma autenticação, API privada ou submissão. '
                             'Ausência de perguntas públicas não significa ausência de quiz na plataforma.'}
    atomic_json(Path(report_dir) / 'bitdegree-quizzes.json', report)
    LOG.info('BitDegree: %d missões verificadas, %d quizzes públicos, %d entregas, %d erros',
             len(observed), report['public_quizzes'], sent, len(errors))
    return 2 if errors else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--sources', type=Path, default=Path('config/sources.json'))
    parser.add_argument('--state', type=Path, default=Path('state/radar.json'))
    parser.add_argument('--reports', type=Path, default=Path('reports'))
    args = parser.parse_args()
    setup_logging('logs')
    try:
        bot = None if args.dry_run else TelegramBot(os.getenv('TELEGRAM_BOT_TOKEN'), os.getenv('TELEGRAM_CHAT_ID'))
        return run(load_sources(args.sources), public_client(),
                   State(args.state), bot, args.reports, args.dry_run, notify_diagnostics=False)
    except Exception as exc:
        LOG.error('BitDegree interrompido: %s', type(exc).__name__)
        atomic_json(args.reports / 'bitdegree-failure.json', {'error_type': type(exc).__name__,
                    'at': utcnow().isoformat()})
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
