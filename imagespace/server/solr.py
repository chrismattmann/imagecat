"""Query ImageCat Solr. Document id is the original image path."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

import httpx

from .config import solr_timeout, solr_url

HIDDEN = {"_version_", "_root_", "text", "text_rev"}
SKIP_FIELD_SEARCH = HIDDEN | {
    "highlight",
    "clip_score",
    "iqr_score",
    "meta_score",
    "jaccard_keys_f",
    "jaccard_vals_f",
}
_FIELD_QUERY = re.compile(r"^[A-Za-z_][\w.]*:")
_FIELD_CLAUSE = re.compile(r"^([A-Za-z_][\w.]*)\s*:\s*(.*)$")


def user_query(raw: str | None) -> str:
    q = (raw or "").strip()
    if not q or q == "*":
        return "*:*"
    return q


def is_field_query(raw: str | None) -> bool:
    q = (raw or "").strip()
    return bool(_FIELD_QUERY.match(q))


def field_query(field: str, value: Any) -> str:
    """Build a Solr clause that matches one Tika/OCR field value."""
    name = re.sub(r"[^\w.]", "", str(field or ""))
    if not name or name in SKIP_FIELD_SEARCH:
        raise ValueError("that field is not searchable")
    if value is None or value == "":
        raise ValueError("empty value")
    text = str(value).strip()
    if not text:
        raise ValueError("empty value")
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return '%s:"%s"' % (name, escaped)


def _unescape_solr_quoted(text: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text):
            out.append(text[i + 1])
            i += 2
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def parse_field_clause(raw: str) -> tuple[str, str]:
    """Split a chip like tiff_Make:\"Canon\" into field and value."""
    match = _FIELD_CLAUSE.match((raw or "").strip())
    if not match:
        raise ValueError("not a field filter")
    name, rest = match.group(1), match.group(2).strip()
    if len(rest) >= 2 and rest[0] == '"' and rest[-1] == '"':
        rest = _unescape_solr_quoted(rest[1:-1])
    if not rest:
        raise ValueError("empty value")
    return name, rest


def filter_queries(raws: list[str] | None) -> list[str]:
    """Rebuild operator-facing chips as Solr fq clauses."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in raws or []:
        name, value = parse_field_clause(raw)
        clause = field_query(name, value)
        if clause not in seen:
            seen.add(clause)
            out.append(clause)
    return out


def _get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    url = solr_url() + path
    with httpx.Client(timeout=solr_timeout()) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()


def search_params(
    q: str, start: int = 0, rows: int = 24, filters: list[str] | None = None
) -> dict[str, Any]:
    start = max(0, int(start))
    rows = min(100, max(1, int(rows)))
    parsed = user_query(q)
    clauses = filter_queries(filters)
    params: dict[str, Any] = {
        "q": parsed,
        "start": start,
        "rows": rows,
        "wt": "json",
        "hl": "true",
        "hl.fl": "ocr_text",
    }
    if clauses:
        params["fq"] = clauses
        params["sort"] = "id asc"
    if is_field_query(q):
        params["defType"] = "lucene"
        params["sort"] = "id asc"
    else:
        params["defType"] = "edismax"
        params["qf"] = "ocr_text text caption"
        params["q.op"] = "AND"
    return params


def search(
    q: str, start: int = 0, rows: int = 24, filters: list[str] | None = None
) -> dict[str, Any]:
    params = search_params(q, start, rows, filters)
    body = _get("/select", params)
    docs = []
    highlighting = (body.get("highlighting") or {})
    for doc in (body.get("response") or {}).get("docs") or []:
        item = {k: v for k, v in doc.items() if k not in HIDDEN}
        hid = highlighting.get(doc.get("id") or "", {})
        if hid:
            item["highlight"] = hid
        docs.append(item)
    response = body.get("response") or {}
    return {
        "query": params["q"],
        "filters": list(params.get("fq") or []),
        "start": int(params["start"]),
        "rows": int(params["rows"]),
        "numFound": int(response.get("numFound") or 0),
        "docs": docs,
    }


def scalar(value: Any) -> Any:
    if isinstance(value, list) and value:
        return value[0]
    return value


def iter_docs(fl: str = "id,sha1sum_s_md", page: int = 100):
    """Yield Solr docs for the whole core."""
    start = 0
    while True:
        body = _get(
            "/select",
            {
                "q": "*:*",
                "fl": fl,
                "start": start,
                "rows": page,
                "wt": "json",
                "sort": "id asc",
            },
        )
        docs = (body.get("response") or {}).get("docs") or []
        if not docs:
            return
        for doc in docs:
            yield doc
        start += len(docs)
        total = int((body.get("response") or {}).get("numFound") or 0)
        if start >= total:
            return


def get_docs(ids: list[str]) -> list[dict[str, Any]]:
    """Hydrate Solr docs, preserving the given id order."""
    wanted = [i for i in ids if i]
    if not wanted:
        return []
    by_id: dict[str, dict[str, Any]] = {}
    chunk = 40
    for i in range(0, len(wanted), chunk):
        part = wanted[i : i + chunk]
        clauses = ['id:"%s"' % doc_id.replace('"', r"\"") for doc_id in part]
        body = _get(
            "/select",
            {
                "q": " OR ".join(clauses),
                "rows": len(part),
                "wt": "json",
            },
        )
        for doc in (body.get("response") or {}).get("docs") or []:
            item = {k: v for k, v in doc.items() if k not in HIDDEN}
            if item.get("id"):
                by_id[item["id"]] = item
    return [by_id[doc_id] for doc_id in wanted if doc_id in by_id]


def get_doc(doc_id: str) -> dict[str, Any] | None:
    if not doc_id:
        return None
    body = _get(
        "/select",
        {
            "q": 'id:"%s"' % doc_id.replace('"', r"\""),
            "rows": 1,
            "wt": "json",
        },
    )
    docs = (body.get("response") or {}).get("docs") or []
    if not docs:
        return None
    return {k: v for k, v in docs[0].items() if k not in HIDDEN}


def ping() -> dict[str, Any]:
    try:
        body = _get("/admin/ping", {"wt": "json"})
        status = body.get("status") or "unknown"
    except Exception as exc:
        return {"ok": False, "solr": solr_url(), "error": str(exc)}
    try:
        found = search("*", 0, 0)["numFound"]
    except Exception:
        found = None
    return {"ok": status == "OK", "solr": solr_url(), "status": status, "numFound": found}


def file_url(doc_id: str) -> str:
    return "/api/file?id=" + quote(doc_id, safe="")
