# ruff: noqa
"""MediaFlow Unhas: 10 fotos diferentes em 10 segundos. Somente ferramentas gratuitas."""
import argparse, hashlib, html, json, os, re, subprocess, tempfile, uuid
from pathlib import Path
from io import BytesIO
from urllib.parse import urlparse
import requests
from PIL import Image, ImageOps, ImageFilter, ImageStat
from quality import evaluate, dhash, is_duplicate

API="https://commons.wikimedia.org/w/api.php"
THEMES={
"vermelhas_elegantes":"elegant red manicure nails",
"francesinha_delicada":"delicate french manicure nails",
"nude_sofisticadas":"nude manicure nails",
"pretas_brilho":"black glitter manicure nails",
"rosa_bebe":"baby pink manicure nails",
"almond":"almond shape nail art",
"encapsuladas":"encapsulated nail art",
"glitter_dourado":"gold glitter manicure nails",
"minimalistas":"minimalist nail art",
"flores":"floral nail art manicure",
"francesinha_colorida":"colorful french tip manicure",
"vinho":"burgundy manicure nails",
"stiletto":"stiletto nail art",
"cromadas":"chrome manicure nails",
"noivas":"bridal manicure nails",
"azul_claro":"light blue manicure nails",
"verde_esmeralda":"emerald green manicure nails",
"pedrarias":"rhinestone manicure nails",
"quadradas":"square shape nail art",
"curtas":"short elegant manicure nails",
"marmore":"marble nail art",
"rosa_glitter":"pink glitter manicure nails",
"brancas":"white elegant manicure nails",
"degrade":"ombre nail art manicure",
"olho_de_gato":"cat eye magnetic nails",
"vermelho_dourado":"red gold nail art",
"lilas":"lilac manicure nails",
"lacos":"coquette bow nail art",
"francesinha_reversa":"reverse french manicure nails",
"luxo_3d":"3d luxury nail art"}
def fetch(theme, output):
    """Only collect high-resolution nail photos demonstrably matching the theme."""
    output.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    agent = {"User-Agent": "MediaFlowUnhas/0.8 (GitHub: Astryze/radar-cripto-bot; strict thematic image retrieval)"}
    base = {
        "action": "query", "generator": "search", "gsrnamespace": 6,
        "gsrlimit": 50, "prop": "imageinfo", "iiprop": "url|extmetadata|mime",
        "iiurlwidth": 1600, "format": "json", "formatversion": 2
    }
    if theme == "vermelhas_elegantes":
        queries = ["red manicure nails", "red nail art", "red fingernails manicure",
                   "red gel manicure", "red painted nails", "red nail designs"]
    else:
        queries = [THEMES[theme], THEMES[theme] + " close-up", THEMES[theme] + " design"]
    images, credits, hashes, examined = [], [], [], set()
    for search in dict.fromkeys(queries):
        print(f"Busca temática: {search}", flush=True)
        try:
            resp = session.get(API, params={**base, "gsrsearch": search}, headers=agent, timeout=30)
            resp.raise_for_status()
            pages = resp.json().get("query", {}).get("pages", [])
        except (requests.RequestException, ValueError) as exc:
            print(f"Fonte indisponível: {type(exc).__name__}", flush=True)
            continue
        ranked = []
        for page in pages:
            item = (page.get("imageinfo") or [{}])[0]
            meta = item.get("extmetadata") or {}
            eligible, score, reason = evaluate(theme, page.get("title", ""), meta)
            if not eligible:
                continue
            url = item.get("thumburl") or item.get("url")
            host = urlparse(url).hostname if url else ""
            if not host or not (host == "wikimedia.org" or host.endswith(".wikimedia.org")):
                continue
            if item.get("mime") not in {"image/jpeg", "image/png", "image/webp"}:
                continue
            if item.get("descriptionurl") in examined:
                continue
            examined.add(item.get("descriptionurl"))
            ranked.append((score, item, meta, url))
        ranked.sort(reverse=True, key=lambda row: row[0])
        for score, item, meta, url in ranked:
            if len(images) >= 10:
                break
            try:
                response = session.get(url, headers=agent, timeout=25)
                response.raise_for_status()
                if len(response.content) > 15_000_000:
                    continue
                with Image.open(BytesIO(response.content)) as original:
                    im = ImageOps.exif_transpose(original).convert("RGB")
                if min(im.size) < 700 or im.width * im.height < 900_000:
                    continue
                ratio = im.width / im.height
                if ratio < 0.55 or ratio > 1.6:
                    continue
                # Reject largely flat/blurry photos. A score is not a semantic
                # vision classifier, so manual preview is still recommended.
                edge_variation = ImageStat.Stat(im.resize((256, 256)).filter(ImageFilter.FIND_EDGES).convert("L")).stddev[0]
                if edge_variation < 11:
                    continue
                visual_hash = dhash(im)
                if is_duplicate(visual_hash, hashes):
                    continue
                hashes.append(visual_hash)
                file = output / f"{len(images) + 1:02}.jpg"
                im.save(file, quality=94)
                images.append(file)
                def field(key):
                    return html.unescape(re.sub(r"<[^>]+>", "", meta.get(key, {}).get("value", "")))[:500]
                credits.append({
                    "file": file.name, "source": item.get("descriptionurl"),
                    "license": field("LicenseShortName"), "license_url": field("LicenseUrl"),
                    "artist": field("Artist"), "relevance_score": score,
                    "edge_variation": round(edge_variation, 2), "search_term": search,
                })
            except (requests.RequestException, OSError, ValueError):
                continue
        print(f"Fotos qualificadas: {len(images)}/10", flush=True)
        if len(images) >= 10:
            break
    (output / "credits.json").write_text(json.dumps(credits, ensure_ascii=False, indent=2), encoding="utf-8")
    if len(images) < 10:
        raise RuntimeError(f"Qualidade insuficiente: somente {len(images)} de 10 fotos de unhas aprovadas; não completar com imagens aleatórias")
    return images

