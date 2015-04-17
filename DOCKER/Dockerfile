FROM continuumio/miniconda

MAINTAINER Benjamin Zaitlen <ben.zaitlen@continuum.io>

RUN apt-get update && \
    apt-get -y upgrade && \
    apt-get -y install git && \
    apt-get -y install tcsh && \
    apt-get -y install inotify-tools && \
    apt-get -y install openjdk-7-jdk curl

RUN pip install solrpy
RUN conda install -c blaze apache-maven
#RUN pip install xmlrpc }

ENV JAVA_HOME=/usr/lib/jvm/java-7-openjdk-amd64
ENV JRE_HOME=/usr/lib/jvm/java-7-openjdk-amd64

RUN mkdir /deploy
RUN git clone https://github.com/chrismattmann/imagecat.git
WORKDIR imagecat
RUN mvn install
RUN cp -R distribution/target/*.tar.gz /deploy

WORKDIR /deploy
RUN tar xvzf *.tar.gz
RUN cp -R ../imagecat/solr4 ./solr4 && cp -R ../imagecat/tomcat7 ./tomcat7
COPY solr.xml /imagecat/master/tomcat7/conf/Catalina/localhost/solr.xml
ENV OODT_HOME /deploy

RUN mkdir -p /deploy/tomcat7/logs
RUN mkdir -p /deploy/tomcat7/temp
RUN mkdir -p /deploy/tomcat/temp

RUN mkdir -p /deploy/pge/extractors/metout
RUN mkdir -p /deploy/pge/extractors/filename

COPY chunkfile_extractor.xml /deploy/pge/extractors/filename/chunkfile_extractor.xml
COPY chunkfile_metout.xml /deploy/pge/extractors/metout/chunkfile_metout.xml

RUN cp /deploy/filemgr/lib/cas-filemgr-*.jar /deploy/workflow/lib/ 
RUN cp /deploy/filemgr/lib/cas-filemgr-*.jar /deploy/resmgr/lib/ 
RUN cp /deploy/filemgr/lib/cas-filemgr-*.jar /deploy/extensions/lib/

COPY imagecatenv.sh /deploy/bin/imagecatenv.sh

COPY solr.xml /deploy/tomcat7/conf/Catalina/localhost/solr.xml

#edit tomcat7/conf/Catalina/localhost/solr.xml and replace [OODT_HOME] with the path to your deploy dir.
#edit deploy/bin/env.sh and deploy/bin/imagecatenv.sh to make sure OODT_HOME is set to the path to your deploy dir.

##download roxy-image-list-jpg-nonzero.txt and place it in $OODT_HOME/data/staging
# in entrypoint
#RUN $OODT_HOME/bin/imagecatenv.sh
#RUN cd $OODT_HOME/bin && ./oodt start
#RUN cd $OODT_HOME/tomcat7/bin && ./startup.sh
#RUN cd $OODT_HOME/resmgr/bin/ && ./start-memex-stubs
#RUN $OODT_HOME/bin/chunker

EXPOSE 8080
EXPOSE 8081
EXPOSE 8888
EXPOSE 8000

COPY entrypoint_imagecatdev.sh /deploy/entrypoint_imagecatdev.sh

ENTRYPOINT ["/deploy/entrypoint_imagecatdev.sh"]
