# ImageCat: what is in, what is out

ImageCat is a RADiX overlay on [Mnemosyne](https://github.com/chrismattmann/mnemosyne) 1.11.0.
The pipeline is unchanged in shape: chunk a file list, ingest-in-place, OCR
into Solr, File Manager catalogs the files. The stack under it is new.

## Keep

- RADiX layout (filemgr, workflow, resmgr, crawler, pge, pcs, distribution)
- Chunker → Ingest-in-place → Solr
- File Manager catalog (Solr core `oodt-fm`)
- Tika MIME / EXIF on the Solr `imagecat` core (`imagecat-ocr.py`), the same place Solr Cell used to put it. File Manager catalogs ChunkList path files, not the images.
- FLAG: after IngestInPlace, metadata Jaccard, ImageSpace CLIP/FAISS, and fg/bg are incremented (`urn:imagecat:IndexMetadataJaccard`, `urn:imagecat:IndexImageSpace`, `urn:imagecat:IndexImageSpaceFgBg`).
- Vue OPSUI overlay of `ai.mattmann.mnemosyne:pcs-opsui`
- ImageSpace analyst UI in this repo (`imagespace/`), started by `bin/oodt start` on port 8090. Indexes under `$OODT_HOME/data/imagespace/`. Inspired by NASA JPL's work on the DARPA MEMEX program.

## Throw out

- Apache OODT 0.9 / Java 1.6
- XML-RPC (File Manager, Workflow Manager, Resource Manager, crawler, batch stub)
- Vendored Solr 4 (`solr4/`)
- Vendored Tomcat 7 (`tomcat7/`)
- Wicket OPSUI (skins, Ganglia, `opsui.skin`)
- Python 2.7
- Tesseract (via Tika OCR / Solr Cell)
- Show-and-Tell captions (`add-captions.py`)
- Docker-as-install (`DOCKER/`)
- `download.java.net` Maven repository
- Curator
- Solr-in-Tomcat WAR (`webapps/solr-webapp`)

## Replace now

| Was | Is |
| --- | --- |
| OODT 0.9 XML-RPC | Mnemosyne 1.11.0 Avro (`ai.mattmann.mnemosyne`) |
| Java 1.6 | Java 8 source, run on JDK 21 |
| Wicket OPSUI | Vue 3 OPSUI from Mnemosyne (`pcs-opsui` WAR overlay) |
| Solr 4.10 + Solr Cell `/update/extract` | Solr 10, cores `imagecat` and `oodt-fm`, JSON `/update` |
| Tomcat 7 | Tomcat 9.0.7 (OPSUI / pcs-services / fmprod only) |
| Tesseract | Paddle/RapidOCR PP-OCR (`--model paddle`, default) via `pge/bin/imagecat-ocr/imagecat-ocr.py`; TrOCR and Donut remain as options |
| `solrcell_ingest` curl loop | same name, now a shim onto `imagecat-ocr.py` |
| `python2.7` shebangs and `print` / `long()` | Python 3 |

## Replace later

- Columbia / Georgetown / weapons / VideoSpace (not v1)

SMQTK / FLANN / Caffe, Girder ImageSpace, and the NASA `image_space` tree
are gone: CLIP + rembg + Keras Lens in this tarball is the replacement.
SCE domain discovery stays public for Sparkler. Sparkler itself lives at
[gitlab.com/sparkler-crawl-environment/sparkler](https://gitlab.com/sparkler-crawl-environment/sparkler).
