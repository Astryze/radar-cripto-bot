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
    # Bank Luxo Premium 3: new Pexels IDs, prioritizing actual elaborate nail art.
    (37869420, "Colorful detailed manicure, close-up"),
    (16363470, "Luxury glitter manicure on pink fabric"),
    (34871614, "Creative vivid red nail art"),
    (29375277, "Elegant burgundy manicured nails and jewelry"),
    (34997577, "Elegant French manicure with gold ring"),
    (33992618, "High-fashion artistic nail art"),
    (34835286, "Pink intricate glitter manicure on red fabric"),
    (23385307, "Delicate artistic nails and flowers"),
    (39365946, "Elegant manicure and rich red fashion"),
    (34871553, "Elegant red and white detailed nail design"),
    (34871606, "Artistic red manicure on blue background"),
    (34871560, "Stylish red and white manicure"),
    (34871655, "Red manicure with intricate white design"),
    (34871570, "Detailed red nails on soft white texture"),
    (9393756, "Red nail art with gold jewelry"),
    (34997574, "French manicure and luxurious jewelry"),
    (5871819, "Intricate decorative nails on green background"),
    (939836, "Soft pink glitter manicure"),
    (34835279, "Colorful glitter design close-up"),
    (34373403, "Elegant hand manicure with gold accessories"),
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
