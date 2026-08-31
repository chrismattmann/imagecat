"""Split an image into foreground / background stills for CLIP.

Uses rembg (U2-Net). The search server does not load this module.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageFile, ImageOps

ImageFile.LOAD_TRUNCATED_IMAGES = True

GRAY = (128, 128, 128)


def rembg_available() -> bool:
    try:
        import rembg  # noqa: F401
        return True
    except Exception:
        return False


def split_fg_bg(path: str | Path, size: int = 768):
    from rembg import remove

    image = Image.open(path)
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail((size, size))
    cut = remove(image)
    if cut.mode != "RGBA":
        cut = cut.convert("RGBA")
    alpha = cut.split()[-1]
    fg = Image.new("RGB", image.size, GRAY)
    fg.paste(cut, mask=alpha)
    inv = Image.eval(alpha, lambda p: 255 - p)
    bg = Image.new("RGB", image.size, GRAY)
    bg.paste(image, mask=inv)
    return fg, bg
