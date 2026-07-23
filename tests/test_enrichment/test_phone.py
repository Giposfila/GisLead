from __future__ import annotations

import pytest

from leadgis.enrichment.phone import normalize_phone


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("+7 999 123-45-67", "+79991234567"),
        ("8 (999) 123-45-67", "+79991234567"),
        ("89991234567", "+79991234567"),
        ("79991234567", "+79991234567"),
        ("+79991234567", "+79991234567"),
        ("9991234567", "+79991234567"),
        ("+7 701 234 56 78", "+77012345678"),
    ],
)
def test_normalize_phone_valid_numbers(raw: str, expected: str) -> None:
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "not a phone", "123", "0000000000"])
def test_normalize_phone_invalid_input_returns_none(raw: str) -> None:
    assert normalize_phone(raw) is None


def test_normalize_phone_respects_default_region() -> None:
    assert normalize_phone("701 234 56 78", default_region="KZ") == "+77012345678"


def test_normalize_phone_leading_eight_maps_to_plus_seven() -> None:
    assert normalize_phone("89991112233") == "+79991112233"
