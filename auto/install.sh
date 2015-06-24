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
mkdir ../../deploy
cd ..
cd ..
cd deploy
export OODT_HOME=`pwd`
cd ..
cd imagecat
echo [SUCCESS]
echo - Building via Maven -
mvn install
echo [SUCCESS]
echo - Copying Files and Changing Paths -
cp -R distribution/target/*.tar.gz ../deploy
cd ../deploy && tar xvzf *.tar.gz
cp -R ../imagecat/solr4 ./solr4 && cp -R ../imagecat/tomcat7 ./tomcat7
sed -i "" s?--OODT_HOME--?${OODT_HOME}? tomcat7/conf/Catalina/localhost/solr.xml
sed -i "" s?--OODT_HOME--?${OODT_HOME}? bin/env.sh
sed -i "" s?--OODT_HOME--?${OODT_HOME}? bin/imagecatenv.sh
source bin/imagecatenv.sh
cp filemgr/lib/cas-filemgr-* resmgr/lib
cp workflow/lib/cas-workflow-* resmgr/lib
cp crawler/lib/cas-crawler-* resmgr/lib
cp pge/lib/cas-pge-* resmgr/lib
cp solr4/example/lib/*.jar tomcat/common/lib
cp solr4/example/resources/log4j.properties tomcat/common/lib
echo - Fixing Extras -
cd tomcat7
mkdir logs
cd logs
touch catalina.out
cd ..
cd ..
cp filemgr/lib/cas-filemgr-* workflow/lib
echo [SUCCESS]
echo - Downloading Roxy... -
cd data/staging
touch roxy-image-list-jpg-nonzero.txt
cd ..
cd ..
echo [SUCCESS]
echo - Moving Global Start/Stop Commands -
cd ..
cd imagecat
cd Auto
mv start.sh ../../deploy
mv stop.sh ../../deploy
cd ..
cd ..
cd deploy
chmod +x start.sh
chmod +x stop.sh
echo [SUCCESS]
echo - Automated Setup Complete -
echo Booyah!
echo Check on website for final edits
echo Loading final file for user input using vi...
echo 3
sleep 2
echo 2
sleep 2
echo 1
sleep 2
vi tomcat/common/lib/log4j.properties
