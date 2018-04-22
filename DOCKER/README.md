
Requirements
============
Docker >= 1.9   
[Docker Compose](https://docs.docker.com/compose/install/)

## Building

    docker build -f Dockerfile -t nasajplmemex/imagecat .

## Starting

You should set the environment variable ```IMAGECAT_IMAGE_PATH``` and the container will start a SimpleHTTPServer on port 9241, for example:

    IMAGECAT_IMAGE_PATH=/path/to/your/images docker-compose up -d

A running container should result in starting all services: solr, tomcat, oodt, etc.  Last few lines of the running container will also expose
the hostname/container id

```
Docker Container ID: e622260b8701
/deploy/logs /deploy/resmgr/bin
Watching /deploy/data/staging/roxy-image-list-jpg-nonzero.txt
Setting up watches.
Watches established.
```

With a running docker container you can now add images to the images dir: `/images` and update the list `staging/roxy-image-list-jpg-nonzero.txt`. Updating the list will automatically result in the `chunker` script being executed. For example:

# Ingesting Images

1. `docker exec -it <CONTAINER ID> bash`
2. `cd /deploy/data/staging && find /images -name "*" -print >> roxy-image-list-jpg-nonzero.txt`

## Ports
You can check which ports are running by executing docker port <CONTAINER_ID>
```
docker port e622260b8701
8080/tcp -> 0.0.0.0:49457
8081/tcp -> 0.0.0.0:49458
8888/tcp -> 0.0.0.0:49455
8000/tcp -> 0.0.0.0:49456
```

8081 mapping is the solr instance where one can externally view/query.  Port 8000 has a simple webserver running in the logs directory for help with debugging a running container.  This should be switched out for logstash or docker's 1.6 logging facilities.
