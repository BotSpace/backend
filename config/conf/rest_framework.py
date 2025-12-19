from typing import Dict, Any

REST_FRAMEWORK: Dict[str, Any] = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework_simplejwt.authentication.JWTAuthentication",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "django_core.paginations.CustomPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_THROTTLE_RATES": {
        "ip": "1000/min",
        "debug_container": "1000/min",
        "user": "1000/min",
    },
}
