import re

from shared.validation.common import ValidationError

# Valid DNS hostname labels (Letters-Digits-Hyphens-Underscores) — allows underscores
# for DKIM selectors, Azure domain verification (_asuid), and cloud targets.
# Hard-caps input length BEFORE regex matching to avoid pathological-length inputs.
_HOSTNAME_RE = re.compile(r"^(?!-)[A-Za-z0-9-_]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-_]{1,63}(?<!-))*\.?$")
_MAX_HOSTNAME_LEN = 253


def validate(value: dict) -> dict:
    target = str(value.get("target", "")).strip()
    if not target:
        raise ValidationError("target", "Target is required")
    if len(target) > _MAX_HOSTNAME_LEN:
        raise ValidationError("target", f"Target exceeds {_MAX_HOSTNAME_LEN} characters")
    if not _HOSTNAME_RE.match(target):
        raise ValidationError("target", f"'{target}' is not a valid DNS name")
    return {"target": target}
