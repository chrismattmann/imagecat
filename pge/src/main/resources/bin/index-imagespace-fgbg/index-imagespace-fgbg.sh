#!/usr/bin/env bash
# Incremental CLIP foreground/background indexes after ImageCat ingest.
# No-op unless IMAGE_SPACE_HOME is set. Needs rembg in the embed venv.
set -euo pipefail

if [ -z "${IMAGE_SPACE_HOME:-}" ]; then
  echo "urn:memex:IndexImageSpaceFgBg: IMAGE_SPACE_HOME is unset; skip fg/bg CLIP"
  exit 0
fi

if [ ! -d "$IMAGE_SPACE_HOME" ]; then
  echo "urn:memex:IndexImageSpaceFgBg: IMAGE_SPACE_HOME=$IMAGE_SPACE_HOME is not a directory" >&2
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
echo "IndexImageSpaceFgBg: incremental fg/bg CLIP from $SOLR_URL using $PY"
"$PY" -m server.embed_fgbg --incremental --reload-url "$RELOAD"
