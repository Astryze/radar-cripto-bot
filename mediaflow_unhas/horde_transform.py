"""GitHub-compatible nail art production: authorized references -> AI Horde -> MP4 -> Telegram.

Never inserts source images directly into the output video.
"""
import argparse
import json
import os
import random
from pathlib import Path

from PIL import Image, ImageOps

try:
    from .horde_provider import generate
    from .reference_collector import collect
    from .quality import dhash, is_duplicate
    from .visual_guard import STYLE_PROMPTS, check_image
    from .run import render, send_telegram
except ImportError:
    from horde_provider import generate
    from reference_collector import collect
    from quality import dhash, is_duplicate
    from visual_guard import STYLE_PROMPTS, check_image
    from run import render, send_telegram

def auto_references(theme, folder, limit=6):
    """No-key Openverse: use only CC sources as input references, not video frames."""
    try:
        from .openverse_source import iter_candidates
    except ImportError:
        from openverse_source import iter_candidates
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    result = []
    credited = []
    seen = []
    for candidate, source in iter_candidates(theme, maximum=45):
        # A noisy index cannot bypass the semantic classifier.
        valid, _ = check_image(candidate, theme)
        if not valid or min(candidate.size) < 500:
            continue
        visual_hash = dhash(candidate)
        if is_duplicate(visual_hash, seen):
            continue
        seen.append(visual_hash)
        file = folder / f"reference_{len(result)+1:02}.jpg"
        candidate.save(file, quality=91)
        result.append(file)
        credited.append({"file": file.name, **source, "reference_only": True})
        if len(result) >= limit:
            break
    (folder / "credits.json").write_text(
        json.dumps(credited, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if not result:
        raise RuntimeError("Nenhuma referência de manicure disponível com licença e qualidade adequadas")
    return result

def create_video(theme, references, destination, *, allow_public=False,
                 automatic=False, effect="zoom", telegram=False, max_attempts=26,
                 timeout_per_image=360):
    if theme not in STYLE_PROMPTS:
        raise ValueError("Tema inexistente")
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    originals = destination / "references"
    if references:
        source_paths = collect(references, originals, allow_remote=allow_public)
    elif automatic:
        source_paths = auto_references(theme, originals)
    else:
        raise ValueError("Informe --referencia ou --auto-references")
    generated = destination / "generated"
    generated.mkdir(exist_ok=True)
    hashes = []
    accepted = []
    metadata = []
    for attempt in range(max_attempts):
        if len(accepted) >= 10:
            break
        source = source_paths[attempt % len(source_paths)]
        prompt = STYLE_PROMPTS[theme] + (
            ". Luxury nail salon portfolio, extreme close-up fingernails, professional "
            "nail art, sparkling fine details, beautiful cuticles, clean hand anatomy, "
            "soft elegant lighting, studio quality, photorealistic, new unique "
            "composition and manicure pattern, keep polished nails dominant in frame."
        )
        try:
            im, info = generate(source, prompt,
                seed=random.SystemRandom().randint(1, 2**31-1),
                timeout=timeout_per_image)
        except (RuntimeError, TimeoutError, ValueError, OSError) as exc:
            print(f"AI Horde tentativa {attempt+1}: {type(exc).__name__}: {str(exc)[:150]}", flush=True)
            # Avoid an expensive loop when anonymous requests are blocked.
            if attempt == 0 and "worker" in str(exc).lower():
                break
            continue
        # Output of an anonymous worker may be only 512 px, not premium resolution.
        # Upscaling improves dimensions, not actual detail; keep this explicit.
        if min(im.size) < 384:
            continue
        output_hash = dhash(im)
        with Image.open(source) as original:
            source_hash = dhash(original)
        if is_duplicate(output_hash, [source_hash], threshold=7):
            continue
        if is_duplicate(output_hash, hashes, threshold=7):
            continue
        approved, report = check_image(im, theme)
        if not approved:
            continue
        hashes.append(output_hash)
        out = generated / f"nails_{len(accepted)+1:02}.jpg"
        ImageOps.fit(im, (720, 1280), method=Image.Resampling.LANCZOS).save(out, quality=95)
        accepted.append(out)
        metadata.append({"file": out.name, "source_ref": str(source),
                         "visual": report, **info, "native_resolution": list(im.size),
                         "upscaled_for_video": im.size != (720, 1280)})
        print(f"Imagem aprovada {len(accepted)}/10", flush=True)
    report_path = destination / "report.json"
    report_path.write_text(json.dumps({
        "theme": theme, "count": len(accepted), "attempts": max_attempts,
        "images": metadata, "reference_only": True,
        "source_photos_in_final_video": False
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    if len(accepted) != 10:
        raise RuntimeError(f"Qualidade insuficiente: {len(accepted)}/10 imagens geradas aprovadas; vídeo e Telegram bloqueados")
    video = render(accepted, destination / "final.mp4", effect)
    if telegram:
        send_telegram(video, theme)
    return video

def main():
    parser = argparse.ArgumentParser(description="AI Horde: referência -> dez novas unhas -> MP4")
    parser.add_argument("--tema", choices=sorted(STYLE_PROMPTS), default="vermelhas_elegantes")
    parser.add_argument("--referencia", action="append", default=[])
    parser.add_argument("--allow-public-references", action="store_true")
    parser.add_argument("--auto-references", action="store_true")
    parser.add_argument("--saida", default="output/unhas-horde")
    parser.add_argument("--efeito", choices=("zoom", "fade", "cortes"), default="zoom")
    parser.add_argument("--enviar-telegram", action="store_true")
    parser.add_argument("--max-attempts", type=int, default=26)
    parser.add_argument("--timeout-per-image", type=int, default=360)
    args = parser.parse_args()
    print(create_video(args.tema, args.referencia, args.saida,
                       allow_public=args.allow_public_references,
                       automatic=args.auto_references, effect=args.efeito,
                       telegram=args.enviar_telegram,
                       max_attempts=args.max_attempts,
                       timeout_per_image=args.timeout_per_image))
if __name__ == "__main__":
    main()
