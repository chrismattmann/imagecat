#!/usr/bin/env python3
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# OCR a chunk file of image paths with HuggingFace TrOCR (printed/scene
# text) or Donut (documents), then POST the text to Solr. Replaces Solr
# Cell + Tesseract. Tika MIME/EXIF stays on the File Manager ingest path.

"""OCR images listed in a chunk file and index the text in Solr."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path


TROCR_MODEL = "microsoft/trocr-base-printed"
DONUT_MODEL = "naver-clova-ix/donut-base"


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


def load_ocr(model_name: str):
    """Return a callable image-path -> text. Heavy imports stay here."""
    from PIL import Image

    name = model_name.lower()
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

    raise SystemExit("Unknown --model %s (use trocr or donut)" % model_name)


def index_docs(solr_url: str, docs: list[dict]) -> None:
    import pysolr

    client = pysolr.Solr(solr_url, always_commit=True, timeout=120)
    client.add(docs)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="OCR a chunk file of images with TrOCR or Donut and post to Solr."
    )
    parser.add_argument("-f", "--chunk-file", required=True, help="text file, one image path per line")
    parser.add_argument("-s", "--solr-url", required=True, help="Solr core URL, e.g. http://localhost:8983/solr/imagecat")
    parser.add_argument(
        "--model",
        default="trocr",
        choices=("trocr", "donut"),
        help="trocr = printed/scene text (default); donut = document understanding",
    )
    parser.add_argument("--commit-every", type=int, default=32, help="Solr batch size")
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

    ocr, hf_id = load_ocr(args.model)
    batch = []
    indexed = 0
    failed = 0
    for path in paths:
        if not Path(path).is_file():
            print("Missing: %s" % path, file=sys.stderr)
            failed += 1
            continue
        try:
            text = ocr(path)
        except Exception as exc:  # keep the chunk moving
            print("OCR failed %s: %s" % (path, exc), file=sys.stderr)
            failed += 1
            continue
        doc = {
            "id": path,
            "ocr_text": text,
            "ocr_model_s": hf_id,
            "sha1sum_s_md": sha1_of(path),
        }
        if args.model == "donut":
            doc["caption"] = text
        batch.append(doc)
        if len(batch) >= args.commit_every:
            index_docs(args.solr_url, batch)
            indexed += len(batch)
            print("Posted %d / %d" % (indexed, len(paths)))
            batch = []

    if batch:
        index_docs(args.solr_url, batch)
        indexed += len(batch)

    print("Indexed: %d  Failed: %d" % (indexed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
