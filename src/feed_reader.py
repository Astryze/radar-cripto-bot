import json
import logging
import re
from datetime import timedelta
from dataclasses import replace
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from defusedxml import ElementTree

from .models import Candidate, Source
from .utils import canonical_url, parse_date, plain_text, utcnow, validate_url

LOG = logging.getLogger(__name__)
ATOM = "{http://www.w3.org/2005/Atom}"


def load_sources(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    sources = [Source(**item) for item in data["sources"]]
    if len({s.id for s in sources}) != len(sources):
        raise ValueError("IDs de fontes duplicados")
    for source in sources:
        if source.kind not in {"feed", "listing", "bitdegree", "page"}:
            raise ValueError("Tipo de fonte inválido")
        if not 1 <= source.max_items <= 50 or not 1 <= source.max_age_days <= 365:
            raise ValueError("Limites de fonte inválidos")
        if not all(isinstance(d, str) and d == d.lower() and "/" not in d for d in source.domains):
            raise ValueError("Domínio inválido")
        validate_url(source.url, source.domains, resolve=False)
        re.compile(source.path_pattern)
    return sources


def parse_feed(data, source, now=None):
    now = now or utcnow()
    root = ElementTree.fromstring(data, forbid_dtd=True)
    if root.tag == "rss":
        entries = root.findall("./channel/item")
        atom = False
    elif root.tag == ATOM + "feed":
        entries = root.findall(ATOM + "entry")
        atom = True
    else:
        raise ValueError("Conteúdo não é RSS 2.0 ou Atom")
    found, seen = [], set()
    for entry in entries:
        if atom:
            title = entry.findtext(ATOM + "title", "")
            links = entry.findall(ATOM + "link")
            link = next((x.get("href", "") for x in links if x.get("rel", "alternate") == "alternate"), "")
            text = entry.findtext(ATOM + "content") or entry.findtext(ATOM + "summary", "")
            date = entry.findtext(ATOM + "published") or entry.findtext(ATOM + "updated")
        else:
            title, link = entry.findtext("title", ""), entry.findtext("link", "")
            text = entry.findtext("{http://purl.org/rss/1.0/modules/content/}encoded") or entry.findtext("description", "")
            date = entry.findtext("pubDate")
        link = urljoin(source.url, link)
        try:
            validate_url(link, source.domains, resolve=False)
        except ValueError:
            LOG.warning("%s: link rejeitado fora do domínio", source.id)
            continue
        published = parse_date(date)
        if published and (published < now - timedelta(days=source.max_age_days) or published > now + timedelta(days=1)):
            continue
        if not published:
            LOG.info("%s: publicação sem data válida", source.id)
        link = canonical_url(link)
        if not title.strip() or link in seen:
            continue
        seen.add(link)
        found.append(Candidate(plain_text(title)[:240], link, source, plain_text(text),
                               published.isoformat() if published else None))
        if len(found) >= source.max_items:
            break
    return found


def parse_listing(data, source):
    soup = BeautifulSoup(data, "html.parser")
    found, seen = [], set()
    for anchor in soup.select(source.selector):
        link = urljoin(source.url, anchor.get("href", ""))
        try:
            validate_url(link, source.domains, resolve=False)
        except ValueError:
            continue
        link = canonical_url(link)
        if not re.search(source.path_pattern, link) or link in seen or link == canonical_url(source.url):
            continue
        title = anchor.get_text(" ", strip=True)
        if not title or len(title) < 8:
            continue
        seen.add(link)
        found.append(Candidate(title[:240], link, source))
        if len(found) >= source.max_items:
            break
    if not found:
        raise ValueError("Nenhum item encontrado; possível mudança de layout, redirecionamento ou bloqueio")
    return found


def read_source(source, client):
    data, final, content_type = client.get(source.url, source.domains)
    # Links relativos pertencem à URL final, não ao domínio anterior ao redirect.
    source = replace(source, url=final)
    if source.kind == "feed":
        return parse_feed(data, source)
    if "html" not in content_type.lower():
        raise ValueError("Página não retornou HTML")
    if source.kind == "bitdegree":
        from .bitdegree import parse_learndrops
        return parse_learndrops(data, source)
    if source.kind == "page":
        soup = BeautifulSoup(data, "html.parser")
        title = soup.find("h1") or soup.find("title")
        if title is None:
            raise ValueError("Página sem título identificável")
        return [Candidate(title.get_text(" ", strip=True)[:240], final, source)]
    return parse_listing(data, source)


def verify_candidate(candidate, client):
    data, final, content_type = client.get(candidate.url, candidate.source.domains)
    if "html" not in content_type.lower():
        raise ValueError("Regras da campanha não retornaram HTML")
    text = plain_text(data, article_only=True)
    if len(text) < 80:
        raise ValueError("Conteúdo insuficiente; possível página dinâmica ou bloqueio")
    # Somente o artigo oficial verificado pode justificar custos/recompensas.
    candidate.text = text
    candidate.url = canonical_url(final)
    candidate.verified = candidate.source.official
    candidate.verification_url = final
    if not candidate.published:
        soup = BeautifulSoup(data, "html.parser")
        meta = soup.select_one('meta[property="article:published_time"]')
        stamp = soup.find("time", datetime=True)
        published = parse_date(meta.get("content") if meta else stamp.get("datetime") if stamp else None)
        candidate.published = published.isoformat() if published else None
    return candidate
