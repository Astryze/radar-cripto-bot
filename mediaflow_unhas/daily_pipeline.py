"""MediaFlow Unhas: scheduled best-effort nail art videos from licensed photography.

Each invocation attempts ONE unique ten-photo, ten-second 9:16 MP4.
Run three times a day via GitHub Actions. Only deliver if ALL 10 independent
quality checks pass. No paid image/video generation service is required.
This is public-photo curation, NOT automatic ChatGPT image generation.
"""
import argparse
import json
import os
import sys
from pathlib import Path

import requests
from PIL import Image, ImageFilter, ImageOps, ImageStat

from openverse_source import iter_candidates
from photo_finish import finish
from quality import dhash, is_duplicate
from photo_video import render_video

ROOT = Path(__file__).resolve().parent
HISTORY = ROOT / "daily_used_photos.json"
SEARCHES = ("luxo_3d", "flores", "pedrarias", "vermelho_dourado", "rosa_glitter")
# No NC/ND images; source license metadata and attribution preserved for review.
CAPTIONS = (
    "💅✨ Decorações apaixonantes! Qual sua favorita? 💖\n"
    "#UnhasDecoradas #NailArt #UnhasDeLuxo #BelaEmDetalhes",
    "🌸💎 Cada unha é uma obra de arte! Qual você escolheria? 💅\n"
    "#UnhasDecoradas #NailDesign #Manicure #BelaEmDetalhes",
    "✨💅 Flores, brilho e pedrarias! Salve sua inspiração favorita! 😍\n"
    "#NailArt #UnhasPerfeitas #UnhasDecoradas #BelaEmDetalhes",
)

def read_history(path=HISTORY):
    if Path(path).exists():
        x=json.loads(Path(path).read_text(encoding="utf-8"))
        return {"sources": set(x.get("sources",[])), "hashes":set(x.get("hashes",[]))}
    return {"sources":set(),"hashes":set()}

