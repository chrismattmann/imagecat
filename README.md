ImageCatalog 
============

This is an [OODT RADIX](https://cwiki.apache.org/confluence/display/OODT/RADiX+Powered+By+OODT)
application that uses [Apache Solr](http://lucene.apache.org/solr/),
[Apache Tika](http://tika.apache.org) and [Apache OODT](http://oodt.apache.org) 
to ingest 10s of millions of files (images,but could be extended to other files) 
in place, and to extract metadata and OCR information from those files/images using 
Tika and [Tesseract OCR](https://wiki.apache.org/tika/TikaOCR).

Shell Pre-Requisites
====================
Some programs used by ImageCat require the use of the [/bin/tcsh](https://en.wikipedia.org/wiki/Tcsh)
shell. You can usually install it on Linux via:

1. yum install tcsh; or
2. apt-get install tcsh

Python Pre-Requisites
=====================
1. pip install xmlrpclib (which comes default in python 2.7)
2. pip install solrpy

Other Pre-Requisites
====================
1. Maven 3.x

Useful Environment Variables
============================
The following environment variables are used in ImageCat.

```
setenv JAVA_HOME e.g. `readlink -f /usr/bin/java | sed "s:bin/java::"`
setenv OODT_HOME ~/imagecat
setenv GANGLIA_URL http://zipper.jpl.nasa.gov/ganglia/
setenv FILEMGR_URL http://localhost:9000
setenv WORKFLOW_URL http://localhost:9001
setenv RESMGR_URL http://localhost:9002
setenv WORKFLOW_HOME $OODT_HOME/workflow
setenv FILEMGR_HOME $OODT_HOME/filemgr
setenv PGE_ROOT $OODT_HOME/pge
setenv PCS_HOME $OODT_HOME/pcs
```
Automated Install
=================
1. Navigate to location for imagecat
2. git clone https://github.com/ATZimdars/ImageCatInstall.git
3. cd ImageCatInstall
4. ./booyah.sh
5. Wait for a install to finish
6. Follow Manual installation step #16
7. cd deploy
7. Add directorys for images in data/staging/roxy-image-list-jpg-nonzero.txt
7. ./start.sh 
8. or Manual Setup #17-#19
9. $OODT_HOME/bin/chunker
10. #win


Manual Installation 
===================
1. mkdir deploy 
2. git clone https://github.com/chrismattmann/imagecat.git 
3. cd imagecat 
4. mvn install 
5. cp -R distribution/target/*.tar.gz ../deploy 
6. cd ../deploy && tar xvzf *.tar.gz 
7. cp -R ../imagecat/solr4 ./solr4 && cp -R ../imagecat/tomcat7 ./tomcat7
8. edit tomcat7/conf/Catalina/localhost/solr.xml and replace --OODT_HOME-- with the path to your deploy dir.
9. edit /bin/env.sh and /bin/imagecatenv.sh in your deploy directory to make sure --OODT_HOME-- is set to the path to your deploy dir.
10. /bin/bash && source bin/imagecatenv.sh
11. mkdir tomcat7/logs
12. Copy cas-filemgr-VERSION.jar, cas-workflow-VERSION.jar, cas-crawler-VERSION.jar and cas-pge-VERSION.jar to the resmgr/lib directory. *Grab them from their component directory (i.e. cas-filemgr-VERSION.jar from filemgr/lib/cas-filemgr-VERSION.jar)*
13. Copy solr4/example/lib/*.jar to tomcat/common/lib
14. Copy solr4/example/resources/log4j.properties to tomcat/common/lib
15. cp filemgr/lib/cas-filemgr-VERSION.jar workflow/lib
16. Edit tomcat/common/lib/log4j.properties to read:  
    #  Logging level                                                                                                             solr.log=logs/                                                 
    log4j.rootLogger=INFO, CONSOLE
    log4j.appender.CONSOLE=org.apache.log4j.ConsoleAppender
    log4j.appender.CONSOLE.layout=org.apache.log4j.PatternLayout
    log4j.appender.CONSOLE.layout.ConversionPattern=%-4r [%t] %-5p %c %x \u2013 %m%n
17. cd $OODT_HOME/bin && ./oodt start 
18. cd $OODT_HOME/tomcat7/bin && ./startup.sh 
19. cd $OODT_HOME/resmgr/bin/ && ./start-memex-stubs 
20. download roxy-image-list-jpg-nonzero.txt and place it in $OODT_HOME/data/staging 
21. $OODT_HOME/bin/chunker 
22. #win

Observing what's going on
=========================
ImageCat runs 2 Solr deployments, and a full stack OODT Deployment. 
The URLs are below:

* http://localhost:8081/solr/#/imagecatdev - [Solr4.10.3-fork](https://issues.apache.org/jira/browse/SOLR-7139) Core where SolrCell runs for Image extraction.
* http://localhost:8081/solr/#/imagecatoodt - [Solr4.10.3-fork](https://issues.apache.org/jira/browse/SOLR-7139) Core where OODT's file catalog is, home to ChunkFiles representing a 50k-sized slice of full file paths from the original file list.
* http://localhost:8080/opsui/ - [Apache OODT OPSUI](https://cwiki.apache.org/confluence/display/OODT/Quick+Start+for+PCS+OPSUI) cockpit to observe ingestion of ChunkFiles, and jobs for ingesting into SolrCell
* http://localhost:8080/pcs/services/health/report - [Apache OODT PCS REST Services](https://cwiki.apache.org/confluence/display/OODT/OODT+REST+Services) showing system health and provenance.

The recommended way to see what's going on is to check the OPSUI, and
then periodically examine $OODT_HOME/data/jobs/crawl/*/logs (where the ingest
into SolrCell jobs are executing). By default ImageCat uses 8 ingest processes
that can run 8 parallel ingests into SolrCell at a time, with 24 jobs on deck
in the Resource Manager waiting to get in.

Each directory in $OODT_HOME/data/jobs/crawl/ is an independent, fully detached
job that can be executed independent of OODT to ingest 50K image files into 
SolrCell and to perform TesesractOCR and EXIF metadata extraction.

Note that sometimes images will fail to ingest, e.g., with a message such
as:

```
INFO: on.SolrException: org.apache.tika.exception.TikaException: TIKA-198: Illegal IOException from org.apache.tika.parser.jpeg.JpegParser@5c0bae4a
OUTPUT:         at org.apache.solr.handler.extraction.ExtractingDocumentLoader.load(ExtractingDocumentLoader.java:225)
OUTPUT:         at org.apache.solr.handler.ContentStreamHandlerBase.handleRequestBody(ContentStreamHandlerBase.java:74)
OUTPUT:         at org.apache.solr.handler.RequestHandlerBase.handleRequest(RequestHandlerBase.java:135)
OUTPUT:         at org.apache.solr.core.RequestHandler
Apr 15, 2015 9:18:29 PM org.apache.oodt.commons.io.LoggerOutputStream flush
```

In the Solr Tomcat logs. This is normal, since sometimes the JpegParser will fail 
to parse the image.

Chunk Files
===========

The overall workflow is as follows:

1. OODT starts with the original large file that contains *full file paths*. It
then chunks this file into sizeof(file) / 
$OODT_HOME/workflow/policy/tasks.xml[urn:id:memex:Chunker/ChunkSize] sized files.

2. Each resultant _ChunkFile_ is then ingested into OODT, by the 
OODT crawler, which triggers the OODT workflow manager to process
a job called _IngestInPlace_.

3. Each _IngestInPlace_ job grabs its ingested _ChunkFile_ (stored in
$OODT_HOME/data/archive/chunks/) and then runs it through
$OODT_HOME/bin/solrcell_ingest which sends the 50k full file paths to 
http://localhost:8081/solr/imagecatdev/extract (the 
[ExtractingRequestHandler](https://wiki.apache.org/solr/ExtractingRequestHandler)).

4. 8 IngestInPlace jobs can run at a time.

5. You can watch http://localhost:8081/solr/imagecatdev build up while it's
going on. This will happen sporadically b/c $OODT_HOME/bin/solrcell_ingest
ingests all 50k files in memory, and then sends a commit at the end for
efficiency (resulting in 50k * 8 files every ~30-40 minutes).

Cleaning up and checking any failed ingestions
==============================================
For whatever reason, sometimes ingests fail. For example initially when
I was building ImageCat, I had an error in the solrcell_ingest script
that didn't account for files that had spaces in the directory path
(fixed now). If you find anything happens that makes ingests fail, just
run:

``$OODT_HOME/bin/check_failed`` 

This program will verify all ChunkFiles in Solr and make sure all paths
were ingested into Solr. If any weren't, new ChunkedFiles with the extension
_missing.txt will be created and any remaining files will be ingested.

Questions, comments?
===================
Send them to [Chris A. Mattmann](mailto:chris.a.mattmann@jpl.nasa.gov).

License
=======
[Apache License, version 2](http://www.apache.org/licenses/LICENSE-2.0)
