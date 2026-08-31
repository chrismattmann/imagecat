"""Serve image bytes only when Solr has that id. Not a general file server.

Grid tiles use ?w=360 so the browser is not decoding 10MB originals.
"""

from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse

from . import solr
from .config import thumb_dir

_ALLOWED = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".tif", ".tiff", ".bmp"}
_THUMB_MAX = 1600
_THUMB_MIN = 32


def _scalar(value):
    if isinstance(value, list) and value:
        return value[0]
    return value


def _resolved(doc_id: str) -> Path:
    doc = solr.get_doc(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="No Solr document for that id")
    path = Path(doc_id)
    if not path.is_absolute() or not path.is_file():
        raise HTTPException(status_code=404, detail="Image file is not on this host")
    if path.suffix.lower() not in _ALLOWED:
        raise HTTPException(status_code=415, detail="Not an image suffix")
    return path


def make_thumb(src: Path, dest: Path, width: int) -> None:
    from PIL import Image, ImageFile, ImageOps

    ImageFile.LOAD_TRUNCATED_IMAGES = True
    dest.parent.mkdir(parents=True, exist_ok=True)
    image = Image.open(src)
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail((width, width), Image.Resampling.LANCZOS)
    tmp = dest.with_suffix(".tmp.jpg")
    image.save(tmp, format="JPEG", quality=80, optimize=True)
    tmp.replace(dest)


def file_response(doc_id: str, width: int | None = None) -> FileResponse:
    path = _resolved(doc_id)
    media = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    headers = {"Cache-Control": "public, max-age=86400"}
    if not width:
        return FileResponse(path, media_type=media, headers=headers)
    width = max(_THUMB_MIN, min(int(width), _THUMB_MAX))
    key = hashlib.sha1(("%s:%d" % (doc_id, width)).encode("utf-8")).hexdigest()
    cache = Path(thumb_dir()) / (key + ".jpg")
    if not cache.is_file() or cache.stat().st_mtime < path.stat().st_mtime:
        make_thumb(path, cache, width)
    return FileResponse(cache, media_type="image/jpeg", headers=headers)
