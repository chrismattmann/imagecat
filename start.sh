export OODT_HOME='pwd'
echo -- Starting All Required Scripts --
/bin/bash/
source bin/imagecatenv.sh
cd $OODT_HOME/bin
./oodt start
cd $OODT_HOME/tomcat7/bin
./startup.sh
cd $OODT_HOME/resmgr/bin
./start-memex-stubs
exit
echo [DONE]
