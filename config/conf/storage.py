from config.env import env
from core.utils.storage import Storage

AWS_ACCESS_KEY_ID = env.str("STORAGE_ID")
AWS_SECRET_ACCESS_KEY = env.str("STORAGE_KEY")
AWS_S3_ENDPOINT_URL = env.str("STORAGE_URL")
AWS_S3_URL_PROTOCOL = env.str("STORAGE_PROTOCOL", "https:")
AWS_S3_FILE_OVERWRITE = False
# Backblaze B2 (and most non-AWS S3) need an explicit region + SigV4. Region comes
# from env (e.g. us-east-005); signature is always v4.
AWS_S3_REGION_NAME = env.str("STORAGE_REGION", "")
AWS_S3_SIGNATURE_VERSION = "s3v4"
# Custom domain only when explicitly set — otherwise S3Boto3Storage builds proper
# (presigned) URLs against the endpoint. Empty STORAGE_PATH => no custom domain.
_storage_custom_domain = env.str("STORAGE_PATH", "")
if _storage_custom_domain:
    AWS_S3_CUSTOM_DOMAIN = _storage_custom_domain

default_storage = Storage(env.str("STORAGE_DEFAULT"), "default")
static_storage = Storage(env.str("STORAGE_STATIC"), "static")

STORAGES = {
    "default": {
        "BACKEND": default_storage.get_backend(),
        "OPTIONS": default_storage.get_options(),
    },
    "staticfiles": {
        "BACKEND": static_storage.get_backend(),
        "OPTIONS": static_storage.get_options(),
    },
}
