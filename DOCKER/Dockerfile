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

RUN find /deploy -type f -exec sed -i 's|--OODT_HOME--|/deploy|g' {} \+

EXPOSE 8080
EXPOSE 8081
EXPOSE 8888
EXPOSE 8000

COPY entrypoint_imagecatdev.sh /deploy/entrypoint_imagecatdev.sh

ENTRYPOINT ["/deploy/entrypoint_imagecatdev.sh"]
