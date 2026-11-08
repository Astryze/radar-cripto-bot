"""Radar multiplataforma com permissão explícita e evidência financeira conservadora."""
import argparse
import json
import os
import re
from datetime import timedelta
from pathlib import Path
from .galxe import galxe_catalog
from .platform_permissions import load_platforms
from .quiz_analyzer import analyze_public_quiz
from .state import State
from .telegram_bot import TelegramBot
from .utils import HttpClient, atomic_json, canonical_url, digest, parse_date, utcnow, validate_url

OBLIGATIONS = ('deposit','purchase','paid_staking','paid_nft','subscription','entry_fee','trading_volume','redemption_fee','gas')
FINANCIAL = {'token','crypto','USDC','BTC'}


def financial_classification(campaign):
    requirements = campaign.get('financial_requirements', {})
    if any(requirements.get(k) == 'required' for k in OBLIGATIONS[:-1]):
        return 'EXIGE_CAPITAL'
    if campaign.get('reward_type') in {'points','badge','certificate','credits'}:
        return 'SEM_RECOMPENSA_FINANCEIRA'
    if (not campaign.get('official') or not campaign.get('official_rules_complete') or not campaign.get('evidence') or
            any(requirements.get(k) != 'none' for k in OBLIGATIONS[:-1])):
        return 'GRATUIDADE_NAO_CONFIRMADA'
    if requirements.get('gas') == 'required':
        return 'CUSTO_DE_REDE'
    if requirements.get('gas') == 'none':
        return 'ZERO_INVESTIMENTO'
    return 'GRATUIDADE_NAO_CONFIRMADA'


def classify(campaign, platform, now=None):
    now = now or utcnow()
    result = dict(campaign)
    result['platform'] = platform['name']
    result['permission'] = platform['permission']
    result['financial_classification'] = financial_classification(campaign)
    end = parse_date(campaign.get('ends_at'))
    result['availability'] = 'encerrada' if end and end < now else campaign.get('availability','não confirmada')
    value = 40 if result['financial_classification']=='ZERO_INVESTIMENTO' else 10 if result['financial_classification']=='CUSTO_DE_REDE' else 0
    value += 15 if campaign.get('official') else 0
    value += 15 if campaign.get('reward_type') in FINANCIAL and campaign.get('reward_verified') else 0
    value += 10 if campaign.get('brazil')=='confirmado' else 0
    value += 10 if result['availability']=='aberta' else 0
    value += 5 if campaign.get('educational_quiz') else 0
    value += 5 if platform['permission'] in {'API_OFICIAL','AUTOMACAO_PERMITIDA'} else 0
    if result['availability']=='encerrada' or campaign.get('brazil')=='não elegível' or result['financial_classification']=='EXIGE_CAPITAL':
        value = 0
    result['score'] = value
    result['priority'] = 'alta' if value >= 90 else 'média' if value >= 50 else 'baixa'
    return result


def authorized_quiz(data, platform, sources, client):
    if (not platform['enabled'] or platform['permission'] not in {'API_OFICIAL','AUTOMACAO_PERMITIDA'}
            or platform.get('quiz_automation_authorized') is not True):
        return []
    return analyze_public_quiz(data, sources, client)


