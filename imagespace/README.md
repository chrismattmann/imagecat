# ImageSpace (inside ImageCat)

Analyst desktop for this RADiX stack: Solr search (`ocr_text` / `text_ocr`,
caption, Tika), CLIP similar, fg/bg, metadata Jaccard (Keys / Vals), IQR,
and a tray of saved thumbs (hover × to drop). Packed into the ImageCat
tarball and started by `bin/oodt start` (FastAPI on port 8090, same idea
as Solr).

CLIP / fg / bg files live under `$OODT_HOME/data/imagespace/`, not in git.

```bash
bin/imagecat-setup    # .venv + Vue build
bin/oodt start        # includes ImageSpace
# UI: http://127.0.0.1:8090/
```

Vite on 5173 is optional for UI development (`cd imagespace/web && npm run dev`).
The ingest PGEs (`urn:imagecat:IndexMetadataJaccard`, `IndexImageSpace`,
`IndexImageSpaceFgBg`) use `IMAGE_SPACE_HOME=$OODT_HOME/imagespace`
from `bin/setenv.sh`.
