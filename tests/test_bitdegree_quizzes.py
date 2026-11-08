import json
from dataclasses import replace
from unittest.mock import Mock

import pytest

from src.bitdegree_quizzes import Budget, DEFAULT_LIMITS, mission_url, related_links, run
from src.quiz_analyzer import analyze_question, extract_public_questions, study_text
from src.state import State
from src.telegram_bot import split_message
from src.utils import FetchError

ROOT = 'https://www.bitdegree.org'
MISSION = ROOT + '/guilds/bitdegree/ledger-course'
QUESTION = ('<fieldset><legend>What does a blockchain store?</legend>'
            '<label>Distributed ledger records</label><label>Weather clouds</label></fieldset>')
MATERIAL = '<article>A blockchain stores distributed ledger records across a network.</article>'


@pytest.fixture
def setup_quiz(source, tmp_path):
    source = replace(source, id='bitdegree', url=ROOT + '/learndrops', kind='bitdegree',
                     domains=['www.bitdegree.org'])
    pages = {source.url: f'<a href="{MISSION}">Ledger course quiz</a>', MISSION: MATERIAL + QUESTION}
    client = Mock(spec=['get'])

    def get(url, domains):
        value = pages[url]
        if isinstance(value, Exception):
            raise value
        return value.encode(), url, 'text/html'
    client.get.side_effect = get
    return source, pages, client, State(tmp_path / 'state.json'), Mock(), tmp_path / 'reports'


def execute(ctx, dry_run=False, **kwargs):
    source, _, client, state, bot, reports = ctx
    return run([source], client, state, bot, reports, dry_run=dry_run, **kwargs)


def report(ctx):
    return json.loads((ctx[-1] / 'bitdegree-quizzes.json').read_text())


def test_discover_analyze_and_telegram(setup_quiz):
    assert execute(setup_quiz) == 0
    data = report(setup_quiz)
    assert data['public_quizzes'] == data['sent'] == 1
    message = setup_quiz[4].send.call_args.args[0]
    for text in ('Distributed ledger records', 'Trecho de apoio:', 'Fonte oficial:', 'Confiança:',
                 'Justificativa:', 'manualmente', MISSION):
        assert text in message
    assert setup_quiz[3].data['quizzes'][MISSION]['results'][0]['automatic_submission'] is False


def test_cache_reuse_and_no_repeat(setup_quiz, monkeypatch):
    execute(setup_quiz)
    first = setup_quiz[3].data['quizzes'][MISSION]['analyzed_at']
    monkeypatch.setattr('src.bitdegree_quizzes.analyze_question', Mock(side_effect=AssertionError('cached')))
    execute(setup_quiz)
    assert setup_quiz[4].send.call_count == 1
    assert report(setup_quiz)['sent'] == 0
    assert setup_quiz[3].data['quizzes'][MISSION]['analyzed_at'] == first


def test_new_questions_notify_once(setup_quiz):
    execute(setup_quiz)
    setup_quiz[1][MISSION] += QUESTION.replace('store?', 'record?')
    execute(setup_quiz)
    execute(setup_quiz)
    assert setup_quiz[4].send.call_count == 2
    assert len(setup_quiz[3].data['quizzes'][MISSION]['results']) == 2
    assert 'atualizada' in setup_quiz[4].send.call_args.args[0]


def test_options_change_is_update(setup_quiz):
    execute(setup_quiz)
    setup_quiz[1][MISSION] = (MATERIAL + QUESTION).replace('Weather clouds', 'Financial clouds')
    execute(setup_quiz)
    assert setup_quiz[4].send.call_count == 2


def test_material_change_reanalyzes(setup_quiz):
    execute(setup_quiz)
    setup_quiz[1][MISSION] = '<article>Nothing to support these answers.</article>' + QUESTION
    execute(setup_quiz)
    assert setup_quiz[3].data['quizzes'][MISSION]['results'][0]['probable_answer'] is None
    assert setup_quiz[4].send.call_count == 2


