import logging
from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from lexicon import LEXICON
from utils import subscriptions

router: Router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def cmd_start(message: Message):
    await subscriptions.add(message.chat.id)
    await message.answer(LEXICON["start"])

    logger.info(f"User {message.from_user.id} {message.from_user.username} subscribed to notifications")


@router.message(Command("stop"))
async def cmd_stop(message: Message):
    await subscriptions.remove(message.chat.id)
    await message.answer(LEXICON["stop"])

    logger.info(f"User {message.from_user.id} {message.from_user.username} unsubscribed to notifications")


@router.message(Command("ping"))
async def cmd_ping(message: Message):
    await message.answer(LEXICON["ping"])
