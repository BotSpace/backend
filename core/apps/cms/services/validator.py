"""Document validation against a collection schema.

Validation is configuration-driven: each Field has a `validators` JSON blob
that may carry `regex`, `min`, `max`, `min_length`, `max_length`, `choices`,
`array_kind`. The dispatcher below maps each `FieldKind` to a coercer that
returns the canonical Python value or raises ValueError.
"""

from __future__ import annotations

import datetime as dt
import re
import uuid
from typing import Any, Callable
from urllib.parse import urlparse

from core.apps.cms.enums import FieldKind


EMAIL_RE = re.compile(r"^[\w.+\-]+@[\w\-]+\.[\w.\-]+$")
PHONE_RE = re.compile(r"^\+?[0-9]{7,15}$")


class ValidationError(Exception):
    """Aggregated errors raised by `validate_document`. `errors` is per-field."""

    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("Validation failed")
        self.errors = errors


# ── per-kind coercers ───────────────────────────────────────────────────────


def _as_text(value: Any) -> str:
    if value is None:
        raise ValueError("value is null")
    return str(value)


def _as_int(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("expected integer, got bool")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value.strip())
    raise ValueError("expected integer")


def _as_float(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("expected number, got bool")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            pass
    raise ValueError("expected number")


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "1", "yes", "y", "on"}:
            return True
        if v in {"false", "0", "no", "n", "off", ""}:
            return False
    raise ValueError("expected boolean")


def _as_datetime(value: Any) -> dt.datetime:
    if isinstance(value, dt.datetime):
        return value
    if isinstance(value, dt.date):
        return dt.datetime(value.year, value.month, value.day)
    if isinstance(value, (int, float)):
        return dt.datetime.utcfromtimestamp(value)
    if isinstance(value, str):
        v = value.strip().replace("Z", "+00:00")
        try:
            return dt.datetime.fromisoformat(v)
        except ValueError:
            pass
    raise ValueError("expected ISO-8601 datetime")


def _as_date(value: Any) -> dt.datetime:
    # BSON has no date-only type and PyMongo cannot encode datetime.date, so a
    # date is stored as a midnight datetime (datetime is a subclass of date).
    dttm = _as_datetime(value)
    return dt.datetime(dttm.year, dttm.month, dttm.day)


def _as_email(value: Any) -> str:
    s = _as_text(value).strip().lower()
    if not EMAIL_RE.match(s):
        raise ValueError("invalid email")
    return s


def _as_url(value: Any) -> str:
    s = _as_text(value).strip()
    p = urlparse(s)
    if p.scheme not in {"http", "https"} or not p.netloc:
        raise ValueError("invalid URL")
    return s


def _as_phone(value: Any) -> str:
    s = re.sub(r"[\s\-()]", "", _as_text(value).strip())
    if not PHONE_RE.match(s):
        raise ValueError("invalid phone")
    return s


def _as_json(value: Any) -> Any:
    if isinstance(value, (dict, list, str, int, float, bool)) or value is None:
        return value
    raise ValueError("expected JSON-serializable value")


def _as_uuid(value: Any) -> str:
    s = _as_text(value).strip()
    try:
        return str(uuid.UUID(s))
    except Exception as exc:
        raise ValueError("invalid uuid") from exc


def _as_geo(value: Any) -> dict[str, float]:
    if isinstance(value, dict) and {"lat", "lng"} <= value.keys():
        lat, lng = float(value["lat"]), float(value["lng"])
    elif isinstance(value, (list, tuple)) and len(value) == 2:
        lat, lng = float(value[0]), float(value[1])
    elif isinstance(value, str) and "," in value:
        a, b = value.split(",", 1)
        lat, lng = float(a), float(b)
    else:
        raise ValueError("expected geo as {lat,lng} or 'lat,lng'")
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        raise ValueError("geo out of range")
    return {"lat": lat, "lng": lng}


