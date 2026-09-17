"""Split an image into foreground / background stills for CLIP.

Uses rembg, which means bria-rmbg: that is rembg's default and this module
has never named a model. The docstring said U2-Net, which was true when it
was written and stopped being true when the dependency changed its default.
An expensive model arrived that way without anyone choosing it, the same
way tesseract arrived inside Tika.

bria-rmbg is now a deliberate choice. It costs 6.4s an image -- about 65
minutes for a 686 image corpus, which is most of a run -- and four lighter
models were measured against it on real corpus images:

    u2netp              0.15s   42x faster   mask IoU 0.66
    silueta             0.21s   30x          mask IoU 0.69
    isnet-general-use   0.59s   11x          mask IoU 0.71

They are not rougher, they are wrong. Each leaves parts of a person
translucent, so the subject leaks into the background plate: the foreground
embedding loses them and the background embedding gains a ghost of them.
The IoU figures say "different" and cannot say "wrong"; that came from
looking at the cutouts.

Three other ways to make this cheaper are measured and dead:

  - a process pool. onnxruntime already spreads inference across about 6.5
    cores, so two workers gave 1.14x and four were slower than two.
  - a smaller input. 768, 512 and 384 all cost 6.4s, because bria-rmbg
    resizes to its own fixed input and never sees the size below.
  - the CoreML provider. onnxruntime spent 18 minutes compiling this model
    for the Neural Engine and produced nothing.

What did work was building the session once rather than per image, which
took the stage from 96 minutes to 65 without changing a mask.

The search server does not load this module.
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
