"""Application configuration: ~/.leadgis/config.toml + env overrides."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import tomli_w
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from leadgis.constants import (
    DEFAULT_LLM_CONCURRENCY_CLOUD,
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OPENAI_COMPAT_MODEL,
    DEFAULT_TWOGIS_RPS,
    DEFAULT_WEBSITE_CHECK_CONCURRENCY,
)

LEADGIS_HOME = Path.home() / ".leadgis"
CONFIG_PATH = LEADGIS_HOME / "config.toml"
DB_PATH = LEADGIS_HOME / "leadgis.db"


class AppSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    open_browser: bool = True
    auth_token: str = ""


class ScraperSettings(BaseModel):
    enabled: bool = False
    max_orgs: int = 200


class SourceSettings(BaseModel):
    active: str = "twogis_api"
    twogis_api_key: str = ""
    scraper: ScraperSettings = Field(default_factory=ScraperSettings)


class LLMSettings(BaseModel):
    provider: str = "openai_compat"
    base_url: str = DEFAULT_OLLAMA_BASE_URL
    api_key: str = ""
    model: str = DEFAULT_OPENAI_COMPAT_MODEL
    concurrency: int = DEFAULT_LLM_CONCURRENCY_CLOUD


class LimitsSettings(BaseModel):
    twogis_rps: int = DEFAULT_TWOGIS_RPS
    website_check_concurrency: int = DEFAULT_WEBSITE_CHECK_CONCURRENCY


class OutreachSettings(BaseModel):
    user_offer: str = ""
    extra_instructions: str = ""
    template: str = "outreach_ru.md"


def _toml_source(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("rb") as fh:
        return tomllib.load(fh)


class Settings(BaseSettings):
    """Runtime settings, layered: defaults < config.toml < env vars."""

    model_config = SettingsConfigDict(
        env_prefix="LEADGIS_",
        env_nested_delimiter="__",
    )

    app: AppSettings = Field(default_factory=AppSettings)
    source: SourceSettings = Field(default_factory=SourceSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    limits: LimitsSettings = Field(default_factory=LimitsSettings)
    outreach: OutreachSettings = Field(default_factory=OutreachSettings)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            _ConfigTomlSource(settings_cls),
        )


class _ConfigTomlSource(PydanticBaseSettingsSource):
    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        raise NotImplementedError

    def __call__(self) -> dict[str, Any]:
        return _toml_source(CONFIG_PATH)


def ensure_config_file() -> Path:
    """Create ~/.leadgis/config.toml with defaults on first run (chmod 600)."""
    LEADGIS_HOME.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        defaults = Settings().model_dump(mode="json")
        CONFIG_PATH.write_bytes(tomli_w.dumps(defaults).encode("utf-8"))
        CONFIG_PATH.chmod(0o600)
    return CONFIG_PATH


def load_settings() -> Settings:
    ensure_config_file()
    return Settings()


def save_settings(settings: Settings) -> None:
    LEADGIS_HOME.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_bytes(tomli_w.dumps(settings.model_dump(mode="json")).encode("utf-8"))
    CONFIG_PATH.chmod(0o600)