COERCERS: dict[str, Callable[[Any], Any]] = {
    FieldKind.TEXT: _as_text,
    FieldKind.LONGTEXT: _as_text,
    FieldKind.INT: _as_int,
    FieldKind.FLOAT: _as_float,
    FieldKind.BOOL: _as_bool,
    FieldKind.DATETIME: _as_datetime,
    FieldKind.DATE: _as_date,
    FieldKind.EMAIL: _as_email,
    FieldKind.URL: _as_url,
    FieldKind.PHONE: _as_phone,
    FieldKind.JSON: _as_json,
    FieldKind.RELATION: _as_text,
    FieldKind.GEO: _as_geo,
    FieldKind.FILE: _as_uuid,
    FieldKind.IMAGE: _as_uuid,
    FieldKind.AUDIO: _as_uuid,
    FieldKind.VIDEO: _as_uuid,
}

# Legacy synonym — agentlar yoki eski client'lar `kind="number"` yuborishi
# mumkin. FieldKind enum'da rasman yo'q, lekin string kalit sifatida int
# sifatida talqin qilamiz.
COERCERS["number"] = _as_int


def _check_extra_validators(kind: str, value: Any, rules: dict[str, Any]) -> None:
    """Common validators applied after coercion."""
    if kind in {FieldKind.TEXT, FieldKind.LONGTEXT, FieldKind.EMAIL, FieldKind.URL, FieldKind.PHONE}:
        s = str(value)
        if "min_length" in rules and len(s) < int(rules["min_length"]):
            raise ValueError(f"min_length={rules['min_length']}")
        if "max_length" in rules and len(s) > int(rules["max_length"]):
            raise ValueError(f"max_length={rules['max_length']}")
        if "regex" in rules:
            if not re.search(str(rules["regex"]), s):
                raise ValueError("regex mismatch")
    if kind in {FieldKind.INT, FieldKind.FLOAT}:
        # Defensiv: agar value coerce'dan keyin ham number bo'lmasa (masalan
        # COERCERS sxemasi noto'g'ri ishlagan bo'lsa), TypeError chiqarmasdan
        # tinch o'tib ketamiz — boshqa joyda aniqroq xato qaytadi.
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "min" in rules and value < rules["min"]:
                raise ValueError(f"min={rules['min']}")
            if "max" in rules and value > rules["max"]:
                raise ValueError(f"max={rules['max']}")
    if "choices" in rules and rules["choices"]:
        if value not in rules["choices"]:
            raise ValueError(f"must be one of {rules['choices']}")


def coerce_field(kind: str, value: Any, rules: dict[str, Any] | None = None) -> Any:
    rules = rules or {}
    if kind == FieldKind.ENUM:
        s = _as_text(value)
        choices = rules.get("choices") or []
        if choices and s not in choices:
            raise ValueError(f"must be one of {choices}")
        return s
    if kind == FieldKind.ARRAY:
        if not isinstance(value, list):
            raise ValueError("expected array")
        elem_kind = rules.get("array_kind") or FieldKind.TEXT
        return [coerce_field(elem_kind, v) for v in value]
    coercer = COERCERS.get(kind, _as_text)
    coerced = coercer(value)
    _check_extra_validators(kind, coerced, rules)
    return coerced


def validate_document(
    fields: list[dict[str, Any]],
    document: dict[str, Any],
    *,
    partial: bool = False,
) -> dict[str, Any]:
    """Run validation. `fields` items shape: {name, kind, required, default, validators}."""
    errors: dict[str, str] = {}
    out: dict[str, Any] = {}
    known: set[str] = set()
    for f in fields:
        name = f["name"]
        kind = f["kind"]
        rules = f.get("validators") or {}
        known.add(name)
        if name in document:
            try:
                out[name] = coerce_field(kind, document[name], rules)
            except ValueError as exc:
                errors[name] = str(exc)
        elif not partial:
            if f.get("required"):
                if f.get("default") is not None:
                    try:
                        out[name] = coerce_field(kind, f["default"], rules)
                    except ValueError as exc:
                        errors[name] = str(exc)
                else:
                    errors[name] = "required"
            elif f.get("default") is not None:
                try:
                    out[name] = coerce_field(kind, f["default"], rules)
                except ValueError as exc:
                    errors[name] = str(exc)

    # Pass-through fields that are not in the schema but provided by callers
    # (e.g. telegram_id), to keep ingestion flexible.
    for k, v in document.items():
        if k not in known and not k.startswith("_"):
            out[k] = v

    if errors:
        raise ValidationError(errors)
    return out
