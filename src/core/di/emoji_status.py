from aiogram import Bot
from dishka import Provider, Scope, provide

from src.bot.services.emoji_status import EmojiStatusBotService
from src.core.db.uow import UowFactory
from src.core.scheduling import Wakeup
from src.runtime.emoji_rotation import EmojiRotationScheduler
from src.services.emoji_rotation import EmojiRotationService
from src.userbot.services.emoji_status import AccountEmojiStatusService
from src.userbot.services.session import UserbotSessionService


class EmojiStatusProvider(Provider):
	@provide(scope=Scope.APP)
	def emoji_rotation_service(
		self,
		uow_factory: UowFactory,
		account_status: AccountEmojiStatusService,
		wakeup: Wakeup,
	) -> EmojiRotationService:
		return EmojiRotationService(
			uow_factory=uow_factory,
			account_status=account_status,
			wakeup=wakeup,
		)

	@provide(scope=Scope.APP)
	def emoji_status_bot_service(
		self, rotation: EmojiRotationService, bot: Bot
	) -> EmojiStatusBotService:
		return EmojiStatusBotService(rotation=rotation, bot=bot)

	@provide(scope=Scope.APP)
	def emoji_rotation_scheduler(
		self,
		rotation: EmojiRotationService,
		sessions: UserbotSessionService,
		wakeup: Wakeup,
		bot: Bot,
	) -> EmojiRotationScheduler:
		return EmojiRotationScheduler(
			rotation=rotation, sessions=sessions, wakeup=wakeup, bot=bot
		)
