"""Tiny Keras head for Interactive Query Refinement.

CLIP vectors stay on disk. This ranker maps a CLIP vector to P(relevant).
The head is fitted at Refine time; Keras is the library, not a pretrained
IQR model. Use the Torch backend (already in ImageCat for CLIP/TrOCR)
so the distro does not pull TensorFlow.
"""

from __future__ import annotations

import os
from functools import lru_cache

DEFAULT_DIM = 512


def _use_torch_backend():
    os.environ.setdefault("KERAS_BACKEND", "torch")


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
            layers.Dense(64, activation="relu", name="iqr_hidden"),
            layers.Dense(1, activation="sigmoid", name="iqr_relevant"),
        ],
        name="iqr_head",
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


def refine(index, positive_ids, negative_ids, n: int = 24):
    """Fit the head on pos/neg CLIP rows and rank the whole index."""
    pos = []
    neg = []
    seen_pos = set()
    seen_neg = set()
    for doc_id in positive_ids or []:
        row = index.row(doc_id)
        if row is None or doc_id in seen_pos:
            continue
        seen_pos.add(doc_id)
        pos.append(row)
    for doc_id in negative_ids or []:
        if doc_id in seen_pos:
            continue
        row = index.row(doc_id)
        if row is None or doc_id in seen_neg:
            continue
        seen_neg.add(doc_id)
        neg.append(row)
    if not pos or not neg:
        raise ValueError("IQR needs at least one relevant and one not-relevant image in the CLIP index")
    import numpy as np

    rows = pos + neg
    labels = [1.0] * len(pos) + [0.0] * len(neg)
    vectors = index.vectors[np.array(rows)]
    dim = int(index.vectors.shape[1])
    model = fit_head(vectors, labels, dim=dim)
    scores = score_vectors(model, index.vectors)
    order = np.argsort(-scores)
    n = max(1, min(int(n), len(index.ids)))
    hits = []
    for j in order[:n]:
        j = int(j)
        hits.append({"id": index.ids[j], "iqr_score": float(scores[j])})
    return hits, {"positive": len(pos), "negative": len(neg), "scored": len(index.ids)}
