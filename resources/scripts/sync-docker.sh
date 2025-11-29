#!/bin/bash

while ! nc -z $DB_HOST $DB_PORT; do
  sleep 2
  echo "Waiting postgress...."
done

while ! nc -z redis 6379; do
  sleep 2
  echo "Waiting redis...."
done

python manage.py sync_docker

exit $?
