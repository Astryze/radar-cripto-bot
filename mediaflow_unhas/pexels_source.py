"""Fonte opcional de fotos Pexels, com atribuição e sem serviços pagos."""
import hashlib
import json
import os
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
import requests
from PIL import Image, ImageOps

def search(query, folder, n=10, api_key=None, session=None):
    key = api_key or os.getenv("PEXELS_API_KEY")
    if not key:
        raise RuntimeError("PEXELS_API_KEY ausente; obtenha chave gratuita no Pexels")
    if not 10 <= n <= 30: raise ValueError("Quantidade precisa ser de 10 a 30")
    session = session or requests.Session()
    folder = Path(folder); folder.mkdir(parents=True,exist_ok=True)
    images=[]; seen=set(); credits=[]
    for page in (1,2,3):
        r=session.get("https://api.pexels.com/v1/search",headers={"Authorization":key},
            params={"query":query,"per_page":30,"page":page,"orientation":"portrait"},timeout=25)
        r.raise_for_status()
        records=r.json().get("photos",[])
        if not records:break
        for item in records:
            if len(images)>=n:break
            url=(item.get("src") or {}).get("large2x") or (item.get("src") or {}).get("large")
            host=urlparse(url).hostname if url else ""
            if not host or not (host=="pexels.com" or host.endswith(".pexels.com")):continue
            try:
                imr=session.get(url,timeout=30);imr.raise_for_status()
                if len(imr.content)>12000000:continue
                with Image.open(BytesIO(imr.content)) as im:
                    im=ImageOps.exif_transpose(im).convert("RGB")
                    if min(im.size)<320:continue
                    sha=hashlib.sha256(im.resize((160,160)).tobytes()).hexdigest()
                    if sha in seen:continue
                    path=folder/f"pexels_{len(images)+1:02}.jpg";im.save(path,quality=90)
                seen.add(sha);images.append(path)
                credits.append({"file":path.name,"source":item.get("url"),
                    "photographer":item.get("photographer"),"photographer_url":item.get("photographer_url"),
                    "license":"Review Pexels license and restrictions"})
            except (requests.RequestException,OSError,ValueError):continue
        if len(images)>=n:break
    (folder/"credits_pexels.json").write_text(json.dumps(credits,ensure_ascii=False,indent=2),encoding="utf-8")
    return images
