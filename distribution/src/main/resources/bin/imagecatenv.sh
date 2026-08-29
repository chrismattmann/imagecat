export IMAGECAT_HOME=${IMAGECAT_HOME:-$(cd "$(dirname "$0")/.." && pwd)}
export OODT_HOME=${OODT_HOME:-$IMAGECAT_HOME}
export FILEMGR_URL="http://localhost:9000"
export WORKFLOW_URL="http://localhost:9001"
export RESMGR_URL="http://localhost:9002"
export FILEMGR_HOME=$OODT_HOME/filemgr
export WORKFLOW_HOME=$OODT_HOME/workflow
export PCS_HOME=$OODT_HOME/pcs
export PGE_ROOT=$OODT_HOME/pge
export PATH=${PCS_HOME}/bin:${PATH}
if [ -d "$OODT_HOME/.venv/bin" ]; then
  export PATH=$OODT_HOME/.venv/bin:$PATH
fi
