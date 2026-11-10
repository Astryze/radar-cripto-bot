"""Openverse CC-licensed nail-art photo candidates without API key.

Uses the documented search endpoint, respects anonymous rate limits (no crawling),
and restricts downloads to expected public image CDNs. Metadata is a candidate
signal only: final approval uses the independent visual gate in run.py.
"""
import time
from io import BytesIO
from urllib.parse import urlparse

import requests
from PIL import Image, ImageOps

API = "https://api.openverse.org/v1/images/"
# CC0 and commercial-reuse-compatible licenses. ND and NC excluded.
PERMITTED_LICENSES = {"cc0", "pdm", "by", "by-sa"}
SEARCHES = {
    "vermelhas_elegantes": ("red nail art manicure", "red manicure nails", "burgundy nails"),
    "francesinha_delicada": ("french manicure nails",),
    "nude_sofisticadas": ("nude manicure nails",),
    "pretas_brilho": ("black nail art manicure",),
    "rosa_bebe": ("pink manicure nails",),
    "almond": ("almond nails manicure",),
    "encapsuladas": ("encapsulated nail art",),
    "glitter_dourado": ("gold glitter nail art",),
    "minimalistas": ("minimal nail art",),
    "flores": ("floral nail art manicure",),
    "francesinha_colorida": ("colorful french manicure",),
    "vinho": ("burgundy nails manicure",),
    "stiletto": ("stiletto nail art",),
    "cromadas": ("chrome manicure nails",),
    "noivas": ("bridal manicure nails",),
    "azul_claro": ("blue nail art manicure",),
    "verde_esmeralda": ("green manicure nails",),
    "pedrarias": ("rhinestone nail art",),
    "quadradas": ("square nails manicure",),
    "curtas": ("short nails manicure",),
    "marmore": ("marble nail art",),
    "rosa_glitter": ("pink glitter nail art",),
    "brancas": ("white nail art manicure",),
    "degrade": ("ombre nails manicure",),
    "olho_de_gato": ("cat eye nail art",),
    "vermelho_dourado": ("red gold manicure nails",),
    "lilas": ("lilac manicure nails",),
    "lacos": ("bow nail art",),
    "francesinha_reversa": ("reverse french manicure",),
    "luxo_3d": ("3d nail art",),
}
SAFE_CDN_SUFFIXES = ("staticflickr.com", "wikimedia.org", "wp.com")

def supported_url(url):
    """Avoid unsafe redirects and private intranet URLs from third-party indexes."""
    if not isinstance(url, str):
        return False
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return (parsed.scheme == "https" and parsed.port in (None, 443)
            and not parsed.username and not parsed.password
            and any(host == suffix or host.endswith("." + suffix)
                    for suffix in SAFE_CDN_SUFFIXES))

def permitted_license(item):
    return (str(item.get("license") or "").lower() in PERMITTED_LICENSES
            and bool(item.get("foreign_landing_url"))
            and bool(item.get("creator") or item.get("license") == "cc0"))

def iter_candidates(theme, session=None, maximum=45, delay=1.1):
    """Yield high-res candidates with source licensing details; no API key."""
    session = session or requests.Session()
    seen = set()
    emitted = 0
    for search in SEARCHES[theme]:
        # Anonymous API permits ordinary interactive search, not mass scraping.
        for page in (1, 2):
            try:
                response = session.get(API,
                    params={"q": search, "page_size": 20, "page": page,
                            "license_type": "commercial", "mature": "false"},
                    headers={"User-Agent": "MediaFlowUnhas/1.0 (noncommercial API evaluation; nail video creator)"},
                    timeout=25)
                if response.status_code == 429:
                    print("Openverse: limite gratuito atingido; interrompendo consultas", flush=True)
                    return
                response.raise_for_status()
                payload = response.json()
            except (requests.RequestException, ValueError) as exc:
                print(f"Openverse indisponível: {type(exc).__name__}", flush=True)
                return
            for item in payload.get("results", []):
                photo_id = item.get("id")
                if photo_id in seen or not permitted_license(item):
                    continue
                seen.add(photo_id)
                if (item.get("width") or 0) < 700 or (item.get("height") or 0) < 700:
                    continue
                url = item.get("url")
                if not supported_url(url):
                    continue
                try:
                    # Do not follow redirects to arbitrary domains from indexed image links.
                    photo_response = session.get(url, timeout=30, allow_redirects=False)
                    if photo_response.status_code != 200 or len(photo_response.content) > 15_000_000:
                        continue
                    with Image.open(BytesIO(photo_response.content)) as original:
                        img = ImageOps.exif_transpose(original).convert("RGB")
                except (requests.RequestException, OSError, ValueError):
                    continue
                emitted += 1
                yield img, {
                    "provider": "openverse",
                    "source": item.get("foreign_landing_url"),
                    "creator": item.get("creator"),
                    "license": item.get("license"),
                    "license_version": item.get("license_version"),
                    "license_url": item.get("license_url"),
                    "title": item.get("title"),
                    "query": search,
                    "requires_attribution": item.get("license") not in ("cc0", "pdm"),
                }
                if emitted >= maximum:
                    return
            if not payload.get("next"):
                break
            if delay:
                time.sleep(delay)
        if delay:
            time.sleep(delay)
