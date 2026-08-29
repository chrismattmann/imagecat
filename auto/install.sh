#!/bin/bash
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

echo - Starting Install -
echo - Creating Deploy Directory -
mkdir -p ../../deploy
cd ../..
cd imagecat
echo [SUCCESS]
echo - Building via Maven -
mvn -B package
echo [SUCCESS]
echo - Unpacking distribution -
cp -R distribution/target/oodt-distribution-*-bin.tar.gz ../deploy/
cd ../deploy && tar xvzf oodt-distribution-*-bin.tar.gz
export OODT_HOME=`pwd`
export IMAGECAT_HOME=`pwd`
echo [SUCCESS]
echo - Python OCR environment -
if [ -f requirements.txt ]; then
  PYTHON=${PYTHON:-python3} bin/imagecat-setup || echo "imagecat-setup failed; install requirements.txt by hand"
fi
echo [SUCCESS]
echo - Automated Setup Complete -
echo Check docs/WHAT-IS-IN.md for keep / throw / replace
echo OPSUI is at http://localhost:8080/opsui/
echo Solr is at http://localhost:8983/solr/imagecat
