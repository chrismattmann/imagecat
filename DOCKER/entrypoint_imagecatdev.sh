#!/bin/bash
source $OODT_HOME/bin/imagecatenv.sh
cd $OODT_HOME/bin && ./oodt start
cd $OODT_HOME/tomcat7/bin && ./startup.sh
cd $OODT_HOME/resmgr/bin/ && ./start-memex-stubs
#$OODT_HOME/bin/chunker

echo "Docker Container ID:" $HOSTNAME
pushd $OODT_HOME/logs/
python -m SimpleHTTPServer &

if [ -n "$1" ]; then
    LIST_FILE=$1
else
    LIST_FILE=/deploy/data/staging/roxy-image-list-jpg-nonzero.txt
fi

echo "Watching $LIST_FILE"
while inotifywait -e close_write $LIST_FILE; do $OODT_HOME/bin/chunker $LIST_FILE; done
