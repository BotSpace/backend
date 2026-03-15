from rest_framework.throttling import SimpleRateThrottle


def _get_client_ip(request):
    ip = request.META.get("HTTP_X_FORWARDED_FOR")
    if ip:
        return ip.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


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
        ip = _get_client_ip(request)
        if not ip:
            return None
        return f"throttle_debug_{ip}"


class ReleaseCreateThrottle(SimpleRateThrottle):
    scope = "release_create"

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            return f"throttle_release_{request.user.pk}"
        ip = _get_client_ip(request)
        if not ip:
            return None
        return f"throttle_release_ip_{ip}"
