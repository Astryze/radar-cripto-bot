"""Fixtures artificiais offline; não representam campanhas reais."""
import json
from unittest.mock import Mock
from datetime import timedelta
from pathlib import Path
import pytest
from src.multiplatform import (OBLIGATIONS, authorized_quiz, classify, financial_classification,
                               run, zealy_catalog)
from src.platform_permissions import guard_request, load_platforms
from src.state import State
from src.utils import utcnow, RedactFilter


@pytest.fixture
def platform():
    return {'id':'zealy','name':'TESTE ARTIFICIAL','url':'https://zealy.io','enabled':True,
            'permission':'API_OFICIAL','last_audit':utcnow().date().isoformat(),
            'limitations':'exemplo offline','communities':[],'quiz_automation_authorized':False}


@pytest.fixture
def campaign():
    return {'platform_id':'zealy','title':'EXEMPLO ARTIFICIAL','url':'https://example.org/quest',
            'official_domains':['example.org'],'official':True,'reward_verified':True,'redeemable':True,'reward_type':'USDC',
            'reward':'10 USDC; exemplo de teste','official_rules_complete':True,
            'financial_requirements':{k:'none' for k in OBLIGATIONS},'availability':'aberta',
            'brazil':'confirmado','reviewed_at':utcnow().date().isoformat(),
            'evidence':[{'url':'https://example.org/rules','support':'Evidência artificial para teste offline.'}]}


@pytest.mark.parametrize('key',OBLIGATIONS[:-1])
def test_capital_never_free(key,campaign):
    campaign['financial_requirements'][key]='required'
    assert financial_classification(campaign)=='EXIGE_CAPITAL'


def test_free_requires_complete_evidence(campaign):
    assert financial_classification(campaign)=='ZERO_INVESTIMENTO'
    campaign['financial_requirements'].pop('purchase')
    assert financial_classification(campaign)=='GRATUIDADE_NAO_CONFIRMADA'


def test_kyc_is_privacy_not_cost(campaign):
    campaign['requirements']=['KYC obrigatório']
    assert financial_classification(campaign)=='ZERO_INVESTIMENTO'


def test_gas_separate(campaign):
    campaign['financial_requirements']['gas']='required'
    assert financial_classification(campaign)=='CUSTO_DE_REDE'


@pytest.mark.parametrize('kind',['points','badge','certificate','credits'])
def test_internal_rewards_not_money(kind,campaign):
    campaign['reward_type']=kind
    assert financial_classification(campaign)=='SEM_RECOMPENSA_FINANCEIRA'


def test_no_official_proof_no_free(campaign):
    campaign['official']=False
    assert financial_classification(campaign)=='GRATUIDADE_NAO_CONFIRMADA'


def test_expiry_and_geography(platform,campaign):
    campaign['ends_at']=(utcnow()-timedelta(days=1)).isoformat()
    result=classify(campaign,platform)
    assert result['availability']=='encerrada' and result['priority']=='baixa'
    campaign.pop('ends_at')
    campaign['brazil']='não elegível'
    assert classify(campaign,platform)['score']==0


@pytest.mark.parametrize('url',['https://www.bitdegree.org/learndrops','https://www.binance.com/en/academy',
                                'https://coinmarketcap.com/earn','https://evil.bitdegree.org/path',
                                'https://layer3.xyz','https://api-v2.zealy.io/private'])
def test_legacy_and_private_requests_blocked(url):
    with pytest.raises(PermissionError):
        guard_request(url)


def test_documented_api_scope_only():
    guard_request('https://api-v2.zealy.io/public/communities/example/quests')


def test_registry_all_requested_and_bitdegree_blocked():
    platforms=load_platforms()
    assert len(platforms)==9
    assert next(p for p in platforms if p['id']=='bitdegree')['permission']=='AUTOMACAO_PROIBIDA'
    assert not any(s.get('enabled',True) for s in json.loads(Path('config/sources.json').read_text())['sources']
                   if s['id'].startswith('bitdegree'))


def test_disabled_source_no_network(platform,tmp_path):
    platform['enabled']=False
    client=Mock(records=[])
    assert run([platform],[],State(tmp_path/'state'),client,None,tmp_path,True)==0
    client.get.assert_not_called()


def test_missing_api_key_no_network(platform,monkeypatch):
    monkeypatch.delenv('ZEALY_API_KEY',raising=False)
    client=Mock()
    assert zealy_catalog(platform,client)[1].startswith('skipped')
    client.get.assert_not_called()


