"""Video-only MediaFlow: public URLs/local references -> 10 images -> 10s MP4.

No generative AI, no CLIP model or GPU required. Source extraction uses existing
reference_collector (gallery-dl Pinterest, yt-dlp TikTok/Douyin). The public
sources must be accessible and users responsible for rights/attribution.
"""
import argparse
import json
import subprocess
from urllib.parse import quote
from pathlib import Path

from PIL import Image, ImageOps, ImageEnhance, ImageFilter, ImageStat

try:
    from .reference_collector import collect
    from .quality import dhash, is_duplicate
except ImportError:
    from reference_collector import collect
    from quality import dhash, is_duplicate

def create_frames(sources, output, *, allow_remote=False, count=10):
    """Require 10 distinct input photos, fail closed instead of repeating photos."""
    if len(sources) < 1:
        raise ValueError("Informe pelo menos um URL ou arquivo de fotografia")
    output = Path(output)
    input_dir = output / "sources"
    photos = collect(sources, input_dir, limit=30, allow_remote=allow_remote)
    selected, hashes = [], []
    for path in photos:
        with Image.open(path) as raw:
            image = ImageOps.exif_transpose(raw).convert("RGB")
            if min(image.size) < 450 or image.width * image.height < 450_000:
                continue
            fingerprint = dhash(image)
            if is_duplicate(fingerprint, hashes, threshold=6):
                continue
            sharpness = ImageStat.Stat(image.resize((200,200)).filter(ImageFilter.FIND_EDGES).convert("L")).stddev[0]
            if sharpness < 7:
                continue
            hashes.append(fingerprint)
            selected.append(path)
            if len(selected) == count:
                break
    if len(selected) != count:
        raise RuntimeError(f"Encontradas somente {len(selected)}/{count} fotografias adequadas e distintas")
    folder = output / "frames"
    folder.mkdir(parents=True, exist_ok=True)
    for idx, photo in enumerate(selected, 1):
        with Image.open(photo) as raw:
            image = ImageOps.exif_transpose(raw).convert("RGB")
            # Preserve entire photo, subtly blur the background to fit a 9:16 canvas.
            bg = ImageOps.fit(image,(720,1280),Image.Resampling.LANCZOS)
            bg=ImageEnhance.Brightness(bg.filter(ImageFilter.GaussianBlur(38))).enhance(0.55)
            fg = ImageOps.contain(image,(706,1266),Image.Resampling.LANCZOS)
            bg.paste(fg,((720-fg.width)//2,(1280-fg.height)//2))
            bg.save(folder/f"frame_{idx:02d}.jpg",quality=93)
    return selected, folder

def render_video(frames, output, *, seconds=10):
    count=len(list(Path(frames).glob("frame_*.jpg")))
    if count!=10 or seconds!=10:
        raise RuntimeError("Video MediaFlow exige exatamente 10 imagens em 10 segundos")
    output=Path(output)
    command=["ffmpeg","-hide_banner","-loglevel","error","-y",
             "-framerate","1","-start_number","1","-i",str(Path(frames)/"frame_%02d.jpg"),
             "-vf","fps=30,format=yuv420p","-frames:v","300",
             "-c:v","libx264","-crf","20","-preset","fast",
             "-movflags","+faststart",str(output)]
    process=subprocess.run(command,capture_output=True,text=True,timeout=180)
    if process.returncode or not output.is_file():
        raise RuntimeError("FFmpeg não produziu MP4: "+process.stderr[-300:])
    return output

def main():
    parser=argparse.ArgumentParser(description="MediaFlow: 10 fotos em MP4 de 10 s, sem geração por IA")
    parser.add_argument("--referencia",action="append",default=[],help="URL pública ou foto local (repetível)")
    parser.add_argument("--urls-file",help="Arquivo TXT com uma URL pública por linha")
    parser.add_argument("--auto-pinterest",action="store_true",help="Pesquisar pins públicos; pode exigir cookies ou falhar")
    parser.add_argument("--consulta",default="luxury nail art manicure red glitter")
    parser.add_argument("--allow-public-references",action="store_true")
    parser.add_argument("--saida",default="output/photo-video")
    parser.add_argument("--enviar-telegram",action="store_true")
    args=parser.parse_args()
    if args.urls_file:
        args.referencia.extend(line.strip() for line in Path(args.urls_file).read_text(encoding="utf8").splitlines()
                               if line.strip() and not line.lstrip().startswith("#"))
    if args.auto_pinterest:
        query=quote(args.consulta[:100])
        args.referencia.insert(0,f"https://www.pinterest.com/search/pins/?q={query}")
        args.allow_public_references=True
    args.referencia=list(dict.fromkeys(args.referencia))
    dest=Path(args.saida)
    dest.mkdir(parents=True,exist_ok=True)
    selected,frames=create_frames(args.referencia,dest,allow_remote=args.allow_public_references)
    video=render_video(frames,dest/"final.mp4")
    (dest/"manifest.json").write_text(json.dumps({"count":len(selected),"duration_seconds":10,
       "source_photos":[str(p) for p in selected],"ai_generated":False,
       "license_review_required":True},ensure_ascii=False,indent=2),encoding="utf8")
    if args.enviar_telegram:
        try:
            from .run import send_telegram
        except ImportError:
            from run import send_telegram
        send_telegram(video,"Nail Art — Fotos selecionadas")
    print("VIDEO_CREATED",video)
if __name__=="__main__":
    main()
