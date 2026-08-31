ImageCatalog
============
<img align="left" width="100" height="80" src="https://github.com/chrismattmann/imagecat/raw/master/ImageCat.png">

This is a [RADiX](https://cwiki.apache.org/confluence/display/OODT/RADiX+Powered+By+OODT)
application on [Mnemosyne](https://github.com/chrismattmann/mnemosyne) 1.11.0
that uses [Apache Solr](https://solr.apache.org/) 10,
[Apache Tika](https://tika.apache.org/) and HuggingFace
[TrOCR](https://huggingface.co/microsoft/trocr-base-printed) /
[Donut](https://huggingface.co/naver-clova-ix/donut-base)
to ingest tens of millions of files (images, but it can be extended) in place,
extract MIME/EXIF with Tika, and OCR them into Solr.

OPSUI is the Vue 3 console from Mnemosyne, overlaid at `/opsui/`. Solr runs as
its own process (not a Tomcat war) with two cores: `imagecat` (OCR text) and
`oodt-fm` (File Manager catalog).

[ImageSpace](imagespace/README.md) is the analyst desktop in this same tarball:
search OCR and Tika fields, browse the image grid, CLIP similar, foreground /
background similar (U2-Net / rembg), and IQR (a tiny Keras head fitted at
Refine time on CLIP vectors). `bin/oodt start` brings it up on port 8090
the way it starts Solr — FastAPI, not a WAR. CLIP / fg / bg indexes live
under `$IMAGECAT_HOME/data/imagespace/`. The NASA Girder/SMQTK ImageSpace
is a different tree.

See [docs/WHAT-IS-IN.md](docs/WHAT-IS-IN.md) for keep / throw / replace.

Build
-----

JDK 21, Maven 3.9+, Python 3.10+. Mnemosyne 1.11.0 must be in the local
Maven repo (`mvn install` from a Mnemosyne checkout) or on Maven Central.

```bash
mvn -B package
tar xzf distribution/target/oodt-distribution-0.1-bin.tar.gz
cd <unpacked>
export IMAGECAT_HOME=$PWD
bin/imagecat-setup          # .venv (OCR, CLIP, Keras IQR) + Vue build
bin/oodt start              # File Manager, Workflow, Resource, Tomcat 9, Solr 10, ImageSpace
```

- OPSUI: `http://localhost:8080/opsui/`
- ImageSpace: `http://127.0.0.1:8090/`
- Solr OCR core: `http://localhost:8983/solr/imagecat`
- Solr FM catalog: `http://localhost:8983/solr/oodt-fm`

OCR
---

The IngestInPlace PGE calls `imagecat-ocr.py` over each chunk file.
`--model trocr` (default) is printed/scene text;
`--model donut` is document understanding and also fills `caption`.
Tika runs on each image in that same script (MIME, EXIF, IPTC) so the
`imagecat` Solr core has the metadata Solr Cell used to attach. Tesseract
and Solr Cell are gone. The old `solrcell_ingest` name remains as a shim
onto the same script.

```bash
python3 pge/bin/imagecat-ocr/imagecat-ocr.py \
  -f data/archive/chunks/0/filelist_chunk_0.txt \
  -s http://localhost:8983/solr/imagecat \
  --model trocr
```

ImageSpace
----------

After OCR, the same ingest workflow increments CLIP/FAISS
(`urn:memex:IndexImageSpace`) and foreground/background CLIP
(`urn:memex:IndexImageSpaceFgBg`). The UI at
`http://127.0.0.1:8090/` searches Solr, shows the pictures, and
runs Similar / FG / BG against those indexes. IQR is not a pretrained
model: mark tiles + / − and Refine fits a small Keras head (Torch
backend) on the CLIP vectors you already have.

`bin/imagecat-setup` installs Keras with the rest of the Python env
and builds the Vue UI. Vite on 5173 is optional for UI development.

See the wiki for more on installing and running ImageCat:
* [Installation instructions](https://github.com/chrismattmann/imagecat/wiki/Installation)
* [How to run](https://github.com/chrismattmann/imagecat/wiki/How-to-Run)
* [How to interact with ImageCat](https://github.com/chrismattmann/imagecat/wiki/Interacting-with-ImageCat)

You can clone the wiki by running
`git clone https://github.com/chrismattmann/imagecat.wiki.git`

Questions, comments?
===================
Send them to [Chris A. Mattmann](mailto:chris.a.mattmann@jpl.nasa.gov).

License
=======
[Apache License, version 2](http://www.apache.org/licenses/LICENSE-2.0)
