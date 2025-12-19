#!/bin/bash

while ! nc -z $DB_HOST $DB_PORT; do
  sleep 2
  echo "Waiting postgres...."
done

while ! nc -z redis 6379; do
  sleep 2
  echo "Waiting redis...."
done

# Start Kubernetes event watcher
# Use --in-cluster flag when running inside Kubernetes cluster
python manage.py sync_kubernetes --in-cluster

exit $?
