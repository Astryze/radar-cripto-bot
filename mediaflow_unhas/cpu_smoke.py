"""Smoke test of actual offline CPU img2img, NOT a nail production video."""
import json
from pathlib import Path

from PIL import Image, ImageDraw
from cpu_provider import generate

def main():
    folder = Path("output/cpu-smoke")
    folder.mkdir(parents=True, exist_ok=True)
    source = folder / "original_reference.png"
    img = Image.new("RGB", (512,512), "#eedccc")
    pen = ImageDraw.Draw(img)
    for i in range(4):
        x = 58+i*105
        pen.rounded_rectangle((x, 92, x+66, 412), radius=28, fill="#d2a58a")
        pen.rounded_rectangle((x+14, 105, x+54, 209), radius=13, fill="#a30d23")
    img.save(source)
    generated, metadata = generate(source,
        "photorealistic studio close-up professional premium ruby red glossy "
        "nail manicure with gold glitter, feminine hand natural realistic fingers, "
        "elaborate luxury nail art, natural skin, beauty salon photography",
        seed=98765, steps=4, strength=0.72, timeout=900)
    generated.save(folder / "ai_output.jpg", quality=90)
    (folder / "report.json").write_text(json.dumps({
        "success": True, "generated_size": list(generated.size), **metadata
    }, indent=2), encoding="utf-8")
    print("CPU_IMG2IMG_REAL_GENERATION_SUCCESS")

if __name__ == "__main__":
    main()
