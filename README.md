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
2. Tesseract - use this [guide](http://wiki.apache.org/tika/TikaOCR)

Useful Environment Variables
============================
The following environment variables are used in ImageCat. Set them in ~/.tcshrc

```
setenv JAVA_HOME `readlink -f /usr/bin/java | sed "s:bin/java::"`
setenv OODT_HOME ~/path_to_deploy_directory 
setenv GANGLIA_URL http://zipper.jpl.nasa.gov/ganglia/
setenv FILEMGR_URL http://localhost:9000
setenv WORKFLOW_URL http://localhost:9001
setenv RESMGR_URL http://localhost:9002
setenv WORKFLOW_HOME $OODT_HOME/workflow
setenv FILEMGR_HOME $OODT_HOME/filemgr
setenv PGE_ROOT $OODT_HOME/pge
setenv PCS_HOME $OODT_HOME/pcs
```

Or, if you're using bash, set `~/.bash_profile` (Mac) or `~/.bashrc`, or with zsh, `~/.zshrc`:

```
export OODT_HOME=~/path_to_deploy_directory 
export FILEMGR_URL="http://localhost:9000"
export WORKFLOW_URL="http://localhost:9001"
export RESMGR_URL="http://localhost:9002"
```

*NOTE* 
- Mac OS X users may need to use a different value for JAVA_HOME because the Java installation that is found by the above command does not necessarily contain the bin/java folder layout.  If that's the case, then try a path along the lines of: (your jdk version may vary)
```
setenv JAVA_HOME /Library/Java/JavaVirtualMachines/jdk1.8.0_51.jdk/Contents/Home
```
- Please ensure that `OODT_HOME`, `FILEMGR_URL`, `WORKFLOW_URL`, `RESMGR_URL` are all set to the above values without fail.


Automated Install
=================
1. Navigate to desired location for imagecat
2. `git clone https://github.com/chrismattmann/imagecat.git`
3. `cd imagecat`
4. `cd auto`
5. `chmod +x install.sh`
6. `./install.sh` and wait for a install to finish
7. `cd ../../deploy`
8. Add the absolute paths of all images (one image path per line) in data/staging/roxy-image-list-jpg-nonzero.txt
9. `./start.sh`
10. `./bin/chunker`
11. #win

Docker Install
==============
1. See [Dockerfile](https://github.com/chrismattmann/imagecat/blob/master/DOCKER/Dockerfile) and instructions [here](https://github.com/chrismattmann/imagecat/blob/master/DOCKER/README.md).

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
