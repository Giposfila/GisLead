"""Phone normalization to E.164 (AGENT.md §5)."""

from __future__ import annotations

import phonenumbers


def normalize_phone(raw: str, default_region: str = "RU") -> str | None:
    """Parse a free-form phone string to E.164, mapping a leading 8 to +7 for RU/KZ."""
    if not raw or not raw.strip():
        return None

    candidate = raw.strip()
    digits = "".join(ch for ch in candidate if ch.isdigit() or ch == "+")
    if default_region in ("RU", "KZ") and digits.startswith("8") and len(digits) == 11:
        digits = "+7" + digits[1:]

    try:
        parsed = phonenumbers.parse(digits, default_region)
    except phonenumbers.NumberParseException:
        return None

    if not phonenumbers.is_valid_number(parsed):
        return None

    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
