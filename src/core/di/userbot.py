from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide

from src.config import cfg
from src.core.crypto import SessionCipher
from src.core.db.uow import UowFactory
from src.core.scheduling import Wakeup
from src.userbot.services.auth import UserbotAuthService
from src.userbot.services.emoji_status import AccountEmojiStatusService
from src.userbot.services.session import UserbotSessionService


class UserbotProvider(Provider):
	@provide(scope=Scope.APP)
	def session_cipher(self) -> SessionCipher:
		return SessionCipher(cfg.security.session_key)

	@provide(scope=Scope.APP)
	def wakeup(self) -> Wakeup:
		# Один будильник на приложение: сейчас его слушает только планировщик
		# эмодзи. Появится второе правило со своим планировщиком — сделать
		# Wakeup широковещательным.
		return Wakeup()

	@provide(scope=Scope.APP)
	async def userbot_sessions(
		self, uow_factory: UowFactory, cipher: SessionCipher, wakeup: Wakeup
	) -> AsyncIterator[UserbotSessionService]:
		sessions = UserbotSessionService(
			uow_factory=uow_factory, cipher=cipher, wakeup=wakeup
		)
		try:
			yield sessions
		finally:
			await sessions.close()

	@provide(scope=Scope.APP)
	async def userbot_auth(
		self, sessions: UserbotSessionService
	) -> AsyncIterator[UserbotAuthService]:
		auth = UserbotAuthService(sessions=sessions)
		try:
			yield auth
		finally:
			await auth.cancel()

	@provide(scope=Scope.APP)
	def account_emoji_status_service(
		self, sessions: UserbotSessionService
	) -> AccountEmojiStatusService:
		return AccountEmojiStatusService(sessions)
