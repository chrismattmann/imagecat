ImageCatalog
============

[![Build](https://github.com/chrismattmann/imagecat/actions/workflows/build.yml/badge.svg?branch=master)](https://github.com/chrismattmann/imagecat/actions/workflows/build.yml)
[![Site](https://github.com/chrismattmann/imagecat/actions/workflows/site.yml/badge.svg?branch=master)](https://github.com/chrismattmann/imagecat/actions/workflows/site.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](http://www.apache.org/licenses/LICENSE-2.0)
[![JDK](https://img.shields.io/badge/JDK-21-orange.svg)](https://adoptium.net/)
[![Powered by Mnemosyne](https://img.shields.io/badge/powered%20by-Mnemosyne%201.11.0-6E4B8E.svg)](https://github.com/chrismattmann/mnemosyne)
[![Website](https://img.shields.io/badge/website-chrismattmann.github.io%2Fimagecat-informational.svg)](https://chrismattmann.github.io/imagecat/)
[![Wiki](https://img.shields.io/badge/wiki-github-informational.svg)](https://github.com/chrismattmann/imagecat/wiki)

<img align="left" width="100" height="80" src="https://github.com/chrismattmann/imagecat/raw/master/ImageCat.png">

This is a [RADiX](https://cwiki.apache.org/confluence/display/OODT/RADiX+Powered+By+OODT)
application on [Mnemosyne](https://github.com/chrismattmann/mnemosyne) 1.11.0
that uses [Apache Solr](https://solr.apache.org/) 10,
[Apache Tika](https://tika.apache.org/) and
[PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) via
[RapidOCR](https://github.com/RapidAI/RapidOCR) (Apache 2.0 ONNX; detect then
recognize) to ingest tens of millions of files (images, but it can be
extended) in place, extract MIME/EXIF with Tika, and OCR them into Solr.
HuggingFace [TrOCR](https://huggingface.co/microsoft/trocr-base-printed) and
[Donut](https://huggingface.co/naver-clova-ix/donut-base) remain as `--model`
options.

OPSUI is the Vue 3 console from Mnemosyne, overlaid at `/opsui/`. Solr runs as
its own process (not a Tomcat war) with two cores: `imagecat` (OCR text) and
`oodt-fm` (File Manager catalog).

[ImageSpace](imagespace/README.md) is the analyst desktop in this same tarball:
search OCR and Tika fields, browse the image grid, CLIP similar, foreground /
background similar (U2-Net / rembg), and Lens (a tiny Keras head fitted at
Refine time on CLIP vectors; save by name and apply later). Saved thumbs sit in a tray; hover (or tap) the
× to drop one. `bin/imagecat start` brings it up on port 8090 the way it starts
Solr — FastAPI, not a WAR. `bin/imagecat index <dir> [dir...]` copies
JPGs (nested paths kept), then OCR / Jaccard / CLIP / fg/bg.
`bin/imagecat reset` empties the catalog; staging and lenses stay
unless `--lenses`. CLIP / fg / bg indexes live under
`$IMAGECAT_HOME/data/imagespace/`. This is new work inspired by NASA JPL's
efforts on the DARPA MEMEX program.

See [docs/WHAT-IS-IN.md](docs/WHAT-IS-IN.md) for keep / throw / replace
and [docs/roadmap.md](docs/roadmap.md) for where we are and what is next.

Build
-----

JDK 21, Maven 3.9+, Python 3.10+. Mnemosyne 1.11.0 must be in the local
Maven repo (`mvn install` from a Mnemosyne checkout) or on Maven Central.

```bash
mvn -B package
tar xzf distribution/target/oodt-distribution-0.1-bin.tar.gz
cd <unpacked>
export IMAGECAT_HOME=$PWD
bin/imagecat setup          # .venv (OCR, CLIP, Keras Lens) + Vue build
bin/imagecat start          # File Manager, Workflow, Resource, Tomcat 9, Solr 10, ImageSpace
bin/imagecat index /path/to/jpgs [/more/dirs...]
```

- OPSUI: `http://localhost:8080/opsui/`
- ImageSpace: `http://127.0.0.1:8090/`
- Solr OCR core: `http://localhost:8983/solr/imagecat`
- Solr FM catalog: `http://localhost:8983/solr/oodt-fm`

OCR
---

The IngestInPlace PGE calls `imagecat-ocr.py` over each chunk file.
`--model paddle` (default) is PP-OCR detect-then-recognize: no text boxes
means empty `ocr_text`, not a hallucinated receipt word.
`--model trocr` is a printed line recognizer;
`--model donut` is document understanding and also fills `caption`.
`ocr_text` is Solr field type `text_ocr` (WordDelimiter, preserve original)
so a URL overlay like `emmejihad.wordpress.com` is searchable as `wordpress`.
Tika runs on each image in that same script (MIME, EXIF, IPTC) so the
`imagecat` Solr core has the metadata Solr Cell used to attach. Tesseract
and Solr Cell are gone. The old `solrcell_ingest` name remains as a shim
onto the same script.

```bash
python3 pge/bin/imagecat-ocr/imagecat-ocr.py \
  -f data/archive/chunks/0/filelist_chunk_0.txt \
  -s http://localhost:8983/solr/imagecat \
  --model paddle
```

ImageSpace
----------

After OCR, the same ingest workflow scores Tika metadata Jaccard
(`urn:imagecat:IndexMetadataJaccard`), then CLIP/FAISS
(`urn:imagecat:IndexImageSpace`) and foreground/background CLIP
(`urn:imagecat:IndexImageSpaceFgBg`). The UI at
`http://127.0.0.1:8090/` searches Solr (`ocr_text`, `caption`, copy-field
`text`), shows the pictures, and runs Similar / FG / BG / Keys / Vals
against those indexes. A Lens is not a pretrained model: mark tiles + / −
and Refine fits a small Keras head (Torch backend) on the CLIP vectors
you already have. Save as… keeps that head on disk; Apply scores the
current catalog with it.

`bin/imagecat setup` installs Keras with the rest of the Python env
and builds the Vue UI. Vite on 5173 is optional for UI development.

Visit the site: [chrismattmann.github.io/imagecat](https://chrismattmann.github.io/imagecat/).

See the wiki for more on installing and running ImageCat:
* [Installation instructions](https://github.com/chrismattmann/imagecat/wiki/Installation)
* [How to run](https://github.com/chrismattmann/imagecat/wiki/How-to-Run)
* [Re-running](https://github.com/chrismattmann/imagecat/wiki/Re-running)
* [How to interact with ImageCat](https://github.com/chrismattmann/imagecat/wiki/Interacting-with-ImageCat)

You can clone the wiki by running
`git clone https://github.com/chrismattmann/imagecat.wiki.git`

Questions, comments?
===================
Send them to [Chris A. Mattmann](mailto:chris.a.mattmann@jpl.nasa.gov).

License
=======
[Apache License, version 2](http://www.apache.org/licenses/LICENSE-2.0)
