"""Gerar 10 fotos com ComfyUI local e renderizar vídeo de 10 segundos.

Workflow: exporte API-format JSON do ComfyUI e coloque {{PROMPT}} em um nó de texto.
Opcionalmente use {{SEED}} no seed do sampler para garantir novas amostras.
"""
import argparse
import copy
import hashlib
import json
import random
import time
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image, ImageOps
from run import THEMES, render


def validate_server(server):
    parsed = urlparse(server)
    if (parsed.scheme != "http" or parsed.hostname not in ("localhost", "127.0.0.1")
            or parsed.username or parsed.password or parsed.path not in ("", "/")):
        raise ValueError("Por segurança, somente ComfyUI local em http://127.0.0.1:8188")
    return server.rstrip("/")


def prepare_workflow(template, prompt, seed):
    graph = copy.deepcopy(template)
    count = 0
    for node in graph.values():
        if not isinstance(node, dict):
            continue
        for key, value in node.get("inputs", {}).items():
            if isinstance(value, str) and "{{PROMPT}}" in value:
                node["inputs"][key] = value.replace("{{PROMPT}}", prompt)
                count += 1
            elif value == "{{SEED}}":
                node["inputs"][key] = seed
    if not count:
        raise ValueError("Workflow precisa de {{PROMPT}} e deve ser exportado no formato API")
    return graph


def generate_one(session, server, graph, timeout=240):
    response = session.post(server + "/prompt", json={"prompt": graph}, timeout=20)
    response.raise_for_status()
    payload = response.json()
    if payload.get("error") or not payload.get("prompt_id"):
        raise RuntimeError("ComfyUI rejeitou o workflow ou o modelo não está disponível")
    prompt_id = payload["prompt_id"]
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        response = session.get(server + "/history/" + prompt_id, timeout=15)
        response.raise_for_status()
        job = response.json().get(prompt_id)
        if job:
            if job.get("status", {}).get("status_str") == "error":
                raise RuntimeError("ComfyUI falhou durante a geração")
            for output in job.get("outputs", {}).values():
                for photo in output.get("images", []):
                    if photo.get("type", "output") != "output":
                        continue
                    r = session.get(server + "/view", params={
                        "filename": photo["filename"],
                        "subfolder": photo.get("subfolder", ""),
                        "type": "output"
                    }, timeout=40)
                    r.raise_for_status()
                    if len(r.content) > 16_000_000:
                        raise RuntimeError("Imagem ComfyUI muito grande")
                    with Image.open(BytesIO(r.content)) as im:
                        return ImageOps.exif_transpose(im).convert("RGB")
            raise RuntimeError("Workflow terminou sem imagem: configure SaveImage")
        time.sleep(2)
    raise TimeoutError("ComfyUI não respondeu a tempo")


def generate_ten(theme, workflow, server, output, effect="zoom"):
    if theme not in THEMES:
        raise ValueError("Tema de unhas desconhecido")
    server = validate_server(server)
    template = json.loads(Path(workflow).read_text(encoding="utf-8"))
    folder = Path(output)
    folder.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    photos, hashes = [], set()
    for i in range(10):
        prompt = (f"Photorealistic editorial macro nail beauty photography: {THEMES[theme]}. "
                  "Realistic hands and fingers, immaculate manicure, studio lighting, "
                  f"vertical 9:16, unique design variation {i+1}, no text or watermark.")
        graph = prepare_workflow(template, prompt, random.SystemRandom().randint(1, 2**48))
        image = generate_one(session, server, graph)
        fingerprint = hashlib.sha256(image.tobytes()).hexdigest()
        if fingerprint in hashes:
            raise RuntimeError("ComfyUI gerou imagem repetida. Vídeo recusado.")
        hashes.add(fingerprint)
        file = folder / f"ai_{i+1:02}.jpg"
        image.save(file, quality=92)
        photos.append(file)
    video = render(photos, folder / "final.mp4", effect)
    (folder / "manifest.json").write_text(json.dumps({
        "theme": theme, "count": len(photos), "seconds": 10,
        "source": "ComfyUI local", "ai_generated": True, "effect": effect
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return video


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tema", choices=sorted(THEMES), default="vermelhas_elegantes")
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--server", default="http://127.0.0.1:8188")
    parser.add_argument("--saida", default="output/ia-unhas")
    parser.add_argument("--efeito", choices=["zoom", "fade", "cortes"], default="zoom")
    a = parser.parse_args()
    print(generate_ten(a.tema, a.workflow, a.server, a.saida, a.efeito))
