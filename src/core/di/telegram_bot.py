from collections.abc import AsyncIterator

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dishka import Provider, Scope, provide

from src.config import cfg


class TelegramBotProvider(Provider):
	@provide(scope=Scope.APP)
	async def bot(self) -> AsyncIterator[Bot]:
		bot = Bot(
			cfg.bot.token,
			default=DefaultBotProperties(
				parse_mode=ParseMode.HTML,
				link_preview_is_disabled=True,
			),
		)
		try:
			yield bot
		finally:
			await bot.session.close()
