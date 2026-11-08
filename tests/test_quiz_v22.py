"""EXEMPLOS ARTIFICIAIS: não são perguntas coletadas da BitDegree."""
import json
import pytest
from src.quiz_analyzer import extract_public_questions, study_text
from src.public_questions import inconclusive
from src.quiz_diagnostics import diagnose

URL = 'https://www.bitdegree.org/guilds/bitdegree/example'


def test_observed_server_shell_not_a_question():
    html = '<div id="missions-mount"><dashboard-layout></dashboard-layout></div>'
    html += '<h1>What is blockchain?</h1><ol class="missions-server-content__rounds"><li>Introduction</li></ol>'
    assert extract_public_questions(html, URL) == []
    result = diagnose(html, URL)
    assert result['dynamic_shell_observed']
    assert result['round_titles'] == ['Introduction']
    assert result['access_requirement'] == 'not_determined'


@pytest.mark.parametrize('kind,options', [('single',['Ledger','Cloud']),('multiple',['Ledger','Cloud']),('written',[])])
def test_explicit_public_json(kind, options):
    data = {'@type':'Quiz','hasPart':[{'@type':'Question','text':'What is blockchain?',
                                     'options':options,'questionType':kind}]}
    html = '<script type="application/ld+json">' + json.dumps(data) + '</script>'
    result = extract_public_questions(html, URL)
    assert len(result) == 1
    assert result[0]['question_type'] == kind
    assert not study_text(html)
    if kind != 'single':
        assert inconclusive(result[0])['probable_answer'] is None


@pytest.mark.parametrize('payload', [{'@type':'FAQPage'}, {'@type':'Quiz','requiresAuthentication':True},
                                     {'@type':'Quiz','hasPart':[{'@type':'Question','requiresAuthentication':True,'text':'Private?','options':['A','B']}]}])
def test_no_private_or_non_quiz_json(payload):
    html = '<script type="application/ld+json">'+json.dumps(payload)+'</script>'
    assert extract_public_questions(html, URL) == []


def test_invalid_json_reported_not_fabricated():
    html = '<script type="application/ld+json">{invalid</script>'
    assert extract_public_questions(html, URL) == []
    assert diagnose(html, URL)['invalid_json_blocks'] == 1


def test_written_question_explicit_html():
    html = '<fieldset data-question-type="written"><legend>Define consensus.</legend><textarea></textarea></fieldset>'
    assert extract_public_questions(html, URL)[0]['question_type'] == 'written'
    assert 'Define consensus' not in study_text(html)


def test_multiple_not_silently_single():
    html = '<fieldset id="q"><legend>Select statements.</legend><label>Ledger</label><input type="checkbox"><label>Cloud</label></fieldset>'
    questions = extract_public_questions(html, URL)
    assert len(questions) == 1
    assert questions[0]['question_type'] == 'multiple'


def test_login_not_inferred_from_js_only():
    html = '<script src="missions.js"></script><h1>Mission</h1>'
    assert diagnose(html, URL)['access_requirement'] == 'not_determined'
    assert diagnose('<form><input type="password"></form>',URL)['login_form_observed']


def test_real_shape_audit_with_mock_only():
    from unittest.mock import Mock
    from scripts.diagnose_bitdegree import audit
    client = Mock()
    client.get.return_value = b'<div id="missions-mount"><dashboard-layout></dashboard-layout></div>', URL, 'text/html'
    result = audit([{'title':'EXEMPLO ARTIFICIAL','url':URL}],client)['missions'][0]
    assert result['http_status'] == 200
    assert result['questions_extracted'] == result['questions_analyzed'] == result['conclusive_answers'] == 0
    assert result['diagnostic']['reason_code'] == 'dynamic_shell_without_question_payload'
