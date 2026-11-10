"""CPU-only image-to-image adapter using leejet/stable-diffusion.cpp sd-cli.

No tokens, inference API, ComfyUI, AI Horde workers, CUDA or GPU are required.
The user must provide a compatible downloaded model with a license that covers
the intended commercial use. The binary must be built separately from source.
"""
import os
import random
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageOps

def generate(reference, prompt, seed=None, *, binary=None, model=None,
             steps=4, strength=0.65, timeout=600):
    binary = Path(binary or os.getenv("SD_CPP_BINARY", "./stable-diffusion.cpp/build/bin/sd-cli"))
    model = Path(model or os.getenv("SD_CPP_MODEL", ""))
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise RuntimeError("sd-cli não instalado. Compile leejet/stable-diffusion.cpp (veja CPU_MODE.md)")
    if not model.is_file() or model.stat().st_size < 100_000_000:
        raise RuntimeError("SD_CPP_MODEL ausente ou arquivo de modelo inválido")
    if not 1 <= steps <= 25 or not 0.3 <= strength <= 0.95:
        raise ValueError("Parâmetros de geração fora da faixa permitida")
    seed = int(seed if seed is not None else random.SystemRandom().randint(1, 2**31-1))
    # sd-cli supports image input through -i and requested denoising via --strength.
    with tempfile.TemporaryDirectory(prefix="mediaflow-cpu-") as temp:
        src = Path(temp) / "source.png"
        out = Path(temp) / "generated.png"
        with Image.open(reference) as original:
            im = ImageOps.fit(ImageOps.exif_transpose(original).convert("RGB"),
                              (512, 512), method=Image.Resampling.LANCZOS)
            im.save(src)
        args = [str(binary), "-m", str(model), "-i", str(src), "-o", str(out),
                "-p", prompt, "-s", str(steps), "-W", "512", "-H", "512",
                "--seed", str(seed), "--strength", str(strength)]
        proc = subprocess.run(args, capture_output=True, text=True,
                              timeout=timeout, check=False)
        if proc.returncode or not out.is_file():
            raise RuntimeError(f"sd-cli falhou: {(proc.stderr or proc.stdout)[-900:]}")
        with Image.open(out) as result:
            image = result.convert("RGB")
        return image, {"provider":"stable-diffusion.cpp CPU", "seed":seed,
                       "model_file":model.name, "native_resolution":list(image.size)}
