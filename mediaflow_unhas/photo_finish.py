"""Premium-looking photo presentation without inventing or distorting nail art.

Input images remain genuine photos. Adaptive, modest tonal correction and crisp
portrait layouts are applied on copies; originals and credits are preserved.
"""
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageStat

SIZE=(720,1280)

def photo_metrics(im):
    """Descriptive, not semantic: a good score doesn't prove it depicts nails."""
    rgb=ImageOps.exif_transpose(im).convert("RGB")
    small=rgb.resize((256,256),Image.Resampling.LANCZOS)
    gray=small.convert("L")
    light=ImageStat.Stat(gray).mean[0]
    contrast=ImageStat.Stat(gray).stddev[0]
    detail=ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES)).stddev[0]
    return {
        "width":rgb.width,"height":rgb.height,
        "brightness":round(light,1),
        "contrast":round(contrast,1),
        "edge_detail":round(detail,1),
        "portrait":round(rgb.height/max(1,rgb.width),2),
    }

def finish(im, *, width=720, height=1280):
    """Fit entire hand and nails; use soft background, slight exposure and detail."""
    rgb=ImageOps.exif_transpose(im).convert("RGB")
    # A light, warm blurred copy keeps the portrait frame elegant and avoids bars.
    bg=ImageOps.fit(rgb,(width,height),method=Image.Resampling.LANCZOS)
    bg=bg.filter(ImageFilter.GaussianBlur(radius=34))
    bg=ImageEnhance.Brightness(bg).enhance(0.52)
    # The original nails remain in full view; cropping can accidentally remove tips.
    fg=ImageOps.contain(rgb,(width-28,height-28),method=Image.Resampling.LANCZOS)
    luminance=ImageStat.Stat(fg.convert("L")).mean[0]
    if luminance<85:
        fg=ImageEnhance.Brightness(fg).enhance(1.12)
    elif luminance>200:
        fg=ImageEnhance.Brightness(fg).enhance(0.95)
    fg=ImageEnhance.Contrast(fg).enhance(1.055)
    fg=ImageEnhance.Color(fg).enhance(1.055)
    fg=fg.filter(ImageFilter.UnsharpMask(radius=1.15,percent=76,threshold=3))
    # A very faint shadow separates photo from the generated background.
    pad=8
    x=(width-fg.width)//2
    y=(height-fg.height)//2
    shadow=Image.new("RGB",(fg.width+2*pad,fg.height+2*pad),(22,17,25))
    shadow=shadow.filter(ImageFilter.GaussianBlur(6))
    bg.paste(shadow,(x-pad,y-pad))
    bg.paste(fg,(x,y))
    return bg

def quality_score(metrics):
    """Soft priority, no score can replace a visual check of manicure relevance."""
    portrait=min(1.0,metrics["portrait"]/1.55)
    contrast=min(1.0,metrics["contrast"]/55)
    sharp=min(1.0,metrics["edge_detail"]/25)
    light=1-min(1,abs(metrics["brightness"]-135)/135)
    return round(100*(0.31*sharp+0.28*portrait+0.23*contrast+0.18*light),1)
