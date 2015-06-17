export OODT_HOME= your/deploy/path/
echo - Starting Install -
echo - Creating Deploy Directory -
mkdir ../deploy
echo [SUCCESS]
echo - Building via Maven -
mvn install
echo [SUCCESS]
echo - Copying Files and Changing Paths -
cp -R distribution/target/*.tar.gz ../deploy
cd ../deploy && tar xvzf *.tar.gz
sed -i "" s?--OODT_HOME--?${OODT_HOME}? tomcat7/conf/Catalina/localhost/solr.xml
sed -i "" s?--OODT_HOME--?${OODT_HOME}? bin/env.sh
sed -i "" s?--OODT_HOME--?${OODT_HOME}? bin/imagecatenv.sh
/bin/bash && source bin/imagecatenv.sh
cp -R ../imagecat/solr4 ./solr4 && cp -R ../imagecat/tomcat7 ./tomcat7
cp filemgr/lib/cas-filemgr-* resmgr/lib
cp workflow/lib/cas-workflow-* resmgr/lib
cp crawler/lib/cas-crawler-* resmgr/lib
cp pge/lib/cas-pge-* resmgr/lib
cp solr4/example/lib/*.jar tomcat/common/lib
cp solr4/example/resources/log4j.properties tomcat/common/lib
echo [SUCCESS]
echo - Downloading Roxy... -
cd data/staging
touch roxy-image-list-jpg-nonzero.txt
cd ..
cd ..
echo [SUCCESS]
echo - Automated Setup Complete -
echo Booyah!
