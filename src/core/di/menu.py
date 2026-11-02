from aiogram import Bot
from dishka import Provider, Scope, provide

from src.bot.services.menu import MenuBotService


class MenuProvider(Provider):
	@provide(scope=Scope.APP)
	def menu_bot_service(self, bot: Bot) -> MenuBotService:
		return MenuBotService(bot)
