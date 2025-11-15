#!/bin/bash

while ! nc -z $DB_HOST $DB_PORT; do
  sleep 2
  echo "Waiting postgress...."
done

while ! nc -z redis 6379; do
  sleep 2
  echo "Waiting redis...."
done
python3 manage.py collectstatic --noinput
python3 manage.py migrate --noinput
python3 manage.py set_webhook --url=https://botmother.uz/authbot/webhook/

celery -A config worker -l info &
python manage.py sync_docker &

gunicorn config.asgi:application -b 0.0.0.0:8000 -k uvicorn.workers.UvicornWorker --workers 4 # $(($(nproc) * 2 + 1))

exit $?
