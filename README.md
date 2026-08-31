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
bin/imagecat-setup          # pysolr + transformers + torch into .venv
bin/oodt start              # File Manager, Workflow, Resource, Tomcat 9, Solr 10
```

- OPSUI: `http://localhost:8080/opsui/`
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

After ingest, `urn:memex:IndexImageSpace` increments CLIP/FAISS and
`urn:memex:IndexImageSpaceFgBg` increments foreground/background CLIP
(U2-Net / rembg). Both no-op unless `IMAGE_SPACE_HOME` is set on the WM.

```bash
python3 pge/bin/imagecat-ocr/imagecat-ocr.py \
  -f data/archive/chunks/0/filelist_chunk_0.txt \
  -s http://localhost:8983/solr/imagecat \
  --model trocr
```

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
