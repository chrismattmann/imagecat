echo -- Stopping All Scripts --
cd $OODT_HOME/bin
./oodt stop
cd $OODT_HOME/tomcat7/bin
./shutdown.sh
killall java
ps -aef | grep java
echo [DONE]
