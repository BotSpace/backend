from django.utils.translation import gettext_lazy as _

from core.apps.cms_legacy.enums.cms import FieldType


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
        elif field.type == FieldType.RELATION.value:
            # Validate relation field - value should be a valid ObjectId string or dict with _id
            if value is not None:
                if isinstance(value, dict):
                    if "_id" not in value:
                        errors[field.name] = [_("Relation field must contain _id")]
                elif not isinstance(value, str):
                    errors[field.name] = [_("Relation field must be string ObjectId or object with _id")]
            continue
    return errors, len(errors) == 0
