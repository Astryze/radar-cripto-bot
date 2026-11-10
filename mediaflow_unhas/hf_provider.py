"""Hugging Face Inference Providers image-to-image; explicit optional HF_TOKEN.

Uses official InferenceClient. Free accounts have small monthly usage credits,
not an unlimited free service. Never silently purchases additional credits.
"""
import os
from PIL import Image, ImageOps

DEFAULT_MODEL = "black-forest-labs/FLUX.2-dev"

def generate(reference, prompt, seed, *, model=None, token=None):
    key = token or os.getenv("HF_TOKEN", "").strip()
    if not key:
        raise RuntimeError("HF_TOKEN ausente; Hugging Face não configurado")
    from huggingface_hub import InferenceClient
    model = model or os.getenv("HF_IMAGE_MODEL", DEFAULT_MODEL)
    # Providers may not accept a seed for image-to-image via shared SDK.
    client = InferenceClient(provider="fal-ai", api_key=key, timeout=120)
    with open(reference, "rb") as image_file:
        input_image = image_file.read()
    result = client.image_to_image(input_image, prompt=prompt, model=model)
    if not isinstance(result, Image.Image):
        raise RuntimeError("Hugging Face não retornou uma imagem PIL")
    return ImageOps.exif_transpose(result).convert("RGB"), {
        "provider": "Hugging Face Inference Providers",
        "model": model, "seed": seed, "billing": "free credits may be consumed",
    }
