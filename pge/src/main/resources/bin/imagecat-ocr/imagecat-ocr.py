#!/usr/bin/env python3
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# OCR a chunk file of image paths with Paddle/RapidOCR (detect then
# recognize; default), HuggingFace TrOCR, or Donut, then POST the text
# plus Tika MIME/EXIF to Solr. Replaces Solr Cell + Tesseract. Solr Cell
# used to run Tika on each image as it indexed; File Manager only
# catalogs the ChunkList path files, so Tika has to happen here.

"""OCR images listed in a chunk file and index the text plus Tika metadata in Solr."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

_BIN = Path(__file__).resolve().parent.parent
if str(_BIN) not in sys.path:
    sys.path.insert(0, str(_BIN))
from progress import write_progress  # noqa: E402


TROCR_MODEL = "microsoft/trocr-base-printed"
DONUT_MODEL = "naver-clova-ix/donut-base"
# RapidOCR ships PP-OCR ONNX (Apache 2.0). Detect-then-recognize: no
# boxes means empty text, unlike TrOCR which always emits a token.
PADDLE_MODEL = "rapidocr/pp-ocr"
MAX_TIKA_VALUE = 1024
# ICC curves, padding, and per-component JPEG tables are not what SolrCell
# users looked at, and they blow up a string field.
SKIP_TIKA_PREFIXES = (
    "ICC:",
    "ICC ",
    "Color Halftoning",
    "Color Transfer",
    "Component 1",
    "Component 2",
    "Component 3",
)
SKIP_TIKA_KEYS = {"Padding", "X-TIKA:content", "X-TIKA:Parsed-By", "X-TIKA:Parsed-By-Full-Set"}
_FIELD_OK = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def sha1_of(path: str) -> str:
    digest = hashlib.sha1()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_chunk(chunk_file: str) -> list[str]:
    paths = []
    with open(chunk_file, "r", encoding="utf-8") as handle:
        for line in handle:
            path = line.strip()
            if path:
                paths.append(path)
    return paths


def solr_field_name(key: str) -> str:
    """Solr 10 field names are [A-Za-z_][A-Za-z0-9_]*. SolrCell's Content-Type
    lands on the explicit content_type field; everything else is sanitized
    onto the catch-all dynamicField."""
    if key in ("Content-Type", "ContentType", "content_type"):
        return "content_type"
    chars = []
    for ch in key:
        if ch.isalnum() or ch == "_":
            chars.append(ch)
        else:
            chars.append("_")
    name = "".join(chars)
    name = re.sub(r"_+", "_", name).strip("_")
    if not name:
        return "tika_field"
    if name[0].isdigit():
        name = "t_" + name
    if not _FIELD_OK.match(name):
        return "tika_field"
    return name


def skip_tika_key(key: str) -> bool:
    if key in SKIP_TIKA_KEYS:
        return True
    for prefix in SKIP_TIKA_PREFIXES:
        if key.startswith(prefix):
            return True
    return False


def parse_tika_metadata_text(text: str) -> dict[str, str]:
    """Parse `tika-app -m` output: one 'Key: value' line per field."""
    out = {}
    for line in text.splitlines():
        if ": " not in line:
            continue
        key, value = line.split(": ", 1)
        key = key.strip()
        value = value.strip()
        if not key or skip_tika_key(key):
            continue
        if len(value) > MAX_TIKA_VALUE:
            continue
        if value.startswith("[") and value.endswith("values]"):
            continue
        field = solr_field_name(key)
        if field in ("id", "ocr_text", "ocr_model_s", "sha1sum_s_md", "_version_"):
            continue
        out[field] = value
    return out


def find_tika_app() -> Path | None:
    env = os.environ.get("TIKA_APP")
    if env:
        path = Path(env)
        if path.is_file():
            return path
    roots = []
    for key in ("PGE_ROOT", "PGE_HOME", "FILEMGR_HOME", "OODT_HOME", "IMAGECAT_HOME"):
        val = os.environ.get(key)
        if val:
            roots.append(Path(val))
    here = Path(__file__).resolve()
    roots.append(here.parents[2])  # pge/
    roots.append(here.parents[3] if len(here.parents) > 3 else here.parents[2])
    for root in roots:
        for lib in (root / "lib", root / "pge" / "lib"):
            if not lib.is_dir():
                continue
            matches = sorted(lib.glob("tika-app-*.jar"))
            if matches:
                return matches[-1]
    m2 = Path.home() / ".m2" / "repository" / "org" / "apache" / "tika" / "tika-app"
    if m2.is_dir():
        jars = sorted(m2.glob("*/tika-app-*.jar"))
        if jars:
            return jars[-1]
    return None


# How many files go to one Tika process.
#
# Not one, which is what this used to do. A JVM that has parsed nothing yet
# still has to load the jar, build the parser registry and the MIME detector,
# and on this corpus that is about half a second before it looks at an image.
# Paid once per file it is most of the cost of the stage; paid once per batch
# it disappears. Measured on twenty 8MB JPEGs:
#
#   twenty JVMs, one file each   29.7s   1.48s per image
#   one JVM, twenty files        18.8s   0.94s per image
#
# Bounded because the paths go on a command line and ARG_MAX is finite. Two
# hundred paths of a few hundred bytes is far inside it on any platform, and
# the amortisation is already flat by then.
TIKA_BATCH = int(os.environ.get("IMAGECAT_TIKA_BATCH", "200"))


def _java_bin() -> str:
    java = os.environ.get("JAVA_HOME", "")
    return str(Path(java) / "bin" / "java") if java else "java"


def parse_tika_json_stream(text: str) -> list[dict[str, str]]:
    """Split `tika-app -j` output for several files into one dict per file.

    Tika writes one JSON object per input with nothing between them, so this
    is a stream of concatenated objects rather than a list. raw_decode walks
    them in order.
    """
    decoder = json.JSONDecoder()
    out: list[dict[str, str]] = []
    index = 0
    length = len(text)
    while index < length:
        while index < length and text[index].isspace():
            index += 1
        if index >= length:
            break
        try:
            obj, index = decoder.raw_decode(text, index)
        except ValueError:
            break
        out.append(obj if isinstance(obj, dict) else {})
    return out


def clean_tika_fields(raw: dict) -> dict[str, str]:
    """The same filtering the line-oriented parser did, over parsed JSON."""
    out = {}
    for key, value in raw.items():
        key = str(key).strip()
        if not key or skip_tika_key(key):
            continue
        if isinstance(value, list):
            value = value[0] if value else ""
        value = str(value).strip()
        if not value or len(value) > MAX_TIKA_VALUE:
            continue
        field = solr_field_name(key)
        if field in ("id", "ocr_text", "ocr_model_s", "sha1sum_s_md", "_version_"):
            continue
        out[field] = value
    return out


def tika_metadata_batch(paths: list[str], tika_app: Path | None) -> list[dict[str, str]]:
    """Metadata for several files from one Tika process, in the order given.

    Tika emits its objects in argument order, and each carries resourceName,
    so position is the mapping and the name is the check. When the two
    disagree, or the batch comes back short, the batch is abandoned and its
    files are read one at a time -- a wrong answer aligned to the wrong image
    is worse than a slow one.
    """
    if tika_app is None or not paths:
        return [{} for _ in paths]
    try:
        proc = subprocess.run(
            [_java_bin(), "-jar", str(tika_app), "-j"] + list(paths),
            check=False,
            capture_output=True,
            text=True,
            timeout=30 + 10 * len(paths),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print("Tika batch failed (%d files): %s" % (len(paths), exc), file=sys.stderr)
        return [tika_metadata(p, tika_app) for p in paths]
    if proc.returncode != 0:
        print("Tika batch exit %s: %s"
              % (proc.returncode, proc.stderr.strip()[:200]), file=sys.stderr)
        return [tika_metadata(p, tika_app) for p in paths]

    objects = parse_tika_json_stream(proc.stdout)
    if len(objects) != len(paths):
        # Short output means some file was skipped, and every object after
        # that point belongs to a different image than the one it would be
        # attached to.
        print("Tika batch returned %d of %d; falling back to one at a time"
              % (len(objects), len(paths)), file=sys.stderr)
        return [tika_metadata(p, tika_app) for p in paths]

    results = []
    for path, obj in zip(paths, objects):
        name = str(obj.get("resourceName", "")).strip('"')
        if name and name != os.path.basename(path):
            print("Tika batch out of order at %s (got %s); one at a time"
                  % (os.path.basename(path), name), file=sys.stderr)
            return [tika_metadata(p, tika_app) for p in paths]
        results.append(clean_tika_fields(obj))
    return results


def tika_metadata(path: str, tika_app: Path | None) -> dict[str, str]:
    """One file, one process. The fallback, and what the batch is measured
    against."""
    if tika_app is None:
        return {}
    try:
        proc = subprocess.run(
            [_java_bin(), "-jar", str(tika_app), "-m", path],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print("Tika failed %s: %s" % (path, exc), file=sys.stderr)
        return {}
    if proc.returncode != 0:
        print("Tika exit %s on %s: %s" % (proc.returncode, path, proc.stderr.strip()[:200]), file=sys.stderr)
        return {}
    return parse_tika_metadata_text(proc.stdout)


def texts_from_paddle(result) -> str:
    """Join RapidOCR / PP-OCR detections. Empty if the detector found nothing."""
    if result is None:
        return ""
    txts = getattr(result, "txts", None)
    if txts is not None:
        lines = [str(t).strip() for t in txts if t and str(t).strip()]
        return "\n".join(lines)
    if isinstance(result, tuple) and result:
        result = result[0]
    if not result:
        return ""
    lines = []
    for item in result:
        if item is None:
            continue
        text = ""
        if isinstance(item, dict):
            text = item.get("text") or item.get("rec_txt") or ""
        elif isinstance(item, (list, tuple)):
            if len(item) >= 2 and isinstance(item[1], str):
                text = item[1]
            elif item and isinstance(item[0], str):
                text = item[0]
        text = str(text).strip()
        if text:
            lines.append(text)
    return "\n".join(lines)


def load_ocr(model_name: str):
    """Return a callable image-path -> text. Heavy imports stay here."""
    from PIL import Image

    name = model_name.lower()
    if name == "paddle":
        try:
            from rapidocr import RapidOCR
        except ImportError:
            raise SystemExit(
                "paddle OCR needs rapidocr: pip install rapidocr onnxruntime"
            )
        engine = RapidOCR()

        def ocr(path: str) -> str:
            return texts_from_paddle(engine(path))

        return ocr, PADDLE_MODEL

    if name == "trocr":
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel

        processor = TrOCRProcessor.from_pretrained(TROCR_MODEL, use_fast=False)
        model = VisionEncoderDecoderModel.from_pretrained(TROCR_MODEL)

        def ocr(path: str) -> str:
            image = Image.open(path).convert("RGB")
            pixel_values = processor(images=image, return_tensors="pt").pixel_values
            generated_ids = model.generate(pixel_values)
            return processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()

        return ocr, TROCR_MODEL

    if name == "donut":
        from transformers import DonutProcessor, VisionEncoderDecoderModel

        processor = DonutProcessor.from_pretrained(DONUT_MODEL)
        model = VisionEncoderDecoderModel.from_pretrained(DONUT_MODEL)
        task_prompt = "<s_ocr>"

        def ocr(path: str) -> str:
            image = Image.open(path).convert("RGB")
            pixel_values = processor(images=image, return_tensors="pt").pixel_values
            decoder_input_ids = processor.tokenizer(
                task_prompt, add_special_tokens=False, return_tensors="pt"
            ).input_ids
            outputs = model.generate(
                pixel_values,
                decoder_input_ids=decoder_input_ids,
                max_length=512,
            )
            return processor.batch_decode(outputs, skip_special_tokens=True)[0].strip()

        return ocr, DONUT_MODEL

    raise SystemExit("Unknown --model %s (use paddle, trocr or donut)" % model_name)


def index_docs(solr_url: str, docs: list[dict]) -> None:
    import pysolr

    client = pysolr.Solr(solr_url, always_commit=True, timeout=120)
    client.add(docs)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="OCR a chunk file of images with Paddle/RapidOCR, TrOCR, or Donut and post to Solr."
    )
    parser.add_argument("-f", "--chunk-file", required=True, help="text file, one image path per line")
    parser.add_argument("-s", "--solr-url", required=True, help="Solr core URL, e.g. http://localhost:8983/solr/imagecat")
    parser.add_argument(
        "--model",
        default="paddle",
        choices=("paddle", "trocr", "donut"),
        help="paddle = PP-OCR detect-then-recognize (default; empty if no text); "
        "trocr = printed line recognizer; donut = document understanding",
    )
    parser.add_argument("--commit-every", type=int, default=32, help="Solr batch size")
    parser.add_argument(
        "--no-tika",
        action="store_true",
        help="Skip Tika MIME/EXIF (OCR text only). Default is to run Tika.",
    )
    args = parser.parse_args(argv)

    chunk = Path(args.chunk_file)
    if not chunk.is_file():
        print("Chunk file not found: %s" % chunk, file=sys.stderr)
        return 2

    paths = read_chunk(str(chunk))
    print("Chunk file : [%s]" % chunk)
    print("Solr URL   : [%s]" % args.solr_url)
    print("OCR model  : [%s]" % args.model)
    print("Images     : [%d]" % len(paths))

    tika_app = None if args.no_tika else find_tika_app()
    if args.no_tika:
        print("Tika       : skipped")
    elif tika_app is None:
        print("Tika       : tika-app.jar not found; MIME/EXIF will be missing", file=sys.stderr)
    else:
        print("Tika       : [%s]" % tika_app)

    ocr, hf_id = load_ocr(args.model)

    # Tika runs ahead of the loop, a slice at a time, because its cost is per
    # process and not per file. OCR still runs one image at a time: that cost
    # is genuinely per image and there is nothing to amortise.
    tika_cache: dict[str, dict[str, str]] = {}
    tika_pending = [p for p in paths if Path(p).is_file()] if tika_app else []

    def tika_for(path: str) -> dict[str, str]:
        if tika_app is None:
            return {}
        if path in tika_cache:
            return tika_cache.pop(path)
        # The loop walks paths in order and the queue was built in that order,
        # so the wanted file is at the front. Anything ahead of it was skipped
        # by the loop -- unreadable, or not a file -- and is discarded rather
        # than searched for, which keeps this O(1) per image instead of O(n).
        while tika_pending and tika_pending[0] != path:
            tika_pending.pop(0)
        window = tika_pending[:TIKA_BATCH]
        if not window:
            return tika_metadata(path, tika_app)
        for got, meta in zip(window, tika_metadata_batch(window, tika_app)):
            tika_cache[got] = meta
        del tika_pending[:len(window)]
        return tika_cache.pop(path, {})

    batch = []
    indexed = 0
    failed = 0
    n = len(paths)
    write_progress(0, n, "ocr")
    for i, path in enumerate(paths):
        if not Path(path).is_file():
            print("Missing: %s" % path, file=sys.stderr)
            failed += 1
            write_progress(i + 1, n, "ocr")
            continue
        try:
            text = ocr(path)
        except Exception as exc:  # keep the chunk moving
            print("OCR failed %s: %s" % (path, exc), file=sys.stderr)
            failed += 1
            write_progress(i + 1, n, "ocr")
            continue
        doc = {
            "id": path,
            "ocr_text": text,
            "ocr_model_s": hf_id,
            "sha1sum_s_md": sha1_of(path),
        }
        if args.model == "donut":
            doc["caption"] = text
        if tika_app is not None:
            doc.update(tika_for(path))
        batch.append(doc)
        write_progress(i + 1, n, "ocr")
        if len(batch) >= args.commit_every:
            index_docs(args.solr_url, batch)
            indexed += len(batch)
            print("Posted %d / %d" % (indexed, n))
            batch = []

    if batch:
        index_docs(args.solr_url, batch)
        indexed += len(batch)

    write_progress(n, n, "ocr")
    print("Indexed: %d  Failed: %d" % (indexed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
