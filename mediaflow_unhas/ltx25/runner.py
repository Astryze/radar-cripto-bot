"""MediaFlow Unhas — LTX-2.5 LOCAL image-to-video proof of concept.

Runs the *official* Lightricks CLI without an API or paid service.
This script never silently replaces real generation with an animated still.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

MODEL_FILES = {
    "transformer-path": "diffusion_models/ltx-2.5-22b-distilled-transformer-bf16.safetensors",
    "text-encoder-path": "text_encoders/gemma4-12b-with-proj-ltx-2.5-bf16.safetensors",
    "video-vae-path": "vae/ltx-2.5-video-vae-bf16.safetensors",
    "audio-vae-path": "vae/ltx-2.5-audio-vae-bf16.safetensors",
    "spatial-upsampler-path":
        "latent_upscale_models/ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors",
}

N_FRAMES = 121  # official LTX temporal grid: 8*k+1, ~5 seconds at 24 fps.
WIDTH = 576
HEIGHT = 1024

PROMPT = (
    "Single continuous 5-second photorealistic macro beauty shot of the "
    "EXACT same elegant emerald green cat-eye gel manicure shown in the "
    "reference image. On a clean silk vanity surface, a real professional "
    "manicurist gently moves a small magnetic wand slowly above the nail "
    "without touching it. The narrow luminous emerald cat-eye reflection "
    "shifts diagonally across the glossy gel surface as the magnet moves. "
    "Maintain the same finger, realistic anatomy, nail shape, decorations "
    "and skin tone throughout. Fixed camera, stable macro focus, subtle "
    "handheld micro-motion, soft beauty lighting, natural shadows, realistic "
    "brush/magnet physics, no color or design changes, no cuts, no text, "
    "no logos and no watermark. A quiet close-up of a luxury manicure."
)


def gpu_check():
    try:
        import torch
    except ImportError:
        return False, "PyTorch ausente"
    if not torch.cuda.is_available():
        return False, "Nenhuma GPU CUDA disponível — LTX 2.5 não será executado na CPU"
    return True, torch.cuda.get_device_name(0)


def validate_image(image):
    from PIL import Image, ImageOps
    image = Path(image).resolve()
    if not image.is_file():
        raise FileNotFoundError(f"Imagem inexistente: {image}")
    with Image.open(image) as src:
        src = ImageOps.exif_transpose(src)
        if min(src.size) < 512:
            raise ValueError("A referência deve ter pelo menos 512 pixels por lado")
        src.verify()
    return image


def build_command(image, output, models_dir, *, prompt=PROMPT, width=WIDTH, height=HEIGHT):
    image, output, models_dir = Path(image), Path(output), Path(models_dir)
    if width % 64 or height % 64 or width * 16 != height * 9:
        raise ValueError("Resolução deve ser 9:16 e múltipla de 64 (ex.: 576x1024)")
    cmd = ["uv", "run", "python", "-m", "ltx_pipelines.distilled"]
    for key, rel in MODEL_FILES.items():
        cmd.extend(("--" + key, str(models_dir / rel)))
    cmd += [
        "--width", str(width), "--height", str(height),
        "--num-frames", str(N_FRAMES),
        "--seed", "42", "--image", str(image), "0", "1.0", "replace",
        "--output-path", str(output),
        "--prompt", prompt,
    ]
    return cmd


def check_models(models_dir):
    missing = [str(Path(models_dir) / f) for f in MODEL_FILES.values()
               if not (Path(models_dir) / f).is_file()]
    if missing:
        raise FileNotFoundError("Pesos não instalados. Ausentes:\n" +
                                "\n".join("  - " + x for x in missing))


def verify_video(path):
    if not shutil.which("ffprobe"):
        raise RuntimeError("ffprobe ausente")
    raw = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=width,height,codec_name",
        "-of", "json", str(path),
    ], text=True)
    data = json.loads(raw)
    streams = [x for x in data["streams"] if "width" in x]
    if not streams:
        raise RuntimeError("Nenhum fluxo de vídeo")
    v = streams[0]
    duration = float(data["format"]["duration"])
    if v["width"] != WIDTH or v["height"] != HEIGHT:
        raise RuntimeError("Dimensões de saída inesperadas")
    if not 4.8 <= duration <= 5.3:
        raise RuntimeError(f"Duração inesperada: {duration}s")
    return {"duration": duration, "width": v["width"], "height": v["height"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, help="Foto original autorizada, sem marca-d'água")
    parser.add_argument("--outdir", default="output/ltx25")
    parser.add_argument("--ltx-dir", default="third_party/LTX-2")
    parser.add_argument("--models-dir", default=None)
    parser.add_argument("--run", action="store_true",
                        help="Executar LTX REAL, se GPU e pesos estiverem disponíveis")
    parser.add_argument("--prompt", default=PROMPT)
    args = parser.parse_args(argv)
    image = validate_image(args.image)
    out = Path(args.outdir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    repo = Path(args.ltx_dir).resolve()
    models = Path(args.models_dir).resolve() if args.models_dir else repo / "models" / "ltx-2.5"
    mp4 = out / "nail_cat_eye_emerald_ltx25.mp4"
    command = build_command(image, mp4, models, prompt=args.prompt)
    ok, hardware = gpu_check()
    state = {
        "engine": "LTX-2.5 Distilled local, official code",
        "source": str(image),
        "output": str(mp4),
        "prompts": args.prompt,
        "command": command,
        "gpu": hardware,
        "ready_gpu": ok,
        "planned_only": not args.run,
        "expected_duration_seconds": 5.04,
        "required_weights": "approximately 66 GiB, subject to HF model terms",
    }
    (out / "plan.json").write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n",
                                   encoding="utf-8")
    print(f"PLAN_CREATED {out/'plan.json'}")
    print(f"GPU_CHECK {hardware}")
    if not args.run:
        print("DRY_RUN_ONLY — Nenhum vídeo IA foi gerado.")
        return 0
    if not ok:
        raise RuntimeError(hardware)
    if not repo.joinpath("packages/ltx-pipelines").is_dir():
        raise FileNotFoundError("LTX-2 oficial não instalado em " + str(repo))
    if not shutil.which("uv"):
        raise RuntimeError("uv ausente: instale https://docs.astral.sh/uv/")
    check_models(models)
    print("RUNNING_TRUE_LTX25_IMAGE_TO_VIDEO", flush=True)
    subprocess.run(command, cwd=repo, check=True)
    verified = verify_video(mp4)
    state["planned_only"] = False
    state["verified"] = verified
    (out/"plan.json").write_text(json.dumps(state, indent=2, ensure_ascii=False)+"\n",
                                 encoding="utf-8")
    print(f"VIDEO_GENERATED_AND_VERIFIED {mp4}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, FileNotFoundError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"MEDIAFLOW_ERROR {exc}", file=sys.stderr)
        sys.exit(2)
