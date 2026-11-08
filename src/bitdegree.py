import re
from dataclasses import replace
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from .models import Candidate
from .utils import canonical_url, normalize, validate_url


def parse_learndrops(data, source):
    """Extrai missões públicas individuais, nunca a promessa global da landing page."""
    soup = BeautifulSoup(data, "html.parser")
    found, seen = [], set()
    for a in soup.select('a[href]'):
        url = urljoin(source.url, a.get("href", ""))
        try:
            validate_url(url, source.domains, resolve=False)
        except ValueError:
            continue
        path = urlsplit(url).path
        if not (re.fullmatch(r"/guilds/[^/]+/[^/]+/?", path) or path.rstrip("/") == "/leaderboard"):
            continue
        # prize-pool é uma aba da mesma missão, não uma segunda campanha.
        url = canonical_url(url.split("?", 1)[0])
        if url in seen:
            continue
        # Algumas versões usam um único <a> por card; outras usam título e CTA separados.
        card = a.find_parent(class_="promotional-card")
        if card is None and path.rstrip("/") == "/leaderboard":
            continue  # Link do menu; procurar o card com regras/status.
        card = card or a
        for parent in ([] if card is not a else [a.parent, a.parent.parent if a.parent else None]):
            if parent is None:
                continue
            text = parent.get_text(" ", strip=True)
            links = {urljoin(source.url, x.get("href", "")) for x in parent.select('a[href*="/guilds/"]')}
            if len(links) > 1:
                break
            if "status:" in text.lower():
                card = parent
                break
        text = card.get_text(" ", strip=True)
        heading = card.select_one("h2, h3, h4")
        title = heading.get_text(" ", strip=True) if heading else a.get_text(" ", strip=True)
        if not title or normalize(title) in {"start gaining", "see rewards"}:
            continue
        status = ""
        if re.search(r"\b(ended|expired|closed|encerrad[ao])\b", normalize(text)):
            status = "encerrado"
        elif re.search(r"\b(paused|on pause|pausad[ao])\b", normalize(text)):
            status = "pausado"
        elif re.search(r"status:\s*active\b", normalize(text)):
            status = "aberto"
        seen.add(url)
        candidate_source = source
        if not source.official:
            guild = path.split("/")[2] if path.startswith("/guilds/") else ""
            candidate_source = replace(source, official=guild in source.trusted_guilds)
        found.append(Candidate(title[:240], url, candidate_source, text, listing_status=status, listing_text=text))
        if len(found) >= source.max_items:
            break
    if not found:
        raise ValueError("BitDegree: nenhuma missão pública encontrada; revisar layout ou bloqueio")
    return found
