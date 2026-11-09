import hashlib
import ipaddress
import json
import logging
import os
import re
import random
import socket
import time
import unicodedata
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit, urljoin

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
        months = {"janeiro": "January", "fevereiro": "February", "março": "March", "marco": "March",
                  "abril": "April", "maio": "May", "junho": "June", "julho": "July", "agosto": "August",
                  "setembro": "September", "outubro": "October", "novembro": "November", "dezembro": "December"}
        if isinstance(value, str) and re.search(r"\b(" + "|".join(months) + r")\b", value, re.I):
            value = re.sub(r"\b(" + "|".join(months) + r")\b", lambda m: months[m.group().lower()], value, flags=re.I)
            value = re.sub(r"\bde\b", " ", value, flags=re.I)
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
        for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "ZEALY_API_KEY", "ZEALY_USER_ID", "GALXE_ACCESS_TOKEN"):
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


class DeferredFetch(FetchError):
    def __init__(self, status, next_retry_at, monitor_url=None):
        self.status = status
        self.next_retry_at = next_retry_at
        self.monitor_url = monitor_url
        super().__init__(f"HTTP {status}: consulta adiada até {next_retry_at}")


def retry_after_seconds(value, now=None):
    """Delta-seconds e HTTP-date; nunca reduz a espera indicada pelo servidor."""
    if not value:
        return None
    now = now or utcnow()
    try:
        seconds = float(value)
        return max(0.0, seconds) if seconds >= 0 and seconds < float('inf') else None
    except (ValueError, TypeError):
        from email.utils import parsedate_to_datetime
        try:
            stamp = parsedate_to_datetime(value)
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            return max(0.0, (stamp - now).total_seconds())
        except (ValueError, TypeError, OverflowError):
            return None


class HttpClient:
    def __init__(self, session=None, sleep=time.sleep, attempts=3, jitter=None,
                 now=utcnow, clock=time.monotonic, max_retry_wait=30, min_interval=0):
        self.session = session or requests.Session()
        self.sleep = sleep
        self.attempts = attempts
        self.jitter = jitter or (lambda: random.uniform(0, 1))
        self.now, self.clock = now, clock
        self.max_retry_wait = max_retry_wait
        self.min_interval = min_interval
        self.records = []
        self.cooldowns = {}
        self._last_request = {}
        self.cache = {}
        self.session.headers.update({"User-Agent": "RadarCriptoBot/2.0 (+public research; no login)"})

    def _defer(self, url, status, delay, monitor_url=None):
        deadline = self.now() + timedelta(seconds=delay)
        self.cooldowns[urlsplit(url).hostname] = {"until": deadline.isoformat(), "status": status}
        raise DeferredFetch(status, deadline.isoformat(), monitor_url)

    def _monitor(self, response, url, domains):
        target = response.headers.get("Location")
        if not target:
            link = response.headers.get("Link", "")
            match = re.search(r'<([^>]+)>;\s*rel=["\']?monitor', link, re.I)
            target = match.group(1) if match else None
        if target:
            target = urljoin(url, target)
            validate_url(target, domains)
        return target

    def get(self, url, domains):
        return self._request(url, domains)

    def _request(self, url, domains, *, method='GET', payload=None, headers=None, record_url=None, cache=True):
        from .platform_permissions import guard_request
        guard_request(url, method=method)
        if cache and url in self.cache:
            return self.cache[url]
        original_url = url
        for _redirect in range(5):
            guard_request(url, method=method)
            validate_url(url, domains)
            host = urlsplit(url).hostname
            cooldown = self.cooldowns.get(host)
            until = parse_date(cooldown.get("until")) if cooldown else None
            if until and until > self.now():
                raise DeferredFetch(cooldown["status"], until.isoformat())
            for attempt in range(self.attempts):
                last = self._last_request.get(host)
                if last is not None:
                    delay = self.min_interval - (self.clock() - last)
                    if delay > 0:
                        self.sleep(delay)
                self._last_request[host] = self.clock()
                response = None
                try:
                    options = {'timeout': (5, 20), 'allow_redirects': False, 'stream': True}
                    if headers is not None:
                        options['headers'] = headers
                    if method == 'POST':
                        response = self.session.post(url, json=payload, **options)
                    else:
                        response = self.session.get(url, **options)
                    status = response.status_code
                    record = {"url": record_url or url, "status": status, "attempt": attempt + 1,
                              "attempted_at": self.now().isoformat(), "content_type": response.headers.get("Content-Type", "")}
                    self.records.append(record)
                    if status == 202:
                        monitor = None if record_url else self._monitor(response, url, domains)
                        wait = retry_after_seconds(response.headers.get("Retry-After"), self.now())
                        # 202 não contém resultado: só consultar depois, sem inventar endpoint.
                        self._defer(url, 202, max(60, wait if wait is not None else 900), monitor)
                    if status == 429 or 500 <= status <= 599:
                        retry = retry_after_seconds(response.headers.get("Retry-After"), self.now())
                        delay = max(2 ** attempt + self.jitter(), retry or 0)
                        limit = min(self.attempts, 2) if status == 429 else self.attempts
                        if attempt + 1 >= limit or delay > self.max_retry_wait:
                            self._defer(url, status, max(delay, 900 if status == 429 else 300))
                        response.close()
                        self.sleep(delay)
                        continue
                    break
                except requests.RequestException:
                    if response is not None:
                        response.close()
                    if attempt + 1 == self.attempts:
                        raise FetchError("Falha de transporte após tentativas limitadas") from None
                    self.sleep(2 ** attempt + self.jitter())
                except Exception:
                    if response is not None:
                        response.close()
                    raise
            if response is None:
                raise FetchError("Sem resposta HTTP")
            if response.status_code in {301, 302, 303, 307, 308}:
                if method != 'GET' or host == 'api-v2.zealy.io':
                    response.close()
                    raise FetchError('Redirecionamento Zealy rejeitado')
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
                result = bytes(data), url, response.headers.get("Content-Type", "")
                if cache:
                    self.cache[original_url] = result
                return result
            except requests.RequestException:
                raise FetchError("Resposta incompleta") from None
            finally:
                response.close()
        raise FetchError("Limite de redirecionamentos excedido")