def zealy_catalog(platform, client):
    """GET documentado, somente comunidades administradas e configuradas; nunca claims."""
    key = os.getenv('ZEALY_API_KEY', '').strip()
    communities = platform.get('communities', [])
    if not platform['enabled'] or platform['permission'] != 'API_OFICIAL':
        return [], 'skipped_permission'
    if not key or not communities:
        return [], 'skipped_missing_api_key_or_admin_communities'
    if len(communities)>3 or any(not re.fullmatch('[a-z0-9-]{1,80}', x) for x in communities):
        raise ValueError('Comunidades inválidas')
    catalog = []
    prior = client.session.headers.get('x-api-key')
    client.session.headers['x-api-key'] = key
    try:
        for community in communities:
            url = f'https://api-v2.zealy.io/public/communities/{community}/quests'
            body, _, kind = client.get(url, ['api-v2.zealy.io'])
            if 'json' not in kind:
                raise ValueError('API não retornou JSON')
            data = json.loads(body)
            if not isinstance(data, list):
                raise ValueError('Schema da API não reconhecido')
            for item in data[:50]:
                if not isinstance(item,dict) or item.get('published') is not True or item.get('archived') or item.get('deleted'):
                    continue
                if isinstance(item.get('id'),str) and isinstance(item.get('name'),str):
                    catalog.append({'id':item['id'][:100], 'title':item['name'][:240], 'community':community,
                                    'queried_at': utcnow().isoformat(), 'source': url,
                                    'brazil': 'desconhecido', 'reward_verified': False,
                                    'financial_classification': 'GRATUIDADE_NAO_CONFIRMADA',
                                    'deadline': None, 'redeemable': None,
                                    'verification':'listagem API; recompensa e gratuidade ainda não verificadas'})
    finally:
        client.session.headers.pop('x-api-key',None)
        if prior is not None:
            client.session.headers['x-api-key'] = prior
    return catalog, 'collected_api_catalog'


def verified_opportunity(campaign):
    reward_description = ' '.join(str(campaign.get(field) or '') for field in
                                  ('reward', 'reward_form', 'distribution'))
    if re.search(r'\b(sorteios?|rifas?|raffles?|lotter(?:y|ies)|giveaways?)\b', reward_description, re.I):
        return False
    return (campaign.get('official') and campaign.get('reward_verified') and campaign.get('evidence')
            and campaign.get('redeemable') is True and campaign.get('reward_type') in FINANCIAL
            and campaign.get('availability') == 'aberta' and campaign.get('brazil') == 'confirmado'
            and campaign.get('financial_classification') == 'ZERO_INVESTIMENTO'
            and campaign.get('verification_status') == 'revisão manual recente; sem reconsulta automática')


def message(campaign):
    return '\n'.join(['RADAR CRIPTO — MULTIPLATAFORMAS', f"Campanha: {campaign['title']}",
        f"Plataforma: {campaign['platform']}", f"Recompensa: {campaign.get('reward','não confirmada')}",
        f"Tipo: {campaign.get('reward_type','desconhecido')}",
        f"Investimento inicial: {campaign['financial_classification']}",
        f"Resgate: {'comprovado' if campaign.get('redeemable') is True else 'não confirmado'}",
        f"Valor e moeda: {campaign.get('reward_amount', 'não confirmado')} {campaign.get('reward_currency', '')}",
        f"KYC: {campaign.get('kyc', 'não confirmado')}",
        f"Taxas adicionais: {campaign.get('fees','não confirmadas')}",
        f"Brasil: {campaign.get('brazil','desconhecido')}",
        f"Prazo: {campaign.get('ends_at') or 'não confirmado'}; {campaign['availability']}",
        'Requisitos: ' + '; '.join(campaign.get('requirements',[])),
        f"Automação: {campaign['permission']}; {campaign.get('access_note','participação manual')}",
        f"Prioridade: {campaign['priority']}", f"Link oficial: {campaign['url']}",
        f"Verificado em: {campaign['reviewed_at']}; evidência: {campaign['evidence'][0]['url']}",
        'Recompensa sujeita aos requisitos, elegibilidade e disponibilidade; não é ganho garantido.'])


