# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements. See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
########  setenv.sh ########
#
# Set project specific configuration in setenv.sh
#
# Example:
# 		- Change filemgr URL to http://locatlhost:1234
#			FILEMGR_URL=http://locatlhost:1234
#
#		- Set custom job directory
#			PROJECT_JOB_DIR=/usr/local/project/data/jobs
#
############################

export IMAGECAT_HOME=${IMAGECAT_HOME:-/usr/local/imagecat}
export FILEMGR_URL=http://localhost:9000
export WORKFLOW_URL=http://localhost:9001
export RESMGR_URL=http://localhost:9002
export FILEMGR_HOME=$IMAGECAT_HOME/filemgr
export PGE_HOME=$IMAGECAT_HOME/pge
export PGE_ROOT=$IMAGECAT_HOME/pge
export PCS_HOME=$IMAGECAT_HOME/pcs
export FMPROD_HOME=$IMAGECAT_HOME/tomcat/webapps/fmprod/WEB-INF/classes/

# ImageSpace lives in this tarball. CLIP/fg/bg ingest hooks use these.
export IMAGE_SPACE_HOME=$IMAGECAT_HOME/imagespace
export IMAGE_SPACE_DATA=$IMAGECAT_HOME/data/imagespace
export IMAGE_SPACE_SOLR=http://localhost:8983/solr/imagecat
export IMAGESPACE_PORT=8090
if [ -x "$IMAGECAT_HOME/.venv/bin/python" ]; then
  export IMAGE_SPACE_PYTHON=$IMAGECAT_HOME/.venv/bin/python
fi
# Lens Keras 3 uses Torch, already installed for CLIP.
export KERAS_BACKEND=${KERAS_BACKEND:-torch}

# Bound every Avro client call (Mnemosyne #197). Ten minutes is the code
# default; 0 waits forever. JDK_JAVA_OPTIONS reaches File Manager, Workflow
# Manager, Resource Manager, and Tomcat.
AVRO_CLIENT_TIMEOUT_MS=${AVRO_CLIENT_TIMEOUT_MS:-600000}
export JDK_JAVA_OPTIONS="${JDK_JAVA_OPTIONS:+$JDK_JAVA_OPTIONS }-Dorg.apache.oodt.avro.client.requestTimeoutMillis=${AVRO_CLIENT_TIMEOUT_MS}"
