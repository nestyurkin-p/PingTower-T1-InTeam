import logging
import os

from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from environs import Env
from redis.asyncio import Redis


# ---------------------- CONFIG ---------------------- #

@dataclass
class TgBotConfig:
    token: str


@dataclass
class RabbitConfig:
    url: str
    exchange: str
    routing_key: str
    queue: str
    prefetch: int


@dataclass
class RedisConfig:
    host: str
    port: int
    db: int


@dataclass
class Settings:
    tg_bot: TgBotConfig
    rabbit: RabbitConfig
    redis: RedisConfig
    log_level: str = "INFO"


def _load_settings() -> Settings:
    env = Env()
    env.read_env(path=str(Path(__file__).resolve().parents[2] / ".env"))

    tg = TgBotConfig(
        token=env.str("TG_TOKEN", ""),
    )

    rabbit = RabbitConfig(
        url=env.str("RABBIT_URL", "amqp://root:toor@rabbitmq:5672/"),
        exchange=env.str("RABBIT_EXCHANGE", "pinger.events"),
        routing_key=env.str("RABBIT_ROUTING_KEY", "#"),
        queue=env.str("RABBIT_QUEUE", "pinger-to-notifier-queue"),
        prefetch=env.int("RABBIT_PREFETCH", 16),
    )

    redis = RedisConfig(
        host=env.str("REDIS_HOST", "localhost"),
        port=env.int("REDIS_PORT", 6379),
        db=env.int("REDIS_DB", 0),
    )

    return Settings(
        tg_bot=tg,
        rabbit=rabbit,
        redis=redis,
        log_level=env.str("LOG_LEVEL", "INFO"),
    )


def setup_logging(level: str = "INFO"):
    log_dir = Path(os.getenv("LOG_DIR", Path(__file__).resolve().parents[1] / "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "notifier.log"

    logger = logging.getLogger()
    logger.handlers.clear()  # чтобы не плодить дубли при повторных вызовах
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    fh = RotatingFileHandler(log_file, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8", delay=True)
    fh.setFormatter(fmt)
    logger.addHandler(fh)


# ---------------------- SINGLETONS ---------------------- #

config: Settings = _load_settings()

default = DefaultBotProperties(parse_mode="HTML")
bot: Bot = Bot(token=config.tg_bot.token, default=default)

redis: Redis = Redis(host=config.redis.host, port=config.redis.port, db=config.redis.db)
storage: RedisStorage = RedisStorage(redis=redis)
dp: Dispatcher = Dispatcher(storage=storage)

# Shared constants
SUBSCRIPTIONS_KEY = "notifier:subs"  # Redis set of chat_ids
