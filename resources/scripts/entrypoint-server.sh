#!/bin/bash
set -e

python3 manage.py collectstatic --noinput
python3 manage.py migrate --noinput
python3 manage.py set_webhook --url=https://api.botmother.uz/authbot/webhook/

# Watcher restart loop
(
  while true; do
    python manage.py watch_k8s_events --verbose >>/var/log/k8s_watcher.log 2>&1
    echo "Watcher crashed, restarting in 5s..."
    sleep 5
  done
) &
WATCHER_PID=$!

# Gunicorn
gunicorn config.asgi:application \
  -b 0.0.0.0:8000 \
  -k uvicorn.workers.UvicornWorker \
  --workers 4 &
GUNICORN_PID=$!

wait -n $WATCHER_PID $GUNICORN_PID
