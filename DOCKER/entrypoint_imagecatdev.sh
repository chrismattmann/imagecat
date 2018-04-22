#!/bin/bash
cd $OODT_HOME
./start.sh
source $OODT_HOME/bin/imagecatenv.sh

echo "Docker Container ID:" $HOSTNAME
pushd $OODT_HOME/logs/
python -m SimpleHTTPServer &

if [ -n "$1" ]; then
    LIST_FILE=$1
else
    LIST_FILE=/deploy/data/staging/roxy-image-list-jpg-nonzero.txt
fi

if [ -n /images ] && [ -d /images ]; then
    pushd /images
    python -m SimpleHTTPServer 9241 &
fi

$OODT_HOME/bin/chunker
INITIAL_CHUNK=$?

if [ $INITIAL_CHUNK -eq 0 ]; then
    echo "Watching $LIST_FILE"
    while inotifywait -e close_write $LIST_FILE; do $OODT_HOME/bin/chunker $LIST_FILE; done
else
    echo "Failed to run chunker"
    exit 1
fi
