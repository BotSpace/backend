#!/bin/bash
# =============================================================================
# Kubernetes Event Watcher Script
# =============================================================================
# This script watches Kubernetes pod events.
# Events from ALL nodes are received automatically via K8s API.
# =============================================================================

echo "Starting Kubernetes event watcher..."
echo "Note: Events from ALL nodes are received automatically via K8s API"

python manage.py watch_k8s_events --verbose

exit $?
