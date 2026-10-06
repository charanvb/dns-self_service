from shared.validation.common import ValidationError

_MAX_LEN = 2048


def validate(value: dict) -> dict:
    text = str(value.get("text", ""))
    if not text:
        raise ValidationError("text", "TXT value is required")
    if len(text) > _MAX_LEN:
        raise ValidationError("text", f"TXT value exceeds {_MAX_LEN} characters")
    return {"text": text}
