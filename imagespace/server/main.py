"""ImageSpace HTTP API. Search, CLIP similar, IQR refine."""

from __future__ import annotations

import os

# FAISS and Keras/Torch each ship libomp. Two copies abort the process on
# macOS (OMP Error #15) the first time IQR imports Keras after CLIP is loaded.
os.environ.setdefault("KERAS_BACKEND", "torch")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import images, iqr, solr
from .config import bg_dir, fg_dir
from .similar import ClipIndex

app = FastAPI(title="ImageSpace", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_UI_DIST = Path(__file__).resolve().parents[1] / "web" / "dist"

class IqrRefineBody(BaseModel):
    positive: list[str] = Field(default_factory=list)
    negative: list[str] = Field(default_factory=list)
    n: int = 24


_clip = ClipIndex()
_fg = ClipIndex(fg_dir())
_bg = ClipIndex(bg_dir())


def _index() -> ClipIndex:
    if not _clip.available():
        _clip.reload()
    return _clip


def _space(name: str | None) -> ClipIndex:
    key = (name or "clip").lower()
    if key == "fg":
        if not _fg.available():
            _fg.reload()
        return _fg
    if key == "bg":
        if not _bg.available():
            _bg.reload()
        return _bg
    return _index()


@app.get("/api/health")
def health():
    ping = solr.ping()
    index = _index()
    ping["capabilities"] = {
        "search": True,
        "similar": index.available(),
        "iqr": index.available() and iqr.keras_available(),
        "fgbg": _fg.available() and _bg.available(),
    }
    if index.available():
        ping["clip"] = {
            "count": len(index.ids),
            "model": index.meta.get("model"),
            "dim": index.meta.get("dim"),
            "backend": index.meta.get("backend"),
            "faiss": index.meta.get("faiss"),
        }
    return ping


def _mark_indexes(docs: list) -> None:
    clip = _index()
    fg = _space("fg")
    bg = _space("bg")
    for doc in docs:
        doc_id = doc.get("id")
        doc["clip_indexed"] = clip.row(doc_id) is not None if clip.available() else False
        doc["fg_indexed"] = fg.row(doc_id) is not None if fg.available() else False
        doc["bg_indexed"] = bg.row(doc_id) is not None if bg.available() else False


@app.get("/api/search")
def search(
    q: str = Query("*"),
    start: int = Query(0),
    rows: int = Query(24),
    fq: list[str] | None = Query(None),
):
    try:
        body = solr.search(q, start, rows, fq or [])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _mark_indexes(body.get("docs") or [])
    return body


@app.get("/api/doc")
def doc(id: str = Query(...)):
    found = solr.get_doc(id)
    if found is None:
        return {"missing": True, "id": id}
    _mark_indexes([found])
    return {"doc": found}


@app.get("/api/file")
def file(id: str = Query(...), w: int | None = Query(None)):
    return images.file_response(id, w)


@app.get("/api/similar")
def similar(id: str = Query(...), n: int = Query(24), space: str = Query("clip")):
    index = _space(space)
    label = (space or "clip").lower()
    if label in ("fg", "bg"):
        missing = "Foreground/background index is not built. Run python -m server.embed_fgbg"
    else:
        missing = "CLIP index is not built. Run python -m server.embed"
    if not index.available():
        raise HTTPException(status_code=503, detail=missing)
    hits = index.similar(id, n)
    if hits is None:
        raise HTTPException(status_code=404, detail="That image is not in the %s index" % (label if label in ("fg", "bg") else "CLIP"))
    docs = solr.get_docs([h["id"] for h in hits])
    scores = {h["id"]: h["clip_score"] for h in hits}
    for doc in docs:
        doc["clip_score"] = scores.get(doc.get("id"))
    _mark_indexes(docs)
    available = max(0, len(index.ids) - 1)
    return {
        "id": id,
        "numFound": available,
        "docs": docs,
    }


@app.post("/api/iqr/refine")
def iqr_refine(body: IqrRefineBody):
    index = _index()
    if not index.available():
        raise HTTPException(status_code=503, detail="CLIP index is not built. Run python -m server.embed")
    if not iqr.keras_available():
        raise HTTPException(status_code=503, detail="Keras is not installed (IQR head)")
    try:
        hits, stats = iqr.refine(index, body.positive, body.negative, body.n)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    docs = solr.get_docs([h["id"] for h in hits])
    scores = {h["id"]: h["iqr_score"] for h in hits}
    for doc in docs:
        doc["iqr_score"] = scores.get(doc.get("id"))
    _mark_indexes(docs)
    return {
        "numFound": int((stats or {}).get("scored") or len(docs)),
        "docs": docs,
        "stats": stats,
    }


@app.post("/api/clip/reload")
def clip_reload():
    """Called after python -m server.embed (and from the ImageCat ingest hook)."""
    _clip.reload()
    _fg.reload()
    _bg.reload()
    index = _clip
    return {
        "ok": index.available(),
        "count": len(index.ids),
        "backend": index.meta.get("backend"),
        "model": index.meta.get("model"),
        "fg": len(_fg.ids),
        "bg": len(_bg.ids),
    }


# Built Vue (npm run build) is served from the same process as /api. Vite
# on 5173 is still fine for development. Register last so /api wins.
if _UI_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(_UI_DIST), html=True), name="ui")
