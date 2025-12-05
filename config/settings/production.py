from config.settings.common import *  # noqa
from config.settings.common import ALLOWED_HOSTS, REST_FRAMEWORK

ALLOWED_HOSTS += []
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = [
    "rest_framework.throttling.UserRateThrottle",
    "rest_framework.throttling.AnonRateThrottle",
]
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
    "ip": "60/min",
    "debug_container": "15/min",
    "user": "60/min",
    "anon": "60/min",
}
