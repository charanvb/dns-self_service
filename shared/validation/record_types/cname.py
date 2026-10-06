import re

from shared.validation.common import ValidationError

_HOSTNAME_RE = re.compile(r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*\.?$")


def validate(value: dict) -> dict:
    target = str(value.get("target", "")).strip()
    if not target:
        raise ValidationError("target", "Target is required")
    if not _HOSTNAME_RE.match(target):
        raise ValidationError("target", f"'{target}' is not a valid DNS name")
    return {"target": target}
