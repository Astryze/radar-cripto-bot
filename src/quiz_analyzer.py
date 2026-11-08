"""Assistente local de estudo, baseado em trechos públicos. Não submete respostas."""
import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup

from .feed_reader import load_sources
from .utils import HttpClient, atomic_json, normalize, plain_text, validate_url

STOP = set("a o e de da do as os um uma em na no the is of to and or for in an which what que qual como are on with".split())
ANALYZER_VERSION = "2.1.0"


def public_soup(body):
    """Somente HTML visível: não consulta hidratação, gabaritos ou endpoints privados."""
    soup = BeautifulSoup(body, "html.parser")
    for el in list(soup.select('form')):
        if el.select_one('input[type="password"], [class*="captcha"]') or re.search(
                r'login|sign.?in|authenticate', el.get('action', ''), re.I):
            el.decompose()
    for el in list(soup.select('script, style, noscript, template, [hidden], [aria-hidden="true"], input')):
        el.decompose()
    for el in list(soup.select('[style]')):
        if re.search(r'display\s*:\s*none|visibility\s*:\s*hidden', el.get('style', ''), re.I):
            el.decompose()
    return soup


def extract_public_questions(body, url, selectors=None):
    selectors = selectors or {}
    soup = public_soup(body)
    questions, seen = [], set()
    for container in soup.select(selectors.get('container_selector', 'fieldset, [data-quiz-question]'))[:50]:
        title = container.select_one(selectors.get('question_selector', 'legend, .question-title'))
        options = [x.get_text(' ', strip=True)[:600] for x in container.select(
            selectors.get('option_selector', 'label, [data-option]'))]
        options = list(dict.fromkeys(x for x in options if x))
        if title is None or len(options) < 2 or len(options) > 12:
            continue
        question = title.get_text(' ', strip=True)[:1200]
        key = (question, tuple(options))
        if question and key not in seen:
            seen.add(key)
            questions.append({'question': question, 'options': options, 'question_source': url})
    return questions


def study_text(body):
    soup = public_soup(body)
    for el in list(soup.select('form, fieldset, [data-quiz-question], nav, footer, header, aside')):
        el.decompose()
    return plain_text(str(soup), article_only=True)


def tokens(text):
    return {x for x in re.findall(r"[a-z0-9]+", normalize(text)) if len(x) > 2 and x not in STOP}


