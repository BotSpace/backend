file=/tmp/db-$(/usr/bin/date +\%Y-%m-%d-%H:%M:%S).sql
service=botmother_postgres
container=$(docker ps -f name=$service -q)
/usr/bin/docker container exec $container pg_dump -Fc -U postgres django >$file
mc cp $file b2/botmotherdb
rm $file
