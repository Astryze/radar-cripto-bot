"""Hand-picked Pexels nail-art photographs; no Pexels API key.

Uses individual Pexels public-photo page IDs and image CDN, NOT an undocumented
Pexels API endpoint. Records page URLs and Pexels license for reuse review.
Rejects unavailable images, duplicates, tiny files, and images with no detail.
Does not silently fill missing images with unrelated photographs.
"""
import hashlib
import json
import time
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image, ImageFilter, ImageOps, ImageStat

PHOTOS = [
    # Curadoria verificável: páginas públicas Pexels que descrevem nail art
    # detalhada e próxima, não esmaltação básica nem retratos de salão.
    (34885842, "Manicure floral rosa detalhada em fundo escuro"),
    (34121866, "Nail art artística colorida avant-garde"),
    (7118662, "Unhas florais com detalhes e pedras delicadas"),
    (9697755, "Nail art azul e prata com aplicações brilhantes"),
    (34835291, "Flores rosa e azul pintadas nas unhas"),
    (34885844, "Unhas rosa com arte elaborada e anel dourado"),
    (34835287, "Unhas rosa e brancas desenhadas com anel prateado"),
    (33625363, "Manicure colorida artística com anel brilhante"),
    (5871928, "Manicure com desenhos elaborados e reflexos"),
    (5871920, "Manicure criativa verde com fundo amarelo"),
    (5871311, "Manicure colorida de alto contraste"),
    (13277177, "Manicure floral desenhada segurando folha"),
    (247836, "Unhas artísticas em close-up com tecido"),
    (7711501, "Unhas decoradas em ambiente externo"),
    (34835279, "Glitter colorido em manicure close-up"),
    (5871312, "Manicure multicolor com brilho"),
    (10612638, "Beleza editorial com nail art e glitter"),
    (34311632, "Manicure de alta joalheria"),
]
CDN="https://images.pexels.com/photos/{id}/pexels-photo-{id}.jpeg"
USER_AGENT="Mozilla/5.0 (compatible; MediaFlowNails/2.4; curated stock photography)"
def image_url(photo_id):
    return CDN.format(id=photo_id)

def collect_premium(folder, *, count=10, session=None):
    """Download curated *different photos*; never repeat prior used photo IDs."""
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    session=session or requests.Session()
    used_file=Path(__file__).with_name("premium_used_ids.json")
    if used_file.is_file():
        used=set(json.loads(used_file.read_text(encoding="utf-8")).get("ids",[]))
    else:
        used=set()
    selected=[]
    credits=[]
    signatures=[]
    for photo_id,description in PHOTOS:
        if len(selected)>=count:
            break
        if photo_id in used:
            continue
        url=image_url(photo_id)
        try:
            r=session.get(url,params={"auto":"compress","cs":"tinysrgb",
                                      "w":1200},headers={"User-Agent":USER_AGENT},
                          timeout=40,allow_redirects=False)
            if r.status_code!=200 or len(r.content)>12_000_000:
                print(f"STOCK_SKIP HTTP={r.status_code} id={photo_id}",flush=True)
                continue
            if not r.headers.get("Content-Type","").startswith("image/"):
                continue
            with Image.open(BytesIO(r.content)) as original:
                im=ImageOps.exif_transpose(original).convert("RGB")
            if min(im.size)<650 or im.width*im.height<850_000:
                continue
            edge=ImageStat.Stat(im.resize((220,220)).filter(ImageFilter.FIND_EDGES)
                               .convert("L")).stddev[0]
            if edge<8:
                continue
            signature=hashlib.sha256(im.resize((100,100)).tobytes()).hexdigest()
            if signature in signatures:
                continue
            signatures.append(signature)
            dest=folder/f"nail_premium_{len(selected)+1:02}.jpg"
            im.save(dest,quality=94)
            selected.append(dest)
            credits.append({"file":dest.name,"pexels_photo_id":photo_id,
                "original_title":description,
                "source":f"https://www.pexels.com/photo/{photo_id}/",
                "license":"Pexels License — verify before distribution",
                "image_url":url})
            print(f"PREMIUM_NAIL {len(selected)}/{count} ID={photo_id} {description}",flush=True)
            time.sleep(0.35)
        except (requests.RequestException, OSError, ValueError) as e:
            print(f"STOCK_SKIP ERROR id={photo_id} {type(e).__name__}",flush=True)
    (folder/"source_credits.json").write_text(json.dumps(
        credits,ensure_ascii=False,indent=2),encoding="utf-8")
    if len(selected)!=count:
        raise RuntimeError(f"Premium stock: only {len(selected)}/{count} images; "
                           "refusing to pad with repeats")
    return selected
