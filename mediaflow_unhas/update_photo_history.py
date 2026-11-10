"""After a successful new video, persist its source titles/hashes to Git.

GitHub Actions can commit this JSON if branch write permissions are available.
If not, the video remains available but operators should commit the generated
history manually before producing a new one.
"""
import argparse
import json
from pathlib import Path
from PIL import Image
try:
    from .quality import dhash
except ImportError:
    from quality import dhash

HISTORY = Path(__file__).with_name("used_photo_history.json")

def update_history(credits, source_dir, history=HISTORY):
    credits=json.loads(Path(credits).read_text(encoding="utf-8"))
    history=Path(history)
    existing=json.loads(history.read_text(encoding="utf-8")) if history.is_file() else {}
    titles=set(existing.get("titles",[]))
    hashes=set(existing.get("hashes",[]))
    count=0
    for source in credits:
        title=source.get("original_title")
        name=source.get("file")
        if not title or not name:
            continue
        photo=Path(source_dir)/name
        if not photo.is_file():
            raise FileNotFoundError(photo)
        with Image.open(photo) as im:
            hashes.add(f"{dhash(im):016x}")
        titles.add(title)
        count+=1
    if count != 10:
        raise RuntimeError(f"Vídeo exige exatamente 10 fotos para registro, obtidas {count}")
    data={"description":"Persisted source images for cross-video deduplication.",
          "titles":sorted(titles), "hashes":sorted(hashes)}
    history.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"MEDIAFLOW_HISTORY_UPDATED titles={len(titles)} hashes={len(hashes)}",flush=True)
    return data

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--credits",required=True)
    p.add_argument("--source-dir",required=True)
    args=p.parse_args()
    update_history(args.credits,args.source_dir)
