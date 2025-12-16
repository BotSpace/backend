file=/tmp/db-$(/usr/bin/date +\%Y-%m-%d-%H:%M:%S).sql
service=botmother_db
container=$(docker ps -f name=service -q)
/usr/bin/docker container exec $container pg_dump -U postgres django >$file
mc cp $file b2/botmother_db
rm $file
