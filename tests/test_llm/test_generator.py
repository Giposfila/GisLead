from __future__ import annotations

from leadgis.generation.generator import parse_template, render_template


def test_parse_template_splits_system_and_user_sections() -> None:
    text = "# system\nYou are helpful.\n\n# user\nHello {name}\n"
    system, user = parse_template(text)
    assert system == "You are helpful."
    assert user == "Hello {name}"


def test_parse_template_raises_without_sections() -> None:
    import pytest

    with pytest.raises(ValueError, match="system.*user"):
        parse_template("just some text")


def test_render_template_fills_known_placeholders() -> None:
    result = render_template("Hi {name} from {city}", {"name": "Аня", "city": "Москва"})
    assert result == "Hi Аня from Москва"


def test_render_template_missing_key_becomes_empty_string() -> None:
    result = render_template("Hi {name}, extra: {missing}", {"name": "Аня"})
    assert result == "Hi Аня, extra: "


def test_default_ru_template_is_valid() -> None:
    from pathlib import Path

    from leadgis.generation.generator import PROMPTS_DIR

    text = (PROMPTS_DIR / "outreach_ru.md").read_text()
    system, user = parse_template(text)
    assert system
    assert user
    assert Path(PROMPTS_DIR / "outreach_en.md").exists()