def integration_diagnostic(platform, health):
    secret, scope = {
        'galxe': ('GALXE_ACCESS_TOKEN', 'space_ids'),
        'zealy': ('ZEALY_API_KEY', 'communities'),
    }[platform['id']]
    present = bool(os.getenv(secret, '').strip())
    configured = bool(platform.get(scope))
    status = health['status']
    total = len(health['campaigns_found'])
    if status.startswith('collected_api_catalog'):
        label = f'conectada e consultada, {total} resultado(s)' if total else 'consulta concluída sem resultados'
        if status.endswith('_partial'):
            label += ' na cobertura parcial'
    elif status == 'api_failure':
        codes = {record.get('status') for record in health['http_responses']}
        codes.add(health.get('api_error_status'))
        if 403 in codes:
            label = 'autorização negada pela API (403)'
        elif 401 in codes:
            label = 'credencial rejeitada pela API (401)'
        elif 429 in codes:
            label = 'limite de consultas atingido (429)'
        else:
            label = 'erro de API'
    elif status == 'skipped_api_cooldown':
        label = 'consulta adiada pelo limite da API'
    elif status in {'disabled', 'skipped_permission', 'skipped_expired_audit', 'manual_link_only'}:
        label = 'autorização de coleta desativada ou auditoria vencida'
    else:
        missing = []
        if not present:
            missing.append('credencial indisponível nesta execução')
        if not configured:
            missing.append('escopo autorizado não configurado')
        label = ' e '.join(missing) or 'consulta ignorada'
    return {'credential_available': present, 'scope_configured': configured,
            'results': total, 'message': label}


