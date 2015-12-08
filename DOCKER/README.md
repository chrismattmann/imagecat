
## Building
`docker build -t="continuumio/imagecat" .`

## Starting

After building or pulling: `docker pull continuumio/imagecat`

- `docker run -v /home/ubuntu/imagecat/DOCKER/images:/images -v /home/ubuntu/imagecat/DOCKER//staging:/deploy/data/staging/ -P -t -i continuumio/imagecat`

Additionally you can specify a file other than ```staging/roxy-image-list-jpg-nonzero.txt``` by passing that filepath to the docker run statement:

    docker run -v /home/ubuntu/imagecat/DOCKER/images:/images -v /home/ubuntu/imagecat/DOCKER//staging:/deploy/data/staging/ -P -t -i continuumio/imagecat my-image-list.txt


A running container should result in starting all services: solr, tomcat, oodt, etc.  Last few lines of the running container will also expose 
the hostname/container id

```
Docker Container ID: e622260b8701
/deploy/logs /deploy/resmgr/bin
Watching /deploy/data/staging/roxy-image-list-jpg-nonzero.txt
Setting up watches.
Watches established.
```

With a running docker containter you can now add images to the images dir: `imagecat/DOCKER/images` and update the list `staging/roxy-image-list-jpg-nonzero.txt`. 
Updating the list will automatically result in the `chunker` script being executed

## Ports
docker port <CONTAINER_ID>
```
docker port e622260b8701
8080/tcp -> 0.0.0.0:49457
8081/tcp -> 0.0.0.0:49458
8888/tcp -> 0.0.0.0:49455
8000/tcp -> 0.0.0.0:49456
```

8081 mapping is the solr instance where one can externally view/query.  Port 8000 has a simple webserver running in the logs directory for 
help with debugging a running conatiner.  This should be switched out for logstash or docker's 1.6 logging facilities.
