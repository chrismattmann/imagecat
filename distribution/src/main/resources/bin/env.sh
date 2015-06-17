#!/bin/sh

# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# OS specific support.  $var _must_ be set to either true or false.
cygwin=false
os400=false
darwin=false
case "`uname`" in
CYGWIN*) cygwin=true;;
OS400*) os400=true;;
Darwin*) darwin=true;;
esac

# resolve links - $0 may be a softlink
PRG="$0"

while [ -h "$PRG" ]; do
  ls=`ls -ld "$PRG"`
  link=`expr "$ls" : '.*-> \(.*\)$'`
  if expr "$link" : '/.*' > /dev/null; then
    PRG="$link"
  else
    PRG=`dirname "$PRG"`/"$link"
  fi
done

# Get standard environment variables
PRGDIR=`dirname "$PRG"`

# Only set OODT_HOME if not already set
[ -z "$OODT_HOME" ] && OODT_HOME=`cd "$PRGDIR/.." ; pwd`

export OODT_HOME= a[OODT_HOME]a
# Ensure that any user defined CLASSPATH variables are not used on startup,
# but allow them to be specified in setenv.sh, in rare case when it is needed.
CLASSPATH=

if [ -r "$OODT_BASE"/bin/setenv.sh ]; then
  . "$OODT_BASE"/bin/setenv.sh
elif [ -r "$OODT_HOME"/bin/setenv.sh ]; then
  . "$OODT_HOME"/bin/setenv.sh
fi

# For Cygwin, ensure paths are in UNIX format before anything is touched
if $cygwin; then
  [ -n "$JAVA_HOME" ] && JAVA_HOME=`cygpath --unix "$JAVA_HOME"`
  [ -n "$JRE_HOME" ] && JRE_HOME=`cygpath --unix "$JRE_HOME"`
  [ -n "$OODT_HOME" ] && OODT_HOME=`cygpath --unix "$OODT_HOME"`
  [ -n "$OODT_BASE" ] && OODT_BASE=`cygpath --unix "$OODT_BASE"`
  [ -n "$CLASSPATH" ] && CLASSPATH=`cygpath --path --unix "$CLASSPATH"`
fi

# Get standard Java environment variables
if $os400; then
  # -r will Only work on the os400 if the files are:
  # 1. owned by the user
  # 2. owned by the PRIMARY group of the user
  # this will not work if the user belongs in secondary groups
  BASEDIR="$OODT_HOME"
  . "$OODT_HOME"/bin/setclasspath.sh
else
  if [ -r "$OODT_HOME"/bin/setclasspath.sh ]; then
    BASEDIR="$OODT_HOME"
    . "$OODT_HOME"/bin/setclasspath.sh
  else
    echo "Cannot find $OODT_HOME/bin/setclasspath.sh"
    echo "This file is needed to run this program"
    exit 1
  fi
fi

if [ -z "$OODT_BASE" ]; then
  OODT_BASE="$OODT_HOME"
  export OODT_BASE
fi

if [ -z "$OODT_OUT" ] ; then
  OODT_OUT="$OODT_BASE"/logs/oodt.out
  export OODT_OUT
fi

if [ -z "$FILEMGR_HOME" ]; then
  FILEMGR_HOME="$OODT_HOME"/filemgr
  export FILEMGR_HOME
fi

if [ -z "$WORKFLOW_HOME" ]; then
  WORKFLOW_HOME="$OODT_HOME"/workflow
  export WORKFLOW_HOME
fi

if [ -z "$RESMGR_HOME" ]; then
  RESMGR_HOME="$OODT_HOME"/resmgr
  export RESMGR_HOME
fi

if [ -z "$PCS_HOME" ]; then
  PCS_HOME="$OODT_HOME"/pcs
  export PCS_HOME
fi

if [ -z "$CRAWLER_HOME" ]; then
  CRAWLER_HOME="$OODT_HOME"/crawler
  export CRAWLER_HOME
fi

if [ -z "$PGE_ROOT" ]; then
  PGE_ROOT="$OODT_HOME"/pge
  export PGE_ROOT
fi

if [ -z "$SOLR_HOME" ]; then
  SOLR_HOME="$OODT_HOME"/solr
  export SOLR_HOME
fi

if [ -z "$OODT_TMPDIR" ]; then
  # Define the java.io.tmpdir to use for OODT
  OODT_TMPDIR="$OODT_BASE"/temp
  export OODT_TMPDIR
fi

if [ -z "$FILEMGR_PORT" ]; then
  FILEMGR_PORT=9000
  export FILEMGR_PORT
fi

if [ -z "$CRAWLER_PORT" ]; then
  CRAWLER_PORT=9020
  export CRAWLER_PORT
fi 

if [ -z "$WORKFLOW_PORT" ]; then
  WORKFLOW_PORT=9001
  export WORKFLOW_PORT
fi

if [ -z "$RESMGR_PORT" ]; then
  RESMGR_PORT=9002
  export RESMGR_PORT
fi

if [ -z "$TOMCAT_PORT" ]; then
  TOMCAT_PORT=8080
  export TOMCAT_PORT
fi

if [ -z "$OODT_SERVICES_HOST" ]; then
  OODT_SERVICES_HOST=localhost
  export OODT_SERVICES_HOST
fi

if [ -z "$FILEMGR_URL" ]; then
  FILEMGR_URL=http://"$OODT_SERVICES_HOST":"$FILEMGR_PORT"
  export FILEMGR_URL
fi

if [ -z "$WORKFLOW_URL" ]; then
  WORKFLOW_URL=http://"$OODT_SERVICES_HOST":"$WORKFLOW_PORT"
  export WORKFLOW_URL
fi

if [ -z "$RESMGR_URL" ]; then
  RESMGR_URL=http://"$OODT_SERVICES_HOST":"$RESMGR_PORT"
  export RESMGR_URL
fi

if [ -z "$CRAWLER_URL" ]; then
  CRAWLER_URL=http://"$OODT_SERVICES_HOST":"$CRAWLER_PORT"
  export CRAWLER_URL
fi


# When no TTY is available, don't output to console
have_tty=0
if [ "`tty`" != "not a tty" ]; then
    have_tty=1
fi

# For Cygwin, switch paths to Windows format before running java
if $cygwin; then
  JAVA_HOME=`cygpath --absolute --windows "$JAVA_HOME"`
  JRE_HOME=`cygpath --absolute --windows "$JRE_HOME"`
  OODT_HOME=`cygpath --absolute --windows "$OODT_HOME"`
  OODT_BASE=`cygpath --absolute --windows "$OODT_BASE"`
  OODT_TMPDIR=`cygpath --absolute --windows "$OODT_TMPDIR"`
  CLASSPATH=`cygpath --path --windows "$CLASSPATH"`
  JAVA_ENDORSED_DIRS=`cygpath --path --windows "$JAVA_ENDORSED_DIRS"`
fi
