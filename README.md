ImageCatalog 
============

This is an [OODT RADIX](https://cwiki.apache.org/confluence/display/OODT/RADiX+Powered+By+OODT)
application that uses [Apache Solr](http://lucene.apache.org/solr/),
[Apache Tika](http://tika.apache.org) and [Apache OODT](http://oodt.apache.org) 
to ingest 10s of millions of files (images, but could be extended to other files) 
in place, and to extract metadata and OCR information from those files/images using 
Tika and [Tesseract OCR](https://wiki.apache.org/tika/TikaOCR).

Installation 
============ 
0. mkdir deploy 
1. git clone https://github.com/chrismattmann/imagecat.git 
2. cd imagecat 
3. mvn install 
4. cp -R distribution/target/*.tar.gz deploy 
5. cd deploy && tar xvzf *.tar.gz 
6. cp -R ../imagecat/solr4 ./solr4 && cp -R ../imagecat/tomcat7 ./tomcat7
7. edit tomcat7/conf/Catalina/localhost/solr.xml and replace [OODT_HOME] with the path to your deploy dir.
8. edit deploy/bin/env.sh to make sure OODT_HOME is set to the path to your deploy dir.
9. cd $OODT_HOME/bin && ./oodt start 
10. cd $OODT_HOME/tomcat7/bin && ./startup.sh 
11 cd $OODT_HOME/resmgr/bin/ && ./start_memex_stubs
12. download roxy-image-list-jpg-nonzero.txt and place it in $OODT_HOME/data/staging 
13. $OODT_HOME/bin/chunker 
14. #win

Observing what's going on
=========================
ImageCat runs 2 Solr deployments, and a full stack OODT Deployment. 
The URLs are below:

http://localhost:8081/solr/imagecatdev - [Solr4.10.3-fork](https://issues.apache.org/jira/browse/SOLR-7139) Core where SolrCell runs for Image extraction.
http://localhost:8081/solr/imagecatoodt - [Solr4.10.3-fork](https://issues.apache.org/jira/browse/SOLR-7139) Core where OODT's file catalog is, home to ChunkFiles representing a 50k-sized slice of full file paths from the original file list.
http://localhost:8080/opsui/ - [Apache OODT OPSUI](https://cwiki.apache.org/confluence/display/OODT/Quick+Start+for+PCS+OPSUI) cockpit to observe ingestion of ChunkFiles, and jobs for ingesting into SolrCell
http://localhost:8080/pcs/services/health/report - [Apache OODT PCS REST Services](https://cwiki.apache.org/confluence/display/OODT/OODT+REST+Services) showing system health and provenance.

The recommended way to see what's going on is to check the OPSUI, and
then periodically examine $OODT_HOME/data/jobs/crawl/*/logs (where the ingest
into SolrCell jobs are executing). By default ImageCat uses 8 ingest processes
that can run 8 parallel ingests into SolrCell at a time, with 24 jobs on deck
in the Resource Manager waiting to get in.

Each directory in $OODT_HOME/data/jobs/crawl/ is an independent, fully detached
job that can be executed independent of OODT to ingest 50K image files into 
SolrCell and to perform TesesractOCR and EXIF metadata extraction.

Chunk Files
===========

The overall workflow is as follows:

1. OODT starts with the original large file that contains *full file paths*. It
then chunks this file into sizeof(file) / 
$OODT_HOME/workflow/policy/tasks.xml[urn:id:memex:Chunker/ChunkSizer] sized files.

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

Questions, comments?
===================
Send them to [Chris A. Mattmann](mailto:chris.a.mattmann@jpl.nasa.gov).

License
=======
[Apache License, version 2](http://www.apache.org/licenses/LICENSE-2.0)
