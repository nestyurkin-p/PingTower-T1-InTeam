from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List
from urllib.parse import quote

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


class TelegramSettings(BaseModel):
    token: str = ""
    admin_ids: List[int] = Field(default_factory=list)

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
        if isinstance(value, int):
            return [value]
        raise TypeError("ADMIN_IDS must be a comma separated string or list of ints")

class RabbitSettings(BaseModel):
    url: str = ""
    host: str = "rabbitmq"
    port: int = 5672
    user: str = ""
    password: str = ""
    vhost: str = "/"
    alert_exchange: str = "pinger.events"
    alert_routing_key: str = "#"
    pinger_exchange: str = "pinger.events"
    pinger_queue: str = "pinger-to-backend-queue"
    pinger_routing_key: str = "pinger.group"
    llm_exchange: str = "llm.events"
    llm_queue: str = "llm-to-backend-queue"
    llm_routing_key: str = "llm.group"

    @model_validator(mode="after")
    def _ensure_url(self) -> RabbitSettings:  # type: ignore[override]
        if self.url:
            return self
        user = quote(self.user, safe="") if self.user else ""
        password = quote(self.password, safe="") if self.password else ""
        credentials = ""
        if user:
            credentials = user
            if password:
                credentials += f":{password}"
            credentials += "@"
        host = (self.host or "localhost").strip() or "localhost"
        port = f":{self.port}" if self.port else ""
        vhost = (self.vhost or "/").lstrip("/")
        path = f"/{vhost}" if vhost else "/"
        url = f"amqp://{credentials}{host}{port}{path}"
        object.__setattr__(self, "url", url)
        return self


class BackendSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000


class DatabaseSettings(BaseModel):
    main_url: str = ""


class ClickhouseSettings(BaseModel):
    host: str = ""
    port: int = 8123
    user: str = "default"
    password: str = ""
    database: str = "monitor"
    table: str = "site_logs"

    @property
    def enabled(self) -> bool:
        return bool(self.host)


class PingerSettings(BaseModel):
    interval_sec: int = 5
    input_database_url: str = ""
    notify_always: bool = False


class DispatcherSettings(BaseModel):
    grouping_window_sec: int = 60
    autocreate_sites: bool = False


class EmailSettings(BaseModel):
    host: str = ""
    port: int = 587
    user: str = ""
    password: str = ""
    tls: bool = True
    ssl: bool = False
    from_addr: str = "PingTower <alerts@localhost>"
    timeout: int = 10


