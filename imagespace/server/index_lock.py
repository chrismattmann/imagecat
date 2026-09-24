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

import math
import sys
from contextlib import contextmanager
from pathlib import Path

import portalocker

LOCK_NAME = ".write.lock"

# Wait, however long it takes. portalocker's timeout=None does not mean
# "no timeout": it falls back to the library default of five seconds and
# then raises AlreadyLocked. Waiting is the whole point of this lock -- on
# a full run the fg/bg stage holds it for the better part of an hour -- so
# a second job has to block rather than fail.
FOREVER = math.inf

# One short attempt first, only so the wait can be announced. Nothing is
# given up by failing it: the blocking acquire follows immediately.
NOTICE_AFTER_SECONDS = 2.0


@contextmanager
def exclusive_index(folder: str | Path):
    path = Path(folder)
    path.mkdir(parents=True, exist_ok=True)
    lock_file = path / LOCK_NAME

    lock = portalocker.Lock(lock_file, mode="a+", timeout=NOTICE_AFTER_SECONDS)
    try:
        lock.acquire()
    except portalocker.exceptions.BaseLockException:
        # Say so before settling in. A job blocked behind an hour-long
        # fg/bg run is indistinguishable from one that has hung, and hung
        # is the reading an operator reaches for.
        print("waiting for index lock on %s" % path, file=sys.stderr, flush=True)
        lock = portalocker.Lock(lock_file, mode="a+", timeout=FOREVER)
        lock.acquire()

    # Only the acquire is guarded above. Wrapping the yield as well would
    # swallow a lock exception raised by the caller's own body and then
    # yield a second time.
    try:
        yield path
    finally:
        lock.release()
