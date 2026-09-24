"""Exclusive lock for CLIP / fg / bg index writes.

Solr can take concurrent IngestInPlace writers. The similarity indexes
are files (ids.json, vectors.npy, index.faiss) rewritten as one snapshot.
Two --incremental jobs without a lock both load the same ids, encode
overlapping images, and the last save_index wins — dropping the other
job's vectors.

portalocker serializes those jobs per index directory. CLIP (data/clip)
and fg/bg (data/fg) use different lock files, so they can still run at the
same time. A second CLIP ingest waits, then sees the updated ids and only
encodes what is still missing.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import portalocker

LOCK_NAME = ".write.lock"


@contextmanager
def exclusive_index(folder: str | Path):
    path = Path(folder)
    path.mkdir(parents=True, exist_ok=True)
    with portalocker.Lock(path / LOCK_NAME, mode="a+", timeout=None):
        yield path
