#!/bin/bash

while ! nc -z db 5432; do
  sleep 2
  echo "Waiting postgress...."
done

python3 manage.py collectstatic --noinput
python3 manage.py migrate --noinput

python3 manage.py authbot &
gunicorn config.asgi:application -b 0.0.0.0:8000 -k uvicorn.workers.UvicornWorker --workers 4 # $(($(nproc) * 2 + 1))


exit $?


