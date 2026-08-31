# ImageCat ingest rebuilds CLIP and fg/bg

After IngestInPlace writes OCR/Tika into Solr `imagecat`, ImageCat runs:

1. `urn:memex:IndexImageSpace` (`pge/bin/index-imagespace/index-imagespace.sh`)
   — `python -m server.embed --incremental`
2. `urn:memex:IndexImageSpaceFgBg` (`pge/bin/index-imagespace-fgbg/index-imagespace-fgbg.sh`)
   — `python -m server.embed_fgbg --incremental`

`bin/setenv.sh` sets `IMAGE_SPACE_HOME=$OODT_HOME/imagespace`. Optional
`IMAGE_SPACE_PYTHON` points at `$OODT_HOME/.venv/bin/python`. Then they
POST `/api/clip/reload`.

`--incremental` only encodes Solr ids not already in the index (`data/clip/ids.json`,
or `data/fg` / `data/bg` for the split). It concatenates the new CLIP rows,
L2-normalizes, and **rewrites** FAISS (`index.faiss`: FlatIP until 10k vectors,
then HNSW). Do not full-rebuild 50k images on every chunk. Fg/bg needs `rembg`
(U2-Net). `POST /api/clip/reload` picks up the new indexes without restarting
uvicorn.

Solr itself is fine with several IngestInPlace writers at once. The CLIP
and fg/bg indexes are not: they rewrite `ids.json`, `vectors.npy`, and
`index.faiss` as one snapshot. Concurrent `--incremental` jobs take an
exclusive lock per index directory (`data/clip/.write.lock`,
`data/fg/.write.lock`) so the second waits, then only encodes ids still
missing. CLIP and fg/bg use different locks, so those two tasks can still
overlap.

Manual:

```bash
IMAGE_SPACE_PYTHON=.venv-embed/bin/python bin/rebuild-clip
PYTHONPATH=. .venv-embed/bin/python -m server.embed_fgbg --incremental
```
