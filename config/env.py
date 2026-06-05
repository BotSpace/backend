"""
Default value for environ variable
"""

import os

import environ

environ.Env.read_env(os.path.join(".env"))

env = environ.Env(
    DEBUG=(bool, False),
    CACHE_TIME=(int, 180),
    OTP_EXPIRE_TIME=(int, 2),
    VITE_LIVE=(bool, False),
    ALLOWED_HOSTS=(str, "localhost"),
    CSRF_TRUSTED_ORIGINS=(str, "localhost"),
    CORS_ALLOWED_ORIGINS=(str, ""),
    DJANGO_SETTINGS_MODULE=(str, "config.settings.local"),
    CACHE_TIMEOUT=(int, 120),
    CACHE_ENABLED=(bool, False),
    VITE_PORT=(int, 5173),
    VITE_HOST=(str, "vite"),
    NGROK_AUTHTOKEN=(str, ""),
    BOT_TOKEN=(str, ""),
    OTP_MODULE="core.services.otp",
    OTP_SERVICE="EskizService",
    PROJECT_ENV=(str, "prod"),
    SILK_ENABLED=(bool, False),
    PAYME_ID=(str, ""),
    PAYME_KEY=(str, ""),
    PAYTECH_API_KEY=(str, ""),
    INTERNAL_API_TOKEN=(str, ""),
    OAUTH_ISSUER=(str, "https://api.botspace.uz"),
    OAUTH_AUTHORIZE_PAGE=(str, "https://botspace.uz/oauth/authorize"),
    RUNNING_BOT_LIMIT=(int, 10),
)
