#!/bin/tcsh
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

export OODT_HOME=`pwd`
echo -- Starting All Required Scripts --
source bin/imagecatenv.sh
cd $OODT_HOME/bin
echo *******Starting OODT*******
./oodt start
cd $OODT_HOME/tomcat7/bin
echo *******Starting Tomcat*******
./startup.sh
cd $OODT_HOME/resmgr/bin
echo ******Starting Memex Stubs******
./start-memex-stubs
exit
echo [DONE]
