import re

from shared.validation.common import ValidationError

_MAX_LEN = 2048
# Printable ASCII only (space 0x20 through tilde 0x7E) — rejects control
# characters, NUL bytes, newlines/tabs, and any non-ASCII input. Legitimate
# SPF/DKIM/DMARC values (=, +, /, :, ;, etc.) are all within this range;
# this only blocks injection-style payloads, not valid TXT content.
_PRINTABLE_ASCII_RE = re.compile(r"^[\x20-\x7E]*$")


def validate(value: dict) -> dict:
    text = str(value.get("text", ""))
    if not text:
        raise ValidationError("text", "TXT value is required")
    if len(text) > _MAX_LEN:
        raise ValidationError("text", f"TXT value exceeds {_MAX_LEN} characters")
    if not _PRINTABLE_ASCII_RE.match(text):
        raise ValidationError("text", "TXT value contains non-printable or non-ASCII characters")
    return {"text": text}
