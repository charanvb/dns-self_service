from shared.validation.common import ValidationError
from shared.validation.record_types.cname import _HOSTNAME_RE


def validate(value: dict) -> dict:
    target = str(value.get("target", "")).strip()
    if not target:
        raise ValidationError("target", "Mail server target is required")
    if not _HOSTNAME_RE.match(target):
        raise ValidationError("target", f"'{target}' is not a valid DNS name")

    try:
        priority = int(value.get("priority"))
    except (TypeError, ValueError):
        raise ValidationError("priority", "Priority must be a whole number")
    if not (0 <= priority <= 65535):
        raise ValidationError("priority", "Priority must be between 0 and 65535")

    return {"priority": priority, "target": target}
