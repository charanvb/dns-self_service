import re

_LABEL_RE = re.compile(r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$")
_LABEL_ALLOW_UNDERSCORE_RE = re.compile(r"^(?!-)[A-Za-z0-9-_]{1,63}(?<!-)$")


class ValidationError(Exception):
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


def validate_fqdn(
    fqdn: str,
    zone_name: str,
    record_type: str | None = None,
    allow_underscore: bool | None = None,
) -> None:
    fqdn = fqdn.rstrip(".")
    zone_name = zone_name.rstrip(".")
    if not fqdn:
        raise ValidationError("fqdn", "FQDN is required")
    if fqdn != zone_name and not fqdn.endswith("." + zone_name):
        raise ValidationError("fqdn", f"FQDN must be within the zone {zone_name}")
    if len(fqdn) > 253:
        raise ValidationError("fqdn", "FQDN exceeds 253 characters")

    if allow_underscore is None:
        # Underscores are standard in DNS labels for TXT (DKIM, DMARC) and CNAME records
        allow_underscore = record_type in ("TXT", "CNAME")

    label_re = _LABEL_ALLOW_UNDERSCORE_RE if allow_underscore else _LABEL_RE
    for label in fqdn.split("."):
        if not label_re.match(label):
            raise ValidationError("fqdn", f"Invalid DNS label: '{label}'")


def validate_ttl(ttl, min_ttl: int = 60, max_ttl: int = 86400) -> int:
    try:
        ttl_int = int(ttl)
    except (TypeError, ValueError):
        raise ValidationError("ttl", "TTL must be a whole number")
    if not (min_ttl <= ttl_int <= max_ttl):
        raise ValidationError("ttl", f"TTL must be between {min_ttl} and {max_ttl} seconds")
    return ttl_int
