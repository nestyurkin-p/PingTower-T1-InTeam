from dataclasses import dataclass
from pathlib import Path

from environs import Env
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

env = Env()
# читаем .env из корня микросервиса notifier-service
env.read_env(path=str(Path(__file__).resolve().parents[1] / ".env"))


@dataclass
class TgBotConfig:
    token: str = env.str("TG_TOKEN", "")


@dataclass
class AppConfig:
    log_level: str = env.str("LOG_LEVEL", "INFO")


tg_bot = TgBotConfig()
app_cfg = AppConfig()

default = DefaultBotProperties(parse_mode="HTML")
bot: Bot = Bot(token=tg_bot.token, default=default)
dp: Dispatcher = Dispatcher()
