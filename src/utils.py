import hashlib
import ipaddress
import json
import logging
import os
import re
import socket
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup
from dateutil import parser

LOG = logging.getLogger(__name__)
MAX_BYTES = 2_000_000


class FetchError(RuntimeError):
    """Mensagem segura: nunca inclui URL da API Telegram ou credenciais."""


def normalize(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text.lower())
                   if not unicodedata.combining(c))


def canonical_url(url):
    p = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid", "ref"}]
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/") or "/",
                       urlencode(sorted(query)), ""))


def validate_url(url, domains=None, resolve=True):
    try:
        p = urlsplit(url)
        host = (p.hostname or "").encode("idna").decode("ascii").lower()
        if (p.scheme != "https" or not host or p.username is not None
                or p.password is not None or p.port not in (None, 443)
                or re.search(r"[\s\\\x00-\x1f]", url) or "%" in p.netloc):
            raise ValueError("URL HTTPS inválida")
        if domains is not None and host not in domains:
            raise ValueError("Domínio fora da lista autorizada")
        if host == "localhost" or host.endswith((".local", ".localhost", ".internal")):
            raise ValueError("Destino local proibido")
        try:
            addresses = [ipaddress.ip_address(host)]
        except ValueError:
            addresses = ([ipaddress.ip_address(a[4][0]) for a in
                          socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)] if resolve else [])
        if any(not ip.is_global for ip in addresses):
            raise ValueError("Destino não público")
    except (OSError, UnicodeError) as exc:
        raise ValueError("Domínio não resolvido") from exc
    return url


def utcnow():
    return datetime.now(timezone.utc)


def parse_date(value):
    if not value:
        return None
    try:
        dt = parser.parse(value, fuzzy=False)
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    except (ValueError, OverflowError, TypeError):
        return None


def plain_text(html, article_only=False):
    soup = BeautifulSoup(html, "html.parser")
    for el in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        el.decompose()
    root = (soup.select_one("article") or soup.select_one("main") or soup) if article_only else soup
    return re.sub(r"[ \t]+", " ", root.get_text("\n", strip=True))[:100_000]


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


class RedactFilter(logging.Filter):
    def filter(self, record):
        message = record.getMessage()
        for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
            secret = os.getenv(key)
            if secret:
                message = message.replace(secret, "[REDACTED]")
        record.msg = re.sub(r"bot\d+:[A-Za-z0-9_-]+", "bot[REDACTED]", message)
        record.args = ()
        return True


def setup_logging(log_dir):
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    handlers = [logging.StreamHandler(), logging.FileHandler(Path(log_dir) / "radar.log", encoding="utf-8")]
    for handler in handlers:
        handler.addFilter(RedactFilter())
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s",
                        handlers=handlers, force=True)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


class HttpClient:
    def __init__(self, session=None, sleep=time.sleep, attempts=3):
        self.session = session or requests.Session()
        self.sleep = sleep
        self.attempts = attempts
        self.session.headers.update({"User-Agent": "RadarCriptoBot/2.0 (+public research; no login)"})

    def get(self, url, domains):
        for _redirect in range(5):
            validate_url(url, domains)
            response = None
            for attempt in range(self.attempts):
                try:
                    response = self.session.get(url, timeout=(5, 20), allow_redirects=False, stream=True)
                    if response.status_code in {429, 500, 502, 503, 504}:
                        response.close()
                        if attempt + 1 < self.attempts:
                            self.sleep(min(2 ** attempt, 8))
                            continue
                    break
                except requests.RequestException:
                    if attempt + 1 == self.attempts:
                        raise FetchError("Falha de transporte após tentativas limitadas") from None
                    self.sleep(2 ** attempt)
            if response is None:
                raise FetchError("Sem resposta HTTP")
            if response.status_code in {301, 302, 303, 307, 308}:
                from urllib.parse import urljoin
                target = urljoin(url, response.headers.get("Location", ""))
                response.close()
                url = target
                continue
            try:
                if response.status_code != 200:
                    raise FetchError(f"HTTP {response.status_code}")
                data = bytearray()
                for chunk in response.iter_content(65536):
                    data.extend(chunk)
                    if len(data) > MAX_BYTES:
                        raise FetchError("Conteúdo excedeu 2 MB")
                return bytes(data), url, response.headers.get("Content-Type", "")
            except requests.RequestException:
                raise FetchError("Resposta incompleta") from None
            finally:
                response.close()
        raise FetchError("Limite de redirecionamentos excedido")
