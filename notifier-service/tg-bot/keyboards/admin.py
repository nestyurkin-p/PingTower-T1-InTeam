from __future__ import annotations

from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class AdminKeyboards:
    """Inline keyboards used by administrators."""

    def teams_list(
        self,
        teams: list[dict[str, Any]],
        page: int = 0,
        per_page: int = 5,
    ) -> InlineKeyboardMarkup:
        """Render a paginated list of teams."""
        if per_page <= 0:
            per_page = 5
        total = len(teams)
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(0, min(page, total_pages - 1))

        start = page * per_page
        end = start + per_page
        visible = teams[start:end]

        builder = InlineKeyboardBuilder()
        for item in visible:
            team_id = int(item["id"])
            name = self._prepare_label(str(item.get("name", "")))
            builder.button(text=name, callback_data=f"choose_team_{team_id}")

        builder.adjust(1)

        if total_pages > 1:
            nav_buttons: list[InlineKeyboardButton] = []
            if page > 0:
                nav_buttons.append(
                    InlineKeyboardButton(text="⬅ Назад", callback_data=f"teams_page_{page - 1}")
                )
            if page < total_pages - 1:
                nav_buttons.append(
                    InlineKeyboardButton(text="Вперёд ➡", callback_data=f"teams_page_{page + 1}")
                )
            if nav_buttons:
                builder.row(*nav_buttons)

        return builder.as_markup()

    def confirm_team(self, team_name: str, team_id: int) -> InlineKeyboardMarkup:
        """Render confirmation buttons for linking a chat to a team."""
        builder = InlineKeyboardBuilder()
        prefix = "✅ Привязать чат к "
        team_label = self._prepare_label(team_name, limit=max(1, 64 - len(prefix)))
        builder.button(
            text=f"{prefix}{team_label}",
            callback_data=f"confirm_team_{team_id}",
        )
        builder.button(text="↩ Назад", callback_data="teams_page_0")
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def _prepare_label(label: str, *, limit: int = 64) -> str:
        text = label.strip()
        if not text:
            text = "Без названия"
        if len(text) <= limit:
            return text
        truncated = text[: max(0, limit - 3)].rstrip()
        if not truncated:
            truncated = text[: limit]
        return f"{truncated}..."


__all__ = ["AdminKeyboards"]
