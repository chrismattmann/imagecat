#!/usr/bin/env bash
# FLAG: ImageSpace CLIP rebuild after ImageCat ingest.
# No-op unless IMAGE_SPACE_HOME is set to the chrismattmann/image_space checkout.
# Incremental encode of new Solr ids, then POST /api/clip/reload.
set -euo pipefail

if [ -z "${IMAGE_SPACE_HOME:-}" ]; then
  echo "FLAG urn:memex:IndexImageSpace: IMAGE_SPACE_HOME is unset; skip CLIP rebuild"
  exit 0
fi

SOLR_URL=${SolrUrl:-${IMAGE_SPACE_SOLR:-http://localhost:8983/solr/imagecat}}
RELOAD=${IMAGE_SPACE_RELOAD_URL:-http://127.0.0.1:8090/api/clip/reload}
PY=${IMAGE_SPACE_PYTHON:-python3}

export IMAGE_SPACE_SOLR="$SOLR_URL"
export PYTHONPATH="$IMAGE_SPACE_HOME"
cd "$IMAGE_SPACE_HOME"
echo "IndexImageSpace: incremental CLIP from $SOLR_URL"
"$PY" -m server.embed --incremental --reload-url "$RELOAD"
