echo - Starting Install -
echo - Creating Deploy Directory -
mkdir ../deploy
cd ..
cd deploy
export OODT_HOME= 'pwd'
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
/bin/bash && source bin/imagecatenv.sh
exit
cp filemgr/lib/cas-filemgr-* resmgr/lib
cp workflow/lib/cas-workflow-* resmgr/lib
cp crawler/lib/cas-crawler-* resmgr/lib
cp pge/lib/cas-pge-* resmgr/lib
cp solr4/example/lib/*.jar tomcat/common/lib
cp solr4/example/resources/log4j.properties tomcat/common/lib
echo - Fixing Extras -
cd tomcat
touch logs
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
mv Startall.sh ../deploy
mv Stopall.sh ../deploy
cd ..
cd deploy
chmod +x Startall.sh
chmod +x Stopall.sh
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