def save_history(history, path=HISTORY):
    Path(path).write_text(json.dumps({
        "sources":sorted(history["sources"]),
        "hashes":sorted(history["hashes"]),
    },indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def content_score(img):
    """Reject blurry or tiny photos; semantic evaluation is separate."""
    im=ImageOps.exif_transpose(img).convert("RGB")
    if min(im.size)<700 or im.width*im.height<1_000_000:
        return False, "resolucao"
    if not (0.54 <= im.width/im.height <= 1.7):
        return False, "enquadramento"
    small=im.resize((224,224),Image.Resampling.LANCZOS)
    stat=ImageStat.Stat(small.convert("L"))
    detail=ImageStat.Stat(small.filter(ImageFilter.FIND_EDGES).convert("L")).stddev[0]
    if detail<8 or stat.stddev[0]<24 or not (50<stat.mean[0]<220):
        return False, "nitidez/luminosidade"
    return True, "ok"

def clip_gate():
    """Offline model, loaded once. Reject plain nails and non-manicure subjects."""
    import torch
    from transformers import CLIPModel, CLIPProcessor
    model="openai/clip-vit-base-patch32"
    m=CLIPModel.from_pretrained(model).eval()
    proc=CLIPProcessor.from_pretrained(model)
    # Wider descriptions reduce the risk of accepting generic fashion portraits.
    descriptions=[
        "High quality professional macro photograph of elaborately decorated long fingernails on a woman's hand, nail art with three-dimensional flowers, sparkling rhinestones and precise painted decoration.",
        "Close-up luxury beauty salon nail design on manicured hands, elaborate intricate floral patterns, crystals and gold embellishments, artistic fingernails in focus.",
        "Photograph of a woman's hand with plain solid-colored nail polish with no decorations.",
        "Photograph of a nail polish bottle, cosmetic products and makeup on a table.",
        "Fashion photograph of a woman's face, hair, dress or accessories rather than fingernails.",
        "Photograph of jewelry, ring, watch, jewelry box, necklaces and gemstone products.",
        "Photograph of artificial plastic nail sample display boards and nail polish swatches.",
        "Photograph of feet with painted toenails and pedicure.",
        "Photograph of flowers, plants, colorful fabric or home decorations.",
        "Photograph of a dinner plate, food, wine and a restaurant table.",
    ]
    tokenized=proc(text=descriptions,return_tensors="pt",padding=True)
    def check(im):
        inp=proc(images=im,return_tensors="pt")
        with torch.inference_mode():
            values=m(pixel_values=inp["pixel_values"],input_ids=tokenized["input_ids"],
                     attention_mask=tokenized["attention_mask"]).logits_per_image[0].tolist()
        positive=max(values[:2])
        other=max(values[2:])
        return positive>=other+0.15, round(positive-other,2)
    return check

def collect(outdir, history, quality_check, minimum=10):
    outdir.mkdir(parents=True,exist_ok=True)
    images=[]
    credits=[]
    hashes=[]
    rejected={}
    for theme in SEARCHES:
        # All Openverse images are license-filtered, attribution retained.
        try:
            iterator=iter_candidates(theme,maximum=60,delay=1.2)
            for photo,meta in iterator:
                source=str(meta.get("source") or "").strip()
                if not source or source in history["sources"]:
                    continue
                good,why=content_score(photo)
                if not good:
                    rejected[why]=rejected.get(why,0)+1
                    continue
                signature=dhash(photo)
                if is_duplicate(signature, hashes, threshold=7) or any(
                    (signature^int(h,16)).bit_count()<=7 for h in history["hashes"]
                ):
                    rejected["duplicata"]=rejected.get("duplicata",0)+1
                    continue
                approved, margin=quality_check(photo)
                if not approved:
                    rejected["decoracao_nao_confirmada"]=rejected.get("decoracao_nao_confirmada",0)+1
                    continue
                dest=outdir/f"nail_{len(images)+1:02d}.jpg"
                ImageOps.exif_transpose(photo).convert("RGB").save(dest,quality=93)
                images.append(dest)
                hashes.append(signature)
                credits.append({**meta,"file":dest.name,"visual_margin":margin,
                                "perceptual_hash":f"{signature:016x}"})
                print(f"APPROVED {len(images)}/{minimum}: {theme} {source[:80]}",flush=True)
                if len(images)>=minimum:
                    break
        except (requests.RequestException,ValueError,RuntimeError) as exc:
            print(f"Fonte {theme} falhou: {type(exc).__name__}",flush=True)
        if len(images)>=minimum:
            break
    print("Rejected reasons",rejected,flush=True)
    (outdir/"credits.json").write_text(json.dumps(credits,ensure_ascii=False,indent=2),encoding="utf-8")
    if len(images)!=minimum:
        raise RuntimeError(f"Somente {len(images)}/{minimum} fotos decoradas inéditas aprovadas; nenhum vídeo enviado.")
    return images,credits

def send(video,caption):
    token=os.environ.get("TELEGRAM_BOT_TOKEN","").strip()
    chat=os.environ.get("TELEGRAM_CHAT_ID","").strip()
    if not token or not chat:
        raise RuntimeError("Secrets do Telegram não configurados")
    with video.open("rb") as handle:
        r=requests.post(f"https://api.telegram.org/bot{token}/sendVideo",
             data={"chat_id":chat,"caption":caption},
             files={"video":(video.name,handle,"video/mp4")},timeout=150)
    payload=r.json()
    if r.status_code!=200 or not payload.get("ok"):
        raise RuntimeError("Telegram recusou envio: "+str(payload.get("description","erro"))[:140])
    message_id=payload["result"].get("message_id")
    print(f"TELEGRAM_DELIVERY_CONFIRMED message_id={message_id}",flush=True)
    return message_id

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="output/mediaflow-daily")
    parser.add_argument("--slot",choices=("manha","tarde","noite"),default="manha")
    parser.add_argument("--dry-run",action="store_true")
    opts=parser.parse_args()
    output=Path(opts.output)
    output.mkdir(parents=True,exist_ok=True)
    history=read_history()
    print(f"Histórico: {len(history['sources'])} URLs usadas",flush=True)
    checker=clip_gate()
    photos,credits=collect(output/"sources",history,checker)
    frames=output/"frames"
    frames.mkdir(exist_ok=True)
    for idx,p in enumerate(photos,1):
        with Image.open(p) as im:
            finish(im).save(frames/f"frame_{idx:02d}.jpg",quality=94)
    video=render_video(frames,output/"final.mp4")
    ffprobe = __import__("subprocess").run(
        ["ffprobe","-v","error","-show_entries","format=duration",
         "-of","default=noprint_wrappers=1:nokey=1",str(video)],
        capture_output=True,text=True,check=True)
    assert abs(float(ffprobe.stdout.strip())-10)<0.1
    slot_index=("manha","tarde","noite").index(opts.slot)
    caption=CAPTIONS[slot_index]
    (output/"post_caption.txt").write_text(caption,encoding="utf-8")
    if not opts.dry_run:
        send(video,caption)
        # Only mark as USED AFTER Telegram confirms the delivery.
        for row in credits:
            history["sources"].add(row["source"])
            history["hashes"].add(row["perceptual_hash"])
        save_history(history)
    print("DAILY_MEDIAFLOW_COMPLETE",str(video),len(photos),"dry_run="+str(opts.dry_run),flush=True)
    return 0

if __name__=="__main__":
    sys.exit(main())
