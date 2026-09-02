# ImageCat / ImageSpace roadmap

ImageCat is the ingest pipeline. ImageSpace is the analyst desktop (now
in this tarball). OPSUI (Mnemosyne) is how we watch the jobs.

The product path is in. Wiki Installation / How to Run match `bin/imagecat-setup`
plus `bin/oodt start` plus ImageSpace on **8090**. Paddle/RapidOCR is the
default OCR. ImageSpace lives in this tarball, not a second GitHub repo.

## Where we started

RADiX ingest (chunk → OCR/Tika → Solr) and OPSUI for jobs. Similarity,
fg/bg, IQR, and “watch it in OPSUI” were missing or bolted on with a
local `IMAGE_SPACE_HOME`. ImageSpace was a second repo.

## Slice / where

| Slice | Where |
| --- | --- |
| CLIP/FAISS ingest hook + thumbs | ImageSpace #1, #2 |
| Field search, FG/BG similar, load-more, clear-X | ImageSpace #3 |
| Concurrent CLIP/FG-BG write lock | ImageSpace #4 |
| EXIF filter chips | ImageSpace #5 |
| `.progress` from CLIP/FG-BG | ImageSpace #6 |
| Card actions stay on the tile | ImageSpace #7 |
| IndexImageSpace + IndexImageSpaceFgBg on IngestInPlace | ImageCat #50–#54 |
| ImageSpace in the ImageCat tarball (`oodt start` → :8090) | ImageCat #55 |
| Keras IQR in the distro; README ImageSpace section | ImageCat #56 |
| MEMEX credit (no second-tree pointer) | ImageCat #57 |
| PGE Peek, progress bar, W1 `PGE EXEC` stamp, wall clock | Mnemosyne #262, #265, #270, #256 |
| Tika metadata Jaccard + Keys/Vals | ImageCat #61, #62 |
| Paddle/RapidOCR default; `text_ocr` URL split | ImageCat #63 |
| Tray × to drop a saved thumb | ImageCat #64 |
| Wiki Installation / How to Run / Interacting | [imagecat wiki](https://github.com/chrismattmann/imagecat/wiki) |

## Next

1. **One clean unpack** — rebuild the tarball and start from it so a live tree is not a pile of overlays
2. **Leave settled-condition unwired** until IngestInPlace is fanned out across chunks; sequential CLIP already waits. A fan-out would want a Solr settle, not FM `ChunkList`

~~Archive `chrismattmann/image_space`~~ **done** (remote deleted; product is `imagespace/` in this repo).

Not next unless asked: W2, DRAT-in-ImageCat, wiring Mnemosyne #267.

## Parked (not missing product)

- **DRAT `.progress`** — done separately (Claude)
- **Mnemosyne #267 `ProductCountSettledCondition`** — merged, not wired. Pre-condition that waits until an FM product type stops growing. ImageCat’s CLIP catalog is Solr `imagecat`, and today’s workflow is sequential, so this stays off until we fan-out ingest
- **W1 only** — `ThreadPoolWorkflowEngineFactory`. Do not switch to W2. If another stack already owns 9000/9001, set `FILEMGR_PORT` / `WORKFLOW_PORT` / `RESMGR_PORT` in `bin/setenv.sh` (git default stays 9000).
