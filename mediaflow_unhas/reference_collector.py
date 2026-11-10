"""Collect *reference-only* nail imagery from authorized URLs and media.

Supported:
  - local reference image or video files
  - HTTPS Pinterest, Douyin and TikTok URLs via optional gallery-dl/yt-dlp
No credential bypass, logged-in scraping, anti-bot evasion or posting of originals.
Collected assets are used solely as visual guides for local AI generation.
"""
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from PIL import Image, ImageOps

ALLOWED_HOSTS = (
    "pinterest.com", "pin.it", "pinterest.co.uk", "pinterest.com.br",
    "douyin.com", "iesdouyin.com", "tiktok.com", "vm.tiktok.com", "vt.tiktok.com",
)
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_VIDEO_SECONDS = 90

def validate_url(value):
    address = urlsplit(value)
    host = (address.hostname or "").lower()
    if address.scheme != "https" or address.port not in (None, 443):
        raise ValueError("Referência exige HTTPS em domínio permitido")
    if address.username or address.password or not any(
        host == allowed or host.endswith("." + allowed) for allowed in ALLOWED_HOSTS
    ):
        raise ValueError("Domínio de referência não permitido")
    return value

def _run(args, timeout=120):
    process = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if process.returncode:
        raise RuntimeError("Não foi possível recuperar esta referência pública: "
                           + process.stderr[-400:])
    return process.stdout

def _collect_from_url(url, directory):
    validate_url(url)
    host = (urlsplit(url).hostname or "").lower()
    if host == "pin.it" or "pinterest." in host:
        if not shutil.which("gallery-dl"):
            raise RuntimeError("Instale gallery-dl para links Pinterest")
        _run(["gallery-dl", "--no-mtime", "--no-part",
              "--directory", str(directory), "--", url])
    else:
        if not shutil.which("yt-dlp"):
            raise RuntimeError("Instale yt-dlp para Douyin/TikTok")
        _run(["yt-dlp", "--no-playlist", "--no-overwrites", "--max-filesize", "30M",
              "--output", str(directory / "reference.%(ext)s"), "--", url])
    return list(directory.rglob("*"))

def _frame(video, target):
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg necessário para extrair quadro de vídeo")
    _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
          "-ss", "1", "-i", str(video), "-frames:v", "1", str(target)], timeout=45)
    return target

def collect(inputs, output, limit=20, *, allow_remote=False):
    """Copy and normalize reference candidates. NEVER upload originals as deliverables.

    Remote references require explicit opt-in and terms/rights verification.
    """
    if not 1 <= limit <= 30:
        raise ValueError("Limite de referências fora do intervalo")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    images = []
    records = []
    seen = set()
    with tempfile.TemporaryDirectory() as tmp:
        temp = Path(tmp)
        for idx, source in enumerate(inputs):
            if len(images) >= limit:
                break
            if source.startswith("https://"):
                if not allow_remote:
                    raise ValueError("Downloads remotos desativados; use --allow-public-references")
                folder = temp / str(idx)
                folder.mkdir()
                candidates = _collect_from_url(source, folder)
            else:
                p = Path(source)
                if not p.is_file():
                    raise FileNotFoundError(f"Referência ausente: {p}")
                candidates = [p]
            for candidate in candidates:
                if len(images) >= limit or not candidate.is_file():
                    continue
                suffix = candidate.suffix.lower()
                if suffix in {".mp4", ".mov", ".webm", ".mkv"}:
                    frame = temp / f"frame_{idx}_{len(images)}.jpg"
                    try:
                        candidate = _frame(candidate, frame)
                    except (RuntimeError, subprocess.TimeoutExpired):
                        continue
                elif suffix not in EXTENSIONS:
                    continue
                try:
                    if candidate.stat().st_size > 30_000_000:
                        continue
                    with Image.open(candidate) as source_img:
                        im = ImageOps.exif_transpose(source_img).convert("RGB")
                        if min(im.size) < 450:
                            continue
                        # Thumbnail for stable fuzzy duplicate detection.
                        fingerprint = hashlib.sha256(im.resize((80, 80)).tobytes()).hexdigest()
                        if fingerprint in seen:
                            continue
                        seen.add(fingerprint)
                        dest = output / f"reference_{len(images)+1:02}.jpg"
                        im.save(dest, quality=91)
                    images.append(dest)
                    records.append({"file": dest.name, "origin": source,
                        "publication_authorized": False, "reference_only": True})
                except (OSError, ValueError):
                    continue
    (output / "references.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if not images:
        raise RuntimeError("Nenhuma referência de imagem válida coletada")
    return images