def test_official_api_read_only_and_header_removed(platform,monkeypatch):
    monkeypatch.setenv('ZEALY_API_KEY','EXEMPLO_NAO_E_CREDENCIAL')
    platform['communities']=['example']
    client=Mock()
    client.session.headers={}
    client.get.return_value=(json.dumps([{'id':'q1','name':'TESTE','published':True,'archived':False},
                                       {'id':'hidden','name':'hidden','published':False}]).encode(),
                             'https://api-v2.zealy.io/public/communities/example/quests','application/json')
    rows,status=zealy_catalog(platform,client)
    assert len(rows)==1 and status=='collected_api_catalog'
    client.get.assert_called_once_with('https://api-v2.zealy.io/public/communities/example/quests',['api-v2.zealy.io'])
    client.post.assert_not_called()
    assert 'x-api-key' not in client.session.headers
    assert 'EXEMPLO_NAO_E_CREDENCIAL' not in json.dumps(rows)


def test_api_failure_not_other_sources(platform,tmp_path,monkeypatch):
    monkeypatch.setenv('ZEALY_API_KEY','EXEMPLO_NAO_E_CREDENCIAL')
    platform['communities']=['example']
    client=Mock(records=[])
    client.session.headers={}
    client.get.side_effect=ValueError('example error')
    second={**platform,'id':'manual','permission':'ACESSO_PUBLICO_MANUAL'}
    assert run([platform,second],[],State(tmp_path/'state'),client,None,tmp_path,True)==2
    report=json.loads((tmp_path/'multiplatform.json').read_text())
    assert len(report['sources'])==2
    assert 'x-api-key' not in client.session.headers


def test_cache_updates_and_delivery(platform,campaign,tmp_path):
    state=State(tmp_path/'state')
    state.data['sent']['legacy']='keep'
    client=Mock(records=[])
    bot=Mock()
    for _ in range(2):
        run([platform],[campaign],state,client,bot,tmp_path)
    assert bot.send.call_count==1
    campaign['reward']='11 USDC; exemplo alterado'
    run([platform],[campaign],state,client,bot,tmp_path)
    assert bot.send.call_count==2
    campaign['ends_at']=(utcnow()-timedelta(days=1)).isoformat()
    run([platform],[campaign],state,client,bot,tmp_path)
    assert bot.send.call_count==3 and 'encerrada' in bot.send.call_args.args[0]
    assert state.data['sent']['legacy']=='keep'


def test_dry_run_no_mutation(platform,campaign,tmp_path):
    state=State(tmp_path/'state')
    before=json.dumps(state.data)
    bot=Mock()
    run([platform],[campaign],state,Mock(records=[]),bot,tmp_path,True)
    assert json.dumps(state.data)==before and not state.path.exists()
    bot.send.assert_not_called()


def test_no_alert_unverified_or_stale(platform,campaign,tmp_path):
    campaign['reviewed_at']=(utcnow()-timedelta(days=8)).isoformat()
    bot=Mock()
    run([platform],[campaign],State(tmp_path/'state'),Mock(records=[]),bot,tmp_path)
    bot.send.assert_not_called()


def test_review_date_only_not_new_alert(platform,campaign,tmp_path):
    bot=Mock()
    state=State(tmp_path/'state')
    run([platform],[campaign],state,Mock(records=[]),bot,tmp_path)
    campaign['reviewed_at']=(utcnow()-timedelta(days=1)).date().isoformat()
    run([platform],[campaign],state,Mock(records=[]),bot,tmp_path)
    assert bot.send.call_count==1


def test_quiz_permission_and_inconclusive(platform,source):
    client=Mock()
    data={'authorized_public_material':True,'materials':[],'questions':[{'question':'TESTE ARTIFICIAL?', 'options':['Ledger','Cloud']}]}
    assert authorized_quiz(data,platform,[source],client)==[]
    platform['quiz_automation_authorized']=True
    results=authorized_quiz(data,platform,[source],client)
    assert results[0]['probable_answer'] is None
    client.get.assert_not_called()


def test_credential_redaction(monkeypatch):
    import logging
    monkeypatch.setenv('ZEALY_API_KEY','EXEMPLO_ARTIFICIAL')
    record=logging.LogRecord('test',20,'',1,'Secret EXEMPLO_ARTIFICIAL',(),None)
    RedactFilter().filter(record)
    assert 'EXEMPLO_ARTIFICIAL' not in record.getMessage()
