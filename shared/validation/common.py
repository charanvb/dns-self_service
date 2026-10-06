import re

_LABEL_RE = re.compile(r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$")


class ValidationError(Exception):
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


def validate_fqdn(fqdn: str, zone_name: str) -> None:
    fqdn = fqdn.rstrip(".")
    zone_name = zone_name.rstrip(".")
    if not fqdn:
        raise ValidationError("fqdn", "FQDN is required")
    if fqdn != zone_name and not fqdn.endswith("." + zone_name):
        raise ValidationError("fqdn", f"FQDN must be within the zone {zone_name}")
    if len(fqdn) > 253:
        raise ValidationError("fqdn", "FQDN exceeds 253 characters")
    for label in fqdn.split("."):
        if not _LABEL_RE.match(label):
            raise ValidationError("fqdn", f"Invalid DNS label: '{label}'")


def validate_ttl(ttl, min_ttl: int = 60, max_ttl: int = 86400) -> int:
    try:
        ttl_int = int(ttl)
    except (TypeError, ValueError):
        raise ValidationError("ttl", "TTL must be a whole number")
    if not (min_ttl <= ttl_int <= max_ttl):
        raise ValidationError("ttl", f"TTL must be between {min_ttl} and {max_ttl} seconds")
    return ttl_int
