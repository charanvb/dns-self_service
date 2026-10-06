import ipaddress

from shared.validation.common import ValidationError


def validate(value: dict) -> dict:
    ipv6 = str(value.get("ipv6", "")).strip()
    try:
        ipaddress.IPv6Address(ipv6)
    except ValueError:
        raise ValidationError("ipv6", f"'{ipv6}' is not a valid IPv6 address")
    return {"ipv6": ipv6}
