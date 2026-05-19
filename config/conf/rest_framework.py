from typing import Dict, Any

REST_FRAMEWORK: Dict[str, Any] = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework_simplejwt.authentication.JWTAuthentication",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "django_core.paginations.CustomPagination",
    "PAGE_SIZE": 10,
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
