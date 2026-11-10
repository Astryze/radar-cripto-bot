"""Retrieve real nail-art photos from Wikimedia Commons' dedicated category.

Uses categorymembers, not free-text Wikimedia search (which previously returned
pizza, posters, and wine). Source and license attribution are retained.
"""
import html
import json
import re
import time
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image, ImageOps, ImageStat, ImageFilter

API = "https://commons.wikimedia.org/w/api.php"
# Manually curated from the actual category listing of Nail_art. Each is a
# known distinct file, not a search result that just happens to mention "nail".
PREFERRED = (
    "Blue cat eye nail art.jpg",
    "Complex nail art.jpg",
    "Crosses and squares nail art.jpg",
    "Dazznailstudio.jpg",
    "Flower nail art.jpg",
    "French Manicure with Glitter nail art on ring finger.jpg",
    "French tip nail art.jpg",
    "Gel Nails Pink Orange and White Design.jpg",
    "Hologram nail art.jpg",
    "Kostka Bojana- Extreme Form- Elatus.jpg",
    "Matte black and white polkadot nails (16476158115).jpg",
    "Matte spotted turquoise nails (15403309163).jpg",
    "Nail art - Glitter Diamond.jpg",
    "Nail Art Butterfly.jpg",
    "Nail art example, Nov 2013.jpg",
    "Nail Art Strass.jpg",
    "Nail art with stripes.jpg",
    "Nail extensions with nail art.jpg",
    "Polished purple nails with nail art on.jpg",
    "Red nail art with white stripes.jpg",
    "Spring on nails.jpg",
    "Starburst nail art.jpg",
    "Stripes nails.jpg",
    "Swirly purple konad nail art.jpg",
    "Tribal nail art.jpg",
    "Unhas.jpg",
)
ALLOWED_LICENSES = {"cc0", "cc-by", "cc-by-sa", "public domain", "pd", "cc by", "cc by-sa"}
USER_AGENT="MediaFlowUnhas/2.2 (GitHub: Astryze/radar-cripto-bot; nail art CC images)"

def field(metadata, key):
    return html.unescape(re.sub(r"<[^>]*>", "", str((metadata.get(key) or {}).get("value") or ""))).strip()

def license_ok(metadata):
    lic=field(metadata,"LicenseShortName").lower().replace(" ", "-")
    if not lic:
        return False
    return (lic in {"cc0", "public-domain", "pd"} or
            lic.startswith("cc-by-") or lic.startswith("cc-by-sa-"))

def image_host_ok(url):
    p=urlparse(url or "")
    h=(p.hostname or "").lower()
    return p.scheme=="https" and p.port in (None,443) and not p.username and not p.password and (
        h in {"upload.wikimedia.org","thumb.wikimedia.org"} or h.endswith(".upload.wikimedia.org"))

def fetch_curated(folder, *, minimum=10, session=None):
    """Collect unique, attribution-eligible actual nail photographs.

    Never fill the shortfall using unrelated images. Returns path list.
    """
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    session=session or requests.Session()
    photos=[]
    manifest=[]
    seen=set()
    for i in range(0,len(PREFERRED),10):
        batch=PREFERRED[i:i+10]
        params={"action":"query", "prop":"imageinfo",
                "iiprop":"url|extmetadata|size|mime",
                "iiurlwidth":900, "format":"json","formatversion":"2",
                "titles":"|".join("File:"+f for f in batch)}
        try:
            resp=session.get(API,params=params,headers={"User-Agent":USER_AGENT},timeout=35)
            resp.raise_for_status()
            pages=resp.json().get("query",{}).get("pages",[])
        except (requests.RequestException,ValueError) as e:
            print(f"Wikimedia batch unavailable: {type(e).__name__}",flush=True)
            continue
        ordered={p.get("title","").removeprefix("File:"):p for p in pages}
        for name in batch:
            if len(photos)>=minimum:
                break
            page=ordered.get(name) or {}
            info=(page.get("imageinfo") or [{}])[0]
            metadata=info.get("extmetadata") or {}
            if (info.get("mime") not in ("image/jpeg","image/png","image/webp")
                or not license_ok(metadata)):
                print(f"SKIP_META {name}: mime={info.get('mime')} license={field(metadata, 'LicenseShortName')}", flush=True)
                continue
            url=info.get("thumburl") or info.get("url")
            if not image_host_ok(url):
                print(f"SKIP_HOST {name}: {(url or '')[:90]}",flush=True)
                continue
            try:
                img_response=None
                for retry in range(3):
                    img_response=session.get(url,headers={"User-Agent":USER_AGENT},
                                             timeout=40,allow_redirects=False)
                    if img_response.status_code not in (429, 503):
                        break
                    time.sleep(3*(retry+1))
                if img_response.status_code!=200 or len(img_response.content)>15_000_000:
                    print(f"SKIP_FETCH {name}: HTTP {img_response.status_code}; bytes={len(img_response.content)}",flush=True)
                    continue
                with Image.open(BytesIO(img_response.content)) as original:
                    im=ImageOps.exif_transpose(original).convert("RGB")
                if min(im.size)<480 or im.width*im.height<480_000:
                    print(f"SKIP_DIM {name}: {im.size}",flush=True)
                    continue
                # Distinctness: cheap 24px image hash rather than title.
                import hashlib
                signature=hashlib.sha256(im.resize((40,40)).tobytes()).hexdigest()
                if signature in seen:
                    continue
                variation=ImageStat.Stat(im.resize((200,200)).filter(
                    ImageFilter.FIND_EDGES).convert("L")).stddev[0]
                if variation<5:
                    continue
                seen.add(signature)
                dest=folder/f"nail_new_{len(photos)+1:02d}.jpg"
                im.save(dest,quality=91)
                photos.append(dest)
                manifest.append({"file":dest.name,
                    "source":info.get("descriptionurl") or ("https://commons.wikimedia.org/wiki/File:"+name.replace(" ","_")),
                    "author":field(metadata,"Artist"), "license":field(metadata,"LicenseShortName"),
                    "license_url":field(metadata,"LicenseUrl"),"original_title":name})
                print(f"NEW_NAIL_PHOTO {len(photos)}/{minimum}: {name}",flush=True)
                time.sleep(0.7)
            except (OSError,requests.RequestException,ValueError):
                continue
        if len(photos)>=minimum:
            break
    (folder/"source_credits.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    if len(photos)<minimum:
        raise RuntimeError(f"Catálogo de nail art: somente {len(photos)}/{minimum} fotos encontradas. Não usar fotos antigas.")
    return photos