def analyze_question(question, options, materials):
    """Ranking lexical auditável; abstém quando as alternativas não têm suporte distinto."""
    if not question.strip() or len(options) < 2 or len(set(options)) != len(options):
        raise ValueError("Forneça pergunta e ao menos duas alternativas distintas")
    docs = []
    for material in materials:
        if not material.get("official"):
            continue
        for passage in re.split(r"\n+|(?<=[.!?])\s+", material["text"]):
            if len(passage) > 25:
                docs.append((material["url"], passage[:1500], tokens(passage)))
    frequencies = Counter(t for _, _, ts in docs for t in ts)
    q = tokens(question)
    ranks = []
    for option in options:
        answer = tokens(option)
        best = (0, "", "")
        for url, passage, ts in docs:
            relevance = len(q & ts) / max(1, len(q))
            support = sum(math.log(1 + len(docs) / frequencies[t]) for t in answer & ts)
            coverage = len(answer & ts) / max(1, len(answer))
            value = relevance * coverage * support
            if value > best[0]:
                best = (value, url, passage)
        ranks.append({"alternative": option, "score": round(best[0], 5),
                      "source": best[1], "excerpt": best[2]})
    ranks.sort(key=lambda r: -r["score"])
    negative = r"\b(not|except|incorrect|false|least|never|nao|exceto|incorret[ao]s?|fals[ao]s?|nunca|menos|sem|without)\b"
    negated = bool(re.search(negative, normalize(question)))
    ambiguous = any(re.search(negative, normalize(o)) for o in options)
    ambiguous = ambiguous or any(re.search(r'\b(all|none|todas|todos|nenhuma|nenhum)\b', normalize(o))
                                 for o in options)
    option_tokens = [tokens(o) for o in options]
    similar = any(len(a & b) / max(1, len(a | b)) >= .65
                  for i, a in enumerate(option_tokens) for b in option_tokens[i + 1:])
    best = ranks[0]
    # A frase precisa estar no trecho. Sobreposição lexical sozinha não prova uma resposta.
    exact = normalize(best['alternative']) in normalize(best['excerpt'])
    contradiction = bool(re.search(negative, normalize(best['excerpt'])))
    contradiction = contradiction or any(
        normalize(best['alternative']) in normalize(passage) and re.search(negative, normalize(passage))
        and q & ts for _, passage, ts in docs)
    supported = (not any((negated, ambiguous, similar, contradiction)) and exact
                 and best['score'] > .2 and best['score'] > ranks[1]['score'] * 1.5)
    return {"question": question, "probable_answer": ranks[0]["alternative"] if supported else None,
            "confidence": "média" if supported else "baixa",
            "reasoning": ("A alternativa tem maior cobertura de termos em trecho oficial relacionado à pergunta. "
                          "É uma pista de estudo por busca lexical; confira o trecho no contexto."
                          if supported else "Evidência insuficiente ou pergunta negativa; resposta não determinada."),
            "evidence": ranks, "options": options,
            "answer_status": "resposta provável" if supported else "não determinado",
            "support": {"url": best['source'], "excerpt": best['excerpt']} if supported else None,
            "limitations": ["Busca lexical conservadora; exige revisão humana. Sem inferência semântica ou gabarito."]
            + (["Pergunta negativa: não é seguro escolher por ausência de evidência."] if negated else [])
            + (["Alternativas semelhantes ou negativas."] if similar or ambiguous else [])
            + ([] if supported else ["Não há apoio oficial distinto e suficiente para determinar a resposta."]),
            "automatic_submission": False}


def analyze_public_quiz(data, sources, client):
    if data.get("authorized_public_material") is not True:
        raise ValueError("Confirme que o material é público e a consulta é autorizada")
    domains = {d for s in sources if s.official for d in s.domains}
    materials = []
    for url in data.get("materials", [])[:10]:
        validate_url(url, domains)
        body, final, content_type = client.get(url, domains)
        if "html" not in content_type:
            raise ValueError("Material deve ser página HTML pública")
        materials.append({"url": final, "text": study_text(body), "official": True})
    questions = list(data.get("questions", []))
    for page in data.get("question_pages", [])[:5]:
        # Extração de formulários públicos estáticos, sem clicar, preencher ou enviar.
        validate_url(page["url"], domains)
        body, final, content_type = client.get(page["url"], domains)
        if "html" not in content_type:
            raise ValueError("Perguntas devem estar em HTML público")
        questions.extend(extract_public_questions(body, final, page))
    if not questions:
        raise ValueError("Nenhuma pergunta pública identificada; não contornar login ou CAPTCHA")
    results = []
    for question in questions[:50]:
        result = analyze_question(question["question"], question["options"], materials)
        result["question_source"] = question.get("question_source", "entrada fornecida pelo usuário")
        results.append(result)
    return results


def main():
    arg = argparse.ArgumentParser(description="Estudo de quizzes públicos; nenhuma submissão automática")
    arg.add_argument("input", type=Path, help="JSON com questions, options, materials e authorized_public_material")
    arg.add_argument("--sources", type=Path, default=Path("config/sources.json"))
    arg.add_argument("--output", type=Path, default=Path("reports/quiz-results.json"))
    args = arg.parse_args()
    result = analyze_public_quiz(json.loads(args.input.read_text()), load_sources(args.sources), HttpClient())
    atomic_json(args.output, result)


if __name__ == "__main__":
    main()
