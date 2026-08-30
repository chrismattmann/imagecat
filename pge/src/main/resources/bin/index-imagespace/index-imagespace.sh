#!/usr/bin/env bash
# ImageSpace CLIP/FAISS rebuild after ImageCat ingest.
# No-op unless IMAGE_SPACE_HOME is set to the chrismattmann/image_space checkout.
# Incremental encode of new Solr ids, rewrite FAISS, POST /api/clip/reload.
set -euo pipefail

if [ -z "${IMAGE_SPACE_HOME:-}" ]; then
  echo "urn:memex:IndexImageSpace: IMAGE_SPACE_HOME is unset; skip CLIP rebuild"
  exit 0
fi

if [ ! -d "$IMAGE_SPACE_HOME" ]; then
  echo "urn:memex:IndexImageSpace: IMAGE_SPACE_HOME=$IMAGE_SPACE_HOME is not a directory" >&2
  exit 1
fi

pick_python() {
  if [ -n "${IMAGE_SPACE_PYTHON:-}" ]; then
    echo "$IMAGE_SPACE_PYTHON"
    return
  fi
  if [ -x "$IMAGE_SPACE_HOME/.venv-embed/bin/python" ]; then
    echo "$IMAGE_SPACE_HOME/.venv-embed/bin/python"
    return
  fi
  echo python3
}

SOLR_URL=${SolrUrl:-${IMAGE_SPACE_SOLR:-http://localhost:8983/solr/imagecat}}
RELOAD=${IMAGE_SPACE_RELOAD_URL:-http://127.0.0.1:8090/api/clip/reload}
PY=$(pick_python)

export IMAGE_SPACE_SOLR="$SOLR_URL"
export PYTHONPATH="$IMAGE_SPACE_HOME"
cd "$IMAGE_SPACE_HOME"
echo "IndexImageSpace: incremental CLIP+FAISS from $SOLR_URL using $PY"
"$PY" -m server.embed --incremental --reload-url "$RELOAD"
