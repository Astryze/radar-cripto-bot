"""Formatos públicos explícitos. Nunca interpreta títulos promocionais como perguntas."""
import json
from bs4 import BeautifulSoup
from .quiz_analyzer import public_soup


def extract_additional(body, url):
    raw = BeautifulSoup(body, 'html.parser')
    visible = public_soup(body)
    found = []
    for node in visible.select('[data-question-type], [role="group"][aria-labelledby], fieldset')[:50]:
        kind = node.get('data-question-type', 'single')
        original = raw.find(id=node.get('id')) if node.get('id') else next(
            (x for x in raw.select('fieldset') if x.get_text(' ', strip=True) == node.get_text(' ', strip=True)), None)
        if original and original.select_one('input[type="checkbox"]'):
            kind = 'multiple'
        if node.select_one('textarea'):
            kind = 'written'
        title = node.select_one('.question-title, legend, [data-question-text]')
        if title is None and node.get('aria-labelledby'):
            title = visible.find(id=node['aria-labelledby'])
        options = [x.get_text(' ', strip=True) for x in node.select('label, [data-option], [role="radio"], [role="checkbox"]')]
        if title and (len(options) >= 2 or kind in {'written', 'text'}):
            found.append({'question': title.get_text(' ', strip=True)[:1200], 'options': options[:12],
                          'question_type': 'written' if kind in {'written','text'} else 'multiple' if kind == 'multiple' else 'single',
                          'question_source': url})
    # Apenas contrato explícito de quiz público. Não varre hidratação, gabaritos ou rotas JS.
    for script in raw.select('script[type="application/json"][data-public-quiz="true"], script[type="application/ld+json"]')[:10]:
        try:
            data = json.loads(script.string or '')
        except (ValueError, TypeError):
            continue
        if script.find_parent(attrs={'hidden': True}):
            continue
        if not isinstance(data, dict) or data.get('@type') != 'Quiz' or data.get('requiresAuthentication') is True:
            continue
        for q in data.get('hasPart', [])[:50]:
            if not isinstance(q, dict) or q.get('@type') != 'Question' or q.get('requiresAuthentication') is True:
                continue
            text, options = q.get('text'), q.get('options', [])
            if not isinstance(text, str) or not isinstance(options, list) or not all(isinstance(x,str) for x in options):
                continue
            kind = q.get('questionType', 'single')
            if kind in {'single', 'multiple', 'written'} and (len(options) >= 2 or kind == 'written'):
                found.append({'question':text[:1200], 'options':options[:12], 'question_type':kind,
                              'question_source':url})
    return found


def inconclusive(question):
    return {**question, 'probable_answer':None, 'answer_status':'não determinado', 'confidence':'baixa',
            'reasoning':'Formato identificado, mas não há método validado para determinar a resposta completa com evidência suficiente.',
            'support':None, 'evidence':[], 'limitations':['Resposta escrita ou múltipla exige revisão humana.'],
            'automatic_submission':False}
