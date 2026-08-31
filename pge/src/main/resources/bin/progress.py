# Write JobDir/.progress for OPSUI. Opt-in: scripts that never call this
# have no bar. StdPGETaskInstance watches this file.
from __future__ import annotations

import os
from pathlib import Path


def progress_dir(folder=None):
    if folder:
        return Path(folder)
    env = os.environ.get("PGE_PROGRESS_DIR")
    if env:
        return Path(env)
    return Path(".")


def write_progress(done, total, msg="working", folder=None):
    path = progress_dir(folder) / ".progress"
    path.write_text(
        "done=%d\ntotal=%d\nmsg=%s\n" % (int(done), int(total), msg or ""),
        encoding="utf-8",
    )
    return path
