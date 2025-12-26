#!/bin/bash

python3 manage.py collectstatic --noinput
python3 manage.py migrate --noinput
python3 manage.py set_webhook --url=https://api.botmother.uz/authbot/webhook/

python manage.py watch_k8s_events --verbose &
gunicorn config.asgi:application -b 0.0.0.0:8000 -k uvicorn.workers.UvicornWorker --workers 4 # $(($(nproc) * 2 + 1))

exit $?
