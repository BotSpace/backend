import json
import re

from rest_framework import serializers

REQUIRED_ENV_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
RESERVED_KEYS = {"RELEASE_BOT_TOKEN"}


def validate_required_envs(value):
    """Validate required_envs list.

    Accepts either a Python list (already parsed) or a JSON string
    (multipart/form-data sends JSON fields as strings).

    Returns the parsed list.
    """
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise serializers.ValidationError("required_envs yaroqli JSON bo'lishi kerak.") from exc

    if not isinstance(value, list):
        raise serializers.ValidationError("required_envs ro'yxat (array) bo'lishi kerak.")

    seen_keys = set()
    errors = []
    for i, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"[{i}]: har bir element dict bo'lishi kerak.")
            continue
        key = item.get("key", "")
        if not key:
            errors.append(f"[{i}]: 'key' maydoni majburiy.")
            continue
        if not REQUIRED_ENV_KEY_RE.match(key):
            errors.append(
                f"[{i}]: key '{key}' noto'g'ri format (^[A-Z][A-Z0-9_]{{0,63}}$)."
            )
        if key in RESERVED_KEYS:
            errors.append(f"[{i}]: '{key}' taqiqlangan — u doim alohida so'raladi.")
        if key in seen_keys:
            errors.append(f"[{i}]: '{key}' takrorlanmoqda — keylar unique bo'lishi shart.")
        seen_keys.add(key)

    if errors:
        raise serializers.ValidationError(errors)

    return value
