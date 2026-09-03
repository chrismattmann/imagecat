"""Runtime settings. Solr is ImageCat; ids are filesystem paths.

Index files live under ``$OODT_HOME/data/imagespace`` when ImageCat is
installed. A standalone checkout still uses ``./data`` if OODT_HOME is unset.
"""

from __future__ import annotations

import os


def solr_url() -> str:
    return os.environ.get("IMAGE_SPACE_SOLR", "http://localhost:8983/solr/imagecat").rstrip("/")


def solr_timeout() -> float:
    return float(os.environ.get("IMAGE_SPACE_SOLR_TIMEOUT", "15"))


def data_root() -> str:
    env = os.environ.get("IMAGE_SPACE_DATA")
    if env:
        return env
    home = os.environ.get("OODT_HOME") or os.environ.get("IMAGECAT_HOME")
    if home:
        return os.path.join(home, "data", "imagespace")
    return "data"


def index_dir() -> str:
    return os.environ.get("IMAGE_SPACE_INDEX_DIR", os.path.join(data_root(), "clip"))


def fg_dir() -> str:
    return os.environ.get("IMAGE_SPACE_FG_DIR", os.path.join(data_root(), "fg"))


def bg_dir() -> str:
    return os.environ.get("IMAGE_SPACE_BG_DIR", os.path.join(data_root(), "bg"))


def thumb_dir() -> str:
    return os.environ.get("IMAGE_SPACE_THUMB_DIR", os.path.join(data_root(), "thumbs"))


def meta_dir() -> str:
    return os.environ.get("IMAGE_SPACE_META_DIR", os.path.join(data_root(), "meta"))


def lenses_dir() -> str:
    return os.environ.get("IMAGE_SPACE_LENSES_DIR", os.path.join(data_root(), "lenses"))


def clip_model() -> str:
    return os.environ.get("IMAGE_SPACE_CLIP_MODEL", "openai/clip-vit-base-patch32")
