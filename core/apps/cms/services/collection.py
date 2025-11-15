from django.utils.translation import gettext_lazy as _

from core.apps.cms.enums.cms import FieldType


def is_int(s: str) -> bool:
    if s is None:
        return True
    try:
        int(s)
        return True
    except ValueError:
        return False


def is_bool(x) -> bool:
    """
    Args:
        x (any): turi nomalum malumot

    Returns:
        bool
    """
    if x is None:
        return True
    if isinstance(x, bool):
        return True
    if type(x) in [int, float]:
        return False
    return x.lower() in ["true", "false", "1", "0", "yes", "no"]


def collection_validate_data(collection, data):
    errors = {}
    for field in collection.fields.all():
        name = field.name
        value = data.get(name, None)
        if field.required and value is None:
            if field.default is None:
                errors[field.name] = [_("Field is required")]
                continue
            else:
                data[name] = field.default
                value = data[name]
        if field.type == FieldType.BOOL.value and not is_bool(value):
            errors[field.name] = [_("Field is not bool")]
            continue
        elif field.type == FieldType.NUMBER.value and not is_int(value):
            errors[field.name] = [_("Field is not number")]
            continue
        elif field.type == FieldType.TEXT.value and not isinstance(value, str) and value is not None:
            errors[field.name] = [_("Field is not string")]
            continue
        elif field.type == FieldType.DATETIME.value:
            continue
    return errors, len(errors) == 0
