import ipaddress

from shared.validation.common import ValidationError


def validate(value: dict) -> dict:
    ipv4 = str(value.get("ipv4", "")).strip()
    try:
        ipaddress.IPv4Address(ipv4)
    except ValueError:
        raise ValidationError("ipv4", f"'{ipv4}' is not a valid IPv4 address")
    return {"ipv4": ipv4}