def test_failed_delivery_cached_but_not_marked(setup_quiz):
    setup_quiz[4].send.side_effect = FetchError('failure')
    assert execute(setup_quiz) == 2
    assert setup_quiz[3].data['quizzes'][MISSION]['delivered_hash'] is None
    setup_quiz[4].send.side_effect = None
    assert execute(setup_quiz) == 0
    persisted = State(setup_quiz[3].path)
    assert persisted.data['quizzes'][MISSION]['delivered_hash']


def test_dry_run_neither_send_nor_write(setup_quiz):
    before = json.dumps(setup_quiz[3].data, sort_keys=True)
    assert execute(setup_quiz, dry_run=True) == 0
    assert json.dumps(setup_quiz[3].data, sort_keys=True) == before
    assert not setup_quiz[3].path.exists()
    setup_quiz[4].send.assert_not_called()
    assert report(setup_quiz)['public_quizzes'] == 1


def test_preserve_airdrop_history(setup_quiz):
    state = setup_quiz[3]
    state.data.update(sent={'old': 'hash'}, campaigns={'old': {'latest': 'unchanged'}}, summaries=['v2:day'])
    execute(setup_quiz)
    restored = State(state.path)
    assert restored.data['sent'] == {'old': 'hash'}
    assert restored.data['campaigns'] == {'old': {'latest': 'unchanged'}}
    assert restored.data['summaries'] == ['v2:day']


def test_no_public_questions_is_honest_and_deduplicated(setup_quiz):
    setup_quiz[1][MISSION] = '<h1>Sign in to start quiz</h1>' + MATERIAL
    execute(setup_quiz)
    execute(setup_quiz)
    assert report(setup_quiz)['public_quizzes'] == 0
    assert 'depende de login' in setup_quiz[3].data['quizzes'][MISSION]['status']
    assert setup_quiz[4].send.call_count == 1
    assert setup_quiz[2].get.call_count == 4  # Apenas hub e missão por execução, nenhuma API oculta.


def test_public_question_appears_later(setup_quiz):
    setup_quiz[1][MISSION] = MATERIAL
    execute(setup_quiz)
    setup_quiz[1][MISSION] += QUESTION
    execute(setup_quiz)
    assert setup_quiz[4].send.call_count == 2
    assert report(setup_quiz)['public_quizzes'] == 1


def test_transient_failure_preserves_cache(setup_quiz):
    execute(setup_quiz)
    old = dict(setup_quiz[3].data['quizzes'][MISSION])
    setup_quiz[1][MISSION] = FetchError('429 deferred')
    assert execute(setup_quiz) == 2
    assert setup_quiz[3].data['quizzes'][MISSION] == old
    assert setup_quiz[4].send.call_count == 1


def test_related_official_study(setup_quiz):
    setup_quiz[1][MISSION] = QUESTION + '<a href="./ledger-course/lesson">Study lesson</a>'
    setup_quiz[1][MISSION + '/lesson'] = MATERIAL
    execute(setup_quiz)
    answer = report(setup_quiz)['missions'][0]['results'][0]
    assert answer['support']['url'] == MISSION + '/lesson'


def test_partial_material_failure_does_not_erase(setup_quiz):
    execute(setup_quiz)
    old = dict(setup_quiz[3].data['quizzes'][MISSION])
    setup_quiz[1][MISSION] += '<a href="./ledger-course/lesson">Study lesson</a>'
    setup_quiz[1][MISSION + '/lesson'] = FetchError('unavailable')
    assert execute(setup_quiz) == 2
    assert setup_quiz[3].data['quizzes'][MISSION] == old


def test_untrusted_guild_is_not_analyzed(setup_quiz):
    ctx = list(setup_quiz)
    ctx[0] = replace(ctx[0], official=False, trusted_guilds=[])
    execute(ctx)
    assert report(ctx)['checked_missions'] == 0
    ctx[4].send.assert_not_called()


@pytest.mark.parametrize('markup', ['hidden', 'aria-hidden="true"', 'style="display:none"', 'style="visibility: hidden"'])
def test_hidden_questions_excluded(markup):
    assert extract_public_questions(f'<div {markup}>{QUESTION}</div>', MISSION) == []


def test_private_hydration_not_read():
    assert extract_public_questions('<script type="application/json">' + QUESTION + '</script>', MISSION) == []


