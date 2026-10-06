from shared.validation.record_types import a, aaaa, cname, mx, txt

# Registry — add a new record type here (+ its module) without touching
# request-creation logic or the UI's core rendering code.
RECORD_TYPE_VALIDATORS = {
    "A": a.validate,
    "AAAA": aaaa.validate,
    "CNAME": cname.validate,
    "TXT": txt.validate,
    "MX": mx.validate,
}

SUPPORTED_RECORD_TYPES = tuple(RECORD_TYPE_VALIDATORS.keys())


def validate_record_value(record_type: str, value: dict) -> dict:
    from shared.validation.common import ValidationError

    validator = RECORD_TYPE_VALIDATORS.get(record_type)
    if validator is None:
        raise ValidationError("record_type", f"Unsupported record type: {record_type}")
    return validator(value)