def render(images,out,effect):
    if len(images)<10:raise ValueError("Mínimo de 10 imagens")
    if effect not in {"zoom","fade","cortes"}:raise ValueError("Efeito inválido")
    with tempfile.TemporaryDirectory() as td:
        td=Path(td); segments=[]
        for i,p in enumerate(images):
            src=td/f"{i:02}.jpg"
            with Image.open(p) as im:
                ImageOps.fit(ImageOps.exif_transpose(im).convert("RGB"),(720,1280)).save(src,quality=90)
            dest=td/f"{i:02}.mp4"
            if effect=="zoom":
                vf="zoompan=z='min(zoom+0.0012,1.1)':d=24:s=720x1280:fps=24,format=yuv420p"
                args=["-i",str(src),"-vf",vf,"-frames:v","24"]
            else:
                args=["-loop","1","-framerate","24","-i",str(src),"-frames:v","24"]
                if effect=="fade":args+=["-vf","fade=t=in:st=0:d=0.1,fade=t=out:st=0.9:d=0.1"]
            subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",*args,
                 "-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p",str(dest)],check=True,timeout=90)
            segments.append(dest)
        concat=td/"files.txt";concat.write_text("".join("file '"+str(p)+"'\n" for p in segments))
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat","-safe","0","-i",str(concat),"-c","copy",str(out)],check=True,timeout=120)
    return out
def send_telegram(path, theme):
    token=os.environ.get("TELEGRAM_BOT_TOKEN","").strip()
    chat=os.environ.get("TELEGRAM_CHAT_ID","").strip()
    if not token or not chat:raise RuntimeError("Secrets TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID ausentes")
    with open(path,"rb") as file:
        r=requests.post(f"https://api.telegram.org/bot{token}/sendVideo",
           data={"chat_id":chat,"caption":theme+" — prévia. Revise créditos e licença."},
           files={"video":file},timeout=90);r.raise_for_status()
        if not r.json().get("ok"):raise RuntimeError("Telegram não confirmou envio")
def main():
    a=argparse.ArgumentParser()
    a.add_argument("--tema",choices=THEMES,default="vermelhas_elegantes")
    a.add_argument("--efeito",choices=["zoom","fade","cortes"],default="zoom")
    a.add_argument("--enviar-telegram",action="store_true")
    a.add_argument("--work",default="work")
    args=a.parse_args()
    out=Path(args.work)/f"{args.tema}_{uuid.uuid4().hex[:8]}";out.mkdir(parents=True)
    images=fetch(args.tema,out)
    video=render(images,out/"final.mp4",args.efeito)
    (out/"manifest.json").write_text(json.dumps({"tema":args.tema,"photos":len(images),"duration":10,"effect":args.efeito,"license_review_required":True},indent=2))
    if args.enviar_telegram:send_telegram(video,args.tema)
    print(video)
if __name__=="__main__":main()