class LLMSettings(BaseModel):
    api_key: str = ""
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.proxyapi.ru/openai/v1"
    use_skip_notification: bool = False


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="allow",
    )

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # legacy flat aliases
    legacy_bot_token: str = Field(default="", alias="BOT_TOKEN", exclude=True)
    legacy_admin_ids: str = Field(default="", alias="ADMIN_IDS", exclude=True)
    legacy_rabbit_host: str = Field(default="", alias="RABBIT_HOST", exclude=True)
    legacy_rabbit_port: str = Field(default="", alias="RABBIT_PORT", exclude=True)
    legacy_rabbit_user: str = Field(default="", alias="RABBIT_USER", exclude=True)
    legacy_rabbit_password: str = Field(default="", alias="RABBIT_PASSWORD", exclude=True)
    legacy_rabbit_vhost: str = Field(default="", alias="RABBIT_VHOST", exclude=True)
    legacy_database_url: str = Field(default="", alias="DATABASE_URL", exclude=True)
    legacy_input_database_url: str = Field(default="", alias="INPUT_DATABASE_URL", exclude=True)
    legacy_notify_always: str | bool = Field(default="", alias="NOTIFY_ALWAYS", exclude=True)
    legacy_clickhouse_host: str = Field(default="", alias="CLICKHOUSE_HOST", exclude=True)
    legacy_clickhouse_port: int | str = Field(default=0, alias="CLICKHOUSE_PORT", exclude=True)
    legacy_clickhouse_user: str = Field(default="", alias="CLICKHOUSE_USER", exclude=True)
    legacy_clickhouse_password: str = Field(default="", alias="CLICKHOUSE_PASSWORD", exclude=True)
    legacy_clickhouse_db: str = Field(default="", alias="CLICKHOUSE_DB", exclude=True)
    legacy_clickhouse_table: str = Field(default="", alias="CLICKHOUSE_TABLE", exclude=True)

    telegram: TelegramSettings = TelegramSettings()
    rabbit: RabbitSettings = RabbitSettings()
    backend: BackendSettings = BackendSettings()
    database: DatabaseSettings = DatabaseSettings()
    pinger: PingerSettings = PingerSettings()
    dispatcher: DispatcherSettings = DispatcherSettings()
    email: EmailSettings = EmailSettings()
    llm: LLMSettings = LLMSettings()
    clickhouse: ClickhouseSettings = ClickhouseSettings()

    @model_validator(mode="after")
    def _apply_legacy_fields(self) -> Settings:  # type: ignore[override]
        telegram_updates: dict[str, object] = {}
        if self.legacy_bot_token and not self.telegram.token:
            telegram_updates["token"] = self.legacy_bot_token
        if self.legacy_admin_ids and not self.telegram.admin_ids:
            telegram_updates["admin_ids"] = self.legacy_admin_ids
        if telegram_updates:
            payload = self.telegram.model_dump()
            payload.update(telegram_updates)
            object.__setattr__(self, "telegram", TelegramSettings.model_validate(payload))

        rabbit_updates: dict[str, object] = {}
        if self.legacy_rabbit_host:
            rabbit_updates["host"] = self.legacy_rabbit_host
            rabbit_updates["url"] = ""
        if self.legacy_rabbit_port:
            rabbit_updates["port"] = self.legacy_rabbit_port
        if self.legacy_rabbit_user:
            rabbit_updates["user"] = self.legacy_rabbit_user
        if self.legacy_rabbit_password:
            rabbit_updates["password"] = self.legacy_rabbit_password
        if self.legacy_rabbit_vhost:
            rabbit_updates["vhost"] = self.legacy_rabbit_vhost
        if rabbit_updates:
            payload = self.rabbit.model_dump()
            payload.update(rabbit_updates)
            object.__setattr__(self, "rabbit", RabbitSettings.model_validate(payload))

        database_updates: dict[str, object] = {}
        if self.legacy_database_url and not self.database.main_url:
            database_updates["main_url"] = self.legacy_database_url
        if database_updates:
            payload = self.database.model_dump()
            payload.update(database_updates)
            object.__setattr__(self, "database", DatabaseSettings.model_validate(payload))

        pinger_updates: dict[str, object] = {}
        if self.legacy_input_database_url and not self.pinger.input_database_url:
            pinger_updates["input_database_url"] = self.legacy_input_database_url

        legacy_notify = self.legacy_notify_always
        if isinstance(legacy_notify, str) and legacy_notify != "":
            try:
                legacy_notify_bool = bool(int(legacy_notify))
            except ValueError:
                legacy_notify_bool = legacy_notify.lower() in {"true", "1", "yes"}
        else:
            legacy_notify_bool = bool(legacy_notify)
        if legacy_notify_bool:
            pinger_updates["notify_always"] = legacy_notify_bool

        if pinger_updates:
            payload = self.pinger.model_dump()
            payload.update(pinger_updates)
            object.__setattr__(self, "pinger", PingerSettings.model_validate(payload))

        clickhouse_updates: dict[str, object] = {}
        if self.legacy_clickhouse_host:
            clickhouse_updates["host"] = self.legacy_clickhouse_host
        if self.legacy_clickhouse_port:
            try:
                clickhouse_updates["port"] = int(self.legacy_clickhouse_port)
            except (TypeError, ValueError):
                pass
        if self.legacy_clickhouse_user:
            clickhouse_updates["user"] = self.legacy_clickhouse_user
        if self.legacy_clickhouse_password:
            clickhouse_updates["password"] = self.legacy_clickhouse_password
        if self.legacy_clickhouse_db:
            clickhouse_updates["database"] = self.legacy_clickhouse_db
        if self.legacy_clickhouse_table:
            clickhouse_updates["table"] = self.legacy_clickhouse_table
        if clickhouse_updates:
            payload = self.clickhouse.model_dump()
            payload.update(clickhouse_updates)
            object.__setattr__(self, "clickhouse", ClickhouseSettings.model_validate(payload))

        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

__all__ = ["Settings", "settings", "get_settings"]
