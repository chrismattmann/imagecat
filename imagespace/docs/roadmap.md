# ImageSpace / ImageCat roadmap

ImageSpace is the analyst desktop. ImageCat is the ingest pipeline that
fills Solr and rebuilds CLIP / fg / bg. OPSUI (Mnemosyne) is how we watch
the jobs.

The product path is in: search, CLIP similar, fg/bg similar, IQR, ingest
hook, and progress in OPSUI. What follows is the slice map and what is
parked on purpose.

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
| PGE Peek, progress bar, W1 `PGE EXEC` stamp, wall clock | Mnemosyne #262, #265, #270, #256 |

## Live (this checkout)

- Solr `imagecat`, CLIP, fg, and bg indexes: last full re-ingest **666** docs
- ImageCat stays on W1 `ThreadPoolWorkflowEngineFactory` (do not switch to W2)
- ImageSpace UI in the distro is FastAPI at **http://127.0.0.1:8090/** (`bin/oodt start`). Vite at **5173** is optional for UI development.
- DRAT stays on **9000/9001**; ImageCat FM/WM are **9100/9101**

## Parked (not missing ImageSpace features)

- **DRAT `.progress`** — done separately (Claude)
- **Mnemosyne #267 `ProductCountSettledCondition`** — merged, not wired into ImageCat. A pre-condition on `IndexImageSpace` / `IndexImageSpaceFgBg` that waits until a File Manager product type stops growing. Useful if IngestInPlace is fanned out across chunks and CLIP should not start until the catalog is stable. Today's dynWorkflow is already sequential, and ImageCat's growing catalog for CLIP is Solr `imagecat`, not FM `ChunkList` products, so this stays unwired unless we fan-out ingest.
- **Mnemosyne #270** — merged; redeploy onto the live ImageCat WM so OPSUI can show `PGE EXEC` instead of `STARTED` while a PGE runs
