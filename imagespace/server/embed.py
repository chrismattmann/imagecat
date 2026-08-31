"""Encode ImageCat Solr images with CLIP. Query time does not load this module.

    PYTHONPATH=. python -m server.embed
    PYTHONPATH=. python -m server.embed --incremental
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import solr
from .config import clip_model, index_dir
from .index_lock import exclusive_index
from .progress import write_progress
from .similar import IDS_NAME, VEC_NAME, save_index


def encode_paths(paths: list[str], model_name: str, progress_msg: str = "encoded"):
    import numpy as np
    import torch
    from PIL import Image, ImageFile, ImageOps

    ImageFile.LOAD_TRUNCATED_IMAGES = True
    from transformers import CLIPModel, CLIPProcessor

    processor = CLIPProcessor.from_pretrained(model_name)
    model = CLIPModel.from_pretrained(model_name)
    model.eval()
    # MPS + huge JPEGs has segfaulted here; CLIP is 224px, CPU is enough.
    device = torch.device("cpu")
    model.to(device)
    rows = []
    kept = []
    n = len(paths)
    if n:
        write_progress(0, n, progress_msg)
    with torch.no_grad():
        for i, path in enumerate(paths):
            try:
                image = Image.open(path)
                image = ImageOps.exif_transpose(image).convert("RGB")
                image.thumbnail((512, 512))
                inputs = processor(images=image, return_tensors="pt")
                inputs = {k: v.to(device) for k, v in inputs.items()}
                feat = model.get_image_features(**inputs)
                rows.append(feat[0].cpu().numpy())
                kept.append(path)
            except Exception as exc:
                print("skip encode %s: %s" % (path, exc), file=sys.stderr)
            if (i + 1) % 50 == 0 or (i + 1) == n:
                write_progress(i + 1, n, progress_msg)
                print("encoded %d / %d" % (i + 1, n))
    if not rows:
        return kept, np.zeros((0, 512), dtype="float32")
    return kept, np.stack(rows, axis=0)


def collect_paths():
    out = []
    for doc in solr.iter_docs("id,sha1sum_s_md"):
        doc_id = doc.get("id")
        if not doc_id:
            continue
        path = Path(doc_id)
        if path.is_file():
            out.append(doc_id)
        else:
            print("skip missing file: %s" % doc_id, file=sys.stderr)
    return out


def load_existing(folder: Path):
    import numpy as np

    ids_path = folder / IDS_NAME
    vec_path = folder / VEC_NAME
    if not ids_path.is_file() or not vec_path.is_file():
        return [], np.zeros((0, 512), dtype="float32")
    return json.loads(ids_path.read_text()), np.load(vec_path)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Encode ImageCat Solr images with CLIP.")
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Only encode Solr ids not already in the index (for ImageCat ingest).",
    )
    parser.add_argument(
        "--reload-url",
        default="http://127.0.0.1:8090/api/clip/reload",
        help="POST here after writing the index so ImageSpace picks it up.",
    )
    parser.add_argument("--no-reload", action="store_true", help="Do not POST reload.")
    args = parser.parse_args(argv)

    model_name = clip_model()
    folder = Path(index_dir())
    print("Solr images -> CLIP [%s] -> %s" % (model_name, folder))
    # Hold the directory lock across load + encode + save so a second
    # IngestInPlace incremental waits, then sees this write, instead of
    # both rewriting ids.json / vectors.npy / index.faiss.
    with exclusive_index(folder):
        return _build(args, folder, model_name)


def _build(args, folder: Path, model_name: str) -> int:
    paths = collect_paths()
    existing_ids, existing_vectors = load_existing(folder) if args.incremental else ([], None)
    existing = set(existing_ids)
    todo = [p for p in paths if p not in existing] if args.incremental else paths
    print("files: %d  already indexed: %d  to encode: %d" % (len(paths), len(existing), len(todo)))
    if args.incremental and not todo:
        print("index already covers Solr")
        _reload(args)
        return 0
    if not args.incremental and len(todo) < 2:
        print("Need at least two on-disk images to build a similarity index.", file=sys.stderr)
        return 2
    new_ids, new_vectors = encode_paths(todo, model_name)
    import numpy as np

    if args.incremental and len(existing_ids):
        ids = existing_ids + new_ids
        vectors = np.concatenate([existing_vectors, new_vectors], axis=0) if len(new_ids) else existing_vectors
    else:
        ids, vectors = new_ids, new_vectors
    if len(ids) < 2:
        print("Need at least two on-disk images to build a similarity index.", file=sys.stderr)
        return 2
    save_index(ids, vectors, {"model": model_name, "count": len(ids), "dim": int(vectors.shape[1])}, folder)
    print("wrote %d vectors dim %d" % (len(ids), int(vectors.shape[1])))
    _reload(args)
    return 0


def _reload(args) -> None:
    if args.no_reload:
        return
    try:
        import urllib.request

        req = urllib.request.Request(args.reload_url, method="POST", data=b"")
        with urllib.request.urlopen(req, timeout=10) as response:
            print("reload", response.status, response.read().decode()[:200])
    except Exception as exc:
        print("index written; reload ImageSpace later (%s)" % exc, file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