def test_quiz_not_its_own_evidence():
    text = study_text(QUESTION)
    assert 'Distributed ledger records' not in text
    result = analyze_question('What does a blockchain store?', ['Distributed ledger records', 'Weather clouds'],
                              [{'url': MISSION, 'official': True, 'text': text}])
    assert result['probable_answer'] is None
    assert result['answer_status'] == 'não determinado'


@pytest.mark.parametrize('question', ['What does blockchain NOT store?', 'Qual alternativa é incorreta?',
                                     'Which is false?', 'Qual NÃO é correta?', 'All except which?'])
def test_negative_abstention(question):
    result = analyze_question(question, ['Distributed ledger records', 'Weather clouds'],
                             [{'url': MISSION, 'official': True, 'text': study_text(MATERIAL)}])
    assert result['probable_answer'] is None
    assert any('negativa' in x for x in result['limitations'])


def test_near_identical_options_abstain():
    result = analyze_question('What does a blockchain store?',
                             ['Distributed ledger records across network', 'Distributed ledger records across networks'],
                             [{'url': MISSION, 'official': True, 'text': study_text(MATERIAL)}])
    assert result['probable_answer'] is None


def test_negated_evidence_abstains():
    result = analyze_question('What does a blockchain store?', ['Distributed ledger records', 'Weather clouds'],
                             [{'url': MISSION, 'official': True,
                               'text': 'A blockchain does not store distributed ledger records.'}])
    assert result['probable_answer'] is None


def test_weak_keyword_overlap_abstains():
    result = analyze_question('What does a blockchain store?', ['Distributed ledger records', 'Weather clouds'],
                             [{'url': MISSION, 'official': True,
                               'text': 'A blockchain ledger may use various technologies for storing data.'}])
    assert result['probable_answer'] is None


def test_safe_link_discovery():
    links = ''.join(f'<a href="{x}">Study quiz lesson</a>' for x in
                    ['http://127.0.0.1/private', 'https://evil.test/quiz', '/api/quiz',
                     '/guilds/spam/quiz', '/login', MISSION + '/lesson', MISSION + '/lesson#again'])
    assert related_links(links, MISSION, ['www.bitdegree.org']) == [MISSION + '/lesson']
    assert mission_url(MISSION)
    assert not mission_url('https://evil.test/guilds/bitdegree/course')


def test_budget_requests_and_time():
    client = Mock()
    client.get.return_value = b'html', MISSION, 'text/html'
    clock = Mock(side_effect=[0, 0, 121])
    budget = Budget(client, DEFAULT_LIMITS, clock=clock)
    budget.get(MISSION, ['www.bitdegree.org'])
    with pytest.raises(FetchError):
        budget.get(MISSION, ['www.bitdegree.org'])
    assert client.get.call_count == 1
    budget = Budget(client, {**DEFAULT_LIMITS, 'max_requests': 1})
    budget.get(MISSION, ['www.bitdegree.org'])
    with pytest.raises(FetchError):
        budget.get(MISSION, ['www.bitdegree.org'])


def test_hard_budget_config(setup_quiz):
    with pytest.raises(ValueError):
        execute(setup_quiz, limits={'max_requests': 999})


def test_response_type_rejected(setup_quiz):
    setup_quiz[2].get.side_effect = None
    setup_quiz[2].get.return_value = b'{}', MISSION, 'application/json'
    assert execute(setup_quiz) == 2
    setup_quiz[4].send.assert_not_called()


def test_invalid_history_fails_closed(setup_quiz):
    setup_quiz[3].data['quizzes']['old'] = {'bad': True}
    with pytest.raises(ValueError):
        execute(setup_quiz)
    setup_quiz[2].get.assert_not_called()


