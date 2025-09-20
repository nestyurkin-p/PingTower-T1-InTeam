from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import AliasChoices, BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


class TelegramSettings(BaseModel):
    token: str = Field(default="", validation_alias=AliasChoices("TELEGRAM__TOKEN", "TG_TOKEN"))
    admin_ids: List[int] = Field(default_factory=list, validation_alias=AliasChoices("TELEGRAM__ADMIN_IDS", "ADMIN_TG_IDS"))

    @field_validator("admin_ids", mode="before")
    @classmethod
    def _parse_admin_ids(cls, value: object) -> List[int]:
        if value in (None, "", []):
            return []
        if isinstance(value, str):
            parts = [part.strip() for part in value.replace(";", ",").split(",")]
            return [int(part) for part in parts if part]
        if isinstance(value, (list, tuple, set)):
            result: List[int] = []
            for item in value:
                if item is None or item == "":
                    continue
                result.append(int(item))
            return result
        raise TypeError("ADMIN_TG_IDS must be a comma separated string or list of ints")


class RabbitSettings(BaseModel):
    url: str = Field(default="", validation_alias=AliasChoices("RABBIT__URL", "RABBIT_URL"))
    alert_exchange: str = Field(default="pinger.events", validation_alias=AliasChoices("RABBIT__ALERT_EXCHANGE", "ALERT_EXCHANGE"))
    alert_routing_key: str = Field(default="#", validation_alias=AliasChoices("RABBIT__ALERT_ROUTING_KEY", "ALERT_ROUTING_KEY"))
    pinger_exchange: str = Field(default="pinger.events", validation_alias=AliasChoices("RABBIT__PINGER_EXCHANGE", "PINGER_EXCHANGE"))
    pinger_queue: str = Field(default="pinger-to-backend-queue", validation_alias=AliasChoices("RABBIT__PINGER_QUEUE", "PINGER_QUEUE"))
    pinger_routing_key: str = Field(default="pinger.group", validation_alias=AliasChoices("RABBIT__PINGER_ROUTING_KEY", "PINGER_ROUTING_KEY"))
    llm_exchange: str = Field(default="llm.events", validation_alias=AliasChoices("RABBIT__LLM_EXCHANGE", "LLM_EXCHANGE"))
    llm_queue: str = Field(default="llm-to-backend-queue", validation_alias=AliasChoices("RABBIT__LLM_QUEUE", "LLM_QUEUE"))
    llm_routing_key: str = Field(default="llm.group", validation_alias=AliasChoices("RABBIT__LLM_ROUTING_KEY", "LLM_ROUTING_KEY"))


class BackendSettings(BaseModel):
    host: str = Field(default="0.0.0.0", validation_alias=AliasChoices("BACKEND__HOST", "APP_HOST"))
    port: int = Field(default=8000, validation_alias=AliasChoices("BACKEND__PORT", "APP_PORT"))


class DatabaseSettings(BaseModel):
    main_url: str = Field(
        default="",
        validation_alias=AliasChoices("DATABASE__URL", "DATABASE_URL"),
    )


class PingerSettings(BaseModel):
    interval_sec: int = Field(default=5, validation_alias=AliasChoices("PINGER__INTERVAL_SEC", "INTERVAL"))
    input_database_url: str = Field(
        default="",
        validation_alias=AliasChoices("PINGER__INPUT_DATABASE_URL", "INPUT_DATABASE_URL"),
    )


class DispatcherSettings(BaseModel):
    grouping_window_sec: int = Field(
        default=60,
        validation_alias=AliasChoices("DISPATCHER__GROUPING_WINDOW_SEC", "GROUPING_WINDOW_GLOBAL_SEC"),
    )
    autocreate_sites: bool = Field(
        default=False,
        validation_alias=AliasChoices("DISPATCHER__AUTOCREATE_SITES", "NOTIFIER_AUTOCREATE_SITES"),
    )


class EmailSettings(BaseModel):
    host: str = Field(default="", validation_alias=AliasChoices("EMAIL__HOST", "SMTP_HOST"))
    port: int = Field(default=587, validation_alias=AliasChoices("EMAIL__PORT", "SMTP_PORT"))
    user: str = Field(default="", validation_alias=AliasChoices("EMAIL__USER", "SMTP_USER"))
    password: str = Field(default="", validation_alias=AliasChoices("EMAIL__PASSWORD", "SMTP_PASSWORD"))
    tls: bool = Field(default=True, validation_alias=AliasChoices("EMAIL__TLS", "SMTP_TLS"))
    ssl: bool = Field(default=False, validation_alias=AliasChoices("EMAIL__SSL", "SMTP_SSL"))
    from_addr: str = Field(default="PingTower <alerts@localhost>", validation_alias=AliasChoices("EMAIL__FROM", "SMTP_FROM"))
    timeout: int = Field(default=10, validation_alias=AliasChoices("EMAIL__TIMEOUT", "SMTP_TIMEOUT"))


class LLMSettings(BaseModel):
    api_key: str = Field(default="", validation_alias=AliasChoices("LLM__API_KEY", "OPENAI_API_KEY"))
    model: str = Field(default="gpt-4o-mini", validation_alias=AliasChoices("LLM__MODEL", "OPENAI_MODEL"))
    base_url: str = Field(
        default="https://api.proxyapi.ru/openai/v1",
        validation_alias=AliasChoices("LLM__BASE_URL", "OPENAI_BASE_URL"),
    )
    use_skip_notification: bool = Field(
        default=False,
        validation_alias=AliasChoices("LLM__USE_SKIP_NOTIFICATION", "USE_SKIP_NOTIFICATION"),
    )


class RedisSettings(BaseModel):
    host: str = Field(default="localhost", validation_alias=AliasChoices("REDIS__HOST", "REDIS_HOST"))
    port: int = Field(default=6379, validation_alias=AliasChoices("REDIS__PORT", "REDIS_PORT"))
    db: int = Field(default=0, validation_alias=AliasChoices("REDIS__DB", "REDIS_DB"))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="allow",
    )

    log_level: str = Field(default="INFO", validation_alias=AliasChoices("CORE__LOG_LEVEL", "LOG_LEVEL"))

    telegram: TelegramSettings = TelegramSettings()
    rabbit: RabbitSettings = RabbitSettings()
    backend: BackendSettings = BackendSettings()
    database: DatabaseSettings = DatabaseSettings()
    pinger: PingerSettings = PingerSettings()
    dispatcher: DispatcherSettings = DispatcherSettings()
    email: EmailSettings = EmailSettings()
    llm: LLMSettings = LLMSettings()
    redis: RedisSettings = RedisSettings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

__all__ = ["Settings", "settings", "get_settings"]
