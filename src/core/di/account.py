from aiogram import Bot
from dishka import Provider, Scope, provide

from src.bot.services.account import AccountBotService
from src.userbot.services.auth import UserbotAuthService
from src.userbot.services.session import UserbotSessionService


class AccountProvider(Provider):
	@provide(scope=Scope.APP)
	def account_bot_service(
		self,
		sessions: UserbotSessionService,
		auth: UserbotAuthService,
		bot: Bot,
	) -> AccountBotService:
		return AccountBotService(sessions=sessions, auth=auth, bot=bot)
