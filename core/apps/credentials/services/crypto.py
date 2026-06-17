"""Fernet-based encrypt/decrypt for credential data.

Key resolution priority:
1. settings.CREDENTIALS_FERNET_KEY  (base64url-encoded 32-byte key)
2. Derived: base64url(sha256(settings.SECRET_KEY))

Never log decrypted data.
"""
from __future__ import annotations

import base64
import hashlib
import json

from cryptography.fernet import Fernet
from django.conf import settings


def _get_fernet() -> Fernet:
    key = getattr(settings, "CREDENTIALS_FERNET_KEY", None)
    if key:
        raw = key.encode() if isinstance(key, str) else key
    else:
        digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        raw = base64.urlsafe_b64encode(digest)
    return Fernet(raw)


def encrypt(data: dict) -> str:
    """Encrypt a dict to a Fernet token string."""
    payload = json.dumps(data, ensure_ascii=False).encode()
    return _get_fernet().encrypt(payload).decode()


def decrypt(token: str) -> dict:
    """Decrypt a Fernet token string to a dict."""
    raw = _get_fernet().decrypt(token.encode())
    return json.loads(raw)
