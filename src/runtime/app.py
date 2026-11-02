"""Единственный процесс: бот-пульт (aiogram) + юзербот (Telethon) + фоновые
правила. Аккаунт один и нагрузка мизерная, поэтому всё в одном event loop:
кнопка «Следующий» вызывает тот же сервис, что и планировщик, без очередей
между процессами."""

import asyncio

from aiogram import Bot

from src.bot.services.account import AccountBotService
from src.runtime.aiogram import AiogramRuntime
from src.runtime.bootstrap import run_async_entrypoint
from src.runtime.containers import make_app_container
from src.runtime.emoji_rotation import EmojiRotationScheduler
from src.userbot.handlers import UserbotRouter
from src.userbot.services.mute import ChatMuteService
from src.userbot.services.session import UserbotSessionService


async def main() -> None:
	container = make_app_container()
	try:
		bot = await container.get(Bot)
		sessions = await container.get(UserbotSessionService)
		await (await container.get(ChatMuteService)).load()
		# Обработчики команд вешаются на каждый новый клиент аккаунта,
		# поэтому подписка — до restore().
		userbot_router = await container.get(UserbotRouter)
		sessions.add_client_listener(userbot_router.attach)
		# Без подключённого аккаунта приложение всё равно стартует —
		# иначе было бы не через что войти (вход идёт через самого бота).
		if not await sessions.restore():
			account = await container.get(AccountBotService)
			await account.notify_not_connected()
		rotation_scheduler = await container.get(EmojiRotationScheduler)
		async with asyncio.TaskGroup() as tg:
			tg.create_task(rotation_scheduler.run())
			tg.create_task(AiogramRuntime(bot, container).run())
	finally:
		await container.close()


def run() -> None:
	run_async_entrypoint(main, process_name="app")


if __name__ == "__main__":
	run()
