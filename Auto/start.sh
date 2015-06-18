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
