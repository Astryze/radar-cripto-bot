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
    negated = bool(re.search(r"\b(not|except|incorrect|nao|exceto|incorret[ao])\b", normalize(question)))
    supported = not negated and ranks[0]["score"] > 0.2 and ranks[0]["score"] > ranks[1]["score"] * 1.5
    return {"question": question, "probable_answer": ranks[0]["alternative"] if supported else None,
            "confidence": "média" if supported else "baixa",
            "reasoning": ("A alternativa tem maior cobertura de termos em trecho oficial relacionado à pergunta. "
                          "É uma pista de estudo por busca lexical; confira o trecho no contexto."
                          if supported else "Evidência insuficiente ou pergunta negativa; resposta não determinada."),
            "evidence": ranks, "automatic_submission": False}


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
        materials.append({"url": final, "text": plain_text(body, article_only=True), "official": True})
    questions = list(data.get("questions", []))
    for page in data.get("question_pages", [])[:5]:
        # Extração de formulários públicos estáticos, sem clicar, preencher ou enviar.
        validate_url(page["url"], domains)
        body, final, content_type = client.get(page["url"], domains)
        if "html" not in content_type:
            raise ValueError("Perguntas devem estar em HTML público")
        soup = BeautifulSoup(body, "html.parser")
        for container in soup.select(page.get("container_selector", "fieldset"))[:50]:
            title = container.select_one(page.get("question_selector", "legend"))
            options = [o.get_text(" ", strip=True) for o in container.select(page.get("option_selector", "label"))]
            if title is not None and len(options) >= 2:
                questions.append({"question": title.get_text(" ", strip=True), "options": options,
                                  "question_source": final})
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
