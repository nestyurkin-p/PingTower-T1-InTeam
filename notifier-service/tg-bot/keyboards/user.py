from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup


class UserKeyboards:
    """Inline keyboards intended for regular bot users."""

    # Placeholder for future user-facing keyboards.
    def empty(self) -> InlineKeyboardMarkup | None:
        return None


__all__ = ["UserKeyboards"]
