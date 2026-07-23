"""WhatsApp / Telegram link builders (AGENT.md §7.2)."""

from __future__ import annotations

from urllib.parse import quote


def build_whatsapp_url(phone_e164: str | None, message: str | None = None) -> str | None:
    if not phone_e164:
        return None
    digits = phone_e164.removeprefix("+")
    url = f"https://wa.me/{digits}"
    if message:
        url += f"?text={quote(message)}"
    return url


def build_telegram_url(username_or_link: str | None) -> str | None:
    if not username_or_link:
        return None
    value = username_or_link.strip()
    if value.startswith(("https://t.me/", "http://t.me/")):
        return value
    handle = value.removeprefix("@")
    return f"https://t.me/{handle}"
