"""Split an image into foreground / background stills for CLIP.

Uses rembg (U2-Net). The search server does not load this module.
"""

from __future__ import annotations

from functools import lru_cache
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


@lru_cache(maxsize=1)
def session(model_name: str = "bria-rmbg"):
    """The rembg session, built once.

    rembg's remove() takes an optional session and, given none, builds one
    per call -- bg.py does

        if session is None:
            session = new_session("bria-rmbg", *args, **kwargs)

    and new_session is not memoised. So a run over a corpus loaded the model
    and constructed an ONNX InferenceSession once per image: measured at
    about 2s of a 10s call, 22 minutes across 686 images.

    Cached per process rather than held in a module global, so that a pool
    of workers gets one session each rather than sharing one across
    processes, which an InferenceSession does not survive.
    """
    from rembg import new_session

    return new_session(model_name)


def split_fg_bg(path: str | Path, size: int = 768, sess=None):
    from rembg import remove

    if sess is None:
        sess = session()
    image = Image.open(path)
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail((size, size))
    cut = remove(image, session=sess)
    if cut.mode != "RGBA":
        cut = cut.convert("RGBA")
    alpha = cut.split()[-1]
    fg = Image.new("RGB", image.size, GRAY)
    fg.paste(cut, mask=alpha)
    inv = Image.eval(alpha, lambda p: 255 - p)
    bg = Image.new("RGB", image.size, GRAY)
    bg.paste(image, mask=inv)
    return fg, bg
