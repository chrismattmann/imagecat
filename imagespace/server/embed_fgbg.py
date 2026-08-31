"""Encode ImageCat images as CLIP foreground and background indexes.

    PYTHONPATH=. python -m server.embed_fgbg --incremental
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import solr
from .config import bg_dir, clip_model, fg_dir
from .embed import _reload, collect_paths, encode_paths, load_existing
from .progress import write_progress
from .index_lock import exclusive_index
from .segment import rembg_available, split_fg_bg
from .similar import save_index


def encode_split(paths: list[str], model_name: str):
    import tempfile

    fg_paths = []
    bg_paths = []
    kept = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        n = len(paths)
        if n:
            write_progress(0, n, "split")
        for i, path in enumerate(paths):
            try:
                fg, bg = split_fg_bg(path)
                fg_file = root / ("fg-%d.jpg" % i)
                bg_file = root / ("bg-%d.jpg" % i)
                fg.save(fg_file, quality=90)
                bg.save(bg_file, quality=90)
                fg_paths.append(str(fg_file))
                bg_paths.append(str(bg_file))
                kept.append(path)
            except Exception as exc:
                print("skip fg/bg %s: %s" % (path, exc), file=sys.stderr)
            if (i + 1) % 25 == 0 or (i + 1) == n:
                write_progress(i + 1, n, "split")
                print("split %d / %d" % (i + 1, n))
        if not kept:
            import numpy as np

            empty = np.zeros((0, 512), dtype="float32")
            return [], empty, empty
        _, fg_vec = encode_paths(fg_paths, model_name, progress_msg="fg CLIP")
        _, bg_vec = encode_paths(bg_paths, model_name, progress_msg="bg CLIP")
    return kept, fg_vec, bg_vec


def _write_side(existing_ids, existing_vectors, new_ids, new_vectors, folder, model_name):
    import numpy as np

    if existing_ids:
        all_ids = existing_ids + new_ids
        vectors = np.concatenate([existing_vectors, new_vectors], axis=0) if len(new_ids) else existing_vectors
    else:
        all_ids, vectors = new_ids, new_vectors
    if len(all_ids) < 2:
        raise SystemExit("Need at least two fg/bg vectors")
    save_index(all_ids, vectors, {"model": model_name, "count": len(all_ids), "dim": int(vectors.shape[1]), "space": folder.name}, folder)
    print("wrote %s %d vectors" % (folder, len(all_ids)))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Encode CLIP foreground and background indexes.")
    parser.add_argument("--incremental", action="store_true")
    parser.add_argument("--reload-url", default="http://127.0.0.1:8090/api/clip/reload")
    parser.add_argument("--no-reload", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="Encode at most N new images (0 = all).")
    args = parser.parse_args(argv)
    if not rembg_available():
        print("rembg is not installed. pip install rembg onnxruntime", file=sys.stderr)
        return 2
    model_name = clip_model()
    fg_folder = Path(fg_dir())
    bg_folder = Path(bg_dir())
    # One lock for both sides: they are always rewritten together. CLIP
    # uses data/clip/.write.lock, so a CLIP incremental can still run
    # while this waits or holds data/fg/.write.lock.
    with exclusive_index(fg_folder):
        return _build(args, fg_folder, bg_folder, model_name)


def _build(args, fg_folder: Path, bg_folder: Path, model_name: str) -> int:
    paths = collect_paths()
    existing_fg_ids, existing_fg = load_existing(fg_folder) if args.incremental else ([], None)
    existing = set(existing_fg_ids)
    todo = [p for p in paths if p not in existing] if args.incremental else paths
    if args.limit and args.limit > 0:
        todo = todo[: args.limit]
    print("fg/bg CLIP [%s] files=%d already=%d todo=%d" % (model_name, len(paths), len(existing), len(todo)))
    if args.incremental and not todo:
        print("fg/bg index already covers Solr")
        _reload(args)
        return 0
    new_ids, fg_vec, bg_vec = encode_split(todo, model_name)
    _write_side(existing_fg_ids, existing_fg, new_ids, fg_vec, fg_folder, model_name)
    existing_bg_ids, existing_bg = load_existing(bg_folder) if args.incremental else ([], None)
    _write_side(existing_bg_ids, existing_bg, new_ids, bg_vec, bg_folder, model_name)
    _reload(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
