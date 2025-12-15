file=/tmp/db-$(/usr/bin/date +\%Y-%m-%d-%H:%M:%S).sql
service=botmother_db
/usr/bin/docker container exec $(docker ps -f name=$service) pg_dump -U postgres django >$file
mc cp $file b2/botmother_db
rm $file

