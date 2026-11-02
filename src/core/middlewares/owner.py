from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from src.core.logger import get_struct_logger

log = get_struct_logger()


class OwnerOnlyMiddleware(BaseMiddleware):
	"""Бот управляет одним аккаунтом — апдейты от всех, кроме владельца,
	молча отбрасываются, чтобы посторонние даже не узнали, что бот живой."""

	def __init__(self, owner_id: int) -> None:
		self.owner_id = owner_id

	async def __call__(
		self,
		handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
		event: TelegramObject,
		data: dict[str, Any],
	) -> Any:
		user: User | None = data.get("event_from_user")
		if user is None or user.id != self.owner_id:
			log.warning(
				"bot.foreign_update_dropped",
				user_id=user.id if user else None,
				username=user.username if user else None,
			)
			return None
		return await handler(event, data)
