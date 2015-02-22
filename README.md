ImageCatalog 
============

This is an [OODT RADIX](https://cwiki.apache.org/confluence/display/OODT/RADiX+Powered+By+OODT)
application that uses [Apache Solr](http://lucene.apache.org/solr/),
[Apache Tika](http://tika.apache.org) and [Apache OODT](http://oodt.apache.org) 
to ingest 10s of millions of files (images,but could be extended to other files) 
in place, and to extract metadtaa and OCR information from those files/images using 
Tika and [Tesseract OCR](https://wiki.apache.org/tika/TikaOCR).

Installation 
============ 
0. mkdir deploy 
1. git clone https://github.com/chrismattmann/imagecat.git 
2. cd imagecat 
3. mvn install 
4. cp -R distribution/target/*.tar.gz deploy 
5. cd deploy && tar xvzf *.tar.gz 
6. edit deploy/bin/env.sh to make sure OODT_HOME is set 
7. cd $OODT_HOME/bin && ./oodt start 
8. cd $OODT_HOME/tomcat7/bin && ./startup.sh 
9. cd $OODT_HOME/resmgr/bin/ && ./start_memex_stubs
10. download roxy-image-list-jpg-nonzero.txt and place it in $OODT_HOME/data/staging 
11. $OODT_HOME/bin/chunker 12. #win

