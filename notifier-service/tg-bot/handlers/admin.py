from __future__ import annotations

from typing import Any, cast

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from core.config import settings
from database import DataBase, db as shared_db
from keyboards import AdminKeyboards

router = Router()

if shared_db is None:
    raise RuntimeError("Database connection is not configured")

database: DataBase = cast(DataBase, shared_db)
kb_factory = AdminKeyboards()
ADMIN_IDS = set(settings.telegram.admin_ids)
PAGE_SIZE = 5
PROMPT_TEXT = "Выберите команду для привязки:"


def _is_admin(user_id: int | None) -> bool:
    return user_id is not None and user_id in ADMIN_IDS


def _parse_number(value: str, default: int = 0) -> int:
    try:
        number = int(value)
        return number if number >= 0 else default
    except (TypeError, ValueError):
        return default


async def _fetch_teams() -> list[dict[str, Any]]:
    teams = await database.list_teams()
    return [{"id": team.id, "name": team.name} for team in teams]


async def _update_message(
    callback: CallbackQuery,
    text: str,
    markup: InlineKeyboardMarkup,
) -> None:
    message = callback.message
    if message is None:
        return
    try:
        if message.text == text:
            await message.edit_reply_markup(reply_markup=markup)
        else:
            await message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            await message.edit_reply_markup(reply_markup=markup)
        else:
            raise


@router.message(Command("link_group"))
async def cmd_link_group(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    if not _is_admin(user_id):
        await message.answer("Эта команда доступна только администраторам.")
        return

    teams = await _fetch_teams()
    if not teams:
        await message.answer("В системе пока нет команд для привязки.")
        return

    markup = kb_factory.teams_list(teams, page=0, per_page=PAGE_SIZE)
    await message.answer(PROMPT_TEXT, reply_markup=markup)


@router.callback_query(F.data.startswith("teams_page_"))
async def cb_teams_page(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id if callback.from_user else None
    if not _is_admin(user_id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    page = _parse_number(callback.data.removeprefix("teams_page_")) if callback.data else 0
    teams = await _fetch_teams()
    if not teams:
        if callback.message:
            await callback.message.edit_text("В системе пока нет команд для привязки.")
        await callback.answer()
        return

    markup = kb_factory.teams_list(teams, page=page, per_page=PAGE_SIZE)
    await _update_message(callback, PROMPT_TEXT, markup)
    await callback.answer()


@router.callback_query(F.data.startswith("choose_team_"))
async def cb_choose_team(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id if callback.from_user else None
    if not _is_admin(user_id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    team_id = _parse_number(callback.data.removeprefix("choose_team_")) if callback.data else 0
    team = await database.get_team(team_id)
    if team is None:
        await callback.answer("Команда не найдена", show_alert=True)
        return

    markup = kb_factory.confirm_team(team.name, team.id)
    text = f"Привязать чат к \"{team.name}\"?"
    await _update_message(callback, text, markup)
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_team_"))
async def cb_confirm_team(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id if callback.from_user else None
    if not _is_admin(user_id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    if callback.message is None or callback.message.chat is None:
        await callback.answer("Не удалось определить чат", show_alert=True)
        return

    team_id = _parse_number(callback.data.removeprefix("confirm_team_")) if callback.data else 0
    team = await database.get_team(team_id)
    if team is None:
        await callback.answer("Команда не найдена", show_alert=True)
        return

    updated = await database.set_team_tg_chat(team.id, callback.message.chat.id)
    if not updated:
        await callback.answer("Не удалось привязать чат", show_alert=True)
        return

    await callback.answer("Готово")
    await callback.message.edit_text(f"Группа привязана к команде {team.name} ✅")
