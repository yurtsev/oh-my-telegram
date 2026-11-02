from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dishka import AsyncContainer
from dishka.integrations.aiogram import setup_dishka

from src.bot.handlers import router
from src.config import cfg
from src.core.exc import aiogram_error_handler
from src.core.logger import get_struct_logger
from src.core.middlewares import OwnerOnlyMiddleware

log = get_struct_logger()


class AiogramRuntime:
	def __init__(self, bot: Bot, container: AsyncContainer) -> None:
		self.bot = bot
		self.container = container

	def create_dispatcher(self) -> Dispatcher:
		dp = Dispatcher(storage=MemoryStorage())
		dp.update.outer_middleware(OwnerOnlyMiddleware(cfg.bot.owner_id))
		dp.include_router(router)
		dp.errors.register(aiogram_error_handler)
		setup_dishka(self.container, dp, auto_inject=True)
		return dp

	async def run(self) -> None:
		dp = self.create_dispatcher()
		await self.bot.delete_webhook(drop_pending_updates=True)
		log.info("aiogram.polling_started", owner_id=cfg.bot.owner_id)
		# Сигналы ловит run_async_entrypoint и отменяет главную задачу —
		# свои обработчики aiogram ставить не должен.
		await dp.start_polling(self.bot, handle_signals=False)
