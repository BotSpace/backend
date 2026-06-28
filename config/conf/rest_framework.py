from typing import Dict, Any

REST_FRAMEWORK: Dict[str, Any] = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        # Tried first so X-Internal-Token + X-User-Id from the agent
        # short-circuits before JWT parsing. Falls through silently on
        # missing/wrong internal token so regular Bearer JWT auth still works.
        "core.apps.shared.authentication.InternalTokenAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "django_core.paginations.CustomPagination",
    "EXCEPTION_HANDLER": "core.apps.shared.exceptions.custom_exception_handler",
    "PAGE_SIZE": 10,
    # Bizning yagona ishonchli proxy — host nginx (api.botspace.uz oldida).
    # u X-Forwarded-For oxiriga real client IP'sini qo'shadi. NUM_PROXIES=1
    # bilan DRF get_ident() XFF'ning ENG O'NGdagi (nginx qo'ygan, spoof
    # qilib bo'lmaydigan) qiymatini oladi — chap tomon client-spoofable.
    # Busiz throttle REMOTE_ADDR (k8s SNAT'langan ichki node IP)'da edi →
    # barcha foydalanuvchi bitta bucket'da.
    "NUM_PROXIES": 1,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "ip": "300/min",
        "anon": "60/min",
        "user": "300/min",
        "debug_container": "10/min",
        "release_create": "10/min",
        "otp": "5/min",
        "register": "10/hour",
        "reset_password": "5/hour",
    },
}
