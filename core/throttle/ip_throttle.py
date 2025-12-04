import logging
from rest_framework.throttling import SimpleRateThrottle


class IPThrottle(SimpleRateThrottle):
    scope = "ip"

    def get_cache_key(self, request, view):
        ip = request.META.get("REMOTE_ADDR")
        if not ip:
            return None
        return f"throttle_ip_{ip}"


class DebugContainerThrottle(SimpleRateThrottle):
    scope = "debug_container"

    def get_cache_key(self, request, view):
        ip = request.META.get("REMOTE_ADDR")
        logging.info("debug reload new client: %s", ip)
        if not ip:
            return None
        return f"throttle_ip_{ip}"
