#!/usr/bin/env bash
# Catalog-wide Tika metadata Jaccard after ImageCat OCR.
# Defaults to $OODT_HOME/imagespace. Skip if missing.
set -euo pipefail

if [ -z "${IMAGE_SPACE_HOME:-}" ] && [ -n "${OODT_HOME:-}" ]; then
  IMAGE_SPACE_HOME=$OODT_HOME/imagespace
fi

if [ -z "${IMAGE_SPACE_HOME:-}" ]; then
  echo "urn:memex:IndexMetadataJaccard: IMAGE_SPACE_HOME is unset; skip Jaccard"
  exit 0
fi

if [ ! -d "$IMAGE_SPACE_HOME/server" ]; then
  echo "urn:memex:IndexMetadataJaccard: no server at $IMAGE_SPACE_HOME; skip Jaccard"
  exit 0
fi

pick_python() {
  if [ -n "${IMAGE_SPACE_PYTHON:-}" ]; then
    echo "$IMAGE_SPACE_PYTHON"
    return
  fi
  if [ -x "${OODT_HOME:-}/.venv/bin/python" ]; then
    echo "$OODT_HOME/.venv/bin/python"
    return
  fi
  echo python3
}

SOLR_URL=${SolrUrl:-${IMAGE_SPACE_SOLR:-http://localhost:8983/solr/imagecat}}
RELOAD=${IMAGE_SPACE_META_RELOAD_URL:-http://127.0.0.1:8090/api/meta/reload}
PY=$(pick_python)

export IMAGE_SPACE_SOLR="$SOLR_URL"
export PYTHONPATH="$IMAGE_SPACE_HOME"
if [ -n "${OODT_HOME:-}" ]; then
  export IMAGE_SPACE_DATA="${IMAGE_SPACE_DATA:-$OODT_HOME/data/imagespace}"
fi
export PGE_PROGRESS_DIR="${PGE_PROGRESS_DIR:-$PWD}"
cd "$IMAGE_SPACE_HOME"
echo "IndexMetadataJaccard: golden-set Jaccard on $SOLR_URL using $PY"
"$PY" -m server.meta --reload-url "$RELOAD"
