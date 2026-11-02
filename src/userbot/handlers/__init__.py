from telethon import TelegramClient

from src.userbot.handlers.animations import UserbotAnimationHandlers
from src.userbot.handlers.chat_actions import UserbotChatActionHandlers
from src.userbot.handlers.commands import UserbotCommandHandlers


class UserbotRouter:
	"""Аналог корневого aiogram-роутера: вешает все обработчики событий
	аккаунта на клиент. Подключается через `sessions.add_client_listener`,
	поэтому срабатывает и на клиент, появившийся после входа через бота."""

	def __init__(
		self,
		commands: UserbotCommandHandlers,
		animations: UserbotAnimationHandlers,
		chat_actions: UserbotChatActionHandlers,
	) -> None:
		self.handlers = (commands, animations, chat_actions)

	async def attach(self, client: TelegramClient) -> None:
		for handlers in self.handlers:
			await handlers.attach(client)


__all__ = [
	"UserbotAnimationHandlers",
	"UserbotChatActionHandlers",
	"UserbotCommandHandlers",
	"UserbotRouter",
]
