"""FAISS nearest neighbors over L2-normalized CLIP vectors. No Torch at query time."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .config import index_dir

IDS_NAME = "ids.json"
VEC_NAME = "vectors.npy"
META_NAME = "meta.json"
FAISS_NAME = "index.faiss"
# Exact inner product until the catalog is large; then HNSW.
HNSW_AFTER = 10_000

def _faiss():
    try:
        import faiss
        return faiss
    except ImportError:
        return None


def _dir() -> Path:
    return Path(index_dir())


def build_faiss(vectors: np.ndarray):
    faiss = _faiss()
    if faiss is None:
        raise RuntimeError("faiss-cpu is not installed")
    n, dim = vectors.shape
    if n >= HNSW_AFTER:
        index = faiss.IndexHNSWFlat(dim, 32, faiss.METRIC_INNER_PRODUCT)
        index.hnsw.efConstruction = 80
        index.hnsw.efSearch = 64
    else:
        index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    return index


class ClipIndex:
    def __init__(self, directory: str | Path | None = None):
        self.directory = Path(directory) if directory else _dir()
        self.ids: list[str] = []
        self.id_to_row: dict[str, int] = {}
        self.vectors: np.ndarray | None = None
        self.faiss = None
        self.meta: dict = {}
        self.reload()

    def reload(self) -> None:
        ids_path = self.directory / IDS_NAME
        vec_path = self.directory / VEC_NAME
        meta_path = self.directory / META_NAME
        faiss_path = self.directory / FAISS_NAME
        self.faiss = None
        if not ids_path.is_file() or not vec_path.is_file():
            self.ids = []
            self.id_to_row = {}
            self.vectors = None
            self.meta = {}
            return
        self.ids = json.loads(ids_path.read_text())
        self.vectors = np.load(vec_path)
        self.meta = json.loads(meta_path.read_text()) if meta_path.is_file() else {}
        if len(self.ids) != int(self.vectors.shape[0]):
            raise ValueError("CLIP index ids and vectors are different lengths")
        self.id_to_row = {doc_id: i for i, doc_id in enumerate(self.ids)}
        faiss = _faiss()
        if faiss is not None:
            if faiss_path.is_file():
                self.faiss = faiss.read_index(str(faiss_path))
            else:
                self.faiss = build_faiss(self.vectors)
        self.meta["backend"] = "faiss" if self.faiss is not None else "numpy"

    def available(self) -> bool:
        return self.vectors is not None and len(self.ids) > 1

    def row(self, doc_id: str) -> int | None:
        return self.id_to_row.get(doc_id)

    def similar(self, doc_id: str, n: int = 24) -> list[dict] | None:
        if not self.available():
            return None
        idx = self.row(doc_id)
        if idx is None:
            return None
        n = max(1, min(int(n), len(self.ids) - 1))
        k = n + 1
        if self.faiss is not None:
            scores, rows = self.faiss.search(self.vectors[idx : idx + 1], k)
            scored_rows = [(int(rows[0][i]), float(scores[0][i])) for i in range(len(rows[0])) if rows[0][i] >= 0]
        else:
            all_scores = self.vectors @ self.vectors[idx]
            order = np.argsort(-all_scores)[:k]
            scored_rows = [(int(j), float(all_scores[int(j)])) for j in order]
        out = []
        for j, score in scored_rows:
            if j == idx:
                continue
            out.append({"id": self.ids[j], "clip_score": score})
            if len(out) >= n:
                break
        return out


def save_index(ids: list[str], vectors: np.ndarray, meta: dict, directory: str | Path | None = None) -> Path:
    folder = Path(directory) if directory else _dir()
    folder.mkdir(parents=True, exist_ok=True)
    if vectors.dtype != np.float32:
        vectors = vectors.astype(np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    vectors = vectors / norms
    np.save(folder / VEC_NAME, vectors)
    (folder / IDS_NAME).write_text(json.dumps(ids))
    faiss = _faiss()
    if faiss is not None:
        faiss.write_index(build_faiss(vectors), str(folder / FAISS_NAME))
        meta = dict(meta)
        meta["backend"] = "faiss"
        meta["faiss"] = "HNSW" if len(ids) >= HNSW_AFTER else "FlatIP"
    (folder / META_NAME).write_text(json.dumps(meta, indent=2))
    return folder
