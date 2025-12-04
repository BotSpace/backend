from config.settings.common import *  # noqa
from config.settings.common import ALLOWED_HOSTS, REST_FRAMEWORK

ALLOWED_HOSTS += []
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = [
    "core.throttle.ip_throttle.IPThrottle",
]
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
    "ip": "60/min",
    "debug_container": "15/min",
    "user": "60/min",
}