def run(platforms, observations, state, client, bot, reports, dry_run=False, *, send_empty_summary=False):
    health, results, sent, errors = [], [], 0, []
    pending = []
    api_responses = 0
    history = state.data['platform_campaigns']
    if isinstance(client, HttpClient):
        client.cooldowns.update(state.data['cooldowns'])
    now = utcnow()
    for platform in platforms:
        h = {'id':platform['id'],'permission':platform['permission'],'last_audit':platform['last_audit'],
             'last_execution':now.isoformat(),'http_status':None,'errors':[], 'campaigns_found':[],
             'status':'manual_link_only', 'http_responses': [], 'limitations':platform['limitations']}
        if not platform['enabled']:
            h['status'] = 'disabled'
            if platform['id'] in {'galxe', 'zealy'}:
                h['integration'] = integration_diagnostic(platform, h)
            health.append(h)
            continue
        connector = {'zealy': zealy_catalog, 'galxe': galxe_catalog}.get(platform['id'])
        if connector and platform['permission']=='API_OFICIAL':
            before = len(client.records)
            try:
                h['campaigns_found'], h['status'] = connector(platform, client)
            except Exception as exc:
                h['status'] = 'api_failure'
                h['api_error_status'] = getattr(exc, 'status', None)
                h['errors'].append(type(exc).__name__)
                errors.append({'platform':platform['id'], 'error_type':type(exc).__name__})
            records = client.records[before:]
            h['http_responses'] = [
                {field: record[field] for field in ('url', 'status', 'attempted_at') if field in record}
                for record in records
            ]
            api_responses += len(records)
            if records:
                h['http_status'] = records[-1]['status']
        if platform['permission']=='API_OFICIAL' and connector is None:
            h['status'] = 'skipped_api_access_or_free_plan_not_verified'
        if connector:
            h['integration'] = integration_diagnostic(platform, h)
        health.append(h)
        if platform['id']=='bitdegree':
            continue
        for observation in observations:
            if observation['platform_id'] != platform['id']:
                continue
            validate_url(observation['url'], observation['official_domains'], resolve=False)
            for evidence in observation.get('evidence',[]):
                validate_url(evidence['url'], observation['official_domains'], resolve=False)
            result = classify(observation, platform, now)
            reviewed = parse_date(result.get('reviewed_at'))
            fresh = reviewed and now-timedelta(days=7) <= reviewed <= now
            result['verification_status'] = 'revisão manual recente; sem reconsulta automática' if fresh else 'revisão vencida; não anunciar como disponível'
            result['opportunity_status'] = ('GRATUITA_CONFIRMADA' if verified_opportunity(result)
                                            else 'OPORTUNIDADE_NAO_CONFIRMADA')
            key = canonical_url(result['url'])
            previous = history.get(key,{})
            relevant = {k:v for k,v in result.items() if k not in {'score','priority','verification_status','reviewed_at'}}
            fingerprint = digest(relevant)
            results.append(result)
            if dry_run:
                continue
            record = {'latest':result, 'hash':fingerprint, 'delivered_hash':previous.get('delivered_hash')}
            history[key] = record
            state.save()
            changed = fingerprint != record['delivered_hash']
            verified = result.get('official') and result.get('reward_verified') and result.get('evidence')
            closed_update = result['availability']=='encerrada' and bool(previous.get('delivered_hash')) and previous.get('latest', {}).get('redeemable') is True
            if changed and verified and (verified_opportunity(result) or closed_update):
                pending.append((result, record, fingerprint))
    results.sort(key=lambda x: -x['score'])
    confirmed = [result for result in results if verified_opportunity(result)]
    for result, record, fingerprint in sorted(pending, key=lambda item: -item[0]['score']):
        try:
            bot.send(message(result))
            record['delivered_hash'] = fingerprint
            state.save()
            sent += 1
        except Exception as exc:
            errors.append({'platform': result['platform_id'], 'error_type': type(exc).__name__})
    summary = 'Nenhuma oportunidade que atenda a todos os critérios de gratuidade e resgate foi confirmada nesta execução.'
    if confirmed:
        summary = f'Oportunidades financeiras verificadas para o Brasil com investimento zero: {len(confirmed)}.'
    diagnostics = [f"{item['id'].title()} — {item['integration']['message']}"
                   for item in health if 'integration' in item]
    if not dry_run and send_empty_summary:
        day = now.date().isoformat()
        marker = f'v27:multiplatform:diagnostic:{day}:{digest([summary, diagnostics])}'
        if marker not in state.data['summaries']:
            try:
                bot.send('RADAR CRIPTO — MULTIPLATAFORMAS\n' + '\n'.join([summary, *diagnostics]))
                previous = state.data['summaries']
                state.data['summaries'] = [
                    item for item in previous if not item.startswith(('v25:multiplatform:empty:', 'v27:multiplatform:diagnostic:'))
                ] + [marker]
                state.save()
                sent += 1
            except Exception as exc:
                errors.append({'platform': 'summary', 'error_type': type(exc).__name__})
    if not dry_run:
        state.data['platform_health'].update({h['id']:h for h in health})
        if isinstance(client, HttpClient):
            state.data['cooldowns'] = client.cooldowns
        state.save()
    report = {'version':'2.7','at':now.isoformat(),'dry_run':dry_run,'sources':health,
              'opportunities':results, 'sent':sent,'errors':errors,
              'live_api_campaigns':sum(len(h['campaigns_found']) for h in health),
              'verified_zero_investment':len(confirmed), 'summary':summary, 'api_http_responses':api_responses,
              'real_quiz_questions':0,
              'limitation':'Observações manuais não são descoberta contínua. Listagens API não confirmam recompensas de projetos.'}
    atomic_json(Path(reports)/'multiplatform.json',report)
    for diagnostic in diagnostics:
        print(diagnostic)
    print(f"Multiplataformas: {len(platforms)} fontes auditadas; {report['live_api_campaigns']} registros API; {report['verified_zero_investment']} gratuitas verificadas; {sent} alertas")
    return 2 if errors else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--reports',type=Path,default=Path('reports'))
    parser.add_argument('--state',type=Path,default=Path('state/radar.json'))
    args = parser.parse_args()
    try:
        bot = None if args.dry_run else TelegramBot(os.getenv('TELEGRAM_BOT_TOKEN'),os.getenv('TELEGRAM_CHAT_ID'))
        observations = json.loads(Path('config/campaign_observations.json').read_text())['campaigns']
        client = HttpClient(attempts=2,min_interval=1,max_retry_wait=5)
        from .bitdegree_quizzes import NoCookies
        client.session.cookies.set_policy(NoCookies())
        return run(load_platforms(), observations, State(args.state),client,bot,args.reports,args.dry_run, send_empty_summary=True)
    except Exception as exc:
        atomic_json(args.reports/'multiplatform-failure.json',{'error_type':type(exc).__name__})
        return 1


if __name__=='__main__':
    raise SystemExit(main())
