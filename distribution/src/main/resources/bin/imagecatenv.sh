# Convenience env for a shell. Prefer bin/setenv.sh (what bin/oodt
# sources). Do not clobber URLs already set there — live ImageCat on a
# box that also runs DRAT uses 9100/9101/9102, not 9000/9001/9002.
HERE=$(cd "$(dirname "$0")/.." && pwd)
if [ -r "$HERE/bin/setenv.sh" ]; then
  # shellcheck disable=SC1091
  . "$HERE/bin/setenv.sh"
fi
export IMAGECAT_HOME=${IMAGECAT_HOME:-$HERE}
export OODT_HOME=${OODT_HOME:-$IMAGECAT_HOME}
export FILEMGR_URL=${FILEMGR_URL:-http://localhost:${FILEMGR_PORT:-9000}}
export WORKFLOW_URL=${WORKFLOW_URL:-http://localhost:${WORKFLOW_PORT:-9001}}
export RESMGR_URL=${RESMGR_URL:-http://localhost:${RESMGR_PORT:-9002}}
export FILEMGR_HOME=${FILEMGR_HOME:-$OODT_HOME/filemgr}
export WORKFLOW_HOME=${WORKFLOW_HOME:-$OODT_HOME/workflow}
export PCS_HOME=${PCS_HOME:-$OODT_HOME/pcs}
export PGE_ROOT=${PGE_ROOT:-$OODT_HOME/pge}
export PATH=${PCS_HOME}/bin:${PATH}
if [ -d "$OODT_HOME/.venv/bin" ]; then
  export PATH=$OODT_HOME/.venv/bin:$PATH
fi
