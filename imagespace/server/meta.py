"""Jaccard on Tika metadata already in Solr.

ETLlib ``compareKeySimilarity`` / ``compareValueSimilarity`` score each
file against the union of keys (or ``key: value`` tokens) in the corpus —
the golden feature set. Pairwise neighbors are the same two-liner
``|A ∩ B| / |A ∪ B|``. Reimplemented here so ImageCat does not pull
etllib or tika-similarity, and so we read Solr instead of walking a
directory (ice subfolders collide on basename).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import meta_dir as _meta_dir, solr_timeout, solr_url
from .progress import write_progress

# Same skip list as imagecat-ocr.py. Jaccard should not see ICC curves.
SKIP_TIKA_PREFIXES = (
    "ICC:",
    "ICC ",
    "ICC_",
    "Color Halftoning",
    "Color Transfer",
    "Component 1",
    "Component 2",
    "Component 3",
)
SKIP_TIKA_KEYS = {
    "Padding",
    "X-TIKA:content",
    "X-TIKA:Parsed-By",
    "X-TIKA:Parsed-By-Full-Set",
}
SYSTEM_FIELDS = {
    "id",
    "ocr_text",
    "ocr_model_s",
    "sha1sum_s_md",
    "caption",
    "content",
    "text",
    "text_rev",
    "_version_",
    "_root_",
    "highlight",
    "jaccard_keys_f",
    "jaccard_vals_f",
    "clip_score",
    "iqr_score",
    "meta_score",
    "clip_indexed",
    "fg_indexed",
    "bg_indexed",
}
MAX_TIKA_VALUE = 1024
GOLDEN_NAME = "golden.json"


def meta_dir() -> Path:
    return Path(_meta_dir())


def skip_field(name: str) -> bool:
    if not name or name in SYSTEM_FIELDS or name in SKIP_TIKA_KEYS:
        return True
    spaced = name.replace("_", " ")
    for prefix in SKIP_TIKA_PREFIXES:
        underscored = prefix.replace(":", "_").replace(" ", "_")
        if name.startswith(prefix) or name.startswith(underscored) or spaced.startswith(prefix):
            return True
    return False


def _scalars(value) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        out = []
        for item in value:
            out.extend(_scalars(item))
        return out
    text = str(value).strip()
    if not text or len(text) > MAX_TIKA_VALUE:
        return []
    return [text]


def key_set(doc: dict) -> frozenset[str]:
    return frozenset(k for k in (doc or {}) if not skip_field(k))


def value_set(doc: dict) -> frozenset[str]:
    tokens = []
    for key, raw in (doc or {}).items():
        if skip_field(key):
            continue
        for item in _scalars(raw):
            tokens.append("%s=%s" % (key, item))
    return frozenset(tokens)


def jaccard(left: frozenset, right: frozenset) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return float(len(left & right)) / float(len(left | right))


def golden_score(feat: frozenset, union: frozenset) -> float:
    if not union:
        return 0.0
    return float(len(feat & union)) / float(len(union))


class MetaIndex:
    """In-memory key/value sets for pairwise neighbors. Source of truth is Solr."""

    def __init__(self):
        self.ids: list[str] = []
        self.keys: dict[str, frozenset] = {}
        self.vals: dict[str, frozenset] = {}
        self.golden_keys: frozenset = frozenset()
        self.golden_vals: frozenset = frozenset()
        self.reload()

    def load_docs(self, docs: list[dict]) -> None:
        self.ids = []
        self.keys = {}
        self.vals = {}
        for doc in docs or []:
            doc_id = doc.get("id")
            if not doc_id:
                continue
            self.ids.append(doc_id)
            self.keys[doc_id] = key_set(doc)
            self.vals[doc_id] = value_set(doc)
        self.golden_keys = frozenset().union(*self.keys.values()) if self.keys else frozenset()
        self.golden_vals = frozenset().union(*self.vals.values()) if self.vals else frozenset()

    def reload(self) -> None:
        try:
            from . import solr
            docs = list(solr.iter_docs(fl="*", page=200))
        except Exception:
            docs = []
        self.load_docs(docs)

    def available(self) -> bool:
        nonempty = sum(1 for feat in self.keys.values() if feat)
        return nonempty >= 2 or len(self.ids) > 1

    def similar(self, doc_id: str, n: int = 24, space: str = "keys") -> list[dict] | None:
        table = self.vals if space == "vals" else self.keys
        query = table.get(doc_id)
        if query is None:
            return None
        scored = []
        for other_id, feat in table.items():
            if other_id == doc_id:
                continue
            scored.append((jaccard(query, feat), other_id))
        scored.sort(key=lambda row: (-row[0], row[1]))
        n = max(1, min(int(n), max(0, len(scored))))
        return [{"id": other_id, "meta_score": score} for score, other_id in scored[:n]]

    def solr_scores(self) -> list[dict]:
        out = []
        for doc_id in self.ids:
            out.append(
                {
                    "id": doc_id,
                    "jaccard_keys_f": golden_score(self.keys[doc_id], self.golden_keys),
                    "jaccard_vals_f": golden_score(self.vals[doc_id], self.golden_vals),
                }
            )
        return out

    def save_golden(self, folder: Path | None = None) -> Path:
        dest = Path(folder) if folder else meta_dir()
        dest.mkdir(parents=True, exist_ok=True)
        payload = {
            "n": len(self.ids),
            "n_keys": len(self.golden_keys),
            "n_vals": len(self.golden_vals),
            "keys": sorted(self.golden_keys),
        }
        path = dest / GOLDEN_NAME
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path


def _xml_escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _atomic_xml(rows: list[dict]) -> bytes:
    # Solr 10 treats JSON {"field": {"set": x}} as a nested child document
    # (missing id). XML update="set" is the atomic form that keeps Tika fields.
    parts = ["<add>"]
    for row in rows:
        parts.append(
            "<doc><field name=\"id\">%s</field>"
            "<field name=\"jaccard_keys_f\" update=\"set\">%.6f</field>"
            "<field name=\"jaccard_vals_f\" update=\"set\">%.6f</field></doc>"
            % (
                _xml_escape(row["id"]),
                float(row["jaccard_keys_f"]),
                float(row["jaccard_vals_f"]),
            )
        )
    parts.append("</add>")
    return "".join(parts).encode("utf-8")


def _post_scores(rows: list[dict], commit_every: int = 32) -> None:
    import httpx

    url = solr_url() + "/update"
    batch = []
    total = len(rows)
    if total:
        write_progress(0, total, "jaccard")
    headers = {"Content-Type": "application/xml"}
    with httpx.Client(timeout=solr_timeout()) as client:
        for i, row in enumerate(rows):
            batch.append(row)
            if len(batch) >= commit_every:
                response = client.post(
                    url, params={"commit": "true"}, content=_atomic_xml(batch), headers=headers
                )
                response.raise_for_status()
                write_progress(i + 1, total, "jaccard")
                batch = []
        if batch:
            response = client.post(
                url, params={"commit": "true"}, content=_atomic_xml(batch), headers=headers
            )
            response.raise_for_status()
            write_progress(total, total, "jaccard")
        elif total:
            write_progress(total, total, "jaccard")


def _reload(url: str) -> None:
    if not url:
        return
    import httpx

    with httpx.Client(timeout=solr_timeout()) as client:
        response = client.post(url)
        print("reload %s %s" % (response.status_code, response.text[:200]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score Solr imagecat docs with metadata Jaccard.")
    parser.add_argument("--reload-url", default="", help="POST after writing (ImageSpace /api/meta/reload)")
    args = parser.parse_args(argv)
    index = MetaIndex()
    if not index.ids:
        print("IndexMetadataJaccard: no Solr docs; skip")
        return 0
    print(
        "IndexMetadataJaccard: %d docs, %d golden keys, %d golden value tokens"
        % (len(index.ids), len(index.golden_keys), len(index.golden_vals))
    )
    index.save_golden()
    _post_scores(index.solr_scores())
    _reload(args.reload_url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
