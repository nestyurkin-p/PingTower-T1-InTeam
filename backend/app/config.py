from dataclasses import dataclass
from pathlib import Path
from environs import Env
from database import db  # ensure package import (and DATABASE_URL used inside)

env = Env()
env.read_env(path=str(Path(__file__).resolve().parents[1] / ".env"))

@dataclass
class AppConfig:
    host: str = env.str("APP_HOST", "0.0.0.0")
    port: int = env.int("APP_PORT", 8000)
    log_level: str = env.str("LOG_LEVEL", "INFO")

@dataclass
class RabbitCfg:
    url: str = env.str("RABBIT_URL", "amqp://root:toor@localhost:5672/")
    pinger_exchange: str = env.str("PINGER_EXCHANGE", "pinger.events")
    llm_exchange: str = env.str("LLM_EXCHANGE", "llm.events")
    pinger_queue: str = env.str("PINGER_QUEUE", "pinger-to-backend-queue")
    pinger_rk: str = env.str("PINGER_ROUTING_KEY", "pinger.group")
    llm_queue: str = env.str("LLM_QUEUE", "llm-to-backend-queue")
    llm_rk: str = env.str("LLM_ROUTING_KEY", "llm.group")

app_cfg = AppConfig()
rabbit_cfg = RabbitCfg()
