#!/usr/bin/env bash
# Catalog-wide Tika metadata Jaccard after ImageCat OCR.
# Defaults to $OODT_HOME/imagespace. Skip if missing.
set -euo pipefail

if [ -z "${IMAGE_SPACE_HOME:-}" ] && [ -n "${OODT_HOME:-}" ]; then
  IMAGE_SPACE_HOME=$OODT_HOME/imagespace
fi

if [ -z "${IMAGE_SPACE_HOME:-}" ]; then
  echo "urn:imagecat:IndexMetadataJaccard: IMAGE_SPACE_HOME is unset; skip Jaccard"
  exit 0
fi

if [ ! -d "$IMAGE_SPACE_HOME/server" ]; then
  echo "urn:imagecat:IndexMetadataJaccard: no server at $IMAGE_SPACE_HOME; skip Jaccard"
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

# SolrUrl arrives from workflow policy, which resolves [SOLR_URL] out of
# the environment bin/setenv.sh exports. Every fallback below is worked
# out from SOLR_PORT for the same reason: one port, one set of URLs.
SOLR_URL=${SolrUrl:-${IMAGE_SPACE_SOLR:-http://${SOLR_HOST:-localhost}:${SOLR_PORT:-8983}/solr/imagecat}}
case "$SOLR_URL" in
  *'['[A-Za-z_]*']'*)
    # An unresolved placeholder, not a URL. Posting to it would index
    # nothing while the task still reported success, so stop here.
    echo "index-metadata-jaccard: SolrUrl did not resolve: $SOLR_URL" >&2
    echo "Set SOLR_PORT in bin/setenv.sh, or IMAGE_SPACE_SOLR in this shell." >&2
    exit 1
    ;;
esac
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
