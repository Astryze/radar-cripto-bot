# ruff: noqa
"""MediaFlow Unhas: 10 fotos diferentes em 10 segundos. Somente ferramentas gratuitas."""
import argparse, hashlib, html, json, os, re, subprocess, tempfile, uuid
from pathlib import Path
from io import BytesIO
from urllib.parse import urlparse
import requests
from PIL import Image, ImageOps

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
    output.mkdir(parents=True,exist_ok=True)
    session=requests.Session()
    agent={"User-Agent":"MediaFlowUnhas/0.4 (noncommercial experimental image index; contact repository owner)"}
    query={"action":"query","generator":"search","gsrsearch":"filetype:bitmap "+THEMES[theme],
           "gsrnamespace":6,"gsrlimit":50,"prop":"imageinfo","iiprop":"url|extmetadata|mime",
           "iiurlwidth":1200,"format":"json","formatversion":2}
    resp=session.get(API,params=query,headers=agent,timeout=30);resp.raise_for_status()
    images=[]; credits=[]; seen=set()
    for page in resp.json().get("query",{}).get("pages",[]):
        if len(images)>=10:break
        item=(page.get("imageinfo") or [{}])[0]
        url=item.get("thumburl") or item.get("url")
        host=urlparse(url).hostname if url else ""
        if not host or not (host=="wikimedia.org" or host.endswith(".wikimedia.org")):continue
        if item.get("mime") not in {"image/jpeg","image/png","image/webp"}:continue
        try:
            r=session.get(url,headers=agent,timeout=25);r.raise_for_status()
            if len(r.content)>12_000_000:continue
            with Image.open(BytesIO(r.content)) as im:
                im=ImageOps.exif_transpose(im).convert("RGB")
                if im.width<320 or im.height<320:continue
                f=output/f"{len(images)+1:02}.jpg"; im.save(f,quality=91)
            digest=hashlib.sha256(f.read_bytes()).hexdigest()
            if digest in seen:f.unlink();continue
            seen.add(digest);images.append(f)
            metadata=item.get("extmetadata") or {}
            def field(key):return html.unescape(re.sub(r"<[^>]+>","",metadata.get(key,{}).get("value","")))[:500]
            credits.append({"file":f.name,"source":item.get("descriptionurl"),"license":field("LicenseShortName"),
                             "license_url":field("LicenseUrl"),"artist":field("Artist")})
        except (requests.RequestException,OSError,ValueError):continue
    (output/"credits.json").write_text(json.dumps(credits,ensure_ascii=False,indent=2),encoding="utf-8")
    if len(images)<10:raise RuntimeError(f"Somente {len(images)} fotos distintas encontradas; não criar vídeo incompleto")
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
