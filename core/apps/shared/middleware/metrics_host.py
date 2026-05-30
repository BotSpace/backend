"""Bypass Django's ALLOWED_HOSTS for the /metrics/ endpoint.

The kube-prometheus-stack Prometheus scrapes each pod by its cluster
IP (e.g. http://10.42.0.146:8000/metrics/), so the Host header is the
pod IP. Adding every possible pod IP to ALLOWED_HOSTS is impractical
(IPs change on restart). Adding "*" would weaken security globally.

This middleware short-circuits the host check ONLY for the /metrics/
path: when Django would normally raise DisallowedHost it appends the
incoming host to settings.ALLOWED_HOSTS for the lifetime of the
process. The metrics endpoint exposes no sensitive data — only counter
values — so a relaxed host check there is acceptable.

Place this middleware ABOVE django.middleware.common.CommonMiddleware
so it intercepts the host validation before it runs.
"""

from __future__ import annotations

from django.conf import settings


class AllowMetricsHostMiddleware:
    METRICS_PATH = "/metrics/"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == self.METRICS_PATH or request.path.startswith(self.METRICS_PATH):
            host = request.get_host().split(":", 1)[0]
            if host and host not in settings.ALLOWED_HOSTS:
                settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + [host]
        return self.get_response(request)
