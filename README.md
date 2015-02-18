 Licensed to the Apache Software Foundation (ASF) under one or more
 contributor license agreements. See the NOTICE file distributed with
 this work for additional information regarding copyright ownership.
 The ASF licenses this file to You under the Apache License, Version 2.0
 (the "License"); you may not use this file except in compliance with
 the License. You may obtain a copy of the License at

 http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.

     OODT RADiX README

    Description:
       This project is meant as template to support faster
       data system deployment. Configurable OODT deployments
       are possible using Maven profiles (see below).
       
       OODT version 0.7-SNAPSHOT 

REQUIREMENTS:
* Java Development Kit (JDK) 1.6+
* JAVA_HOME set 
  see: http://docs.oracle.com/cd/E19182-01/820-7851/inst_cli_jdk_javahome_t/index.html
* (Snapshot releases only) OODT source tree installed. 
  see: http://oodt.apache.org/components/maven/filemgr/user/basic.html

INSTALLATION:
  # build oodt
  $ mvn clean package <OPTIONAL PROFILES> # see optional build profiles below

  # deploy oodt
  $ tar zxf distribution/target/${PROJECT_ARTIFACT_ID}-distribution-*-bin.tar.gz -C /my/deployment/directory/oodt
  
  ---
  NOTE: For other build configurations, add the following arguments:
  (default)           : bin, crawler, data, extensions,
                        filemgr (Lucene), logs, pcs, resmgr,
                        tomcat, workflow, pge

  -Pfm-solr-catalog   : default components, filemgr (Solr),
                        solr, tomcat/webapps/solr

RUN:
  $ cd /my/deployment/directory/oodt
  $ cd bin
  $ ./oodt start
