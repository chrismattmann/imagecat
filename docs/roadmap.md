# ImageCat / ImageSpace roadmap

ImageCat is the ingest pipeline. ImageSpace is the analyst desktop (now
in this tarball). OPSUI (Mnemosyne) is how we watch the jobs.

The product path is in. Wiki Installation / How to Run match `bin/imagecat-setup`
plus `bin/oodt start` plus ImageSpace on **8090**.

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
| Wiki Installation / How to Run / Interacting | [imagecat wiki](https://github.com/chrismattmann/imagecat/wiki) |

## Live (this box)

- Solr `imagecat` **653** (CTCEU + ice JPGs; PDFs skipped)
- CLIP + fg/bg + IQR **on** at http://127.0.0.1:8090/
- OPSUI http://localhost:8080/opsui/
- W1 `ThreadPoolWorkflowEngineFactory` (do not switch to W2)
- DRAT **9000/9001**; ImageCat FM/WM **9100/9101**
- Mnemosyne #270 is on the live WM (`PGE EXEC` while a PGE runs)

## Next

1. ~~Wiki / How to Run~~ **done**
2. **One clean unpack** — rebuild the tarball and start from it so live is not a pile of overlays
3. **Leave settled-condition unwired** until IngestInPlace is fanned out across chunks; sequential CLIP already waits. A fan-out would want a Solr settle, not FM `ChunkList`
4. **Archive** `chrismattmann/image_space` on GitHub when the README pointer should be official

Not next unless asked: W2, DRAT-in-ImageCat, wiring Mnemosyne #267.

## Parked (not missing product)

- **DRAT `.progress`** — done separately (Claude)
- **Mnemosyne #267 `ProductCountSettledCondition`** — merged, not wired. Pre-condition that waits until an FM product type stops growing. ImageCat’s CLIP catalog is Solr `imagecat`, and today’s workflow is sequential, so this stays off until we fan-out ingest
