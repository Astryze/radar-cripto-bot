"""One-image remote AI Horde connectivity test using synthetic original reference.

A test only: NEVER publishes generated nail imagery to Telegram or TikTok.
"""
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw
try:
    from .horde_provider import generate
except ImportError:
    from horde_provider import generate

def main():
    directory = Path("output/horde-probe")
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / "reference_original.png"
    image = Image.new("RGB", (512, 512), "#e6c4b4")
    draw = ImageDraw.Draw(image)
    for i in range(4):
        x = 70 + 96*i
        draw.rounded_rectangle((x, 85, x+65, 425), radius=26, fill="#d7a593")
        draw.rounded_rectangle((x+12, 93, x+53, 200), radius=18, fill="#b01730")
    image.save(source)
    report={"test": "anonymous AI Horde img2img", "source":"original drawing", "status":"failed"}
    try:
        output, detail = generate(source,
            "Beautiful luxury nail salon photorealistic close-up of elegant red glossy nail art, "
            "beautiful feminine fingers, realistic skin, professional manicure, clear nails, "
            "gold glitter delicate detail, bright studio light",
            seed=401, timeout=160)
        output.save(directory / "remote_generation.jpg", quality=93)
        report.update({"status":"generated", "model":detail.get("model"),
                       "native_size":list(output.size)})
        print("HORDE_PROBE_SUCCESS", flush=True)
    except Exception as exc:
        report["error"]=type(exc).__name__ + ": " + str(exc)[:200]
        print("HORDE_PROBE_NOT_READY " + report["error"], flush=True)
    (directory / "report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    # Treat unavailable anonymous workers as reported state, not a false success.
    if report["status"] != "generated":
        raise RuntimeError("AI Horde remote generation not verified: "+report.get("error", ""))

if __name__=="__main__":
    main()
