"""Fail-closed image QA using local CLIP visual-text embeddings (no paid service).

This is a screening step, not a guarantee. A human must still review visuals
for publication. Model download from Hugging Face is required on first use.
"""
from functools import lru_cache

GENERAL_POSITIVE = (
    "A professional luxury nail salon close-up photograph with polished fingernails prominently in focus, elegant feminine hand, beautiful nail art and soft studio lighting.",
    "A premium editorial macro photograph of flawless elaborate nail art on long glossy fingernails, highly detailed designs, tasteful jewelry and clean cuticles.",
    "A vertical studio beauty photograph of ornate high-end manicured fingernails occupying most of the image, sparkling polish, realistic hands and subtle background.",
)
GENERAL_NEGATIVE = (
    "A photograph of food, pizza or a restaurant meal.",
    "A photograph of a wine glass or drink in someone's hand.",
    "A photograph of a drinking glass, vase or a small object.",
    "A vintage magazine cover, advertisement or poster.",
    "A photograph of people at a party or an awards ceremony.",
    "A photograph of toys or billiard balls on a table.",
    "A photograph of archeological objects in a museum.",
    "A photograph of cosmetic bottles and beauty products.",
    "A photograph of feet, toenails or a pedicure.",
    "A photograph of colorful rings on fingers without a manicure.",
)
STYLE_PROMPTS = {
    "vermelhas_elegantes": "A premium vertical nail art salon photograph of long elegant glossy deep red and burgundy manicured fingernails prominently in focus, with sophisticated festive gold glitter, delicately painted snowflakes or tartan nail art, studio lighting.",
    "francesinha_delicada": "A close-up manicure beauty photograph of fingernails with classic white French tips.",
    "nude_sofisticadas": "A close-up manicure photograph of fingernails with elegant nude beige nail polish.",
    "pretas_brilho": "Luxury editorial macro photograph of black and gold geometric nail art on long stiletto fingernails, glossy black pointed tips, refined nude and gold details, clean manicure.",
    "rosa_bebe": "A close-up beauty photograph of fingernails with baby pink nail polish.",
    "almond": "A close-up beauty photograph of long almond shaped polished fingernails.",
    "encapsuladas": "A close-up photograph of encapsulated nail art in fingernails.",
    "glitter_dourado": "A close-up photograph of fingernails with gold glitter nail polish.",
    "minimalistas": "A close-up photograph of minimalist nail art fingernails.",
    "flores": "A close-up photograph of fingernails with floral nail art.",
    "francesinha_colorida": "A close-up photograph of fingernails with colorful French tips.",
    "vinho": "A close-up photograph of fingernails painted glossy burgundy wine red.",
    "stiletto": "A close-up manicure photograph of sharp stiletto shaped fingernails.",
    "cromadas": "A close-up manicure photograph of metallic chrome fingernails.",
    "noivas": "A close-up elegant bridal manicure photograph of fingernails.",
    "azul_claro": "A close-up manicure photograph of fingernails with light blue polish.",
    "verde_esmeralda": "A close-up manicure photograph of fingernails painted emerald green.",
    "pedrarias": "A close-up manicure photograph of fingernails with rhinestone nail art.",
    "quadradas": "A close-up manicure photograph of polished square shaped fingernails.",
    "curtas": "A close-up beauty photograph of short manicured fingernails.",
    "marmore": "A close-up photograph of fingernails with marble pattern nail art.",
    "rosa_glitter": "A close-up photograph of fingernails painted pink glitter polish.",
    "brancas": "A close-up manicure photograph of white painted fingernails.",
    "degrade": "A close-up photograph of ombre gradient manicure fingernails.",
    "olho_de_gato": "A close-up photograph of magnetic cat eye nail polish on fingernails.",
    "vermelho_dourado": "A close-up photograph of red and gold nail art on fingernails.",
    "lilas": "A close-up manicure photograph of lilac lavender painted fingernails.",
    "lacos": "A close-up photograph of fingernails decorated with tiny bow nail art.",
    "francesinha_reversa": "A close-up photograph of reverse French manicure on fingernails.",
    "luxo_3d": "A close-up beauty photograph of luxurious three dimensional nail art.",
}
OTHER_STYLE = (
    "A close-up photograph of fingernails painted bright blue.",
    "A close-up photograph of fingernails painted shiny black.",
    "A close-up photograph of fingernails painted bright red.",
    "A close-up photograph of fingernails painted white with French tips.",
)

@lru_cache(maxsize=1)
def _model():
    import torch
    from transformers import CLIPModel, CLIPProcessor
    model_id = "openai/clip-vit-base-patch32"
    model = CLIPModel.from_pretrained(model_id).eval()
    processor = CLIPProcessor.from_pretrained(model_id)
    return model, processor, torch

def check_image(image, theme, *, minimum_general=0.50, minimum_style=0.38, margin=0.03):
    """Reject images where negative subjects outrank nails or the style doesn't match.

    Thresholds are conservative, tune with hand-labeled examples; never claim
    these scores are calibrated probabilities.
    """
    model, processor, torch = _model()
    style = STYLE_PROMPTS[theme]
    prompts = (*GENERAL_POSITIVE, *GENERAL_NEGATIVE, style, *OTHER_STYLE)
    tokens = processor(text=list(prompts), images=image, return_tensors="pt", padding=True)
    with torch.inference_mode():
        values = model(**tokens).logits_per_image[0]
        probabilities = values.softmax(dim=0).tolist()
    positive = max(probabilities[:len(GENERAL_POSITIVE)])
    negative = max(probabilities[len(GENERAL_POSITIVE):len(GENERAL_POSITIVE)+len(GENERAL_NEGATIVE)])
    style_score = probabilities[len(GENERAL_POSITIVE)+len(GENERAL_NEGATIVE)]
    # Relative ranking is more trustworthy than raw confidence in a prompt-set.
    general_sum = sum(probabilities[:len(GENERAL_POSITIVE)])
    neg_sum = sum(probabilities[len(GENERAL_POSITIVE):len(GENERAL_POSITIVE)+len(GENERAL_NEGATIVE)])
    matches_nails = general_sum > neg_sum + margin and positive > negative
    if theme == "vermelhas_elegantes":
        style_offset = len(GENERAL_POSITIVE) + len(GENERAL_NEGATIVE) + 1
        blue_score = probabilities[style_offset]
        black_score = probabilities[style_offset+1]
        if style_score <= max(blue_score, black_score):
            matches_nails = False
    return matches_nails, {
        "nail_mass": round(general_sum, 4),
        "other_mass": round(neg_sum, 4),
        "style_score": round(style_score, 4),
        "style_over_other": round(style_score - max(probabilities[-len(OTHER_STYLE):]), 4),
        "model": "openai/clip-vit-base-patch32",
    }
