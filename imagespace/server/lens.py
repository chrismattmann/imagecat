"""Tiny Keras head that ranks CLIP vectors: a Lens.

CLIP stays on disk. A Lens maps a CLIP vector to P(yes) for whatever the
operator marked + / −. Fitted at Refine time; saved under
$data/imagespace/lenses/<slug>/. Keras is the library, not a pretrained
model. Torch backend (already in ImageCat for CLIP) so we do not pull
TensorFlow.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from .config import clip_model, lenses_dir

DEFAULT_DIM = 512
META_NAME = "meta.json"
MODEL_NAME = "model.keras"
_SLUG = re.compile(r"[^a-z0-9]+")


def _use_torch_backend():
    os.environ.setdefault("KERAS_BACKEND", "torch")
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")


@lru_cache(maxsize=1)
def keras_available() -> bool:
    _use_torch_backend()
    try:
        import keras  # noqa: F401
        return True
    except Exception:
        try:
            import tensorflow  # noqa: F401
            return True
        except Exception:
            return False


def _layers():
    _use_torch_backend()
    try:
        from keras import Sequential, layers
        return Sequential, layers
    except Exception:
        from tensorflow.keras import Sequential, layers
        return Sequential, layers


def build_head(dim: int = DEFAULT_DIM):
    Sequential, layers = _layers()
    if dim < 1:
        raise ValueError("dim must be positive")
    return Sequential(
        [
            layers.Input(shape=(dim,)),
            layers.Dense(64, activation="relu", name="lens_hidden"),
            layers.Dense(1, activation="sigmoid", name="lens_yes"),
        ],
        name="lens_head",
    )


def fit_head(vectors, labels, dim: int = DEFAULT_DIM, epochs: int = 40):
    import numpy as np

    model = build_head(dim)
    model.compile(optimizer="adam", loss="binary_crossentropy")
    x = np.asarray(vectors, dtype="float32")
    y = np.asarray(labels, dtype="float32").reshape((-1, 1))
    batch = max(1, min(8, len(x)))
    model.fit(x, y, epochs=epochs, batch_size=batch, verbose=0)
    return model


def score_vectors(model, vectors):
    import numpy as np

    x = np.asarray(vectors, dtype="float32")
    raw = model.predict(x, verbose=0)
    return np.asarray(raw, dtype="float32").reshape(-1)


def slugify(name: str) -> str:
    slug = _SLUG.sub("-", (name or "").strip().lower()).strip("-")[:80]
    if not slug:
        raise ValueError("Lens name needs a letter or number")
    return slug


def _root() -> Path:
    return Path(lenses_dir())


def _load_keras(path: Path):
    _use_torch_backend()
    try:
        from keras.saving import load_model
    except Exception:
        from tensorflow.keras.models import load_model
    return load_model(path)


def collect_examples(index, positive_ids, negative_ids):
    pos = []
    neg = []
    seen_pos = set()
    seen_neg = set()
    pos_ids = []
    neg_ids = []
    for doc_id in positive_ids or []:
        row = index.row(doc_id)
        if row is None or doc_id in seen_pos:
            continue
        seen_pos.add(doc_id)
        pos.append(row)
        pos_ids.append(doc_id)
    for doc_id in negative_ids or []:
        if doc_id in seen_pos:
            continue
        row = index.row(doc_id)
        if row is None or doc_id in seen_neg:
            continue
        seen_neg.add(doc_id)
        neg.append(row)
        neg_ids.append(doc_id)
    if not pos or not neg:
        raise ValueError("Lens needs at least one yes and one no image in the CLIP index")
    import numpy as np

    labels = [1.0] * len(pos) + [0.0] * len(neg)
    vectors = index.vectors[np.array(pos + neg)]
    dim = int(index.vectors.shape[1])
    return pos_ids, neg_ids, vectors, labels, dim


def score_index(model, index, n: int = 24):
    import numpy as np

    scores = score_vectors(model, index.vectors)
    order = np.argsort(-scores)
    n = max(1, min(int(n), len(index.ids)))
    hits = []
    for j in order[:n]:
        j = int(j)
        hits.append({"id": index.ids[j], "lens_score": float(scores[j])})
    return hits


def refine(index, positive_ids, negative_ids, n: int = 24):
    """Fit the head on yes/no CLIP rows and rank the whole index."""
    pos_ids, neg_ids, vectors, labels, dim = collect_examples(
        index, positive_ids, negative_ids
    )
    model = fit_head(vectors, labels, dim=dim)
    hits = score_index(model, index, n)
    stats = {"positive": len(pos_ids), "negative": len(neg_ids), "scored": len(index.ids)}
    return hits, stats


def save_lens(index, name, positive_ids, negative_ids):
    """Fit from labels and write $data/imagespace/lenses/<slug>/."""
    pos_ids, neg_ids, vectors, labels, dim = collect_examples(
        index, positive_ids, negative_ids
    )
    model = fit_head(vectors, labels, dim=dim)
    slug = slugify(name)
    dest = _root() / slug
    dest.mkdir(parents=True, exist_ok=True)
    model.save(dest / MODEL_NAME)
    clip = index.meta.get("model") or clip_model()
    meta = {
        "name": (name or slug).strip() or slug,
        "slug": slug,
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "clip_model": clip,
        "dim": dim,
        "positive": pos_ids,
        "negative": neg_ids,
        "positive_n": len(pos_ids),
        "negative_n": len(neg_ids),
    }
    (dest / META_NAME).write_text(json.dumps(meta, indent=2) + "\n")
    return meta


def list_lenses():
    root = _root()
    if not root.is_dir():
        return []
    found = []
    for child in sorted(root.iterdir()):
        meta_path = child / META_NAME
        if not child.is_dir() or not meta_path.is_file():
            continue
        try:
            meta = json.loads(meta_path.read_text())
        except (OSError, ValueError):
            continue
        meta.setdefault("slug", child.name)
        meta.setdefault("name", child.name)
        found.append(meta)
    return found


def load_lens(slug: str):
    name = slugify(slug)
    dest = _root() / name
    meta_path = dest / META_NAME
    model_path = dest / MODEL_NAME
    if not meta_path.is_file() or not model_path.is_file():
        raise FileNotFoundError("No lens named %s" % name)
    meta = json.loads(meta_path.read_text())
    meta.setdefault("slug", name)
    model = _load_keras(model_path)
    return model, meta


def apply_lens(index, slug: str, n: int = 24):
    """Load a saved head and score the current CLIP index (not saved scores)."""
    model, meta = load_lens(slug)
    want_dim = int(meta.get("dim") or 0)
    have_dim = int(index.vectors.shape[1])
    if want_dim and want_dim != have_dim:
        raise ValueError(
            "Lens %s is dim %s; CLIP index is dim %s" % (meta.get("slug"), want_dim, have_dim)
        )
    want_clip = meta.get("clip_model")
    have_clip = index.meta.get("model") or clip_model()
    if want_clip and have_clip and want_clip != have_clip:
        raise ValueError(
            "Lens %s was fit on %s; CLIP index is %s" % (meta.get("slug"), want_clip, have_clip)
        )
    hits = score_index(model, index, n)
    pos = [doc_id for doc_id in meta.get("positive") or [] if index.row(doc_id) is not None]
    neg = [doc_id for doc_id in meta.get("negative") or [] if index.row(doc_id) is not None]
    stats = {
        "slug": meta.get("slug"),
        "name": meta.get("name"),
        "positive": pos,
        "negative": neg,
        "positive_n": len(pos),
        "negative_n": len(neg),
        "dropped_positive": len(meta.get("positive") or []) - len(pos),
        "dropped_negative": len(meta.get("negative") or []) - len(neg),
        "scored": len(index.ids),
    }
    return hits, stats


def delete_lens(slug: str) -> None:
    name = slugify(slug)
    dest = _root() / name
    if not dest.is_dir():
        raise FileNotFoundError("No lens named %s" % name)
    shutil.rmtree(dest)