def test_long_telegram_output_uses_existing_splitter(setup_quiz):
    execute(setup_quiz)
    message = setup_quiz[4].send.call_args.args[0] * 10
    chunks = split_message(message)
    assert len(chunks) > 1
    assert ''.join(chunks) == message
    assert all(len(x.encode('utf-16-le')) // 2 <= 3900 for x in chunks)


def test_round_robin_mission_checks(setup_quiz):
    source, pages, client, state, bot, reports = setup_quiz
    second = MISSION + '-two'
    pages[source.url] += f'<a href="{second}">Second quiz</a>'
    pages[second] = MATERIAL + QUESTION
    run([source], client, state, bot, reports, limits={'max_missions': 1})
    run([source], client, state, bot, reports, limits={'max_missions': 1})
    assert len(state.data['quizzes']) == 2


def test_login_form_is_not_quiz_or_study():
    markup = '<form action="/login"><fieldset><legend>Login</legend><label>User</label><label>Password</label>'
    markup += '<input type="password"></fieldset></form>'
    assert extract_public_questions(markup, MISSION) == []
    assert 'Password' not in study_text(markup)


def test_conflicting_official_material_abstains():
    result = analyze_question('What does a blockchain store?', ['Distributed ledger records', 'Weather clouds'],
                             [{'url': MISSION, 'official': True, 'text': study_text(MATERIAL)},
                              {'url': MISSION + '/other', 'official': True,
                               'text': 'A blockchain does not store distributed ledger records.'}])
    assert result['probable_answer'] is None


def test_all_of_above_abstains():
    result = analyze_question('What does a blockchain store?', ['Distributed ledger records', 'All of the above'],
                             [{'url': MISSION, 'official': True, 'text': study_text(MATERIAL)}])
    assert result['probable_answer'] is None


def test_public_client_rejects_cookies():
    from http.cookiejar import Cookie
    from urllib.request import Request
    from src.bitdegree_quizzes import public_client
    client = public_client()
    cookie = Cookie(0, 'session', 'private', None, False, 'www.bitdegree.org', True, False,
                    '/', True, True, None, True, None, None, {})
    client.session.cookies.set_cookie_if_ok(cookie, Request(MISSION))
    assert not list(client.session.cookies)


def test_cli_dry_run_and_report_failure(tmp_path, monkeypatch):
    from src.bitdegree_quizzes import main
    monkeypatch.setattr('sys.argv', ['quiz', '--dry-run', '--reports', str(tmp_path)])
    monkeypatch.setattr('src.bitdegree_quizzes.setup_logging', lambda *a: None)
    monkeypatch.setattr('src.bitdegree_quizzes.load_sources', Mock(side_effect=ValueError('bad config')))
    monkeypatch.setattr('src.bitdegree_quizzes.TelegramBot', Mock(side_effect=AssertionError('no Telegram')))
    assert main() == 1
    assert json.loads((tmp_path / 'bitdegree-failure.json').read_text())['error_type'] == 'ValueError'


def test_rejected_redirect_does_not_collect(setup_quiz):
    setup_quiz[2].get.side_effect = None
    setup_quiz[2].get.return_value = b'<html/>', 'https://evil.test/data', 'text/html'
    assert execute(setup_quiz) == 2
    assert report(setup_quiz)['checked_missions'] == 0
    setup_quiz[4].send.assert_not_called()


def test_mission_redirected_to_guild_not_a_quiz(setup_quiz):
    source, pages, client, state, bot, reports = setup_quiz
    original = client.get.side_effect
    def get(url, domains):
        if url == MISSION:
            return (MATERIAL + QUESTION).encode(), ROOT + '/guilds/bitdegree', 'text/html'
        return original(url, domains)
    client.get.side_effect = get
    assert execute(setup_quiz) == 2
    assert not state.data['quizzes']
    bot.send.assert_not_called()


def test_unrelated_mission_link_not_used_as_material():
    links = f'<a href="{ROOT}/guilds/bitdegree/unrelated">Study quiz lesson</a>'
    links += f'<a href="{ROOT}/crypto/tutorials/blockchain">Study lesson</a>'
    assert related_links(links, MISSION, ['www.bitdegree.org']) == [ROOT + '/crypto/tutorials/blockchain']


def test_failed_mission_does_not_starve_new_ones(setup_quiz):
    source, pages, client, state, bot, reports = setup_quiz
    second = MISSION + '-two'
    pages[source.url] += f'<a href="{second}">Second quiz</a>'
    pages[second] = MATERIAL + QUESTION
    pages[MISSION] = FetchError('unavailable')
    assert run([source], client, state, bot, reports, limits={'max_missions': 1}) == 2
    assert run([source], client, state, bot, reports, limits={'max_missions': 1}) == 0
    assert second in state.data['quizzes']
