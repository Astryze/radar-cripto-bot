"""AI Horde remote img2img; replaces local ComfyUI for GitHub-hosted execution.

Anonymous access via apikey 0000000000 may have long queues, low-resolution
outputs, model unavailability and rate limits. Images sent to volunteer workers
must be yours or permitted to be processed by a third-party service.
"""
import base64
import io
import os
import time
from urllib.parse import urlsplit

import requests
from PIL import Image, ImageOps

API = "https://aihorde.net/api/v2"
USER_AGENT = "MediaFlow-Unhas/2.0 (Astryze/radar-cripto-bot)"
MAX_PAYLOAD = 700_000

def make_payload(reference, prompt, seed, *, width=512, height=512, strength=0.77):
    if width % 64 or height % 64 or width > 576 or height > 576 or min(width, height) < 384:
        raise ValueError("Resolução não suportada pelo modo gratuito")
    with Image.open(reference) as original:
        image = ImageOps.fit(ImageOps.exif_transpose(original).convert("RGB"), (width, height))
    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", quality=76, method=4)
    if len(buffer.getvalue()) > MAX_PAYLOAD:
        raise ValueError("Imagem de referência grande demais para enviar")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return {
        "prompt": (prompt + " ### low quality, blurry, mangled nails, extra fingers, "
                   "text, watermark, food, drinks, random objects, feet, bottles, warped hand"),
        "source_image": encoded, "source_processing": "img2img",
        "params": {
            "sampler_name": "k_euler_a", "steps": 22, "n": 1,
            "width": width, "height": height, "cfg_scale": 7,
            "denoising_strength": strength, "seed": str(seed),
        },
        "nsfw": False, "censor_nsfw": True,
        "trusted_workers": True, "validated_backends": True, "slow_workers": True,
        "r2": True,
    }

def safe_result(url):
    """Restrict remote output downloads to Horde-controlled hosts, HTTPS only."""
    u = urlsplit(url or "")
    host = (u.hostname or "").lower()
    return (u.scheme == "https" and u.port in (None, 443)
            and not u.username and not u.password
            and (host == "stablehorde.net" or host.endswith(".stablehorde.net")
                 or host == "aihorde.net" or host.endswith(".aihorde.net")
                 or host == "cdn.stablehorde.net"))

def _response(resp):
    resp.raise_for_status()
    return resp.json()

def generate(reference, prompt, seed, *, session=None, api_key=None, timeout=480,
             poll=10, sleeper=time.sleep, clock=time.monotonic):
    session = session or requests.Session()
    key = api_key if api_key is not None else os.getenv("AI_HORDE_API_KEY", "0000000000")
    headers = {"apikey": key, "Content-Type": "application/json", "Client-Agent": USER_AGENT}
    payload = make_payload(reference, prompt, seed)
    submitted = _response(session.post(API + "/generate/async", json=payload,
                                      headers=headers, timeout=35))
    job_id = submitted.get("id")
    if not job_id or not isinstance(job_id, str):
        raise RuntimeError("AI Horde não confirmou pedido; créditos ou filas indisponíveis")
    deadline = clock() + timeout
    try:
        while clock() < deadline:
            check = _response(session.get(API + "/generate/check/" + job_id,
                                          headers=headers, timeout=25))
            if check.get("faulted") or check.get("is_possible") is False:
                raise RuntimeError("AI Horde não possui worker para este pedido")
            if check.get("done"):
                status = _response(session.get(API + "/generate/status/" + job_id,
                                               headers=headers, timeout=30))
                generations = status.get("generations") or []
                if not generations:
                    raise RuntimeError("AI Horde encerrou sem imagem")
                for result in generations:
                    if result.get("censored"):
                        continue
                    value = result.get("img")
                    if not value:
                        continue
                    if isinstance(value, str) and value.startswith("https://"):
                        if not safe_result(value):
                            raise RuntimeError("URL de imagem fora dos domínios aprovados")
                        download = session.get(value, timeout=50, allow_redirects=False)
                        if download.status_code != 200 or len(download.content) > 20_000_000:
                            raise RuntimeError("Falha ao recuperar imagem gerada")
                        raw = download.content
                    else:
                        raw = base64.b64decode(value, validate=True)
                    with Image.open(io.BytesIO(raw)) as image:
                        return ImageOps.exif_transpose(image).convert("RGB"), {
                            "job_id": job_id, "seed": result.get("seed"),
                            "model": result.get("model"), "provider": "AI Horde",
                        }
                raise RuntimeError("AI Horde retornou apenas resultados censurados")
            sleeper(poll)
        raise TimeoutError("AI Horde excedeu limite de fila de " + str(timeout) + " s")
    finally:
        # This is a no-op for completed jobs; cancels queued job when timeout/error.
        try:
            session.delete(API + "/generate/status/" + job_id, headers=headers, timeout=10)
        except requests.RequestException:
            pass
