"""Pexels candidate retrieval. All images must pass separate visual QA before use.

Use PEXELS_API_KEY from environment. Licensing/attribution retained for review.
"""
import os
from io import BytesIO
from urllib.parse import urlparse

import requests
from PIL import Image, ImageOps

PEXELS_API = "https://api.pexels.com/v1/search"
QUERY_BY_THEME = {
    "vermelhas_elegantes": ["red luxury nail art close up", "red glitter manicure nails", "burgundy nail art manicure"],
    "francesinha_delicada": ["elegant french tip manicure close up", "white french nails"],
    "nude_sofisticadas": ["luxury nude nail art close up", "beige gel nails"],
    "pretas_brilho": ["black gold luxury nail art", "black glitter manicure nails"],
    "rosa_bebe": ["baby pink gel nails close up"],
    "almond": ["almond shape manicure art close up"],
    "encapsuladas": ["encapsulated nail art manicure"],
    "glitter_dourado": ["gold glitter luxury nail art close up"],
    "minimalistas": ["minimalist manicure nail art close up"],
    "flores": ["floral nail art manicure close up"],
    "francesinha_colorida": ["colorful french tip nail art close up"],
    "vinho": ["burgundy nail art close up"],
    "stiletto": ["luxury stiletto nail art close up"],
    "cromadas": ["chrome nail art manicure close up"],
    "noivas": ["bridal luxury manicure wedding nails"],
    "azul_claro": ["light blue nail art close up"],
    "verde_esmeralda": ["emerald green nail art close up"],
    "pedrarias": ["rhinestone nail art close up"],
    "quadradas": ["square nail art manicure close up"],
    "curtas": ["short luxury nail art manicure"],
    "marmore": ["marble nail art manicure"],
    "rosa_glitter": ["pink glitter nail art close up"],
    "brancas": ["white luxury nail art manicure"],
    "degrade": ["ombre gradient nail art manicure"],
    "olho_de_gato": ["cat eye magnetic gel nail art"],
    "vermelho_dourado": ["red gold luxury nail art manicure"],
    "lilas": ["lilac nail art manicure close up"],
    "lacos": ["coquette bow nail art manicure"],
    "francesinha_reversa": ["reverse french tip manicure close up"],
    "luxo_3d": ["luxury 3d nail art close up"],
}

def iter_candidates(theme, *, api_key=None, session=None, max_candidates=100):
    """Yield (PIL RGB image, credit dict), not pre-approved photos."""
    key = api_key or os.getenv("PEXELS_API_KEY", "").strip()
    if not key:
        return
    session = session or requests.Session()
    yielded = 0
    seen_ids = set()
    for query in QUERY_BY_THEME[theme]:
        for page in (1, 2):
            r = session.get(PEXELS_API,
                headers={"Authorization": key},
                params={"query": query, "orientation": "portrait", "per_page": 40, "page": page},
                timeout=25)
            r.raise_for_status()
            photos = r.json().get("photos", [])
            if not photos:
                break
            for item in photos:
                photo_id = item.get("id")
                if not photo_id or photo_id in seen_ids:
                    continue
                seen_ids.add(photo_id)
                src = item.get("src") or {}
                url = src.get("large2x") or src.get("large")
                host = urlparse(url).hostname if url else ""
                if not host or not (host == "pexels.com" or host.endswith(".pexels.com")):
                    continue
                try:
                    response = session.get(url, timeout=30)
                    response.raise_for_status()
                    if len(response.content) > 15_000_000:
                        continue
                    with Image.open(BytesIO(response.content)) as original:
                        photo = ImageOps.exif_transpose(original).convert("RGB")
                    yielded += 1
                    yield photo, {
                        "provider": "pexels", "source": item.get("url"),
                        "photographer": item.get("photographer"),
                        "photographer_url": item.get("photographer_url"),
                        "pexels_id": photo_id, "query": query,
                        "license": "Pexels License — review conditions before publication",
                    }
                    if yielded >= max_candidates:
                        return
                except (requests.RequestException, ValueError, OSError):
                    continue
