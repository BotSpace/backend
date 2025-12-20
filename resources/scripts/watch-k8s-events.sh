#!/bin/bash
# =============================================================================
# Kubernetes Event Watcher Script
# =============================================================================
# This script watches Kubernetes pod events.
# Events from ALL nodes are received automatically via K8s API.
# =============================================================================

while ! nc -z $DB_HOST $DB_PORT; do
  sleep 2
  echo "Waiting for PostgreSQL..."
done

while ! nc -z redis 6379; do
  sleep 2
  echo "Waiting for Redis..."
done

echo "Starting Kubernetes event watcher..."
echo "Note: Events from ALL nodes are received automatically via K8s API"

python manage.py watch_k8s_events --verbose

exit $?
