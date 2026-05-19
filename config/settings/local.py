from config.settings.common import *  # noqa
from config.settings.common import ALLOWED_HOSTS, INSTALLED_APPS, REST_FRAMEWORK

INSTALLED_APPS += ["django_extensions"]

ALLOWED_HOSTS += ["127.0.0.1", "localhost", "192.168.100.26"]

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
