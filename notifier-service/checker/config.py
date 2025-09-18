from dataclasses import dataclass
from pathlib import Path
from environs import Env

env = Env()
# .env лежит в корне микросервиса notifier-service
env.read_env(path=str(Path(__file__).resolve().parents[1] / ".env"))


@dataclass
class RabbitCfg:
    url: str = env.str("RABBIT_URL", "amqp://root:toor@localhost:5672/")
    alert_exchange: str = env.str("ALERT_EXCHANGE", "pinger.events")
    alert_rk: str = env.str("ALERT_ROUTING_KEY", "#")


@dataclass
class AppCfg:
    log_level: str = env.str("LOG_LEVEL", "INFO")


@dataclass
class TgCfg:
    token: str = env.str("TG_TOKEN", "")


rabbit_cfg = RabbitCfg()
app_cfg = AppCfg()
tg_cfg = TgCfg()
