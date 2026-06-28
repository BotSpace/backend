from rest_framework.throttling import SimpleRateThrottle


# Eslatma: client IP'ni qo'lda HTTP_X_FORWARDED_FOR[0] dan olish XAVFLI edi —
# chap tomondagi qiymatni client o'zi yuboradi (spoof). Buning o'rniga DRF'ning
# `self.get_ident(request)` ishlatamiz: u NUM_PROXIES (=1) bo'yicha XFF'ning eng
# o'ngdagi, ishonchli proxy (host nginx) qo'ygan qiymatini oladi; proxy bo'lmasa
# REMOTE_ADDR'ga qaytadi. Shu sabab barcha throttle bitta mantiqdan foydalanadi.


class IPThrottle(SimpleRateThrottle):
    scope = "ip"

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        if not ident:
            return None
        return f"throttle_ip_{ident}"


class DebugContainerThrottle(SimpleRateThrottle):
    scope = "debug_container"

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        if not ident:
            return None
        return f"throttle_debug_{ident}"


class ReleaseCreateThrottle(SimpleRateThrottle):
    scope = "release_create"

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            return f"throttle_release_{request.user.pk}"
        ident = self.get_ident(request)
        if not ident:
            return None
        return f"throttle_release_ip_{ident}"
