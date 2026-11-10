"""Conservative nail-photo preflight; false positives are worse than too few photos."""
import html
import re

NAILS = re.compile(r"\b(nails?|fingernails?|manicure|nail[- ]art|esmalta(?:ção|cao|da|das)|unhas?)\b", re.I)
BAD = re.compile(r"\b(toe|toes|toenails?|feet|foot|pedicure|bottle|bottles|logo|icon|vector|clipart|poster|advertisement|catalogue|advertising|cartoon|drawing|illustration|packaging)\b", re.I)
THEME_TERMS = {
    "vermelhas_elegantes": ("red", "crimson", "scarlet", "ruby", "burgundy", "vermelh", "rouge"),
    "francesinha_delicada": ("french", "francesinha"),
    "nude_sofisticadas": ("nude", "beige", "natural"),
    "pretas_brilho": ("black", "preta", "glitter"),
    "rosa_bebe": ("pink", "rosa"),
    "almond": ("almond", "amendoada"),
    "encapsuladas": ("encapsulad", "encapsulat"),
    "glitter_dourado": ("gold", "glitter", "dourad"),
    "minimalistas": ("minimal", "simple"),
    "flores": ("flower", "floral", "flores"),
    "francesinha_colorida": ("french", "colorful", "coloured", "francesinha"),
    "vinho": ("wine", "burgundy", "vinho"),
    "stiletto": ("stiletto",),
    "cromadas": ("chrome", "chromatic", "cromad"),
    "noivas": ("bridal", "bride", "wedding", "noiva"),
    "azul_claro": ("blue", "azul"),
    "verde_esmeralda": ("green", "emerald", "verde"),
    "pedrarias": ("rhinestone", "crystal", "pedraria"),
    "quadradas": ("square", "quadrad"),
    "curtas": ("short", "curtas"),
    "marmore": ("marble", "mármore", "marmore"),
    "rosa_glitter": ("pink", "rosa"),
    "brancas": ("white", "brancas", "branco"),
    "degrade": ("ombre", "gradient", "degrad"),
    "olho_de_gato": ("cat eye", "magnetic"),
    "vermelho_dourado": ("red", "vermelh"),
    "lilas": ("lilac", "lavender", "purple", "lilás", "lilas"),
    "lacos": ("bow", "laço", "laco"),
    "francesinha_reversa": ("reverse french", "francesinha reversa"),
    "luxo_3d": ("3d", "luxury", "3-d"),
}

def clean_metadata(title, metadata):
    values = [title or ""]
    for key in ("ImageDescription", "ObjectName", "Categories"):
        entry = metadata.get(key, {})
        if isinstance(entry, dict):
            values.append(str(entry.get("value") or ""))
    return re.sub(r"<[^>]*>", " ", html.unescape(" ".join(values))).lower()

def evaluate(theme, title, metadata):
    """Return (eligible, score, reason) with strictly theme-matched keywords."""
    blob = clean_metadata(title, metadata)
    if not NAILS.search(blob):
        return False, 0, "não identifica unhas/manicure"
    if BAD.search(blob):
        return False, 0, "descrição sugere produto/pedicure/ilustração"
    words = THEME_TERMS.get(theme)
    if not words or not any(term in blob for term in words):
        return False, 0, "não confirma o tema específico"
    title_text = clean_metadata(title, {})
    score = 2 + (3 if NAILS.search(title_text) else 0) + (3 if any(t in title_text for t in words) else 0)
    score += min(3, blob.count("manicure") + blob.count("nail art"))
    return True, score, "metadados compatíveis"

def dhash(im):
    """64-bit difference hash on a normalized image; used to avoid visually similar photos."""
    gray = im.convert("L").resize((9, 8))
    pixels = list(gray.getdata())
    out = 0
    for y in range(8):
        for x in range(8):
            out = (out << 1) | (pixels[y * 9 + x] > pixels[y * 9 + x + 1])
    return out

def is_duplicate(candidate, seen, threshold=6):
    return any((candidate ^ old).bit_count() <= threshold for old in seen)
