from typing import cast

from aiogram import F, Router
from aiogram.types import Message

from database import DataBase, db  # общий модуль БД из корня проекта

router = Router()

if db is None:
    raise RuntimeError("Database is not configured")


database: DataBase = cast(DataBase, db)


@router.message(F.text == "/start")
async def cmd_start(message: Message) -> None:
    await database.upsert_user_tg_chat(
        user_id=message.from_user.id,
        chat_id=message.chat.id,
        login=message.from_user.username,
    )
    await message.answer("Вы подписаны на уведомления в этом чате.")


@router.message(F.text == "/stop")
async def cmd_stop(message: Message) -> None:
    await database.disable_user_tg(message.from_user.id)
    await message.answer("Telegram-уведомления отключены.")


@router.message(F.text == "/ping")
async def cmd_ping(message: Message) -> None:
    await message.answer("pong")
