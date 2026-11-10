"""Generate 10 NEW images from nail references through a LOCAL ComfyUI img2img graph.

Reference photos are never used as the final MP4 frames. The graph must be an
API-format JSON template with {{PROMPT}}, {{SEED}} and {{REFERENCE_IMAGE}}
placeholders; the latter must be the LoadImage node's image input. The ComfyUI
graph must actually connect LoadImage to the image generation path (img2img /
IPAdapter / ControlNet). Users own model installation and workflow selection.
"""
import argparse
import json
import random
import time
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image, ImageOps

try:
    from .reference_collector import collect
    from .quality import dhash, is_duplicate
    from .visual_guard import check_image, STYLE_PROMPTS
except ImportError:
    from reference_collector import collect
    from quality import dhash, is_duplicate
    from visual_guard import check_image, STYLE_PROMPTS

def build_graph(template, prompt, seed, reference_name):
    """Replace placeholders recursively without touching other model settings."""
    counts = {"prompt": 0, "seed": 0, "image": 0}
    def replace(obj):
        if isinstance(obj, dict):
            return {k: replace(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [replace(v) for v in obj]
        if obj == "{{SEED}}":
            counts["seed"] += 1
            return seed
        if isinstance(obj, str):
            if "{{PROMPT}}" in obj:
                counts["prompt"] += 1
                obj = obj.replace("{{PROMPT}}", prompt)
            if "{{REFERENCE_IMAGE}}" in obj:
                counts["image"] += 1
                obj = obj.replace("{{REFERENCE_IMAGE}}", reference_name)
        return obj
    graph = replace(template)
    if not isinstance(graph, dict) or not all(counts.values()):
        raise ValueError("Workflow API requer {{PROMPT}}, {{SEED}} e {{REFERENCE_IMAGE}}")
    # Fail-closed: at least one LoadImage node must consume the uploaded asset.
    has_load = any(node.get("class_type") == "LoadImage"
                   and reference_name in str(node.get("inputs", {}).get("image", ""))
                   for node in graph.values() if isinstance(node, dict))
    if not has_load:
        raise ValueError("{{REFERENCE_IMAGE}} precisa estar num nó LoadImage")
    return graph

def upload_reference(session, server, path):
    with Path(path).open("rb") as image_file:
        response = session.post(server + "/upload/image",
            files={"image": (Path(path).name, image_file, "image/jpeg")},
            data={"type": "input", "overwrite": "false"}, timeout=60)
    response.raise_for_status()
    data = response.json()
    name = data.get("name")
    if not name or "/" in name or "\\" in name:
        raise RuntimeError("ComfyUI não confirmou nome seguro da imagem de entrada")
    return name

def image_result(session, server, graph, timeout=240):
    response = session.post(server + "/prompt", json={"prompt": graph}, timeout=30)
    response.raise_for_status()
    data = response.json()
    if not data.get("prompt_id") or data.get("error"):
        raise RuntimeError(f"ComfyUI rejeitou o workflow: {data.get('error')}")
    prompt_id = data["prompt_id"]
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = session.get(server + "/history/" + prompt_id, timeout=20)
        response.raise_for_status()
        history = response.json().get(prompt_id)
        if history:
            if history.get("status", {}).get("status_str") == "error":
                raise RuntimeError("Falha de inferência no ComfyUI")
            for node_output in history.get("outputs", {}).values():
                for item in node_output.get("images", []):
                    if item.get("type", "output") != "output":
                        continue
                    response = session.get(server + "/view", params={
                        "filename": item["filename"],
                        "subfolder": item.get("subfolder", ""),
                        "type": "output"}, timeout=35)
                    response.raise_for_status()
                    if len(response.content) > 25_000_000:
                        raise RuntimeError("Imagem ComfyUI acima do limite")
                    with Image.open(BytesIO(response.content)) as im:
                        return ImageOps.exif_transpose(im).convert("RGB")
            raise RuntimeError("ComfyUI não retornou nenhuma imagem; use SaveImage")
        time.sleep(2)
    raise TimeoutError("ComfyUI não concluiu a imagem")

def process(theme, references, workflow, output, *, server="http://127.0.0.1:8188",
            effect="zoom", telegram=False, allow_remote=False):
    # Never assume GitHub-hosted runner has localhost ComfyUI.
    try:
        from .comfy_local import validate_server
        from .run import render, send_telegram
    except ImportError:
        from comfy_local import validate_server
        from run import render, send_telegram

    if theme not in STYLE_PROMPTS:
        raise ValueError("Tema inválido")
    server = validate_server(server)
    template = json.loads(Path(workflow).read_text(encoding="utf-8"))
    output = Path(output)
    ref_dir = output / "references"
    final_dir = output / "generated"
    final_dir.mkdir(parents=True, exist_ok=True)
    reference_paths = collect(references, ref_dir, limit=20, allow_remote=allow_remote)
    session = requests.Session()
    uploaded = [(p, upload_reference(session, server, p)) for p in reference_paths]
    accepted, accepted_hashes, records = [], [], []
    # Generate multiple attempts for both variation and quality gating.
    for attempt in range(40):
        if len(accepted) >= 10:
            break
        source, remote_name = uploaded[attempt % len(uploaded)]
        prompt = (STYLE_PROMPTS[theme] +
            " Professional editorial beauty photograph of stylish nails, nail salon "
            "quality, luxurious delicate details, clean natural hand with five fingers, "
            "new background and new composition, create a distinct original arrangement "
            "of nail designs, crisp well-lit manicure, portrait 9:16; no text or watermark.")
        seed = random.SystemRandom().randint(1, 2**48)
        graph = build_graph(template, prompt, seed, remote_name)
        im = image_result(session, server, graph)
        if min(im.size) < 700 or im.width*im.height < 900_000:
            continue
        # Reject near-copies of the source: transformation must materially differ.
        if is_duplicate(dhash(im), [dhash(Image.open(source))], threshold=10):
            continue
        if is_duplicate(dhash(im), accepted_hashes, threshold=8):
            continue
        ok, visual_score = check_image(im, theme)
        if not ok:
            continue
        accepted_hashes.append(dhash(im))
        image_path = final_dir / f"new_nails_{len(accepted)+1:02}.jpg"
        im.save(image_path, quality=95)
        accepted.append(image_path)
        records.append({
            "generated_file": image_path.name, "source_reference": str(source),
            "prompt": prompt, "seed": seed, "visual_validation": visual_score,
            "generated_with": "ComfyUI img2img workflow",
        })
    (output / "generation_report.json").write_text(
        json.dumps({"theme": theme, "attempted": 40, "approved": len(accepted),
                    "items": records}, ensure_ascii=False, indent=2), encoding="utf-8")
    if len(accepted) != 10:
        raise RuntimeError(f"Somente {len(accepted)} imagens transformadas aprovadas; envio bloqueado")
    video = render(accepted, output / "final.mp4", effect)
    if telegram:
        send_telegram(video, theme)
    return video

def main():
    parser = argparse.ArgumentParser(description="MediaFlow Unhas: referências → IA → 10 imagens → MP4")
    parser.add_argument("--tema", default="vermelhas_elegantes", choices=sorted(STYLE_PROMPTS))
    parser.add_argument("--referencia", action="append", required=True, help="Imagem/vídeo local ou URL pública autorizada (repetível)")
    parser.add_argument("--allow-public-references", action="store_true")
    parser.add_argument("--workflow", required=True, help="JSON API-format de img2img/IPAdapter/ControlNet")
    parser.add_argument("--server", default="http://127.0.0.1:8188")
    parser.add_argument("--saida", default="output/recriado")
    parser.add_argument("--efeito", choices=("zoom", "fade", "cortes"), default="zoom")
    parser.add_argument("--enviar-telegram", action="store_true")
    args = parser.parse_args()
    print(process(args.tema, args.referencia, args.workflow, args.saida,
                  server=args.server, effect=args.efeito,
                  telegram=args.enviar_telegram,
                  allow_remote=args.allow_public_references))
if __name__ == "__main__":
    main()
