from __future__ import annotations

from leadgis.enrichment.messengers import build_telegram_url, build_whatsapp_url


def test_build_whatsapp_url_without_message() -> None:
    assert build_whatsapp_url("+79991234567") == "https://wa.me/79991234567"


def test_build_whatsapp_url_with_message() -> None:
    url = build_whatsapp_url("+79991234567", "Привет!")
    assert url is not None
    assert url.startswith("https://wa.me/79991234567?text=")


def test_build_whatsapp_url_none_phone() -> None:
    assert build_whatsapp_url(None) is None


def test_build_telegram_url_from_handle() -> None:
    assert build_telegram_url("@studio") == "https://t.me/studio"


def test_build_telegram_url_from_bare_username() -> None:
    assert build_telegram_url("studio") == "https://t.me/studio"


def test_build_telegram_url_passthrough_link() -> None:
    assert build_telegram_url("https://t.me/studio") == "https://t.me/studio"


def test_build_telegram_url_none() -> None:
    assert build_telegram_url(None) is None
